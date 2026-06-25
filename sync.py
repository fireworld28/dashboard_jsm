#!/usr/bin/env python3
"""
scripts/sync.py
Pipeline de collecte quotidienne : Spotify API → Turso Cloud.
Utilise libsql-client (SDK HTTP officiel, pur Python, zéro Rust).
"""

import os
import sys
import asyncio
import logging
from datetime import date, datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import libsql_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("sync")


def require_env(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        log.critical("Variable manquante : %s", key)
        sys.exit(1)
    return val


SPOTIFY_CLIENT_ID     = require_env("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = require_env("SPOTIFY_CLIENT_SECRET")
TURSO_URL             = require_env("TURSO_DATABASE_URL")
TURSO_TOKEN           = require_env("TURSO_AUTH_TOKEN")
ARTIST_SPOTIFY_ID     = require_env("ARTIST_SPOTIFY_ID")
FORCE_UPSERT          = os.getenv("FORCE_UPSERT", "false").lower() == "true"
TODAY                 = date.today().isoformat()

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


async def sync():
    start = datetime.now(tz=timezone.utc)
    log.info("═══ Sync Spotify → Turso [%s] ═══", TODAY)

    # 1. Spotify
    log.info("Connexion Spotify…")
    try:
        sp   = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
        ))
        data = sp.artist(ARTIST_SPOTIFY_ID)
    except Exception as exc:
        log.error("Échec Spotify : %s", exc)
        sys.exit(1)

    name       = data.get("name", "INCONNU").upper()
    followers  = data.get("followers", {}).get("total", 0)
    popularity = data.get("popularity", 0)
    log.info("%s | followers=%d | popularité=%d", name, followers, popularity)

    # 2. Turso
    log.info("Connexion Turso Cloud…")
    async with libsql_client.create_client(url=TURSO_URL, auth_token=TURSO_TOKEN) as client:
        # Schéma
        await client.execute(DDL)
        try:
            await client.execute(
                "ALTER TABLE historique_artistes ADD COLUMN streams_real INTEGER NOT NULL DEFAULT 0"
            )
        except Exception:
            pass

        # Vérif doublon
        check = await client.execute(
            "SELECT COUNT(*) FROM historique_artistes WHERE spotify_id = ? AND date_enregistrement = ?",
            [ARTIST_SPOTIFY_ID, TODAY],
        )
        already = check.rows[0][0] > 0

        if already and not FORCE_UPSERT:
            log.info("Déjà synchronisé aujourd'hui. Utiliser FORCE_UPSERT=true pour écraser.")
            return

        # Upsert
        await client.execute(
            """
            INSERT OR REPLACE INTO historique_artistes
                (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score)
            VALUES (?, ?, ?, ?, ?)
            """,
            [TODAY, name, ARTIST_SPOTIFY_ID, followers, popularity],
        )
        action = "replaced" if already else "inserted"
        log.info("Turso OK [%s] — %s", action, TODAY)

    elapsed = (datetime.now(tz=timezone.utc) - start).total_seconds()
    log.info("═══ Terminé en %.2fs ═══", elapsed)


if __name__ == "__main__":
    asyncio.run(sync())
