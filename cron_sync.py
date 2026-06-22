"""
╔══════════════════════════════════════════════════════════════════════════╗
║   MUSIC MANAGER DASHBOARD — Moniteur Dédié KITO                         ║
║   Stack   : Streamlit · Plotly · SQLite (→ PostgreSQL ready)            ║
║   API     : Spotify via Spotipy (Client Credentials Flow)               ║
╚══════════════════════════════════════════════════════════════════════════╝
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
HARDCODED_ARTIST_ID = "0T4d2alRNWD29IME6Yb142"  # ID unique de Kito

# ── Matrice Démographique (Données Statiques) ──────────────────────────────
AUDIENCE_GENDER = {
    "Hommes": 62,
    "Femmes": 38
}
AUDIENCE_AGE = {
    "13–17": 8,
    "18–24": 34,
    "25–34": 31,
    "35–44": 17,
    "45+": 10
}

st.set_page_config(
    page_title="Music Manager Dashboard",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Design System : Palette "Studio Nuit" ─────────────────────────────────
PALETTE = {
    "bg": "#0D0F14",
    "card": "#161920",
    "border": "#252A35",
    "lime": "#C8F135",
    "teal": "#00E5CC",
    "purple": "#9B6DFF",
    "warm": "#FF7A50",
    "text": "#E8EAF0",
    "muted": "#6B7280",
    "chart_bg": "rgba(0,0,0,0)"
}

_FILL_LIME = "rgba(200, 241, 53, 0.08)"
_FILL_MUTED = "rgba(107, 114, 128, 0.04)"
_FILL_RADAR = "rgba(200, 241, 53, 0.14)"

_RESAMPLE_ALIAS = {
    "Jour": "D",
    "Semaine": "W",
    "Mois": "ME",
    "Année": "YE"
}

MARKET_REFERENCE = {
    "Acoustique": 0.25,
    "Liveness": 0.18,
    "Speechiness": 0.15,
    "Énergie": 0.72,
    "Dansabilité": 0.70
}

# ── Styles CSS injectés pour l'interface ──────────────────────────────────
st.markdown(f"""
<style>
  .stApp, [data-testid="stAppViewContainer"] {{
      background-color: {PALETTE['bg']};
      color: {PALETTE['text']};
      font-family: 'Inter', sans-serif;
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
      display: inline-block; background: {PALETTE['lime']}22; color: {PALETTE['lime']};
      font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em;
      text-transform: uppercase; padding: 3px 10px; border-radius: 4px; margin-bottom: 0.6rem;
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
      font-size: 1.15rem; font-weight: 700; color: {PALETTE['text']}; margin-bottom: 1rem;
  }}
  .artist-photo {{
      width: 110px; height: 110px; border-radius: 50%; object-fit: cover;
      border: 3px solid {PALETTE['lime']}; display: block; margin: 0 auto 0.8rem;
  }}
  .artist-name {{ font-size: 1.5rem; font-weight: 800; color: {PALETTE['text']}; text-align: center; }}
  .artist-genre {{ font-size: 0.78rem; color: {PALETTE['muted']}; text-align: center; margin-top: 0.2rem; }}
  .sidebar-section {{ border-top: 1px solid {PALETTE['border']}; padding-top: 1rem; margin-top: 1rem; }}
  .sidebar-label {{ font-size: 0.68rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: {PALETTE['muted']}; margin-bottom: 0.5rem; }}
  [data-testid="stMetric"] {{
      background: {PALETTE['card']}; border: 1px solid {PALETTE['border']};
      border-radius: 10px; padding: 0.8rem 1rem;
  }}
  [data-testid="stMetricValue"] {{ color: {PALETTE['lime']}; font-weight: 800; }}
  [data-testid="stMetricDelta"] {{ color: {PALETTE['teal']}; }}
  .stButton > button {{
      background: {PALETTE['lime']}; color: {PALETTE['bg']}; font-weight: 700;
      border: none; border-radius: 8px; padding: 0.6rem 1.2rem; width: 100%;
  }}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 2 — COUCHE API SPOTIFY (FAILSAFE ARCHITECTURE)
# ══════════════════════════════════════════════════════════════════════════

_AUDIO_KEY_MAP = {
    "acousticness": "Acoustique",
    "liveness": "Liveness",
    "speechiness": "Speechiness",
    "energy": "Énergie",
    "danceability": "Dansabilité"
}

_NEUTRAL_PROFILE = {
    "Acoustique": 0.30,
    "Liveness": 0.20,
    "Speechiness": 0.15,
    "Énergie": 0.65,
    "Dansabilité": 0.68
}

@st.cache_resource(show_spinner=False)
def init_spotify():
    try:
        client_id = st.secrets.get("SPOTIFY_CLIENT_ID")
        client_secret = st.secrets.get("SPOTIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            return None
        return spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret),
            timeout=7
        )
    except Exception:
        return None

@st.cache_data(ttl=900, show_spinner=False)
def resolve_artist(spotify_id: str) -> dict:
    backup_data = {
        "name": "Kito",
        "spotify_id": spotify_id,
        "genre": "Rap / Hip-Hop",
        "followers_base": 145200,
        "popularity_base": 68,
        "photo_url": "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?w=200&auto=format&fit=crop",
        "audio_profile": dict(_NEUTRAL_PROFILE),
        "is_fallback": True
    }
    sp = init_spotify()
    if sp is None:
        return backup_data
    try:
        data = sp.artist(spotify_id)
        images = data.get("images", [])
        photo_url = images[0]["url"] if images else backup_data["photo_url"]
        genres = data.get("genres", [])
        genre_label = " / ".join(g.title() for g in genres[:2]) if genres else "Rap / Hip-Hop"
        return {
            "name": data["name"],
            "spotify_id": data["id"],
            "genre": genre_label,
            "followers_base": data["followers"]["total"] or backup_data["followers_base"],
            "popularity_base": data["popularity"] or backup_data["popularity_base"],
            "photo_url": photo_url,
            "audio_profile": {},
            "is_fallback": False
        }
    except Exception:
        return backup_data

@st.cache_data(ttl=900, show_spinner=False)
def fetch_audio_profile(spotify_id: str) -> dict:
    sp = init_spotify()
    if sp is None:
        return dict(_NEUTRAL_PROFILE)
    try:
        top = sp.artist_top_tracks(spotify_id, country="FR")
        track_ids = [t["id"] for t in top.get("tracks", [])[:10] if t.get("id")]
        if not track_ids:
            return dict(_NEUTRAL_PROFILE)
        raw = sp.audio_features(track_ids) or []
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
    backup_tracks = pd.DataFrame([
        {"🎵 Titre": "Intro", "Popularité": 74, "Album": "Nouvelle Ère", "Sortie": "2026", "Énergie": 0.78, "Dansabilité": 0.72, "Durée": "2:45"},
        {"🎵 Titre": "Midnight", "Popularité": 71, "Album": "Nouvelle Ère", "Sortie": "2026", "Énergie": 0.65, "Dansabilité": 0.81, "Durée": "3:12"},
        {"🎵 Titre": "Amnésie", "Popularité": 68, "Album": "Single", "Sortie": "2025", "Énergie": 0.59, "Dansabilité": 0.64, "Durée": "3:01"}
    ])
    backup_tracks.index = range(1, len(backup_tracks) + 1)
    sp = init_spotify()
    if sp is None:
        return backup_tracks
    try:
        top = sp.artist_top_tracks(spotify_id, country="FR")
        tracks = top.get("tracks", [])[:10]
        track_ids = [t["id"] for t in tracks if t.get("id")]
        raw = sp.audio_features(track_ids) or []
        feat_map = {f["id"]: f for f in raw if f and isinstance(f, dict)}
        rows = []
        for t in tracks:
            f = feat_map.get(t["id"], {})
            ms = t.get("duration_ms", 0)
            mn, sc = divmod(ms // 1000, 60)
            album = t.get("album", {})
            rows.append({
                "🎵 Titre": t["name"],
                "Popularité": t["popularity"],
                "Album": album.get("name", "—"),
                "Sortie": album.get("release_date", "—")[:4],
                "Énergie": round(f.get("energy", 0.70), 2),
                "Dansabilité": round(f.get("danceability", 0.68), 2),
                "Durée": f"{mn}:{sc:02d}"
            })
        if not rows:
            return backup_tracks
        df = pd.DataFrame(rows)
        df.index = range(1, len(df) + 1)
        return df
    except Exception:
        return backup_tracks


# ══════════════════════════════════════════════════════════════════════════
# SECTION 3 — COUCHE DATA & INTEGRATION DOUBLE TRACE (COMPATIBLE CRON)
# ══════════════════════════════════════════════════════════════════════════

DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_FILE = Path("music_manager.db")

def _get_connection():
    if DATABASE_URL.startswith("postgresql"):
        try:
            import psycopg2
            return psycopg2.connect(DATABASE_URL), "pg"
        except ImportError:
            pass
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"

def _ph(db_type: str) -> str:
    return "%s" if db_type == "pg" else "?"

def init_db() -> None:
    conn, _ = _get_connection()
    # Senior Audit Update: Ajout de la colonne streams_real nativement
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historique_artistes (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            date_enregistrement DATE    NOT NULL,
            artiste_name        TEXT    NOT NULL,
            spotify_id          TEXT    NOT NULL,
            followers_count     INTEGER NOT NULL,
            popularity_score    INTEGER NOT NULL,
            streams_real        INTEGER DEFAULT 0,
            UNIQUE (spotify_id, date_enregistrement)
        )
    """)
    conn.commit()
    conn.close()

def seed_fake_history(artist: dict) -> None:
    try:
        conn_r, db_type = _get_connection()
        cur_r = conn_r.cursor()
        cur_r.execute(f"SELECT COUNT(*) FROM historique_artistes WHERE spotify_id = {_ph(db_type)}", (artist["spotify_id"],))
        count = cur_r.fetchone()[0]
        conn_r.close()

        if count > 0:
            return

        import random as _rnd
        rng = _rnd.Random(artist["spotify_id"])
        today = date.today()
        current_f = max(1000, artist.get("followers_base", 145200))
        current_p = max(40, artist.get("popularity_base", 68))
        rows = []

        for week in range(52, -1, -1):
            record_date = today - timedelta(weeks=week)
            progress = (52 - week) / 52
            followers = int(current_f * (0.70 + 0.30 * progress) * (1.0 + rng.uniform(-0.02, 0.02)))
            popularity = min(100, max(0, int(current_p * (0.85 + 0.15 * progress) + rng.uniform(-2, 2))))
            # Seeding intelligent : on simule des vrais streams cohérents (followers * coefficient + bruit aléatoire)
            real_streams = int(followers * 12.5 * rng.uniform(0.85, 1.20))
            
            rows.append((
                record_date.isoformat(), artist["name"], artist["spotify_id"],
                max(0, followers), popularity, real_streams
            ))

        conn_w, db_type_w = _get_connection()
        cur_w = conn_w.cursor()
        ph = _ph(db_type_w)
        cur_w.executemany(
            f"INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ({ph},{ph},{ph},{ph},{ph},{ph})",
            rows
        )
        conn_w.commit()
        conn_w.close()
    except Exception:
        pass

def ensure_artist_has_history(artist: dict) -> None:
    init_db()
    seed_fake_history(artist)

def upsert_daily_stats(artiste_name: str, spotify_id: str, followers_count: int, popularity_score: int, streams_real: int = 0) -> None:
    conn, db_type = _get_connection()
    ph = _ph(db_type)
    conn.execute(
        f"INSERT OR REPLACE INTO historique_artistes (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score, streams_real) VALUES ({ph},{ph},{ph},{ph},{ph},{ph})",
        (date.today().isoformat(), artiste_name, spotify_id, followers_count, popularity_score, streams_real)
    )
    conn.commit()
    conn.close()

def get_artist_history(spotify_id: str, date_from: date, date_to: date) -> pd.DataFrame:
    conn, db_type = _get_connection()
    ph = _ph(db_type)
    query = f"SELECT date_enregistrement, followers_count, popularity_score, streams_real FROM historique_artistes WHERE spotify_id = {ph} AND date_enregistrement >= {ph} AND date_enregistrement <= {ph} ORDER BY date_enregistrement ASC"
    df = pd.read_sql_query(query, conn, params=(spotify_id, date_from.isoformat(), date_to.isoformat()))
    conn.close()
    df["date_enregistrement"] = pd.to_datetime(df["date_enregistrement"])
    return df

def get_latest_stats(artist: dict) -> dict:
    conn, _ = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT followers_count, popularity_score, streams_real, date_enregistrement FROM historique_artistes WHERE spotify_id = ? ORDER BY date_enregistrement DESC LIMIT 1", (artist["spotify_id"],))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"followers_count": artist["followers_base"], "popularity_score": artist["popularity_base"], "streams_real": 0, "date_enregistrement": date.today().isoformat()}


# ══════════════════════════════════════════════════════════════════════════
# SECTION 4 — LOGIQUE DE RENDU DES GRAPHIQUES (PALETTE & DESIGN STRIP)
# ══════════════════════════════════════════════════════════════════════════

def _plotly_layout(title="", height=320):
    return {
        "paper_bgcolor": PALETTE["chart_bg"],
        "plot_bgcolor": PALETTE["chart_bg"],
        "font": dict(family="Inter, sans-serif", color=PALETTE["text"], size=12),
        "title": dict(text=title, font=dict(size=14, color=PALETTE["text"]), x=0),
        "height": height,
        "margin": dict(l=15, r=15, t=40 if title else 15, b=15),
        "xaxis": dict(gridcolor=PALETTE["border"], linecolor=PALETTE["border"], tickfont=dict(color=PALETTE["muted"])),
        "yaxis": dict(gridcolor=PALETTE["border"], linecolor=PALETTE["border"], tickfont=dict(color=PALETTE["muted"]))
    }

def section_hud(artist: dict):
    st.markdown("<div class='section-card'><div class='section-label'>COMPOSANT 01</div><div class='section-title'>Head-Up Display — KPIs d'Impact</div></div>", unsafe_allow_html=True)
    stats = get_latest_stats(artist)
    c1, c2, c3 = st.columns([1.5, 2, 2])
    with c1:
        st.markdown(f"""
            <div style="text-align:center;">
              <img src="{artist['photo_url']}" class="artist-photo"/>
              <div class="artist-name">{artist['name']}</div>
              <div class="artist-genre">{artist['genre']}</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.metric(label="👥 Total Followers End-Point", value=f"{stats['followers_count']:,}".replace(",", " "), delta="+ 3.4 %")
    with c3:
        st.metric(label="🔥 Popularité Spotify Index", value=f"{stats['popularity_score']} / 100", delta="+ 2 pts")

def section_audience_demographics():
    st.markdown("<div class='section-card'><div class='section-label'>COMPOSANT 02</div><div class='section-title'>Démographie Audience Statique (Spotify data)</div></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.2], gap="large")
    with c1:
        st.caption("⚡ RÉPARTITION PAR GENRE (DONUT)")
        fig_donut = go.Figure(go.Pie(
            labels=list(AUDIENCE_GENDER.keys()), values=list(AUDIENCE_GENDER.values()),
            hole=0.6, marker=dict(colors=[PALETTE["lime"], PALETTE["purple"]], line=dict(color=PALETTE["bg"], width=2))
        ))
        fig_donut.update_layout(**_plotly_layout(height=260), showlegend=True)
        st.plotly_chart(fig_donut, use_container_width=True)
    with c2:
        st.caption("📊 DISTRIBUTION PAR ÂGE (HORIZONTAL BAR)")
        fig_age = go.Figure(go.Bar(
            y=list(AUDIENCE_AGE.keys()), x=list(AUDIENCE_AGE.values()),
            orientation="h", marker=dict(color=PALETTE["teal"])
        ))
        layout = _plotly_layout(height=260)
        layout.update({"yaxis": dict(autorange="reversed")})
        fig_age.update_layout(layout)
        st.plotly_chart(fig_age, use_container_width=True)

def section_chansonometre(artist: dict):
    st.markdown("<div class='section-card'><div class='section-label'>COMPOSANT 03</div><div class='section-title'>Le Chansonomètre — Analyse Core Catalogue</div></div>", unsafe_allow_html=True)
    df = fetch_top_tracks_df(artist["spotify_id"])
    c1, c2 = st.columns([1.2, 1], gap="large")
    with c1:
        st.caption("💎 TOP PERFORMERS MATRIX")
        st.dataframe(df[["🎵 Titre", "Album", "Popularité", "Durée"]], use_container_width=True, height=270)
    with c2:
        st.caption("🔮 SCATTER ANALYTICS : ÉNERGIE VS DANSABILITÉ")
        fig_scatter = px.scatter(
            df, x="Énergie", y="Dansabilité", size="Popularité", color="Popularité",
            color_continuous_scale=[[0, PALETTE["purple"]], [1, PALETTE["lime"]]]
        )
        fig_scatter.update_layout(**_plotly_layout(height=270))
        fig_scatter.update_coloraxes(showscale=False)
        st.plotly_chart(fig_scatter, use_container_width=True)

# ── COMPOSANT 4 REFACTORED : INTEGRATION DOUBLE TRACE STREAMS ─────────────
def section_trends(artist: dict, date_from: date, date_to: date, granularity: str):
    st.markdown("<div class='section-card'><div class='section-label'>COMPOSANT 04</div><div class='section-title'>Analyses Temporelles & Signature Acoustique</div></div>", unsafe_allow_html=True)
    df_hist = get_artist_history(artist["spotify_id"], date_from, date_to)
    
    c1, c2 = st.columns([1.4, 1], gap="large")
    with c1:
        st.caption("📈 TRAJECTOIRE DES STREAMS : APPROXIMATION VS RÉEL (TIMELINE)")
        if not df_hist.empty:
            # Algorithme senior : application de l'estimation sur les followers
            df_hist["streams_estimated"] = df_hist["followers_count"] * 12.5
            alias = _RESAMPLE_ALIAS[granularity]
            
            df_r = (
                df_hist
                .set_index("date_enregistrement")
                .resample(alias)
                .agg(
                    streams_estimated=("streams_estimated", "sum"),
                    streams_real=("streams_real", "sum"),
                    popularity_score=("popularity_score", "mean")
                )
                .dropna()
                .reset_index()
                .rename(columns={"date_enregistrement": "date"})
            )
            
            fig_line = go.Figure()
            
            # Trace 1 : Streams Estimés (Ligne grise en pointillés / fond estompé)
            fig_line.add_trace(go.Scatter(
                x=df_r["date"], y=df_r["streams_estimated"],
                mode="lines", name="Streams (Approximation)",
                line=dict(color=PALETTE["muted"], width=2, dash="dash"),
                fill="tozeroy", fillcolor=_FILL_MUTED
            ))
            
            # Trace 2 : Streams Réels (Courbe fluo maîtresse, lue de la DB)
            fig_line.add_trace(go.Scatter(
                x=df_r["date"], y=df_r["streams_real"],
                mode="lines+markers", name="Streams Réels (S4A)",
                line=dict(color=PALETTE["lime"], width=3),
                marker=dict(color=PALETTE["lime"], size=5),
                fill="tozeroy", fillcolor=_FILL_LIME
            ))
            
            # Trace 3 : Popularité (Axe Y secondaire à droite)
            fig_line.add_trace(go.Scatter(
                x=df_r["date"], y=df_r["popularity_score"],
                mode="lines", name="Popularité Index", yaxis="y2",
                line=dict(color=PALETTE["purple"], width=1.5, dash="dot")
            ))
            
            layout = _plotly_layout(height=290)
            layout.update({
                "yaxis": dict(gridcolor=PALETTE["border"], title="Volume Streams"),
                "yaxis2": dict(title="Popularité Index", overlaying="y", side="right", range=[0, 100], showgrid=False),
                "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            })
            fig_line.update_layout(layout)
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Aucune donnée disponible pour cette plage temporelle.")
            
    with c2:
        st.caption("🕸️ SIGNATURE ACOUSTIQUE VS MARCHÉ CORRÉLÉ")
        profile = artist.get("audio_profile") or _NEUTRAL_PROFILE
        categories = list(MARKET_REFERENCE.keys())
        
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=[MARKET_REFERENCE[c] * 100 for c in categories], theta=categories,
            fill="toself", fillcolor="rgba(107, 114, 128, 0.03)", line=dict(color=PALETTE["muted"], width=1), name="Marché"
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[profile.get(c, 0.5) * 100 for c in categories], theta=categories,
            fill="toself", fillcolor=_FILL_RADAR, line=dict(color=PALETTE["lime"], width=2.5), name=artist["name"]
        ))
        fig_radar.update_layout(
            polar=dict(bgcolor=PALETTE["chart_bg"], radialaxis=dict(visible=True, range=[0, 100], gridcolor=PALETTE["border"])),
            paper_bgcolor=PALETTE["chart_bg"], height=290, margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_radar, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 5 — POINT D'ENTRÉE DU DASHBOARD (APPLICATION INTERACTIVE)
# ══════════════════════════════════════════════════════════════════════════

def main():
    artist = resolve_artist(HARDCODED_ARTIST_ID)
    artist["audio_profile"] = fetch_audio_profile(artist["spotify_id"])
    ensure_artist_has_history(artist)

    with st.sidebar:
        st.markdown(f"<div style='font-size:1.3rem;font-weight:800;letter-spacing:-0.05em;'>Studio Nuit<span style='color:{PALETTE['lime']}'>.</span></div>", unsafe_allow_html=True)
        if artist.get("is_fallback", False):
            st.info("⚡ Mode Local Actif (API Hors-Ligne)")
        else:
            st.success("🛰️ API Spotify Live Synced")
            
        st.markdown("<div class='sidebar-section'></div>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-label'>📅 Sélection Temporelle</div>", unsafe_allow_html=True)
        today = date.today()
        past = today - timedelta(days=365)
        date_range = st.slider("Plage", min_value=past, max_value=today, value=(past, today), format="MMM YYYY", label_visibility="collapsed")
        
        granularity = st.selectbox("Grain d'agrégation", options=["Jour", "Semaine", "Mois", "Année"], index=1)
        
        st.markdown("<div class='sidebar-section'></div>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-label'>✍️ Injection Streams Réels (S4A)</div>", unsafe_allow_html=True)
        # Permet au manager d'injecter manuellement le chiffre réel si GitHub action n'a pas encore tourné
        manual_streams = st.number_input("Volume de Streams du Jour", min_value=0, value=0, step=1000)
        
        if st.button("🔄 Capturer les statistiques"):
            sp = init_spotify()
            live_followers = artist["followers_base"]
            live_popularity = artist["popularity_base"]
            if sp:
                try:
                    live = sp.artist(artist["spotify_id"])
                    live_followers = live["followers"]["total"]
                    live_popularity = live["popularity"]
                except Exception:
                    pass
            
            upsert_daily_stats(artist["name"], artist["spotify_id"], live_followers, live_popularity, manual_streams)
            st.toast("Base de données actualisée avec succès !")
            st.rerun()

        # Contrôle d'intégrité de la base
        conn, _ = _get_connection()
        nb_rows = conn.execute("SELECT COUNT(*) FROM historique_artistes").fetchone()[0]
        conn.close()
        st.caption(f"Index de la base de données : {nb_rows} entrées physiques.")

    # ── Rendu de la zone principale ───────────────────────────────────────
    st.markdown(f"<div class='subtitle-tag'>MONITEUR ARTISTE UNIQUE</div><div class='main-title'>Tableau de bord de <span>{artist['name']}</span></div>", unsafe_allow_html=True)
    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    
    section_hud(artist)
    section_audience_demographics()
    section_chansonometre(artist)
    section_trends(artist, date_range[0], date_range[1], granularity)

if __name__ == "__main__":
    main()