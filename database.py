# database.py
"""
Couche d'accès aux données — Turso Cloud via libsql-client (SDK HTTP officiel).
Zéro compilation Rust — compatible Python 3.11+ et Streamlit Cloud.

Stratégie de cache :
  get_client()              → @st.cache_resource : client unique par session
  get_artist_history_full() → @st.cache_data(ttl=3600) : 1 appel DB/heure
  filter_history()          → filtrage en mémoire, zéro appel réseau
"""

import os
import asyncio
import libsql_client
import pandas as pd
import streamlit as st

TURSO_URL   = st.secrets.get("TURSO_DATABASE_URL") or os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = st.secrets.get("TURSO_AUTH_TOKEN")   or os.getenv("TURSO_AUTH_TOKEN")


def _run(coro):
    """Exécute une coroutine asyncio depuis un contexte synchrone."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _execute(sql: str, args: list = None):
    """Exécute une requête SQL sur Turso Cloud via HTTP."""
    async with libsql_client.create_client(
        url=TURSO_URL,
        auth_token=TURSO_TOKEN,
    ) as client:
        if args:
            result = await client.execute(sql, args)
        else:
            result = await client.execute(sql)
        return result


async def _batch(statements: list):
    """Exécute plusieurs requêtes en batch."""
    async with libsql_client.create_client(
        url=TURSO_URL,
        auth_token=TURSO_TOKEN,
    ) as client:
        return await client.batch(statements)


# ── Schéma ───────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Crée la table si absente et applique les migrations silencieusement."""
    if not TURSO_URL or not TURSO_TOKEN:
        st.error("⚠️ Identifiants Turso introuvables — vérifie secrets.toml.")
        return
    try:
        _run(_batch([
            libsql_client.Statement("""
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
            """),
        ]))
        # Migration silencieuse
        try:
            _run(_execute(
                "ALTER TABLE historique_artistes ADD COLUMN streams_real INTEGER NOT NULL DEFAULT 0"
            ))
        except Exception:
            pass
    except Exception as e:
        st.error(f"Erreur init DB : {e}")


# ── Historique ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_artist_history_full(spotify_id: str) -> pd.DataFrame:
    """
    Charge tout l'historique en une seule requête.
    Mis en cache 1 heure — filter_history() filtre ensuite en mémoire.
    """
    try:
        result = _run(_execute(
            """
            SELECT date_enregistrement,
                   followers_count,
                   popularity_score,
                   COALESCE(streams_real, 0) AS streams_real
            FROM   historique_artistes
            WHERE  spotify_id = ?
            ORDER  BY date_enregistrement ASC
            """,
            [spotify_id],
        ))
        if not result.rows:
            return pd.DataFrame(columns=[
                "date_enregistrement", "followers_count",
                "popularity_score", "streams_real"
            ])
        cols = [c.name for c in result.columns]
        df   = pd.DataFrame([list(r) for r in result.rows], columns=cols)
        df["date_enregistrement"] = pd.to_datetime(df["date_enregistrement"])
        return df
    except Exception as e:
        st.warning(f"Impossible de charger l'historique : {e}")
        return pd.DataFrame(columns=[
            "date_enregistrement", "followers_count",
            "popularity_score", "streams_real"
        ])


def filter_history(df: pd.DataFrame, date_from, date_to) -> pd.DataFrame:
    """Filtre en mémoire — aucun appel réseau supplémentaire."""
    if df.empty:
        return df
    mask = (
        (df["date_enregistrement"] >= pd.Timestamp(date_from)) &
        (df["date_enregistrement"] <= pd.Timestamp(date_to))
    )
    return df[mask].copy()


# Alias de compatibilité
def get_artist_history(spotify_id: str, date_from=None, date_to=None) -> pd.DataFrame:
    df = get_artist_history_full(spotify_id)
    if date_from or date_to:
        df = filter_history(
            df,
            date_from or df["date_enregistrement"].min().date(),
            date_to   or df["date_enregistrement"].max().date(),
        )
    return df


# ── Stats ponctuelles ────────────────────────────────────────────────────────

def get_latest_stats(spotify_id: str) -> dict:
    """Dernier snapshot disponible pour un artiste."""
    try:
        result = _run(_execute(
            """
            SELECT followers_count, popularity_score,
                   COALESCE(streams_real, 0), date_enregistrement
            FROM   historique_artistes
            WHERE  spotify_id = ?
            ORDER  BY date_enregistrement DESC
            LIMIT  1
            """,
            [spotify_id],
        ))
        if result.rows:
            row = result.rows[0]
            return {
                "followers_count":     row[0],
                "popularity_score":    row[1],
                "streams_real":        row[2],
                "date_enregistrement": row[3],
            }
    except Exception:
        pass
    return {"followers_count": 0, "popularity_score": 0,
            "streams_real": 0, "date_enregistrement": None}


def get_previous_stats(spotify_id: str) -> dict | None:
    """Avant-dernier snapshot pour calculer les deltas KPI."""
    try:
        result = _run(_execute(
            """
            SELECT followers_count, popularity_score
            FROM   historique_artistes
            WHERE  spotify_id = ?
            ORDER  BY date_enregistrement DESC
            LIMIT  2
            """,
            [spotify_id],
        ))
        if len(result.rows) >= 2:
            row = result.rows[1]
            return {"followers_count": row[0], "popularity_score": row[1]}
    except Exception:
        pass
    return None


def get_all_artists() -> list[dict]:
    """Liste tous les artistes en base."""
    try:
        result = _run(_execute(
            "SELECT DISTINCT spotify_id, artiste_name FROM historique_artistes ORDER BY artiste_name ASC"
        ))
        return [{"spotify_id": r[0], "artiste_name": r[1]} for r in result.rows]
    except Exception:
        return []
