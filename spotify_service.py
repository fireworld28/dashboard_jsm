# spotify_service.py
"""
Service Spotify via Spotipy (Client Credentials Flow).
- artist_top_tracks() est déprécié par Spotify depuis 2024 → retourne 403
- Remplacé par search(type='track', q='artist:NOM') pour les top titres
- audio_features() toujours fonctionnel
"""

import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import streamlit as st
import pandas as pd

try:
    from config import PALETTE
    _LIME = PALETTE.get("lime", "C8F135")
except Exception:
    _LIME = "C8F135"

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


@st.cache_resource
def get_spotify_client() -> spotipy.Spotify:
    """Client Spotipy unique et persistant pour toute la session."""
    client_id, client_secret = "", ""
    try:
        client_id     = st.secrets["SPOTIFY_CLIENT_ID"]
        client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
    except Exception:
        pass
    if not client_id:
        client_id = os.getenv("SPOTIFY_CLIENT_ID", "")
    if not client_secret:
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        st.error("**Identifiants Spotify manquants.** Vérifie ton fichier secrets.toml.")
        st.stop()
    try:
        return spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret,
            )
        )
    except Exception as exc:
        st.error(f"**Échec connexion Spotify.** `{exc}`")
        st.stop()


@st.cache_data(ttl=900, show_spinner=False)
def resolve_artist(spotify_id: str) -> dict:
    """Récupère l'identité de l'artiste avec mécanisme failsafe."""
    sp = get_spotify_client()
    try:
        data        = sp.artist(spotify_id)
        images      = data.get("images", [])
        photo_url   = (
            images[0]["url"] if images
            else f"https://via.placeholder.com/150/{_LIME[1:]}/0D0F14?text={data['name'][:2].upper()}"
        )
        genres      = data.get("genres", [])
        genre_label = " / ".join(g.title() for g in genres[:2]) if genres else "N/A"
        return {
            "name":            data["name"],
            "spotify_id":      data["id"],
            "genre":           genre_label,
            "followers_base":  data["followers"]["total"],
            "popularity_base": data["popularity"],
            "photo_url":       photo_url,
        }
    except Exception:
        return {
            "name":            "KITO",
            "spotify_id":      spotify_id,
            "genre":           "Rap Français / Drill",
            "followers_base":  32000,
            "popularity_base": 44,
            "photo_url":       f"https://via.placeholder.com/150/{_LIME[1:]}/0D0F14?text=KT",
        }


def _get_top_tracks_via_search(sp: spotipy.Spotify, spotify_id: str) -> list:
    """
    Récupère jusqu'à 10 titres via search() — alternative officielle
    à artist_top_tracks() déprécié par Spotify (retourne 403 depuis 2024).
    """
    try:
        artist_data = sp.artist(spotify_id)
        artist_name = artist_data.get("name", "")
        results = sp.search(
            q=f"artist:{artist_name}",
            type="track",
            limit=20,
        )
        tracks = results.get("tracks", {}).get("items", [])
        filtered = [
            t for t in tracks
            if any(a["id"] == spotify_id for a in t.get("artists", []))
        ]
        filtered.sort(key=lambda t: t.get("popularity", 0), reverse=True)
        return filtered[:10]
    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def fetch_audio_profile(spotify_id: str) -> dict:
    """Analyse l'empreinte sonore de l'artiste sur ses top titres."""
    sp = get_spotify_client()
    try:
        tracks    = _get_top_tracks_via_search(sp, spotify_id)
        track_ids = [t["id"] for t in tracks if t.get("id")]
        if not track_ids:
            return dict(_NEUTRAL_PROFILE)
        raw      = sp.audio_features(track_ids) or []
        features = [f for f in raw if f and isinstance(f, dict)]
        if not features:
            return dict(_NEUTRAL_PROFILE)
        return {
            fr_label: round(
                sum(f[sp_key] for f in features if sp_key in f) / len(features), 3
            )
            for sp_key, fr_label in _AUDIO_KEY_MAP.items()
        }
    except Exception:
        return dict(_NEUTRAL_PROFILE)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_top_tracks_df(spotify_id: str) -> pd.DataFrame:
    """Génère le tableau Top 10 titres avec indicateurs audio."""
    _COLS = ["🎵 Titre", "Popularité", "Album", "Sortie", "Énergie", "Dansabilité", "Durée"]
    sp = get_spotify_client()
    try:
        tracks = _get_top_tracks_via_search(sp, spotify_id)
        if not tracks:
            return pd.DataFrame(columns=_COLS)
        track_ids = [t["id"] for t in tracks if t.get("id")]
        raw       = sp.audio_features(track_ids) or []
        feat_map  = {f["id"]: f for f in raw if f and isinstance(f, dict)}
        rows = []
        for t in tracks:
            f      = feat_map.get(t["id"], {})
            ms     = t.get("duration_ms", 0)
            mn, sc = divmod(ms // 1000, 60)
            album  = t.get("album", {})
            rows.append({
                "🎵 Titre":    t["name"],
                "Popularité":  t.get("popularity", 0),
                "Album":       album.get("name", "—"),
                "Sortie":      album.get("release_date", "—")[:4],
                "Énergie":     round(f.get("energy",       0.0), 2),
                "Dansabilité": round(f.get("danceability",  0.0), 2),
                "Durée":       f"{mn}:{sc:02d}",
            })
        df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=_COLS)
        df.index = range(1, len(df) + 1)
        return df
    except Exception:
        return pd.DataFrame(columns=_COLS)
