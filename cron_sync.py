# cron_sync.py
import os
import sqlite3
import logging
from datetime import date
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from config import HARDCODED_ARTIST_ID, DB_FILE

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def init_db_if_missing():
    logging.info("🗄️ Alignement des structures de stockage...")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historique_artistes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_enregistrement DATE NOT NULL,
                artiste_name TEXT NOT NULL,
                spotify_id TEXT NOT NULL,
                followers_count INTEGER NOT NULL,
                popularity_score INTEGER NOT NULL,
                streams_real INTEGER DEFAULT 0,
                UNIQUE (spotify_id, date_enregistrement)
            )
        """)
        conn.commit()

def main():
    logging.info("🚀 Lancement du pipeline automatisé nocturne...")
    init_db_if_missing()
    
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        logging.critical("❌ Impossible de s'authentifier : Clés API GitHub absentes.")
        raise ValueError("Variables d'environnement non configurées.")
        
    try:
        auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(auth_manager=auth_manager, timeout=10)
        
        logging.info(f"📡 Extraction des métriques pour l'ID : {HARDCODED_ARTIST_ID}")
        live_data = sp.artist(HARDCODED_ARTIST_ID)
        name = live_data["name"]
        followers = live_data["followers"]["total"]
        popularity = live_data["popularity"]
        
        logging.info(f"🎵 Sync réussie pour {name} ({followers} abonnés).")
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO historique_artistes 
                (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score) 
                VALUES (?, ?, ?, ?, ?)
            """, (date.today().isoformat(), name, HARDCODED_ARTIST_ID, followers, popularity))
            conn.commit()
            
        logging.info("💾 Écriture sur disque terminée avec succès.")
    except Exception as e:
        logging.error(f"💥 Échec critique du script : {e}")
        raise

if __name__ == "__main__":
    main()