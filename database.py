# database.py
import os
import libsql
import pandas as pd
import streamlit as st

TURSO_URL = st.secrets.get("TURSO_DATABASE_URL") or os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = st.secrets.get("TURSO_AUTH_TOKEN") or os.getenv("TURSO_AUTH_TOKEN")

@st.cache_resource
def get_db():
    if not TURSO_URL or not TURSO_TOKEN:
        st.error("⚠️ Identifiants Turso introuvables. Vérifie ton fichier secrets.toml.")
        raise ValueError("Configuration Turso manquante.")
    return libsql.connect(TURSO_URL, auth_token=TURSO_TOKEN)

def init_db() -> None:
    conn = get_db()
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
        cursor.execute("ALTER TABLE historique_artistes ADD COLUMN streams_real INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass 
    conn.commit()

@st.cache_data(ttl=3600)
def get_artist_history(spotify_id: str, date_from=None, date_to=None) -> pd.DataFrame:
    conn = get_db()
    query = "SELECT date_enregistrement, followers_count, popularity_score, COALESCE(streams_real, 0) AS streams_real FROM historique_artistes WHERE spotify_id = ?"
    params = [spotify_id]
    
    if date_from:
        query += " AND date_enregistrement >= ?"
        params.append(date_from.isoformat())
    if date_to:
        query += " AND date_enregistrement <= ?"
        params.append(date_to.isoformat())
    query += " ORDER BY date_enregistrement ASC"
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(cursor.fetchall(), columns=columns)
    
    if not df.empty:
        df["date_enregistrement"] = pd.to_datetime(df["date_enregistrement"])
    return df

def get_latest_stats(spotify_id: str) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT followers_count, popularity_score, date_enregistrement FROM historique_artistes WHERE spotify_id = ? ORDER BY date_enregistrement DESC LIMIT 1", (spotify_id,))
    row = cursor.fetchone()
    if row:
        return {"followers_count": row[0], "popularity_score": row[1], "date_enregistrement": row[2]}
    return {"followers_count": 0, "popularity_score": 0, "date_enregistrement": None}

def get_previous_stats(spotify_id: str) -> dict | None:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT followers_count, popularity_score FROM historique_artistes WHERE spotify_id = ? ORDER BY date_enregistrement DESC LIMIT 2", (spotify_id,))
    rows = cursor.fetchall()
    if len(rows) >= 2:
        return {"followers_count": rows[1][0], "popularity_score": rows[1][1]}
    return None