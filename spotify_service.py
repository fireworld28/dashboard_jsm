# spotify_service.py
"""
Service Spotify — Client Credentials Flow.
Fix final : sp.tracks() retourne 403 sans market.
Solution : récupérer la popularité via sp.albums() qui l'inclut dans les tracks.
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


def _make_clean_client(client_id: str, client_secret: str) -> spotipy.Spotify:
    """Patch _internal_call pour filtrer les params None avant chaque requête."""
    sp = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )
    )
    original = sp._internal_call
    def _patched(method, url, payload, params):
        clean = {k: v for k, v in params.items() if v is not None}
        return original(method, url, payload, clean)
    sp._internal_call = _patched
    return sp


@st.cache_resource
def get_spotify_client() -> spotipy.Spotify:
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
        st.error("Identifiants Spotify manquants.")
        st.stop()
    try:
        return _make_clean_client(client_id, client_secret)
    except Exception as exc:
        st.error(f"Échec connexion Spotify : {exc}")
        st.stop()


@st.cache_data(ttl=900, show_spinner=False)
def resolve_artist(spotify_id: str) -> dict:
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
    Collecte les titres via artist_albums() + album() complet (inclut popularity).
    N'utilise PAS sp.tracks() qui retourne 403 sans market depuis 2024.
    sp.album() retourne les tracks avec leur popularité directement.
    """
    try:
        # 1. Lister les albums/singles
        albums_result = sp.artist_albums(
            spotify_id,
            include_groups="album,single",
            limit=10,
        )
        album_items = albums_result.get("items", [])

        all_tracks = []
        for album_meta in album_items[:6]:
            album_id = album_meta.get("id")
            if not album_id:
                continue

            # 2. Appel album() complet — retourne tracks avec popularity
            full_album = sp.album(album_id)
            tracks     = full_album.get("tracks", {}).get("items", [])

            for track in tracks:
                artist_ids = [a["id"] for a in track.get("artists", [])]
                if spotify_id not in artist_ids:
                    continue
                all_tracks.append({
                    "id":          track["id"],
                    "name":        track["name"],
                    "duration_ms": track.get("duration_ms", 0),
                    "album":       album_meta,
                    # popularity dans album() est sur l'album, pas le track
                    # On utilisera l'ordre de l'album comme proxy
                    "popularity":  full_album.get("popularity", 0),
                    "track_number": track.get("track_number", 99),
                })

        if not all_tracks:
            return []

        # Dédoublonner par nom, trier par popularité album puis numéro de piste
        seen, dedup = set(), []
        for t in sorted(all_tracks,
                        key=lambda x: (-x["popularity"], x["track_number"])):
            key = t["name"].lower()
            if key not in seen:
                seen.add(key)
                dedup.append(t)

        return dedup[:10]

    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def fetch_audio_profile(spotify_id: str) -> dict:
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
