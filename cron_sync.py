import os
import sqlite3
from datetime import date
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

HARDCODED_ARTIST_ID = "0T4d2alRNWD29IME6Yb142"  # Kito
DB_FILE = "music_manager.db"

def init_db_if_missing():
    """Garantit que le fichier .db existe et possède la bonne structure d'injection."""
    print("🗄️ Initialisation/Vérification de la base de données locale...")
    conn = sqlite3.connect(DB_FILE)
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
    conn.close()

def main():
    print("🚀 Démarrage de la synchronisation automatique...")
    
    # Stratégie de sécurité : On crée le fichier .db TOUT DE SUITE
    init_db_if_missing()
    
    # Récupération des secrets d'environnement
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("❌ Erreur : Identifiants SPOTIFY_CLIENT_ID ou SPOTIFY_CLIENT_SECRET introuvables.")
        raise ValueError("Les variables d'environnement Spotify ne sont pas configurées sur GitHub.")

    try:
        # Connexion API Spotify
        auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        # Récupération des données en direct
        print(f"📡 Interrogation de l'API Spotify pour l'ID : {HARDCODED_ARTIST_ID}...")
        live_data = sp.artist(HARDCODED_ARTIST_ID)
        name = live_data["name"]
        followers = live_data["followers"]["total"]
        popularity = live_data["popularity"]
        
        print(f"🎵 Données récupérées pour {name} : {followers} followers, {popularity} popularité.")
        
        # Écriture dans la base SQLite
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Insertion ou mise à jour des données du jour
        cursor.execute("""
            INSERT OR REPLACE INTO historique_artistes 
            (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score) 
            VALUES (?, ?, ?, ?, ?)
        """, (date.today().isoformat(), name, HARDCODED_ARTIST_ID, followers, popularity))
        
        conn.commit()
        conn.close()
        print("💾 Base de données mise à jour avec succès.")
        
    except Exception as e:
        print(f"❌ Erreur critique lors de l'appel Spotify : {str(e)}")
        # On lève l'erreur pour forcer GitHub Actions à nous montrer le problème sous forme de log rouge
        raise e

if __name__ == "__main__":
    main()