import os
import sqlite3
from datetime import date
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

HARDCODED_ARTIST_ID = "0T4d2alRNWD29IME6Yb142"  # Kito
DB_FILE = "music_manager.db"

def main():
    print("🚀 Démarrage de la synchronisation automatique...")
    
    # Récupération des secrets d'environnement
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("❌ Erreur : Identifiants Spotify introuvables dans l'environnement.")
        return

    try:
        # Connexion API Spotify
        auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(auth_manager=auth_manager, timeout=10)
        
        # Récupération des données en direct
        live_data = sp.artist(HARDCODED_ARTIST_ID)
        name = live_data["name"]
        followers = live_data["followers"]["total"]
        popularity = live_data["popularity"]
        
        print(f"🎵 Données récupérées pour {name} : {followers} followers, {popularity} popularité.")
        
        # Écriture dans la base SQLite locale
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # S'assurer que la table existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historique_artistes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_enregistrement DATE NOT NULL,
                artiste_name TEXT NOT NULL,
                spotify_id TEXT NOT NULL,
                followers_count INTEGER NOT NULL,
                popularity_score INTEGER NOT NULL,
                UNIQUE (spotify_id, date_enregistrement)
            )
        """)
        
        # Insertion des données du jour
        cursor.execute("""
            INSERT OR REPLACE INTO historique_artistes 
            (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score) 
            VALUES (?, ?, ?, ?, ?)
        """, (date.today().isoformat(), name, HARDCODED_ARTIST_ID, followers, popularity))
        
        conn.commit()
        conn.close()
        print("💾 Base de données mise à jour avec succès.")
        
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation : {str(e)}")

if __name__ == "__main__":
    main()