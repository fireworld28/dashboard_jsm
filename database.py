# database.py
"""
Couche d'accès aux données — Turso Cloud (libSQL).

Stratégie de cache :
  get_db()                  → @st.cache_resource  : connexion unique par session
  get_artist_history_full() → @st.cache_data(ttl=3600) : 1 seul appel DB par artiste/heure
  filter_history()          → filtrage en mémoire, zéro appel réseau
"""

import os
import libsql_experimental as libsql
import pandas as pd
import streamlit as st

TURSO_URL   = st.secrets.get("TURSO_DATABASE_URL") or os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = st.secrets.get("TURSO_AUTH_TOKEN")   or os.getenv("TURSO_AUTH_TOKEN")


# ── Connexion ────────────────────────────────────────────────────────────────

@st.cache_resource
def get_db():
    """Connexion unique et persistante à Turso Cloud pour toute la session."""
    if not TURSO_URL or not TURSO_TOKEN:
        st.error("⚠️ Identifiants Turso introuvables — vérifie secrets.toml ou les variables d'env.")
        raise ValueError("TURSO_DATABASE_URL / TURSO_AUTH_TOKEN manquants.")
    return libsql.connect(TURSO_URL, auth_token=TURSO_TOKEN)


# ── Schéma ───────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Crée la table si absente et applique les migrations silencieusement."""
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute("""
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
    """)
    try:
        cursor.execute(
            "ALTER TABLE historique_artistes ADD COLUMN streams_real INTEGER NOT NULL DEFAULT 0"
        )
    except Exception:
        pass  # colonne déjà présente
    conn.commit()


# ── Historique ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_artist_history_full(spotify_id: str) -> pd.DataFrame:
    """
    Charge tout l'historique d'un artiste en une seule requête.
    Mis en cache 1 heure — filter_history() filtre ensuite en mémoire.
    """
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT date_enregistrement,
               followers_count,
               popularity_score,
               COALESCE(streams_real, 0) AS streams_real
        FROM   historique_artistes
        WHERE  spotify_id = ?
        ORDER  BY date_enregistrement ASC
        """,
        (spotify_id,),
    )
    cols = [d[0] for d in cursor.description]
    df   = pd.DataFrame(cursor.fetchall(), columns=cols)
    if not df.empty:
        df["date_enregistrement"] = pd.to_datetime(df["date_enregistrement"])
    return df


def filter_history(df: pd.DataFrame, date_from, date_to) -> pd.DataFrame:
    """Filtre en mémoire — aucun appel réseau supplémentaire."""
    if df.empty:
        return df
    mask = (
        (df["date_enregistrement"] >= pd.Timestamp(date_from)) &
        (df["date_enregistrement"] <= pd.Timestamp(date_to))
    )
    return df[mask].copy()


# ── Stats ponctuelles ────────────────────────────────────────────────────────

def get_latest_stats(spotify_id: str) -> dict:
    """Dernier snapshot disponible pour un artiste."""
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT followers_count, popularity_score,
               COALESCE(streams_real, 0), date_enregistrement
        FROM   historique_artistes
        WHERE  spotify_id = ?
        ORDER  BY date_enregistrement DESC
        LIMIT  1
        """,
        (spotify_id,),
    )
    row = cursor.fetchone()
    if row:
        return {
            "followers_count":   row[0],
            "popularity_score":  row[1],
            "streams_real":      row[2],
            "date_enregistrement": row[3],
        }
    return {"followers_count": 0, "popularity_score": 0,
            "streams_real": 0, "date_enregistrement": None}


def get_previous_stats(spotify_id: str) -> dict | None:
    """Avant-dernier snapshot — sert à calculer les deltas KPI."""
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT followers_count, popularity_score
        FROM   historique_artistes
        WHERE  spotify_id = ?
        ORDER  BY date_enregistrement DESC
        LIMIT  2
        """,
        (spotify_id,),
    )
    rows = cursor.fetchall()
    if len(rows) >= 2:
        return {"followers_count": rows[1][0], "popularity_score": rows[1][1]}
    return None


# ── Multi-artistes (roadmap) ─────────────────────────────────────────────────

def get_all_artists() -> list[dict]:
    """Liste tous les artistes en base — pour le sélecteur sidebar multi-artiste."""
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT spotify_id, artiste_name FROM historique_artistes ORDER BY artiste_name ASC"
    )
    return [{"spotify_id": r[0], "artiste_name": r[1]} for r in cursor.fetchall()]
