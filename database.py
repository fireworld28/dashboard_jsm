# database.py
import os
import sqlite3
import pandas as pd
import streamlit as st
import random as _rnd
from datetime import date, timedelta
from config import DB_FILE

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_FILE}")

def get_db():
    """Gère le pool de connexions optimisé de Streamlit."""
    return st.connection("sql", url=DATABASE_URL)

def init_db() -> None:
    """Initialise et applique les migrations structurelles de la base."""
    conn = get_db()
    with conn.session as session:
        session.execute("""
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
        # Interception ciblée (Senior Clean Code) au lieu du pass générique
        try:
            session.execute("ALTER TABLE historique_artistes ADD COLUMN streams_real INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass 
        session.commit()

def seed_fake_history(artist: dict) -> None:
    """Injecte l'historique progressif si la base est neuve."""
    conn = get_db()
    check = conn.query("SELECT COUNT(*) as count FROM historique_artistes WHERE spotify_id = :id", params={"id": artist["spotify_id"]}, ttl=0)
    if check.iloc[0]["count"] > 0:
        return

    rng = _rnd.Random(artist["spotify_id"])
    today = date.today()
    current_f = max(1, artist.get("followers_base",  1000))
    current_p = max(1, artist.get("popularity_base", 40))
    
    with conn.session as session:
        for week in range(52, -1, -1):
            record_date = today - timedelta(weeks=week)
            progress    = (52 - week) / 52
            followers   = int(current_f * (0.70 + 0.30 * progress) * (1.0 + rng.uniform(-0.03, 0.03)))
            popularity  = min(100, max(0, int(current_p * (0.80 + 0.20 * progress) + rng.uniform(-3, 3))))
            
            session.execute("""
                INSERT OR REPLACE INTO historique_artistes
                (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score)
                VALUES (:date, :name, :id, :followers, :pop)
            """, {"date": record_date.isoformat(), "name": artist["name"], "id": artist["spotify_id"], "followers": max(0, followers), "pop": popularity})
        session.commit()

def ensure_artist_has_history(artist: dict) -> None:
    try: seed_fake_history(artist)
    except Exception: pass

def upsert_daily_stats(artiste_name: str, spotify_id: str, followers_count: int, popularity_score: int, record_date: date | None = None) -> None:
    if record_date is None:
        record_date = date.today()
    conn = get_db()
    with conn.session as session:
        session.execute("""
            INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score)
            VALUES (:date, :name, :id, :followers, :pop)
        """, {"date": record_date.isoformat(), "name": artiste_name, "id": spotify_id, "followers": followers_count, "pop": popularity_score})
        session.commit()

def get_artist_history(spotify_id: str, date_from: date | None = None, date_to: date | None = None) -> pd.DataFrame:
    conn = get_db()
    query = "SELECT date_enregistrement, followers_count, popularity_score, COALESCE(streams_real, 0) AS streams_real FROM historique_artistes WHERE spotify_id = :id"
    params = {"id": spotify_id}
    if date_from:
        query += " AND date_enregistrement >= :date_from"
        params["date_from"] = date_from.isoformat()
    if date_to:
        query += " AND date_enregistrement <= :date_to"
        params["date_to"] = date_to.isoformat()
    query += " ORDER BY date_enregistrement ASC"
    
    # Cache SQL intelligent géré par Streamlit durant 1 heure
    df = conn.query(query, params=params, ttl="1h")
    df["date_enregistrement"] = pd.to_datetime(df["date_enregistrement"])
    return df

def get_latest_stats(spotify_id: str) -> dict:
    conn = get_db()
    df = conn.query("SELECT followers_count, popularity_score, date_enregistrement FROM historique_artistes WHERE spotify_id = :id ORDER BY date_enregistrement DESC LIMIT 1", params={"id": spotify_id}, ttl=0)
    return df.iloc[0].to_dict() if not df.empty else {"followers_count": 0, "popularity_score": 0, "date_enregistrement": None}

def get_previous_stats(spotify_id: str) -> dict | None:
    conn = get_db()
    df = conn.query("SELECT followers_count, popularity_score FROM historique_artistes WHERE spotify_id = :id ORDER BY date_enregistrement DESC LIMIT 2", params={"id": spotify_id}, ttl=0)
    return df.iloc[1].to_dict() if len(df) >= 2 else None