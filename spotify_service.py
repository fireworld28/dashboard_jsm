# spotify_service.py — VERSION DEBUG (temporaire)
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
    """Version debug — affiche les étapes dans les logs Streamlit."""
    import sys

    try:
        print(f"[DEBUG] Fetching albums for {spotify_id}", file=sys.stderr)
        albums_result = sp.artist_albums(
            spotify_id,
            include_groups="album,single",
            limit=10,
        )
        albums = albums_result.get("items", [])
        print(f"[DEBUG] Found {len(albums)} albums", file=sys.stderr)

        all_tracks = []
        for album in albums[:6]:
            album_id   = album.get("id")
            album_name = album.get("name", "?")
            if not album_id:
                continue

            tracks_result = sp.album_tracks(album_id, limit=10)
            raw_tracks    = tracks_result.get("items", [])
            print(f"[DEBUG] Album '{album_name}' → {len(raw_tracks)} tracks", file=sys.stderr)

            for track in raw_tracks:
                artist_ids = [a["id"] for a in track.get("artists", [])]
                match      = spotify_id in artist_ids
                print(f"[DEBUG]   Track '{track.get('name')}' artists={artist_ids} match={match}", file=sys.stderr)
                if match:
                    all_tracks.append({
                        "id":          track["id"],
                        "name":        track["name"],
                        "duration_ms": track.get("duration_ms", 0),
                        "album":       album,
                        "artists":     track.get("artists", []),
                        "popularity":  0,
                    })

        print(f"[DEBUG] Total tracks collected: {len(all_tracks)}", file=sys.stderr)

        if not all_tracks:
            return []

        track_ids   = [t["id"] for t in all_tracks if t.get("id")][:50]
        full_tracks = sp.tracks(track_ids).get("tracks", [])
        pop_map     = {t["id"]: t.get("popularity", 0) for t in full_tracks if t}
        for t in all_tracks:
            t["popularity"] = pop_map.get(t["id"], 0)

        seen, dedup = set(), []
        for t in sorted(all_tracks, key=lambda x: x["popularity"], reverse=True):
            key = t["name"].lower()
            if key not in seen:
                seen.add(key)
                dedup.append(t)

        result = dedup[:10]
        print(f"[DEBUG] Returning {len(result)} tracks", file=sys.stderr)
        return result

    except Exception as e:
        print(f"[DEBUG] EXCEPTION in _get_artist_tracks: {type(e).__name__}: {e}", file=sys.stderr)
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
    except Exception as e:
        import sys
        print(f"[DEBUG] EXCEPTION in fetch_top_tracks_df: {type(e).__name__}: {e}", file=sys.stderr)
        return pd.DataFrame(columns=_COLS)
