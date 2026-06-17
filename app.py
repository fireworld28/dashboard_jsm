"""
╔══════════════════════════════════════════════════════════════════════════╗
║         MUSIC MANAGER DASHBOARD — Analyse de Performance Artiste         ║
║         Auteur  : Digital Next / RBK Groupe                             ║
║         Stack   : Streamlit · Plotly · SQLite (→ PostgreSQL ready)      ║
║         API     : Spotify via Spotipy (Client Credentials Flow)         ║
╚══════════════════════════════════════════════════════════════════════════╝

Architecture :
  ┌─ spotify/    Couche API Spotify
  │   init_spotify()            — Client Credentials, mis en cache
  │   resolve_artist()          — Texte libre ou URL/URI → metadata dict
  │   fetch_audio_profile()     — Top tracks → moyennes audio features
  │   fetch_top_tracks_df()     — Top tracks formatés pour le tableau
  │
  ├─ db/         Couche d'accès aux données (SQLite par défaut)
  │   init_db()                 — Crée la table si elle n'existe pas
  │   seed_fake_history()       — Génère 12 mois d'historique fictif
  │   get_artist_history()      — Lit l'historique d'un artiste
  │   insert_daily_stats()      — Insère une nouvelle ligne quotidienne
  │   get_latest_stats()        — Dernière entrée d'un artiste
  │   get_previous_stats()      — Avant-dernière entrée (calcul delta)
  │
  └─ ui/         Logique d'affichage Streamlit / Plotly
      section_hud()             — Head-Up Display (photo, metrics)
      section_chansonometre()   — Top 10 réel + Scatter Plot
      section_trends()          — Line Chart DB (markers) + Radar Chart

Secrets Streamlit requis (fichier .streamlit/secrets.toml ou Cloud UI) :
  SPOTIFY_CLIENT_ID     = "votre_client_id"
  SPOTIFY_CLIENT_SECRET = "votre_client_secret"
"""

# ──────────────────────────────────────────────────────────────────────────
# 0. IMPORTS
# ──────────────────────────────────────────────────────────────────────────
import os
import random
import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────
# 1. CONFIGURATION GÉNÉRALE
# ──────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Music Manager Dashboard",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Palette "Studio Nuit" ──────────────────────────────────────────────────
PALETTE = {
    "bg":       "#0D0F14",
    "card":     "#161920",
    "border":   "#252A35",
    "lime":     "#C8F135",
    "teal":     "#00E5CC",
    "purple":   "#9B6DFF",
    "warm":     "#FF7A50",
    "text":     "#E8EAF0",
    "muted":    "#6B7280",
    "chart_bg": "rgba(0,0,0,0)",
}

# RGBA pour les overlays Plotly — jamais de hex 8-chars (TypeError Plotly/Py3.14)
_FILL_LIME  = "rgba(200, 241,  53, 0.08)"   # lime @ 8 %
_FILL_MUTED = "rgba(107, 114, 128, 0.12)"   # muted @ 12 %
_FILL_RADAR = "rgba(200, 241,  53, 0.14)"   # lime @ 14 %

# Correspondance label UI → alias Pandas resample
_RESAMPLE_ALIAS: dict[str, str] = {
    "Jour":    "D",
    "Semaine": "W",
    "Mois":    "ME",
    "Année":   "YE",
}

# CSS global
st.markdown(f"""
<style>
  .stApp, [data-testid="stAppViewContainer"] {{
      background-color: {PALETTE['bg']};
      color: {PALETTE['text']};
      font-family: 'Inter', 'Segoe UI', sans-serif;
  }}
  [data-testid="stSidebar"] {{
      background-color: {PALETTE['card']};
      border-right: 1px solid {PALETTE['border']};
  }}
  .main-title {{
      font-size: 2.4rem; font-weight: 800; letter-spacing: -0.03em;
      color: {PALETTE['text']}; line-height: 1.1;
  }}
  .main-title span {{ color: {PALETTE['lime']}; }}
  .subtitle-tag {{
      display: inline-block;
      background: {PALETTE['lime']}22;
      color: {PALETTE['lime']};
      font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em;
      text-transform: uppercase; padding: 3px 10px;
      border-radius: 4px; margin-bottom: 0.6rem;
  }}
  .section-card {{
      background: {PALETTE['card']}; border: 1px solid {PALETTE['border']};
      border-radius: 12px; padding: 1.4rem 1.6rem; margin-bottom: 1.2rem;
  }}
  .section-label {{
      font-size: 0.68rem; font-weight: 700; letter-spacing: 0.15em;
      text-transform: uppercase; color: {PALETTE['muted']}; margin-bottom: 0.2rem;
  }}
  .section-title {{
      font-size: 1.15rem; font-weight: 700;
      color: {PALETTE['text']}; margin-bottom: 1rem;
  }}
  .metric-box {{
      background: {PALETTE['bg']}; border: 1px solid {PALETTE['border']};
      border-radius: 10px; padding: 1rem 1.2rem; text-align: center;
  }}
  .metric-label {{
      font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em;
      text-transform: uppercase; color: {PALETTE['muted']}; margin-bottom: 0.3rem;
  }}
  .artist-photo {{
      width: 110px; height: 110px; border-radius: 50%; object-fit: cover;
      border: 3px solid {PALETTE['lime']}; display: block; margin: 0 auto 0.8rem;
  }}
  .artist-name {{
      font-size: 1.5rem; font-weight: 800;
      color: {PALETTE['text']}; text-align: center;
  }}
  .artist-genre {{
      font-size: 0.78rem; color: {PALETTE['muted']};
      text-align: center; margin-top: 0.2rem;
  }}
  .sidebar-section {{
      border-top: 1px solid {PALETTE['border']};
      padding-top: 1rem; margin-top: 1rem;
  }}
  .sidebar-label {{
      font-size: 0.68rem; font-weight: 700; letter-spacing: 0.12em;
      text-transform: uppercase; color: {PALETTE['muted']}; margin-bottom: 0.5rem;
  }}
  [data-testid="stMetric"] {{
      background: {PALETTE['card']}; border: 1px solid {PALETTE['border']};
      border-radius: 10px; padding: 0.8rem 1rem;
  }}
  [data-testid="stMetricValue"] {{ color: {PALETTE['lime']}; font-weight: 800; }}
  [data-testid="stMetricDelta"] {{ color: {PALETTE['teal']}; }}
  div[data-testid="stDataFrame"] > div {{ border-radius: 8px; }}
  .stButton > button {{
      background: {PALETTE['lime']}; color: {PALETTE['bg']};
      font-weight: 700; border: none; border-radius: 8px;
      padding: 0.6rem 1.2rem; width: 100%; transition: opacity 0.15s;
  }}
  .stButton > button:hover {{ opacity: 0.85; }}
  h1, h2, h3 {{ color: {PALETTE['text']}; }}
  [data-testid="stPlotlyChart"] {{ border-radius: 8px; overflow: hidden; }}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# 2. COUCHE SPOTIFY API
# ══════════════════════════════════════════════════════════════════════════

# Regex pour extraire un artist ID depuis une URL ou URI Spotify
# Formats acceptés :
#   https://open.spotify.com/artist/4Z8W4fKeB5YxbusRsdQVPb
#   spotify:artist:4Z8W4fKeB5YxbusRsdQVPb
_SPOTIFY_ARTIST_RE = re.compile(
    r"(?:spotify:artist:|open\.spotify\.com/(?:intl-[a-z]+/)?artist/)([A-Za-z0-9]+)"
)

# Profil audio de référence marché (valeurs fixes, indépendantes de l'artiste)
MARKET_REFERENCE = {
    "Acoustique":  0.25,
    "Liveness":    0.18,
    "Speechiness": 0.15,
    "Énergie":     0.72,
    "Dansabilité": 0.70,
}

# Clés audio features Spotify → labels français pour le radar
_AUDIO_KEY_MAP = {
    "acousticness":  "Acoustique",
    "liveness":      "Liveness",
    "speechiness":   "Speechiness",
    "energy":        "Énergie",
    "danceability":  "Dansabilité",
}


@st.cache_resource(show_spinner=False)
def init_spotify():
    """
    Initialise le client Spotipy en Client Credentials Flow.
    Mis en cache par st.cache_resource : une seule instance par session worker.
    Lit les credentials depuis st.secrets (Streamlit Cloud) ou variables
    d'environnement SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET (local).

    Retourne None si les credentials sont absents ou invalides,
    ce qui déclenche le mode dégradé (données mockées uniquement).
    """
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials

        client_id = st.secrets.get(
            "SPOTIFY_CLIENT_ID", os.getenv("SPOTIFY_CLIENT_ID", "")
        )
        client_secret = st.secrets.get(
            "SPOTIFY_CLIENT_SECRET", os.getenv("SPOTIFY_CLIENT_SECRET", "")
        )

        if not client_id or not client_secret:
            return None

        auth = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret,
        )
        return spotipy.Spotify(auth_manager=auth)

    except Exception:
        return None


def _extract_artist_id(query: str) -> str | None:
    """
    Si query contient une URL ou URI Spotify d'artiste, retourne l'ID.
    Sinon retourne None (= recherche textuelle).
    """
    m = _SPOTIFY_ARTIST_RE.search(query.strip())
    return m.group(1) if m else None


@st.cache_data(ttl=900, show_spinner=False)   # Cache 15 min
def resolve_artist(query: str) -> dict | None:
    """
    Résout un texte libre ou une URL/URI Spotify en dictionnaire artiste.
    Retourne un dict unifié avec les clés utilisées par le reste de l'app,
    ou None si aucun résultat.

    Clés retournées :
      name, spotify_id, genre, followers_base, popularity_base,
      photo_url, audio_profile (rempli par fetch_audio_profile)
    """
    sp = init_spotify()
    if sp is None:
        return None

    try:
        artist_id = _extract_artist_id(query)

        if artist_id:
            # URL ou URI → lookup direct
            data = sp.artist(artist_id)
        else:
            # Texte libre → recherche
            results = sp.search(q=query.strip(), type="artist", limit=1)
            items = results.get("artists", {}).get("items", [])
            if not items:
                return None
            data = items[0]

        # Photo : première image dispo, sinon placeholder coloré
        images = data.get("images", [])
        photo_url = (
            images[0]["url"]
            if images
            else f"https://via.placeholder.com/150/{PALETTE['lime'][1:]}/0D0F14?text={data['name'][:2].upper()}"
        )

        # Genre : 2 premiers genres ou "N/A"
        genres = data.get("genres", [])
        genre_label = " / ".join(g.title() for g in genres[:2]) if genres else "N/A"

        return {
            "name":            data["name"],
            "spotify_id":      data["id"],
            "genre":           genre_label,
            "followers_base":  data["followers"]["total"],
            "popularity_base": data["popularity"],
            "photo_url":       photo_url,
            "audio_profile":   {},   # Rempli par fetch_audio_profile()
        }

    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def fetch_audio_profile(spotify_id: str) -> dict:
    """
    Calcule le profil audio moyen de l'artiste à partir de ses top tracks.
    Retourne un dict {label_fr: valeur_0_à_1} pour les 5 dimensions radar.
    Retourne un profil fictif si l'API est indisponible.
    """
    sp = init_spotify()
    if sp is None:
        return {v: round(random.uniform(0.1, 0.9), 2) for v in _AUDIO_KEY_MAP.values()}

    try:
        # Top tracks (marché FR par défaut)
        top = sp.artist_top_tracks(spotify_id, country="FR")
        track_ids = [t["id"] for t in top.get("tracks", [])[:10]]

        if not track_ids:
            raise ValueError("Aucun top track disponible")

        features_list = sp.audio_features(track_ids)
        # Filtrer les None (tracks sans features)
        features_list = [f for f in features_list if f]

        if not features_list:
            raise ValueError("Aucune audio feature disponible")

        # Moyenne par dimension
        profile = {}
        for sp_key, fr_label in _AUDIO_KEY_MAP.items():
            vals = [f[sp_key] for f in features_list if sp_key in f]
            profile[fr_label] = round(sum(vals) / len(vals), 3) if vals else 0.5

        return profile

    except Exception:
        # Fallback : profil fictif cohérent
        return {v: round(random.uniform(0.1, 0.9), 2) for v in _AUDIO_KEY_MAP.values()}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_top_tracks_df(spotify_id: str, audio_profile: dict) -> pd.DataFrame:
    """
    Retourne un DataFrame Top 10 depuis l'API Spotify.
    Fallback sur données mockées si l'API est indisponible.
    """
    sp = init_spotify()

    if sp is not None:
        try:
            top = sp.artist_top_tracks(spotify_id, country="FR")
            tracks = top.get("tracks", [])[:10]
            track_ids = [t["id"] for t in tracks]
            features_list = sp.audio_features(track_ids) or []
            feat_map = {f["id"]: f for f in features_list if f}

            rows = []
            for t in tracks:
                f = feat_map.get(t["id"], {})
                duration_ms = t.get("duration_ms", 0)
                mins, secs = divmod(duration_ms // 1000, 60)
                rows.append({
                    "🎵  Titre":    t["name"],
                    "Popularité":  t["popularity"],
                    "Énergie":     round(f.get("energy", 0), 2),
                    "Dansabilité": round(f.get("danceability", 0), 2),
                    "Durée":       f"{mins}:{secs:02d}",
                })

            if rows:
                df = pd.DataFrame(rows)
                df.index = range(1, len(df) + 1)
                return df

        except Exception:
            pass

    # ── Fallback mockée ───────────────────────────────────────────────────
    random.seed(spotify_id + "_top10")
    adj   = ["Nuit", "Feu", "Ombre", "Lumière", "Rue", "Rêve", "Zone",
             "Pulse", "Flow", "Ciel", "Vague", "Soleil", "Brise", "Storm"]
    nouns = ["Éternelle", "Sans fin", "Perdue", "Cachée", "Dorée", "Froide",
             "Libre", "Sauvage", "Secrète", "Ultime", "Profonde", "Vivante"]

    energy_base = audio_profile.get("Énergie", 0.72)
    dance_base  = audio_profile.get("Dansabilité", 0.70)
    pop_base    = 55

    rows = []
    for i in range(10):
        rows.append({
            "🎵  Titre":    f"{random.choice(adj)} {random.choice(nouns)}",
            "Popularité":  int(max(10, min(99, random.gauss(pop_base - i * 3, 8)))),
            "Énergie":     round(max(0.05, min(0.98, random.gauss(energy_base, 0.12))), 2),
            "Dansabilité": round(max(0.05, min(0.98, random.gauss(dance_base,  0.10))), 2),
            "Durée":       f"{random.randint(2, 4)}:{random.randint(10, 59):02d}",
        })

    df = pd.DataFrame(rows)
    df.index = range(1, 11)
    return df


# ══════════════════════════════════════════════════════════════════════════
# 3. COUCHE BASE DE DONNÉES
# ══════════════════════════════════════════════════════════════════════════

DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_FILE = Path("music_manager.db")


def _get_connection():
    """Connexion SQLite (défaut) ou PostgreSQL selon DATABASE_URL."""
    if DATABASE_URL.startswith("postgresql"):
        try:
            import psycopg2
            return psycopg2.connect(DATABASE_URL), "pg"
        except ImportError:
            st.error("psycopg2 non installé. Lancez : pip install psycopg2-binary")
            st.stop()
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"


def _ph(db_type: str) -> str:
    """Placeholder paramétré selon le moteur SQL."""
    return "%s" if db_type == "pg" else "?"


def init_db() -> None:
    """Crée la table historique_artistes si elle n'existe pas. Idempotente."""
    conn, _ = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historique_artistes (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            date_enregistrement DATE    NOT NULL,
            artiste_name        TEXT    NOT NULL,
            spotify_id          TEXT    NOT NULL,
            followers_count     INTEGER NOT NULL,
            popularity_score    INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def seed_fake_history(artist: dict) -> None:
    """
    Insère 12 mois d'historique hebdomadaire fictif pour un artiste donné,
    SEULEMENT si cet artiste n'a encore aucune entrée en base.
    Progression sigmoïde légère + bruit aléatoire reproductible.
    """
    conn, db_type = _get_connection()
    cur = conn.cursor()
    cur.execute(
        f"SELECT COUNT(*) FROM historique_artistes WHERE spotify_id = {_ph(db_type)}",
        (artist["spotify_id"],),
    )
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    today  = date.today()
    base_f = artist["followers_base"]
    base_p = artist["popularity_base"]
    random.seed(artist["spotify_id"])
    rows   = []

    for days_ago in range(365, -1, -7):
        record_date = today - timedelta(days=days_ago)
        progress    = (365 - days_ago) / 365
        followers   = int(base_f * (1 + 0.35 * progress + random.uniform(-0.03, 0.05)))
        popularity  = min(100, int(base_p + 12 * progress + random.uniform(-2, 3)))
        rows.append((
            record_date.isoformat(),
            artist["name"],
            artist["spotify_id"],
            max(0, followers),
            max(0, min(100, popularity)),
        ))

    cur.executemany(
        f"""INSERT INTO historique_artistes
            (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score)
            VALUES ({_ph(db_type)},{_ph(db_type)},{_ph(db_type)},{_ph(db_type)},{_ph(db_type)})""",
        rows,
    )
    conn.commit()
    conn.close()


def get_artist_history(
    spotify_id: str,
    date_from:  date | None = None,
    date_to:    date | None = None,
) -> pd.DataFrame:
    """Lit l'historique filtré d'un artiste. Retourne un DataFrame."""
    conn, db_type = _get_connection()
    ph = _ph(db_type)

    query  = f"SELECT date_enregistrement, followers_count, popularity_score FROM historique_artistes WHERE spotify_id = {ph}"
    params = [spotify_id]
    if date_from:
        query += f" AND date_enregistrement >= {ph}"
        params.append(date_from.isoformat())
    if date_to:
        query += f" AND date_enregistrement <= {ph}"
        params.append(date_to.isoformat())
    query += " ORDER BY date_enregistrement ASC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    df["date_enregistrement"] = pd.to_datetime(df["date_enregistrement"])
    return df


def insert_daily_stats(
    artiste_name:    str,
    spotify_id:      str,
    followers_count: int,
    popularity_score: int,
    record_date:     date | None = None,
) -> None:
    """Insère une ligne datée (aujourd'hui par défaut) dans historique_artistes."""
    if record_date is None:
        record_date = date.today()
    conn, db_type = _get_connection()
    ph = _ph(db_type)
    conn.execute(
        f"""INSERT INTO historique_artistes
            (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score)
            VALUES ({ph},{ph},{ph},{ph},{ph})""",
        (record_date.isoformat(), artiste_name, spotify_id, followers_count, popularity_score),
    )
    conn.commit()
    conn.close()


def get_latest_stats(spotify_id: str) -> dict:
    """Dernière entrée connue pour un artiste."""
    conn, _ = _get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT followers_count, popularity_score, date_enregistrement "
        "FROM historique_artistes WHERE spotify_id = ? "
        "ORDER BY date_enregistrement DESC LIMIT 1",
        (spotify_id,),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {"followers_count": 0, "popularity_score": 0, "date_enregistrement": None}


def get_previous_stats(spotify_id: str) -> dict | None:
    """Avant-dernière entrée pour calculer les deltas."""
    conn, _ = _get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT followers_count, popularity_score "
        "FROM historique_artistes WHERE spotify_id = ? "
        "ORDER BY date_enregistrement DESC LIMIT 2",
        (spotify_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return dict(rows[1]) if len(rows) >= 2 else None


# ══════════════════════════════════════════════════════════════════════════
# 4. FONCTIONS D'AFFICHAGE STREAMLIT / PLOTLY
# ══════════════════════════════════════════════════════════════════════════

def _plotly_layout(title: str = "", height: int = 320) -> dict:
    """
    Retourne un dict de base pour update_layout().
    NE PAS l'unpacker avec ** dans un appel qui passe aussi yaxis/legend/xaxis
    en kwargs explicites → TypeError: keyword argument repeated.
    Modifier les clés par mutation avant d'appeler update_layout(base_dict).
    """
    return dict(
        paper_bgcolor = PALETTE["chart_bg"],
        plot_bgcolor  = PALETTE["chart_bg"],
        font          = dict(family="Inter, Segoe UI, sans-serif", color=PALETTE["text"], size=12),
        title         = dict(text=title, font=dict(size=14, color=PALETTE["text"]), x=0),
        height        = height,
        margin        = dict(l=16, r=16, t=40 if title else 16, b=16),
        legend        = dict(bgcolor="rgba(0,0,0,0)", bordercolor=PALETTE["border"], font=dict(size=11)),
        xaxis         = dict(gridcolor=PALETTE["border"], linecolor=PALETTE["border"], tickfont=dict(color=PALETTE["muted"], size=11)),
        yaxis         = dict(gridcolor=PALETTE["border"], linecolor=PALETTE["border"], tickfont=dict(color=PALETTE["muted"], size=11)),
    )


# ── Section 1 : Head-Up Display ───────────────────────────────────────────

def section_hud(artist: dict) -> None:
    st.markdown("""
        <div class='section-card'>
          <div class='section-label'>Section 01</div>
          <div class='section-title'>Head-Up Display — Santé Globale</div>
        </div>
    """, unsafe_allow_html=True)

    latest   = get_latest_stats(artist["spotify_id"])
    previous = get_previous_stats(artist["spotify_id"])

    # Priorité à la valeur en base ; fallback sur données API en mémoire
    followers   = latest["followers_count"]   or artist.get("followers_base", 0)
    popularity  = latest["popularity_score"]  or artist.get("popularity_base", 0)
    last_update = latest.get("date_enregistrement") or "—"

    delta_f = followers  - previous["followers_count"]  if previous else 0
    delta_p = popularity - previous["popularity_score"] if previous else 0

    col_photo, col_followers, col_popularity, col_info = st.columns([1.6, 2, 2, 2])

    with col_photo:
        st.markdown(f"""
            <div style="text-align:center;padding:0.5rem;">
              <img src="{artist['photo_url']}" class="artist-photo"
                   onerror="this.src='https://via.placeholder.com/110/161920/6B7280?text=?'"/>
              <div class="artist-name">{artist['name']}</div>
              <div class="artist-genre">{artist['genre']}</div>
            </div>
        """, unsafe_allow_html=True)

    with col_followers:
        st.metric(
            label="👥 Followers Spotify",
            value=f"{followers:,}".replace(",", "\u202f"),
            delta=f"{delta_f:+,} vs. précédent".replace(",", "\u202f"),
        )

    with col_popularity:
        bar = "█" * int(popularity / 10) + "░" * (10 - int(popularity / 10))
        st.metric(
            label="🔥 Score de Popularité",
            value=f"{popularity} / 100",
            delta=f"{delta_p:+d} pts vs. précédent",
        )
        st.markdown(
            f"<div style='font-size:0.85rem;color:{PALETTE['lime']};letter-spacing:2px'>{bar}</div>",
            unsafe_allow_html=True,
        )

    with col_info:
        genres_html = artist.get("genre", "N/A")
        st.markdown(f"""
            <div class="metric-box">
              <div class="metric-label">Dernière synchro</div>
              <div style="font-size:1.05rem;font-weight:700;color:{PALETTE['text']};margin:0.4rem 0;">
                {last_update}
              </div>
              <div class="metric-label" style="margin-top:0.8rem;">Spotify ID</div>
              <div style="font-size:0.75rem;color:{PALETTE['muted']};font-family:monospace;word-break:break-all;">
                {artist['spotify_id']}
              </div>
              <div class="metric-label" style="margin-top:0.8rem;">Genre</div>
              <div style="font-size:0.82rem;color:{PALETTE['teal']};">{genres_html}</div>
            </div>
        """, unsafe_allow_html=True)


# ── Section 2 : Le Chansonomètre ──────────────────────────────────────────

def section_chansonometre(artist: dict) -> None:
    st.markdown("""
        <div class='section-card'>
          <div class='section-label'>Section 02</div>
          <div class='section-title'>Le Chansonomètre — Analyse du Catalogue</div>
        </div>
    """, unsafe_allow_html=True)

    top10 = fetch_top_tracks_df(artist["spotify_id"], artist.get("audio_profile", {}))

    col_table, col_scatter = st.columns([1, 1.2], gap="large")

    with col_table:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem;'>🏆 Top 10 Hits</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            top10,
            use_container_width=True,
            height=340,
            column_config={
                "Popularité": st.column_config.ProgressColumn(
                    "Popularité", min_value=0, max_value=100, format="%d",
                ),
            },
        )

    with col_scatter:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem;'>"
            f"📊 Énergie × Dansabilité (taille = popularité)</div>",
            unsafe_allow_html=True,
        )
        fig = px.scatter(
            top10.reset_index().rename(columns={"index": "Rang"}),
            x="Énergie", y="Dansabilité",
            size="Popularité", color="Popularité",
            hover_name="🎵  Titre",
            color_continuous_scale=[
                [0, PALETTE["purple"]], [0.5, PALETTE["teal"]], [1, PALETTE["lime"]],
            ],
            size_max=30,
        )
        fig.update_layout(**_plotly_layout(height=340))
        fig.update_coloraxes(showscale=False)
        fig.update_traces(marker=dict(line=dict(color=PALETTE["bg"], width=1.5)))
        st.plotly_chart(fig, use_container_width=True)


# ── Section 3 : Tendances temporelles ─────────────────────────────────────

def section_trends(
    artist:    dict,
    date_from: date,
    date_to:   date,
) -> None:
    st.markdown("""
        <div class='section-card'>
          <div class='section-label'>Section 03</div>
          <div class='section-title'>Vision Temporelle — Court terme vs. Long terme</div>
        </div>
    """, unsafe_allow_html=True)

    col_line, col_radar = st.columns([1.2, 1], gap="large")

    # ── Line Chart : streams estimés depuis la DB ─────────────────────
    with col_line:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.3rem;'>"
            f"📈 Streams estimés (base de données)</div>",
            unsafe_allow_html=True,
        )

        granularity = st.radio(
            label="Agrégation temporelle",
            options=list(_RESAMPLE_ALIAS.keys()),
            index=1,                        # "Semaine" par défaut
            horizontal=True,
            label_visibility="collapsed",
        )

        df_hist = get_artist_history(artist["spotify_id"], date_from, date_to)

        if df_hist.empty:
            st.info("Aucune donnée dans la plage temporelle sélectionnée.")
        else:
            # Streams estimés : 12,5 streams par follower (benchmark indé 2024)
            df_hist["streams_estimated"] = df_hist["followers_count"] * 12.5

            # Rééchantillonnage selon la granularité choisie
            alias = _RESAMPLE_ALIAS[granularity]
            df_resampled = (
                df_hist
                .set_index("date_enregistrement")
                .resample(alias)
                .agg(
                    streams_estimated=("streams_estimated", "sum"),
                    popularity_score=("popularity_score", "mean"),
                )
                .dropna()
                .reset_index()
                .rename(columns={"date_enregistrement": "date"})
            )

            fig_line = go.Figure()

            # Axe gauche — Streams (lime, zone remplie, markers sur chaque point de synchro)
            fig_line.add_trace(go.Scatter(
                x=df_resampled["date"],
                y=df_resampled["streams_estimated"],
                # lines+markers : la ligne relie les points, chaque dot = un save en base
                mode="lines+markers",
                name="Streams estimés",
                line=dict(color=PALETTE["lime"], width=2.5),
                marker=dict(
                    color=PALETTE["lime"],
                    size=6,
                    symbol="circle",
                    line=dict(color=PALETTE["bg"], width=1.5),   # halo sombre = lisibilité
                ),
                fill="tozeroy",
                fillcolor=_FILL_LIME,       # rgba, jamais de hex 8-chars
                hovertemplate=(
                    "<b>%{x|%d %b %Y}</b><br>"
                    "Streams : <b>%{y:,.0f}</b><extra></extra>"
                ),
            ))

            # Axe droit — Popularité (purple, pointillé, markers carrés)
            fig_line.add_trace(go.Scatter(
                x=df_resampled["date"],
                y=df_resampled["popularity_score"],
                mode="lines+markers",
                name="Popularité",
                yaxis="y2",
                line=dict(color=PALETTE["purple"], width=1.8, dash="dot"),
                marker=dict(
                    color=PALETTE["purple"],
                    size=5,
                    symbol="square",
                    line=dict(color=PALETTE["bg"], width=1),
                ),
                hovertemplate="Popularité : <b>%{y:.1f}</b>/100<extra></extra>",
            ))

            # Fusion sûre du layout : mutation du dict de base avant update_layout()
            # → aucun doublon de clé, zéro TypeError sur Python 3.14
            _base = _plotly_layout(height=360)
            _base["yaxis"] = dict(
                title="Streams estimés",
                gridcolor=PALETTE["border"],
                linecolor=PALETTE["border"],
                tickfont=dict(color=PALETTE["muted"], size=11),
            )
            _base["yaxis2"] = dict(
                title="Popularité /100",
                overlaying="y",
                side="right",
                range=[0, 100],
                showgrid=False,
                tickfont=dict(color=PALETTE["purple"]),
            )
            _base["legend"] = dict(
                orientation="h",
                yanchor="bottom", y=1.02,
                xanchor="left",   x=0,
                bgcolor="rgba(0,0,0,0)",
                bordercolor=PALETTE["border"],
                font=dict(size=11),
            )
            fig_line.update_layout(_base)
            st.plotly_chart(fig_line, use_container_width=True)

    # ── Radar Chart ───────────────────────────────────────────────────────
    with col_radar:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem;'>"
            f"🕸️ Profil Audio vs. Marché</div>",
            unsafe_allow_html=True,
        )

        profile = artist.get("audio_profile") or MARKET_REFERENCE
        categories      = list(MARKET_REFERENCE.keys())   # ordre fixe = radar stable
        categories_loop = categories + [categories[0]]

        artist_vals = [profile.get(c, 0.5) for c in categories]
        market_vals = [MARKET_REFERENCE[c]  for c in categories]

        fig_radar = go.Figure()

        fig_radar.add_trace(go.Scatterpolar(
            r=[v * 100 for v in market_vals] + [market_vals[0] * 100],
            theta=categories_loop,
            fill="toself",
            fillcolor=_FILL_MUTED,
            line=dict(color=PALETTE["muted"], width=1.5, dash="dot"),
            name="Standard marché",
        ))

        fig_radar.add_trace(go.Scatterpolar(
            r=[v * 100 for v in artist_vals] + [artist_vals[0] * 100],
            theta=categories_loop,
            fill="toself",
            fillcolor=_FILL_RADAR,
            line=dict(color=PALETTE["lime"], width=2.5),
            name=artist["name"],
        ))

        fig_radar.update_layout(
            polar=dict(
                bgcolor=PALETTE["chart_bg"],
                radialaxis=dict(
                    visible=True, range=[0, 100],
                    tickfont=dict(color=PALETTE["muted"], size=9),
                    gridcolor=PALETTE["border"], linecolor=PALETTE["border"],
                ),
                angularaxis=dict(
                    tickfont=dict(color=PALETTE["text"], size=11),
                    linecolor=PALETTE["border"], gridcolor=PALETTE["border"],
                ),
            ),
            paper_bgcolor=PALETTE["chart_bg"],
            font=dict(color=PALETTE["text"]),
            height=360,
            margin=dict(l=30, r=30, t=30, b=30),
            legend=dict(
                orientation="h",
                yanchor="bottom", y=-0.15,
                xanchor="center", x=0.5,
                font=dict(size=11),
                bgcolor="rgba(0,0,0,0)",
            ),
        )
        st.plotly_chart(fig_radar, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# 5. POINT D'ENTRÉE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    # ── 5.1  Initialisation DB ────────────────────────────────────────────
    init_db()

    # ── 5.2  SIDEBAR ──────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
            <div style="padding:0.5rem 0 1rem;">
              <div style="font-size:0.65rem;font-weight:700;letter-spacing:0.15em;
                          text-transform:uppercase;color:{PALETTE['muted']};">
                  MUSIC MANAGER
              </div>
              <div style="font-size:1.35rem;font-weight:800;color:{PALETTE['text']};">
                  Dashboard<span style="color:{PALETTE['lime']};">.</span>
              </div>
            </div>
        """, unsafe_allow_html=True)

        # ── Recherche artiste ─────────────────────────────────────────────
        st.markdown(f"<div class='sidebar-label'>🔍 Recherche artiste</div>", unsafe_allow_html=True)
        query = st.text_input(
            label="Rechercher un artiste (Nom ou Lien Spotify)",
            value="KITO",
            label_visibility="collapsed",
            placeholder="Nom, URL ou URI Spotify…",
        )

        # Résolution via API Spotify (avec cache 15 min)
        sp_available = init_spotify() is not None

        with st.spinner("Recherche en cours…"):
            artist = resolve_artist(query) if query.strip() else None

        if artist is None:
            # Mode dégradé : artiste fictif KITO si pas d'API ou pas de résultat
            if not sp_available:
                st.caption("⚠️ Secrets Spotify non configurés — mode démo activé.")
            else:
                st.warning(f"Aucun artiste trouvé pour « {query} ».")

            artist = {
                "name":            "KITO",
                "spotify_id":      "kito_demo_001",
                "genre":           "Rap Français / Afrotrap",
                "followers_base":  28_400,
                "popularity_base": 42,
                "photo_url":       f"https://via.placeholder.com/150/C8F135/0D0F14?text=KITO",
                "audio_profile": {
                    "Acoustique":  0.12, "Liveness": 0.21, "Speechiness": 0.38,
                    "Énergie":     0.82, "Dansabilité": 0.74,
                },
            }
        else:
            # Profil audio réel depuis les top tracks
            with st.spinner("Chargement du profil audio…"):
                artist["audio_profile"] = fetch_audio_profile(artist["spotify_id"])

        # Seed l'historique fictif si c'est la première fois qu'on voit cet artiste
        seed_fake_history(artist)

        # ── Filtre temporel ───────────────────────────────────────────────
        st.markdown("<div class='sidebar-section'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sidebar-label'>📅 Fenêtre temporelle</div>", unsafe_allow_html=True)

        today    = date.today()
        min_date = today - timedelta(days=365)

        date_range = st.slider(
            label="Période d'analyse",
            min_value=min_date, max_value=today,
            value=(min_date, today),
            format="MMM YYYY",
            label_visibility="collapsed",
        )
        date_from, date_to = date_range
        st.caption(f"Du **{date_from.strftime('%d %b %Y')}** au **{date_to.strftime('%d %b %Y')}**")

        # ── Synchronisation API ───────────────────────────────────────────
        st.markdown("<div class='sidebar-section'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='sidebar-label'>🔄 Synchronisation Spotify</div>",
            unsafe_allow_html=True,
        )

        if st.button("▶  Simuler la synchro hebdomadaire"):
            latest       = get_latest_stats(artist["spotify_id"])
            new_followers = int(latest["followers_count"] * random.uniform(1.005, 1.025))
            new_popularity = min(100, latest["popularity_score"] + random.randint(-1, 3))

            insert_daily_stats(
                artiste_name=artist["name"],
                spotify_id=artist["spotify_id"],
                followers_count=new_followers,
                popularity_score=new_popularity,
            )
            st.success(
                f"✅ Sync OK — {today.strftime('%d/%m/%Y')}\n\n"
                f"Followers : **{new_followers:,}**  |  Pop. : **{new_popularity}/100**"
            )
            st.rerun()

        # ── Infos DB ──────────────────────────────────────────────────────
        st.markdown("<div class='sidebar-section'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sidebar-label'>🗄️ Base de données</div>", unsafe_allow_html=True)

        db_label = (
            "PostgreSQL"
            if DATABASE_URL.startswith("postgresql")
            else f"SQLite — {DB_FILE.name}"
        )
        st.markdown(
            f"<div style='font-size:0.75rem;color:{PALETTE['teal']};'>"
            f"Moteur actif : <strong>{db_label}</strong></div>",
            unsafe_allow_html=True,
        )

        conn, _ = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM historique_artistes")
        nb_rows = cur.fetchone()[0]
        conn.close()
        st.caption(f"{nb_rows} enregistrements au total dans la base.")

        # Indicateur statut API Spotify
        sp_status    = "Connecté" if sp_available else "Non configuré (mode démo)"
        sp_icon      = "\u2705" if sp_available else "\u26a0\ufe0f"
        sp_color     = PALETTE["teal"] if sp_available else PALETTE["warm"]
        st.markdown(
            f"<div style='font-size:0.75rem;margin-top:0.5rem;color:{sp_color};'>"
            f"Spotify API : <strong>{sp_icon} {sp_status}</strong></div>",
            unsafe_allow_html=True,
        )

    # ── 5.3  EN-TÊTE PRINCIPAL ────────────────────────────────────────────
    st.markdown(f"""
        <div class="subtitle-tag">DIGITAL NEXT — Music Intelligence</div>
        <div class="main-title">
            Tableau de bord <span>{artist['name']}</span>
        </div>
        <div style="color:{PALETTE['muted']};font-size:0.9rem;margin:0.4rem 0 1.8rem;">
            Analyse de performance · Données du {date_from.strftime('%d %b %Y')}
            au {date_to.strftime('%d %b %Y')}
        </div>
    """, unsafe_allow_html=True)

    # ── 5.4  SECTIONS ─────────────────────────────────────────────────────
    section_hud(artist)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    section_chansonometre(artist)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    section_trends(artist, date_from, date_to)

    # ── 5.5  FOOTER ───────────────────────────────────────────────────────
    st.markdown(f"""
        <div style="border-top:1px solid {PALETTE['border']};margin-top:2.5rem;
                    padding-top:1rem;text-align:center;
                    font-size:0.72rem;color:{PALETTE['muted']};">
            Music Manager Dashboard · Digital Next / RBK Groupe ·
            Données partiellement simulées
        </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
