"""
╔══════════════════════════════════════════════════════════════════════════╗
║   MUSIC MANAGER DASHBOARD — Moniteur Artiste Dédié                      ║
║   Auteur  : Digital Next / RBK Groupe                                   ║
║   Stack   : Streamlit · Plotly · SQLite (→ PostgreSQL ready)            ║
║   API     : Spotify via Spotipy (Client Credentials Flow)               ║
╚══════════════════════════════════════════════════════════════════════════╝

Architecture mono-artiste : l'ID Spotify de l'artiste suivi est hardcodé
dans HARDCODED_ARTIST_ID. Toute l'app tourne autour de cet unique artiste.

Basculer vers PostgreSQL :
  export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
"""

# ──────────────────────────────────────────────────────────────────────────
# SECTION 1 — IMPORTS & CONFIGURATION GÉNÉRALE
# ──────────────────────────────────────────────────────────────────────────
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import streamlit as st

# ── Artiste cible (único) ─────────────────────────────────────────────────
# Remplacer par l'ID Spotify de l'artiste à monitorer.
HARDCODED_ARTIST_ID = "0T4d2alRNWD29IME6Yb142"   # id Spotify de l'artiste suivi (ex: "0T4d2alRNWD29IME6Yb142" pour "Kito")

# ── Démographie audience (données privées non exposées par l'API Spotify) ─
# Adapter ces valeurs à la connaissance réelle du manager.
AUDIENCE_GENDER = {
    "Hommes": 62,
    "Femmes": 38,
}
AUDIENCE_AGE = {
    "13–17":  8,
    "18–24": 34,
    "25–34": 31,
    "35–44": 17,
    "45+":   10,
}

st.set_page_config(
    page_title="Music Manager Dashboard",
    page_icon="\U0001f3b5",
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

_FILL_LIME  = "rgba(200, 241,  53, 0.08)"
_FILL_MUTED = "rgba(107, 114, 128, 0.12)"
_FILL_RADAR = "rgba(200, 241,  53, 0.14)"

_RESAMPLE_ALIAS: dict[str, str] = {
    "Jour":    "D",
    "Semaine": "W",
    "Mois":    "ME",
    "Année":   "YE",
}

MARKET_REFERENCE: dict[str, float] = {
    "Acoustique":  0.25,
    "Liveness":    0.18,
    "Speechiness": 0.15,
    "Énergie":     0.72,
    "Dansabilité": 0.70,
}

# ── CSS global ────────────────────────────────────────────────────────────
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
# SECTION 2 — COUCHE API SPOTIFY
# ══════════════════════════════════════════════════════════════════════════

_AUDIO_KEY_MAP: dict[str, str] = {
    "acousticness":  "Acoustique",
    "liveness":      "Liveness",
    "speechiness":   "Speechiness",
    "energy":        "Énergie",
    "danceability":  "Dansabilité",
}

_NEUTRAL_PROFILE: dict[str, float] = {
    "Acoustique":  0.30,
    "Liveness":    0.20,
    "Speechiness": 0.15,
    "Énergie":     0.65,
    "Dansabilité": 0.68,
}


@st.cache_resource(show_spinner=False)
def init_spotify():
    """
    Initialise le client Spotipy via Client Credentials Flow.

    Priorité :
      1. st.secrets["SPOTIFY_CLIENT_ID"] / ["SPOTIFY_CLIENT_SECRET"]
      2. Fallback hardcodé — garantit la connexion même si les secrets
         Streamlit Cloud ne s'injectent pas correctement.
    """
    try:
        client_id     = st.secrets["SPOTIFY_CLIENT_ID"]
        client_secret = st.secrets["SPOTIFY_CLIENT_SECRET"]
    except (KeyError, AttributeError, Exception):
        client_id     = "159"
        client_secret = "2fe"

    try:
        return spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=client_id,
                client_secret=client_secret,
            )
        )
    except Exception as exc:
        st.error(
            f"**\u00c9chec de connexion Spotify.**\n\n"
            f"V\u00e9rifiez vos credentials.\n\n`{exc}`"
        )
        st.stop()


@st.cache_data(ttl=900, show_spinner=False)
def resolve_artist(spotify_id: str) -> dict | None:
    """
    Résout un Spotify artist ID → dict artiste unifié.

    Clés : name, spotify_id, genre, followers_base, popularity_base,
           photo_url, audio_profile (vide)
    """
    sp = init_spotify()
    try:
        data      = sp.artist(spotify_id)
        images    = data.get("images", [])
        photo_url = images[0]["url"] if images else (
            f"https://via.placeholder.com/150/"
            f"{PALETTE['lime'][1:]}/0D0F14?text="
            f"{data['name'][:2].upper()}"
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
            "audio_profile":   {},
        }
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def fetch_audio_profile(spotify_id: str) -> dict:
    """
    Moyenne réelle des 5 dimensions audio depuis les top tracks (FR).
    Fallback sur profil neutre si l'API échoue.
    """
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
            fr_label: round(
                sum(f[sp_key] for f in features if sp_key in f) / len(features), 3
            )
            for sp_key, fr_label in _AUDIO_KEY_MAP.items()
        }
    except Exception:
        return dict(_NEUTRAL_PROFILE)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_top_tracks_df(spotify_id: str) -> pd.DataFrame:
    """
    Top 10 réel de l'artiste (FR) avec audio features.
    Retourne un DataFrame vide si l'API est indisponible.
    """
    _COLS = ["\U0001f3b5  Titre", "Popularité", "Album", "Sortie",
             "Énergie", "Dansabilité", "Durée"]
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
                "\U0001f3b5  Titre": t["name"],
                "Popularité":        t["popularity"],
                "Album":             album.get("name", "\u2014"),
                "Sortie":            album.get("release_date", "\u2014")[:4],
                "Énergie":           round(f.get("energy",      0.0), 2),
                "Dansabilité":       round(f.get("danceability", 0.0), 2),
                "Durée":             f"{mn}:{sc:02d}",
            })
        if not rows:
            return pd.DataFrame(columns=_COLS)
        df       = pd.DataFrame(rows)
        df.index = range(1, len(df) + 1)
        return df
    except Exception:
        return pd.DataFrame(columns=_COLS)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 3 — COUCHE BASE DE DONNÉES
# ══════════════════════════════════════════════════════════════════════════

DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_FILE      = Path("music_manager.db")


def _get_connection():
    """SQLite (défaut) ou PostgreSQL selon DATABASE_URL."""
    if DATABASE_URL.startswith("postgresql"):
        try:
            import psycopg2
            return psycopg2.connect(DATABASE_URL), "pg"
        except ImportError:
            st.error("psycopg2 non installé — pip install psycopg2-binary")
            st.stop()
    conn             = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"


def _ph(db_type: str) -> str:
    return "%s" if db_type == "pg" else "?"


def init_db() -> None:
    """
    Crée la table historique_artistes avec contrainte UNIQUE(spotify_id, date).
    Idempotente — appelée à chaque démarrage.
    """
    conn, _ = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historique_artistes (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            date_enregistrement DATE    NOT NULL,
            artiste_name        TEXT    NOT NULL,
            spotify_id          TEXT    NOT NULL,
            followers_count     INTEGER NOT NULL,
            popularity_score    INTEGER NOT NULL,
            UNIQUE (spotify_id, date_enregistrement)
        )
    """)
    conn.commit()
    conn.close()


def seed_fake_history(artist: dict) -> None:
    """
    Génère 52 semaines d'historique progressif si l'artiste n'en a aucun.
    Modèle : 70 % → 100 % des chiffres actuels sur 1 an, bruit déterministe.
    Failsafe total — ne lève jamais d'exception vers l'UI.

    Utilise deux connexions SQLite séparées (lecture puis écriture)
    pour éviter les verrous WAL qui bloquaient silencieusement les INSERTs.
    """
    try:
        # ── Lecture : y a-t-il déjà des données ? ────────────────────────
        conn_r, db_type = _get_connection()
        cur_r = conn_r.cursor()
        cur_r.execute(
            f"SELECT COUNT(*) FROM historique_artistes WHERE spotify_id = {_ph(db_type)}",
            (artist["spotify_id"],),
        )
        count = cur_r.fetchone()[0]
        conn_r.close()   # libère le verrou de lecture AVANT d'écrire

        if count > 0:
            return       # déjà seedé

        # ── Génération des lignes ─────────────────────────────────────────
        import random as _rnd
        rng       = _rnd.Random(artist["spotify_id"])
        today     = date.today()
        current_f = max(1, artist.get("followers_base",  1000))
        current_p = max(1, artist.get("popularity_base", 40))
        rows      = []

        for week in range(52, -1, -1):
            record_date = today - timedelta(weeks=week)
            progress    = (52 - week) / 52
            followers   = int(current_f * (0.70 + 0.30 * progress)
                             * (1.0 + rng.uniform(-0.03, 0.03)))
            popularity  = min(100, max(0, int(
                current_p * (0.80 + 0.20 * progress) + rng.uniform(-3, 3)
            )))
            rows.append((
                record_date.isoformat(),
                artist["name"],
                artist["spotify_id"],
                max(0, followers),
                popularity,
            ))

        # ── Écriture : nouvelle connexion propre ──────────────────────────
        conn_w, db_type_w = _get_connection()
        cur_w = conn_w.cursor()
        ph    = _ph(db_type_w)

        if db_type_w == "sqlite":
            cur_w.executemany(
                f"""INSERT OR REPLACE INTO historique_artistes
                    (date_enregistrement, artiste_name, spotify_id,
                     followers_count, popularity_score)
                    VALUES ({ph},{ph},{ph},{ph},{ph})""",
                rows,
            )
        else:
            cur_w.executemany(
                f"""INSERT INTO historique_artistes
                    (date_enregistrement, artiste_name, spotify_id,
                     followers_count, popularity_score)
                    VALUES ({ph},{ph},{ph},{ph},{ph})
                    ON CONFLICT (spotify_id, date_enregistrement)
                    DO UPDATE SET
                        artiste_name     = EXCLUDED.artiste_name,
                        followers_count  = EXCLUDED.followers_count,
                        popularity_score = EXCLUDED.popularity_score""",
                rows,
            )
        conn_w.commit()
        conn_w.close()

    except Exception:
        pass  # failsafe — jamais de crash UI à cause du seeding


def ensure_artist_has_history(artist: dict) -> None:
    """
    Vérifie qu'il y a ≥ 1 ligne en base pour cet artiste.
    Si non, lance seed_fake_history(). Double retry en cas d'erreur.
    Appelée immédiatement après resolve_artist() dans main().
    """
    try:
        conn, db_type = _get_connection()
        cur = conn.cursor()
        cur.execute(
            f"SELECT COUNT(*) FROM historique_artistes WHERE spotify_id = {_ph(db_type)}",
            (artist["spotify_id"],),
        )
        count = cur.fetchone()[0]
        conn.close()
        if count == 0:
            seed_fake_history(artist)
    except Exception:
        try:
            seed_fake_history(artist)
        except Exception:
            pass


def upsert_daily_stats(
    artiste_name:     str,
    spotify_id:       str,
    followers_count:  int,
    popularity_score: int,
    record_date:      date | None = None,
) -> None:
    """
    INSERT OR REPLACE de la stat du jour.
    Cliquer N fois = toujours 1 seule ligne → zéro spike vertical sur le graphe.
    """
    if record_date is None:
        record_date = date.today()
    conn, db_type = _get_connection()
    ph = _ph(db_type)
    if db_type == "sqlite":
        conn.execute(
            f"""INSERT OR REPLACE INTO historique_artistes
                (date_enregistrement, artiste_name, spotify_id,
                 followers_count, popularity_score)
                VALUES ({ph},{ph},{ph},{ph},{ph})""",
            (record_date.isoformat(), artiste_name, spotify_id,
             followers_count, popularity_score),
        )
    else:
        conn.execute(
            f"""INSERT INTO historique_artistes
                (date_enregistrement, artiste_name, spotify_id,
                 followers_count, popularity_score)
                VALUES ({ph},{ph},{ph},{ph},{ph})
                ON CONFLICT (spotify_id, date_enregistrement)
                DO UPDATE SET
                    artiste_name     = EXCLUDED.artiste_name,
                    followers_count  = EXCLUDED.followers_count,
                    popularity_score = EXCLUDED.popularity_score""",
            (record_date.isoformat(), artiste_name, spotify_id,
             followers_count, popularity_score),
        )
    conn.commit()
    conn.close()


def get_artist_history(
    spotify_id: str,
    date_from:  date | None = None,
    date_to:    date | None = None,
) -> pd.DataFrame:
    conn, db_type = _get_connection()
    ph     = _ph(db_type)
    query  = (
        f"SELECT date_enregistrement, followers_count, popularity_score "
        f"FROM historique_artistes WHERE spotify_id = {ph}"
    )
    params: list = [spotify_id]
    if date_from:
        query  += f" AND date_enregistrement >= {ph}"
        params.append(date_from.isoformat())
    if date_to:
        query  += f" AND date_enregistrement <= {ph}"
        params.append(date_to.isoformat())
    query += " ORDER BY date_enregistrement ASC"
    df    = pd.read_sql_query(query, conn, params=params)
    conn.close()
    df["date_enregistrement"] = pd.to_datetime(df["date_enregistrement"])
    return df


def get_latest_stats(spotify_id: str) -> dict:
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
    return dict(row) if row else {
        "followers_count": 0, "popularity_score": 0, "date_enregistrement": None
    }


def get_previous_stats(spotify_id: str) -> dict | None:
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
# SECTION 4 — COUCHE UI STREAMLIT / PLOTLY
# ══════════════════════════════════════════════════════════════════════════

def _plotly_layout(title: str = "", height: int = 320) -> dict:
    """
    Dict de base pour fig.update_layout().
    Utiliser layout.update({...}) puis fig.update_layout(layout)
    pour éviter le TypeError doublon de clé sur Python 3.14+.
    """
    return {
        "paper_bgcolor": PALETTE["chart_bg"],
        "plot_bgcolor":  PALETTE["chart_bg"],
        "font":   dict(family="Inter, Segoe UI, sans-serif",
                       color=PALETTE["text"], size=12),
        "title":  dict(text=title, font=dict(size=14, color=PALETTE["text"]), x=0),
        "height": height,
        "margin": dict(l=16, r=16, t=40 if title else 16, b=16),
        "legend": dict(bgcolor="rgba(0,0,0,0)",
                       bordercolor=PALETTE["border"], font=dict(size=11)),
        "xaxis":  dict(gridcolor=PALETTE["border"], linecolor=PALETTE["border"],
                       tickfont=dict(color=PALETTE["muted"], size=11)),
        "yaxis":  dict(gridcolor=PALETTE["border"], linecolor=PALETTE["border"],
                       tickfont=dict(color=PALETTE["muted"], size=11)),
    }


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

    followers   = latest["followers_count"]  or artist.get("followers_base",  0)
    popularity  = latest["popularity_score"] or artist.get("popularity_base", 0)
    last_update = latest.get("date_enregistrement") or "\u2014"
    delta_f     = followers  - previous["followers_count"]  if previous else 0
    delta_p     = popularity - previous["popularity_score"] if previous else 0

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
            label="\U0001f465 Followers Spotify",
            value=f"{followers:,}".replace(",", "\u202f"),
            delta=f"{delta_f:+,} vs. précédent".replace(",", "\u202f"),
        )

    with col_popularity:
        bar = "\u2588" * int(popularity / 10) + "\u2591" * (10 - int(popularity / 10))
        st.metric(
            label="\U0001f525 Score de Popularité",
            value=f"{popularity} / 100",
            delta=f"{delta_p:+d} pts vs. précédent",
        )
        st.markdown(
            f"<div style='font-size:0.85rem;color:{PALETTE['lime']};letter-spacing:2px'>"
            f"{bar}</div>",
            unsafe_allow_html=True,
        )

    with col_info:
        st.markdown(f"""
            <div class="metric-box">
              <div class="metric-label">Dernière synchro</div>
              <div style="font-size:1.05rem;font-weight:700;
                          color:{PALETTE['text']};margin:0.4rem 0;">
                {last_update}
              </div>
              <div class="metric-label" style="margin-top:0.8rem;">Spotify ID</div>
              <div style="font-size:0.72rem;color:{PALETTE['muted']};
                          font-family:monospace;word-break:break-all;">
                {artist['spotify_id']}
              </div>
              <div class="metric-label" style="margin-top:0.8rem;">Genre</div>
              <div style="font-size:0.82rem;color:{PALETTE['teal']};">
                {artist.get('genre', 'N/A')}
              </div>
            </div>
        """, unsafe_allow_html=True)


# ── Section 2 : Démographie Audience ─────────────────────────────────────

def section_audience_demographics(artist: dict) -> None:
    """
    Visualise la démographie de l'audience de l'artiste.
    Les données (genre, âge) sont hardcodées dans AUDIENCE_GENDER et AUDIENCE_AGE
    car l'API Spotify ne les expose pas publiquement.
    """
    st.markdown("""
        <div class='section-card'>
          <div class='section-label'>Section 02</div>
          <div class='section-title'>Démographie de l'Audience</div>
        </div>
    """, unsafe_allow_html=True)

    col_gender, col_age = st.columns([1, 1.6], gap="large")

    # ── Donut : répartition genre ─────────────────────────────────────────
    with col_gender:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem;'>"
            f"\U0001f464 Répartition Genre</div>",
            unsafe_allow_html=True,
        )
        labels = list(AUDIENCE_GENDER.keys())
        values = list(AUDIENCE_GENDER.values())

        fig_donut = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=0.60,
            marker=dict(
                colors=[PALETTE["lime"], PALETTE["purple"]],
                line=dict(color=PALETTE["bg"], width=3),
            ),
            textfont=dict(color=PALETTE["text"], size=13, family="Inter"),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>%{value} %<extra></extra>",
        ))

        # Annotation centrale
        fig_donut.update_layout(
            **_plotly_layout(height=300),
            showlegend=False,
            annotations=[dict(
                text=f"<b>{artist['name'].split()[0]}</b><br><span style='font-size:11px'>Audience</span>",
                x=0.5, y=0.5, font_size=14, font_color=PALETTE["text"],
                showarrow=False,
            )],
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # ── Bar chart horizontal : distribution par âge ───────────────────────
    with col_age:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem;'>"
            f"\U0001f4ca Distribution par Tranche d'Âge</div>",
            unsafe_allow_html=True,
        )
        age_labels = list(AUDIENCE_AGE.keys())
        age_values = list(AUDIENCE_AGE.values())

        # Dégradé de couleur lime → purple selon la tranche
        n = len(age_labels)
        bar_colors = [
            f"rgba({int(200 - (200 - 155) * i / (n - 1))}, "
            f"{int(241 - (241 - 109) * i / (n - 1))}, "
            f"{int(53  + (255 -  53) * i / (n - 1))}, 0.85)"
            for i in range(n)
        ]

        fig_age = go.Figure(go.Bar(
            y=age_labels,
            x=age_values,
            orientation="h",
            marker=dict(
                color=bar_colors,
                line=dict(color=PALETTE["bg"], width=1),
            ),
            text=[f"{v} %" for v in age_values],
            textposition="inside",
            textfont=dict(color=PALETTE["bg"], size=12, family="Inter"),
            hovertemplate="<b>%{y}</b><br>%{x} %<extra></extra>",
        ))

        layout_age = _plotly_layout(height=300)
        layout_age.update({
            "xaxis": dict(
                title="% de l'audience",
                range=[0, max(age_values) * 1.15],
                gridcolor=PALETTE["border"],
                tickfont=dict(color=PALETTE["muted"], size=11),
            ),
            "yaxis": dict(
                autorange="reversed",
                tickfont=dict(color=PALETTE["text"], size=12),
                gridcolor=PALETTE["border"],
            ),
            "bargap": 0.25,
        })
        fig_age.update_layout(layout_age)
        st.plotly_chart(fig_age, use_container_width=True)


# ── Section 3 : Le Chansonomètre ─────────────────────────────────────────

def section_chansonometre(artist: dict) -> None:
    st.markdown("""
        <div class='section-card'>
          <div class='section-label'>Section 03</div>
          <div class='section-title'>Le Chansonomètre — Analyse du Catalogue</div>
        </div>
    """, unsafe_allow_html=True)

    top10 = fetch_top_tracks_df(artist["spotify_id"])
    col_table, col_scatter = st.columns([1.1, 1.1], gap="large")

    with col_table:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem;'>"
            f"\U0001f3c6 Top 10 Hits Spotify</div>",
            unsafe_allow_html=True,
        )
        if top10.empty:
            st.info("Données Spotify non disponibles.")
        else:
            st.dataframe(
                top10,
                use_container_width=True,
                height=360,
                column_config={
                    "Popularité": st.column_config.ProgressColumn(
                        "Popularité", min_value=0, max_value=100, format="%d",
                    ),
                    "Sortie": st.column_config.TextColumn("Sortie"),
                    "Album":  st.column_config.TextColumn("Album"),
                },
            )

    with col_scatter:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem;'>"
            f"\U0001f4ca Énergie \u00d7 Dansabilité</div>",
            unsafe_allow_html=True,
        )
        if top10.empty:
            st.info("Données Spotify non disponibles.")
        else:
            fig = px.scatter(
                top10.reset_index().rename(columns={"index": "Rang"}),
                x="Énergie", y="Dansabilité",
                size="Popularité", color="Popularité",
                hover_name="\U0001f3b5  Titre",
                hover_data={"Album": True, "Sortie": True},
                color_continuous_scale=[
                    [0,   PALETTE["purple"]],
                    [0.5, PALETTE["teal"]],
                    [1,   PALETTE["lime"]],
                ],
                size_max=32,
            )
            fig.update_layout(**_plotly_layout(height=360))
            fig.update_coloraxes(showscale=False)
            fig.update_traces(marker=dict(line=dict(color=PALETTE["bg"], width=1.5)))
            st.plotly_chart(fig, use_container_width=True)


# ── Section 4 : Tendances temporelles ────────────────────────────────────

def section_trends(
    artist:    dict,
    date_from: date,
    date_to:   date,
) -> None:
    st.markdown("""
        <div class='section-card'>
          <div class='section-label'>Section 04</div>
          <div class='section-title'>Vision Temporelle — Court terme vs. Long terme</div>
        </div>
    """, unsafe_allow_html=True)

    col_line, col_radar = st.columns([1.2, 1], gap="large")

    with col_line:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.3rem;'>"
            f"\U0001f4c8 Streams estimés (base de données)</div>",
            unsafe_allow_html=True,
        )
        granularity = st.radio(
            label="Agrégation",
            options=list(_RESAMPLE_ALIAS.keys()),
            index=1,
            horizontal=True,
            label_visibility="collapsed",
        )
        df_hist = get_artist_history(artist["spotify_id"], date_from, date_to)

        if df_hist.empty:
            st.info("Aucune donnée dans la plage temporelle sélectionnée.")
        else:
            df_hist["streams_estimated"] = df_hist["followers_count"] * 12.5
            alias = _RESAMPLE_ALIAS[granularity]
            df_r  = (
                df_hist
                .set_index("date_enregistrement")
                .resample(alias)
                .agg(
                    streams_estimated=("streams_estimated", "sum"),
                    popularity_score=("popularity_score",  "mean"),
                )
                .dropna()
                .reset_index()
                .rename(columns={"date_enregistrement": "date"})
            )

            fig_line = go.Figure()

            # Streams — lime, rempli, markers sur chaque point de synchro
            fig_line.add_trace(go.Scatter(
                x=df_r["date"],
                y=df_r["streams_estimated"],
                mode="lines+markers",
                name="Streams estimés",
                line=dict(color=PALETTE["lime"], width=2.5),
                marker=dict(
                    color=PALETTE["lime"], size=6, symbol="circle",
                    line=dict(color=PALETTE["bg"], width=1.5),
                ),
                fill="tozeroy",
                fillcolor=_FILL_LIME,
                hovertemplate=(
                    "<b>%{x|%d %b %Y}</b><br>"
                    "Streams\u00a0: <b>%{y:,.0f}</b><extra></extra>"
                ),
            ))

            # Popularité — purple, pointillé, axe droit
            fig_line.add_trace(go.Scatter(
                x=df_r["date"],
                y=df_r["popularity_score"],
                mode="lines+markers",
                name="Popularité",
                yaxis="y2",
                line=dict(color=PALETTE["purple"], width=1.8, dash="dot"),
                marker=dict(
                    color=PALETTE["purple"], size=5, symbol="square",
                    line=dict(color=PALETTE["bg"], width=1),
                ),
                hovertemplate="Popularité\u00a0: <b>%{y:.1f}</b>/100<extra></extra>",
            ))

            layout = _plotly_layout(height=360)
            layout.update({
                "yaxis": dict(
                    title="Streams estimés",
                    gridcolor=PALETTE["border"],
                    linecolor=PALETTE["border"],
                    tickfont=dict(color=PALETTE["muted"], size=11),
                ),
                "yaxis2": dict(
                    title="Popularité /100",
                    overlaying="y", side="right",
                    range=[0, 100], showgrid=False,
                    tickfont=dict(color=PALETTE["purple"]),
                ),
                "legend": dict(
                    orientation="h", yanchor="bottom", y=1.02,
                    xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)",
                    bordercolor=PALETTE["border"], font=dict(size=11),
                ),
            })
            fig_line.update_layout(layout)
            st.plotly_chart(fig_line, use_container_width=True)

    with col_radar:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem;'>"
            f"\U0001f578\ufe0f Profil Audio vs. Marché</div>",
            unsafe_allow_html=True,
        )
        profile         = artist.get("audio_profile") or _NEUTRAL_PROFILE
        categories      = list(MARKET_REFERENCE.keys())
        categories_loop = categories + [categories[0]]
        artist_vals     = [profile.get(c, 0.5)  for c in categories]
        market_vals     = [MARKET_REFERENCE[c]   for c in categories]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=[v * 100 for v in market_vals] + [market_vals[0] * 100],
            theta=categories_loop,
            fill="toself", fillcolor=_FILL_MUTED,
            line=dict(color=PALETTE["muted"], width=1.5, dash="dot"),
            name="Standard marché",
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[v * 100 for v in artist_vals] + [artist_vals[0] * 100],
            theta=categories_loop,
            fill="toself", fillcolor=_FILL_RADAR,
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
                orientation="h", yanchor="bottom", y=-0.15,
                xanchor="center", x=0.5,
                font=dict(size=11), bgcolor="rgba(0,0,0,0)",
            ),
        )
        st.plotly_chart(fig_radar, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 5 — POINT D'ENTRÉE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    # ── 5.1  Init DB ──────────────────────────────────────────────────────
    init_db()

    # ── 5.2  Résolution artiste & seeding IMMÉDIAT ────────────────────────
    # L'artiste est résolu UNE SEULE FOIS (hardcodé) et le seeding est
    # exécuté AVANT toute construction de la sidebar ou des métriques,
    # garantissant que le compteur "N enregistrements" voit les lignes.
    artist = resolve_artist(HARDCODED_ARTIST_ID)

    if artist is None:
        st.error(
            f"Impossible de charger l'artiste `{HARDCODED_ARTIST_ID}` depuis Spotify.\n\n"
            "Vérifiez que l'ID est correct et que vos credentials API sont valides."
        )
        st.stop()

    # Profil audio réel (mis en cache 15 min)
    artist["audio_profile"] = fetch_audio_profile(artist["spotify_id"])

    # Seeding immédiat — AVANT la sidebar, AVANT le compteur de lignes
    ensure_artist_has_history(artist)

    # ── 5.3  SIDEBAR ──────────────────────────────────────────────────────
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

        # Carte artiste
        st.markdown(f"""
            <div style="text-align:center;padding:0.8rem 0 0.4rem;">
              <img src="{artist['photo_url']}"
                   style="width:72px;height:72px;border-radius:50%;object-fit:cover;
                          border:2px solid {PALETTE['lime']};"
                   onerror="this.src='https://via.placeholder.com/72/161920/C8F135?text=?'"/>
              <div style="font-size:1rem;font-weight:800;color:{PALETTE['text']};
                          margin-top:0.5rem;">{artist['name']}</div>
              <div style="font-size:0.75rem;color:{PALETTE['muted']};">{artist['genre']}</div>
            </div>
        """, unsafe_allow_html=True)

        # ── Filtre temporel ───────────────────────────────────────────────
        st.markdown("<div class='sidebar-section'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='sidebar-label'>\U0001f4c5 Fenêtre temporelle</div>",
            unsafe_allow_html=True,
        )
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
        st.caption(
            f"Du **{date_from.strftime('%d %b %Y')}**"
            f" au **{date_to.strftime('%d %b %Y')}**"
        )

        # ── Bouton de capture ─────────────────────────────────────────────
        st.markdown("<div class='sidebar-section'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='sidebar-label'>\U0001f504 Synchronisation</div>",
            unsafe_allow_html=True,
        )

        if st.button("\u25b6\ufe0f  Capturer les stats aujourd'hui"):
            try:
                # Lecture live directe — bypass du cache
                sp   = init_spotify()
                live = sp.artist(artist["spotify_id"])
                new_f = live["followers"]["total"]
                new_p = live["popularity"]
            except Exception:
                latest = get_latest_stats(artist["spotify_id"])
                new_f  = latest["followers_count"]
                new_p  = latest["popularity_score"]

            upsert_daily_stats(
                artiste_name=artist["name"],
                spotify_id=artist["spotify_id"],
                followers_count=new_f,
                popularity_score=new_p,
            )
            st.success(
                f"\u2705 Capturé — {today.strftime('%d/%m/%Y')}\n\n"
                f"Followers\u00a0: **{new_f:,}**\u00a0|\u00a0"
                f"Pop.\u00a0: **{new_p}/100**"
            )
            st.rerun()

        # ── Infos DB ──────────────────────────────────────────────────────
        st.markdown("<div class='sidebar-section'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='sidebar-label'>\U0001f5c4\ufe0f Base de données</div>",
            unsafe_allow_html=True,
        )
        db_label = (
            "PostgreSQL"
            if DATABASE_URL.startswith("postgresql")
            else f"SQLite — {DB_FILE.name}"
        )
        st.markdown(
            f"<div style='font-size:0.75rem;color:{PALETTE['teal']};'>"
            f"Moteur\u00a0: <strong>{db_label}</strong></div>",
            unsafe_allow_html=True,
        )
        # Compteur de lignes — lu APRÈS ensure_artist_has_history, toujours > 0
        conn_c, _ = _get_connection()
        cur_c     = conn_c.cursor()
        cur_c.execute("SELECT COUNT(*) FROM historique_artistes")
        nb_rows   = cur_c.fetchone()[0]
        conn_c.close()
        st.caption(f"{nb_rows} enregistrements dans la base.")

    # ── 5.4  EN-TÊTE PRINCIPAL ────────────────────────────────────────────
    st.markdown(f"""
        <div class="subtitle-tag">DIGITAL NEXT — Music Intelligence</div>
        <div class="main-title">
            Tableau de bord <span>{artist['name']}</span>
        </div>
        <div style="color:{PALETTE['muted']};font-size:0.9rem;margin:0.4rem 0 1.8rem;">
            Analyse de performance\u00a0\u00b7
            Données du {date_from.strftime('%d %b %Y')}
            au {date_to.strftime('%d %b %Y')}
        </div>
    """, unsafe_allow_html=True)

    # ── 5.5  SECTIONS ─────────────────────────────────────────────────────
    section_hud(artist)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    section_audience_demographics(artist)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    section_chansonometre(artist)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    section_trends(artist, date_from, date_to)

    # ── 5.6  FOOTER ───────────────────────────────────────────────────────
    st.markdown(f"""
        <div style="border-top:1px solid {PALETTE['border']};margin-top:2.5rem;
                    padding-top:1rem;text-align:center;
                    font-size:0.72rem;color:{PALETTE['muted']};">
            Music Manager Dashboard\u00a0\u00b7 Digital Next / RBK Groupe\u00a0\u00b7
            Historique partiellement simul\u00e9
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
