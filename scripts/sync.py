#!/usr/bin/env python3
"""
scripts/sync_spotify_to_turso.py
─────────────────────────────────
Pipeline de collecte quotidienne : Spotify API → Turso Cloud (libSQL).

Exécuté par GitHub Actions tous les jours à 06h00 UTC.
Peut aussi être lancé manuellement :
    python scripts/sync_spotify_to_turso.py

Variables d'environnement requises (GitHub Secrets / .env local) :
    SPOTIFY_CLIENT_ID
    SPOTIFY_CLIENT_SECRET
    TURSO_DATABASE_URL
    TURSO_AUTH_TOKEN
    ARTIST_SPOTIFY_ID       (ex: 0T4d2alRNWD29IME6Yb142 pour KITO)

Variable optionnelle :
    FORCE_UPSERT=true       pour écraser un enregistrement existant du jour
"""

import os
import sys
import logging
from datetime import date, datetime, timezone

# ── Chargement .env local (ignoré en CI où les secrets sont injectés) ─────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optionnel en CI

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import libsql_experimental as libsql   # libsql-experimental sur PyPI

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sync")


# ── Config depuis l'environnement ─────────────────────────────────────────────
def require_env(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        log.error("Variable d'environnement manquante : %s", key)
        sys.exit(1)
    return val


SPOTIFY_CLIENT_ID     = require_env("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = require_env("SPOTIFY_CLIENT_SECRET")
TURSO_DATABASE_URL    = require_env("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN      = require_env("TURSO_AUTH_TOKEN")
ARTIST_SPOTIFY_ID     = require_env("ARTIST_SPOTIFY_ID")
FORCE_UPSERT          = os.getenv("FORCE_UPSERT", "false").lower() == "true"
TODAY                 = date.today().isoformat()


# ── Initialisation du schéma DB ───────────────────────────────────────────────
DDL = """
CREATE TABLE IF NOT EXISTS historique_artistes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    date_enregistrement DATE    NOT NULL,
    artiste_name        TEXT    NOT NULL,
    spotify_id          TEXT    NOT NULL,
    followers_count     INTEGER NOT NULL,
    popularity_score    INTEGER NOT NULL,
    streams_real        INTEGER NOT NULL DEFAULT 0,
    UNIQUE (spotify_id, date_enregistrement)
)
"""

DDL_MIGRATION = """
ALTER TABLE historique_artistes
ADD COLUMN streams_real INTEGER NOT NULL DEFAULT 0
"""


def get_turso_conn():
    """Ouvre une connexion Turso Cloud via libsql-experimental."""
    log.info("Connexion à Turso Cloud : %s", TURSO_DATABASE_URL)
    return libsql.connect(TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)


def ensure_schema(conn) -> None:
    """Crée la table si absente, applique les migrations silencieusement."""
    cur = conn.cursor()
    cur.execute(DDL)
    try:
        cur.execute(DDL_MIGRATION)
        log.info("Migration appliquée : colonne streams_real ajoutée")
    except Exception:
        pass  # colonne déjà présente
    conn.commit()
    log.info("Schéma vérifié")


# ── Collecte Spotify ──────────────────────────────────────────────────────────

def get_spotify_data(spotify_id: str) -> dict:
    """
    Récupère followers et popularité depuis l'API Spotify.
    Retourne un dict avec les métriques ou lève une exception.
    """
    log.info("Connexion à l'API Spotify…")
    sp = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
        )
    )
    log.info("Récupération de l'artiste Spotify ID : %s", spotify_id)
    data = sp.artist(spotify_id)

    result = {
        "artiste_name":    data["name"],
        "spotify_id":      data["id"],
        "followers_count": data["followers"]["total"],
        "popularity_score": data["popularity"],
    }
    log.info(
        "Données récupérées → %s | Followers : %d | Popularité : %d/100",
        result["artiste_name"],
        result["followers_count"],
        result["popularity_score"],
    )
    return result


# ── Upsert Turso ─────────────────────────────────────────────────────────────

def already_synced_today(conn, spotify_id: str) -> bool:
    """Vérifie si un enregistrement existe déjà pour aujourd'hui."""
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM historique_artistes WHERE spotify_id = ? AND date_enregistrement = ?",
        (spotify_id, TODAY),
    )
    return cur.fetchone()[0] > 0


def upsert_record(conn, data: dict) -> str:
    """
    INSERT OR REPLACE pour insérer ou écraser le snapshot du jour.
    Retourne 'inserted' ou 'replaced' selon l'action effectuée.
    """
    already = already_synced_today(conn, data["spotify_id"])

    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO historique_artistes
            (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real)
        VALUES
            (?, ?, ?, ?, ?, COALESCE(
                (SELECT streams_real FROM historique_artistes
                 WHERE spotify_id = ? AND date_enregistrement = ?),
                0
            ))
        """,
        (
            TODAY,
            data["artiste_name"],
            data["spotify_id"],
            data["followers_count"],
            data["popularity_score"],
            # params pour le sous-SELECT qui récupère streams_real existant
            data["spotify_id"],
            TODAY,
        ),
    )
    conn.commit()
    action = "replaced" if already else "inserted"
    log.info("Enregistrement %s → date=%s artist=%s", action, TODAY, data["artiste_name"])
    return action


# ── Point d'entrée ────────────────────────────────────────────────────────────

def main() -> None:
    start = datetime.now(tz=timezone.utc)
    log.info("═══ Démarrage sync Spotify → Turso [%s] ═══", TODAY)

    # 1. Connexion et schéma
    conn = get_turso_conn()
    ensure_schema(conn)

    # 2. Vérification doublons (sauf si FORCE_UPSERT)
    if already_synced_today(conn, ARTIST_SPOTIFY_ID) and not FORCE_UPSERT:
        log.info(
            "Enregistrement du %s déjà présent pour %s. "
            "Utiliser FORCE_UPSERT=true pour écraser.",
            TODAY, ARTIST_SPOTIFY_ID,
        )
        conn.close()
        sys.exit(0)

    # 3. Collecte Spotify
    try:
        spotify_data = get_spotify_data(ARTIST_SPOTIFY_ID)
    except Exception as exc:
        log.error("Échec de la collecte Spotify : %s", exc)
        conn.close()
        sys.exit(1)

    # 4. Upsert Turso
    try:
        action = upsert_record(conn, spotify_data)
    except Exception as exc:
        log.error("Échec de l'écriture Turso : %s", exc)
        conn.close()
        sys.exit(1)

    conn.close()

    elapsed = (datetime.now(tz=timezone.utc) - start).total_seconds()
    log.info("═══ Sync terminée en %.2fs [action=%s] ═══", elapsed, action)


if __name__ == "__main__":
    main()
