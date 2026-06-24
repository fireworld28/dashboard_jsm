# cron_sync.py
import os
import logging
from datetime import date
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from config import HARDCODED_ARTIST_ID
import libsql
import streamlit as st

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    logging.info("🚀 Lancement de la synchronisation vers Turso...")
    
    # 1. Chargement des secrets
    try:
        client_id = os.getenv("SPOTIFY_CLIENT_ID") or st.secrets["SPOTIFY_CLIENT_ID"]
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET") or st.secrets["SPOTIFY_CLIENT_SECRET"]
        turso_url = os.getenv("TURSO_DATABASE_URL") or st.secrets["TURSO_DATABASE_URL"]
        turso_token = os.getenv("TURSO_AUTH_TOKEN") or st.secrets["TURSO_AUTH_TOKEN"]
    except KeyError as e:
        logging.critical(f"❌ Clé manquante dans tes secrets : {e}")
        return
    
    if not all([client_id, client_secret, turso_url, turso_token]):
        logging.critical("❌ Il manque des clés d'API (Vérifie ton fichier secrets.toml).")
        return
        
    try:
        # 2. Authentification et requête Spotify
        auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        artist_id = HARDCODED_ARTIST_ID.strip()
        logging.info(f"📡 Requête de l'ID artiste : '{artist_id}'")
        
        live_data = sp.artist(artist_id)
        
        if not live_data:
            logging.error("❌ Réponse vide reçue de Spotify.")
            return

        # Extraction sécurisée : si la clé n'existe pas, on met 0
        name = live_data.get("name", "INCONNU").upper()
        
        followers_data = live_data.get("followers")
        if isinstance(followers_data, dict):
            followers = followers_data.get("total", 0)
        else:
            followers = 0
            
        popularity = live_data.get("popularity", 0)
        
        logging.info(f"🎵 {name}: {followers} abonnés, Pop: {popularity}")
        
        # 3. Envoi sur Turso Cloud
        conn = libsql.connect(turso_url, auth_token=turso_token)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO historique_artistes 
            (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score) 
            VALUES (?, ?, ?, ?, ?)
        """, (date.today().isoformat(), name, artist_id, followers, popularity))
        
        conn.commit()
        conn.close()
            
        logging.info("💾 Écriture sur le Cloud Turso terminée avec succès !")
    except Exception as e:
        logging.error(f"💥 Erreur lors de la synchronisation : {e}")

if __name__ == "__main__":
    main()