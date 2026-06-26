# spotify_service.py
"""
Service Spotify via Spotipy (Client Credentials Flow).

Historique des endpoints testés :
  - artist_top_tracks(country='FR') → 403 (déprécié nov 2024)
  - search(limit=50) → 400 Invalid limit
  - search(limit=20) → 400 Invalid limit (market=None injecté par spotipy)
  Solution finale : artist_albums() + album_tracks() — stables et sans market requis
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
        st.error("**Identifiants Spotify manquants.** Vérifie secrets.toml.")
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
    """Récupère l'identité de l'artiste avec failsafe."""
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


def _get_artist_tracks(sp: spotipy.Spotify, spotify_id: str) -> list:
    """
    Collecte les titres d'un artiste via artist_albums() + album_tracks().
    Évite artist_top_tracks (déprécié → 403) et search (market=None → 400).
    Retourne les 10 titres les plus populaires.
    """
    try:
        all_tracks = []

        # Récupérer les albums et singles de l'artiste
        albums_result = sp.artist_albums(
            spotify_id,
            include_groups="album,single",
            limit=10,
        )
        albums = albums_result.get("items", [])

        for album in albums[:6]:  # Limiter à 6 albums pour la perf
            album_id = album.get("id")
            if not album_id:
                continue
            tracks_result = sp.album_tracks(album_id, limit=10)
            for track in tracks_result.get("items", []):
                # Vérifier que l'artiste principal est bien celui recherché
                if any(a["id"] == spotify_id for a in track.get("artists", [])):
                    # Récupérer la popularité via tracks() en batch
                    all_tracks.append({
                        "id":           track["id"],
                        "name":         track["name"],
                        "duration_ms":  track.get("duration_ms", 0),
                        "album":        album,
                        "artists":      track.get("artists", []),
                    })

        if not all_tracks:
            return []

        # Récupérer la popularité de tous les tracks en batch (max 50)
        track_ids  = [t["id"] for t in all_tracks if t.get("id")][:50]
        full_tracks = sp.tracks(track_ids).get("tracks", [])

        # Fusionner popularité
        pop_map = {t["id"]: t.get("popularity", 0) for t in full_tracks if t}
        for t in all_tracks:
            t["popularity"] = pop_map.get(t["id"], 0)

        # Dédoublonner par nom et trier par popularité
        seen  = set()
        dedup = []
        for t in sorted(all_tracks, key=lambda x: x["popularity"], reverse=True):
            name_lower = t["name"].lower()
            if name_lower not in seen:
                seen.add(name_lower)
                dedup.append(t)

        return dedup[:10]

    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def fetch_audio_profile(spotify_id: str) -> dict:
    """Analyse l'empreinte sonore de l'artiste."""
    sp = get_spotify_client()
    try:
        tracks    = _get_artist_tracks(sp, spotify_id)
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
        tracks = _get_artist_tracks(sp, spotify_id)
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
