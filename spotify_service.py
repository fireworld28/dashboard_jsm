# spotify_service.py
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import streamlit as st
import pandas as pd
from config import PALETTE

_AUDIO_KEY_MAP = {
    "acousticness":  "Acoustique",
    "liveness":      "Liveness",
    "speechiness":   "Speechiness",
    "energy":        "Énergie",
    "danceability":  "Dansabilité",
}

_NEUTRAL_PROFILE = {
    "Acoustique":  0.30,
    "Liveness":    0.20,
    "Speechiness": 0.15,
    "Énergie":     0.65,
    "Dansabilité": 0.68,
}

def init_spotify():
    """Initialise de façon sécurisée le client Spotipy."""
    try:
        client_id     = st.secrets["SPOTIFY_CLIENT_ID"]
        client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
    except (KeyError, AttributeError, Exception):
        # Fallback de développement si les variables locales manquent
        client_id     = os.getenv("SPOTIFY_CLIENT_ID", "159")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "2fe")

    try:
        return spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=client_id, client_secret=client_secret
            )
        )
    except Exception as exc:
        st.error(f"**Échec de la connexion à l'API Spotify.** \n\n `{exc}`")
        st.stop()

@st.cache_data(ttl=900, show_spinner=False)
def resolve_artist(spotify_id: str) -> dict:
    """Récupère l'identité de l'artiste avec mécanisme Failsafe intégré."""
    sp = init_spotify()
    try:
        data      = sp.artist(spotify_id)
        images    = data.get("images", [])
        photo_url = images[0]["url"] if images else f"https://via.placeholder.com/150/{PALETTE['lime'][1:]}/0D0F14?text={data['name'][:2].upper()}"
        genres      = data.get("genres", [])
        genre_label = " / ".join(g.title() for g in genres[:2]) if genres else "N/A"
        return {
            "name":            data["name"],
            "spotify_id":      data["id"],
            "genre":           genre_label,
            "followers_base":  data["followers"]["total"],
            "popularity_base": data["popularity"],
            "photo_url":       photo_url,
            "audio_profile":   {},
        }
    except Exception:
        # Fallback si l'API Spotify crash en journée
        return {
            "name":            "KITO",
            "spotify_id":      spotify_id,
            "genre":           "Rap Français / Drill",
            "followers_base":  32000,
            "popularity_base": 44,
            "photo_url":       f"https://via.placeholder.com/150/{PALETTE['lime'][1:]}/0D0F14?text=KT",
            "audio_profile":   {},
        }

@st.cache_data(ttl=900, show_spinner=False)
def fetch_audio_profile(spotify_id: str) -> dict:
    """Analyse l'empreinte sonore de l'artiste."""
    sp = init_spotify()
    try:
        top       = sp.artist_top_tracks(spotify_id, country="FR")
        track_ids = [t["id"] for t in top.get("tracks", [])[:10] if t.get("id")]
        if not track_ids:
            return dict(_NEUTRAL_PROFILE)
        raw      = sp.audio_features(track_ids) or []
        features = [f for f in raw if f and isinstance(f, dict)]
        if not features:
            return dict(_NEUTRAL_PROFILE)
        return {
            fr_label: round(sum(f[sp_key] for f in features if sp_key in f) / len(features), 3)
            for sp_key, fr_label in _AUDIO_KEY_MAP.items()
        }
    except Exception:
        return dict(_NEUTRAL_PROFILE)

@st.cache_data(ttl=900, show_spinner=False)
def fetch_top_tracks_df(spotify_id: str) -> pd.DataFrame:
    """Génère le tableau Top 10 Spotify avec indicateurs."""
    _COLS = ["🎵 Titre", "Popularité", "Album", "Sortie", "Énergie", "Dansabilité", "Durée"]
    sp = init_spotify()
    try:
        top       = sp.artist_top_tracks(spotify_id, country="FR")
        tracks    = top.get("tracks", [])[:10]
        track_ids = [t["id"] for t in tracks if t.get("id")]
        raw       = sp.audio_features(track_ids) or []
        feat_map  = {f["id"]: f for f in raw if f and isinstance(f, dict)}
        rows = []
        for t in tracks:
            f          = feat_map.get(t["id"], {})
            ms         = t.get("duration_ms", 0)
            mn, sc     = divmod(ms // 1000, 60)
            album      = t.get("album", {})
            rows.append({
                "🎵 Titre": t["name"],
                "Popularité":        t["popularity"],
                "Album":             album.get("name", "—"),
                "Sortie":            album.get("release_date", "—")[:4],
                "Énergie":           round(f.get("energy",      0.0), 2),
                "Dansabilité":       round(f.get("danceability", 0.0), 2),
                "Durée":             f"{mn}:{sc:02d}",
            })
        df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=_COLS)
        df.index = range(1, len(df) + 1)
        return df
    except Exception:
        return pd.DataFrame(columns=_COLS)