"""
╔══════════════════════════════════════════════════════════════════════════╗
║         MUSIC MANAGER DASHBOARD — Analyse de Performance Artiste         ║
║         Auteur  : Digital Next / RBK Groupe                             ║
║         Stack   : Streamlit · Plotly · SQLite (→ PostgreSQL ready)      ║
╚══════════════════════════════════════════════════════════════════════════╝

Architecture :
  ┌─ db/         Couche d'accès aux données (SQLite par défaut)
  │   init_db()               — Crée la table si elle n'existe pas
  │   seed_fake_history()     — Génère 12 mois d'historique fictif
  │   get_artist_history()    — Lit l'historique d'un artiste
  │   insert_daily_stats()    — Insère une nouvelle ligne quotidienne
  │
  └─ ui/         Logique d'affichage Streamlit / Plotly
      section_hud()           — Head-Up Display (photo, metrics)
      section_chansonometre() — Top 10 + Scatter Plot
      section_trends()        — Line Chart DB + Radar Chart
"""

# ──────────────────────────────────────────────────────────────────────────
# 0. IMPORTS
# ──────────────────────────────────────────────────────────────────────────
import os
import random
import sqlite3
from datetime import date, datetime, timedelta
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
# Fond quasi-noir / accents néon lime / texte crème
PALETTE = {
    "bg":        "#0D0F14",
    "card":      "#161920",
    "border":    "#252A35",
    "lime":      "#C8F135",
    "teal":      "#00E5CC",
    "purple":    "#9B6DFF",
    "warm":      "#FF7A50",
    "text":      "#E8EAF0",
    "muted":     "#6B7280",
    "chart_bg":  "rgba(0,0,0,0)",
}

# CSS global injecté une seule fois
st.markdown(f"""
<style>
  /* ── Reset & fond ── */
  .stApp, [data-testid="stAppViewContainer"] {{
      background-color: {PALETTE['bg']};
      color: {PALETTE['text']};
      font-family: 'Inter', 'Segoe UI', sans-serif;
  }}
  [data-testid="stSidebar"] {{
      background-color: {PALETTE['card']};
      border-right: 1px solid {PALETTE['border']};
  }}

  /* ── Titre principal ── */
  .main-title {{
      font-size: 2.4rem;
      font-weight: 800;
      letter-spacing: -0.03em;
      color: {PALETTE['text']};
      line-height: 1.1;
  }}
  .main-title span {{
      color: {PALETTE['lime']};
  }}
  .subtitle-tag {{
      display: inline-block;
      background: {PALETTE['lime']}22;
      color: {PALETTE['lime']};
      font-size: 0.72rem;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      padding: 3px 10px;
      border-radius: 4px;
      margin-bottom: 0.6rem;
  }}

  /* ── Cartes de section ── */
  .section-card {{
      background: {PALETTE['card']};
      border: 1px solid {PALETTE['border']};
      border-radius: 12px;
      padding: 1.4rem 1.6rem;
      margin-bottom: 1.2rem;
  }}
  .section-label {{
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: {PALETTE['muted']};
      margin-bottom: 0.2rem;
  }}
  .section-title {{
      font-size: 1.15rem;
      font-weight: 700;
      color: {PALETTE['text']};
      margin-bottom: 1rem;
  }}

  /* ── Metric cards ── */
  .metric-box {{
      background: {PALETTE['bg']};
      border: 1px solid {PALETTE['border']};
      border-radius: 10px;
      padding: 1rem 1.2rem;
      text-align: center;
  }}
  .metric-label {{
      font-size: 0.7rem;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: {PALETTE['muted']};
      margin-bottom: 0.3rem;
  }}
  .metric-value {{
      font-size: 2rem;
      font-weight: 800;
      color: {PALETTE['lime']};
      line-height: 1;
  }}
  .metric-delta {{
      font-size: 0.78rem;
      color: {PALETTE['teal']};
      margin-top: 0.2rem;
  }}

  /* ── Artist HUD ── */
  .artist-photo {{
      width: 110px;
      height: 110px;
      border-radius: 50%;
      object-fit: cover;
      border: 3px solid {PALETTE['lime']};
      display: block;
      margin: 0 auto 0.8rem;
  }}
  .artist-name {{
      font-size: 1.5rem;
      font-weight: 800;
      color: {PALETTE['text']};
      text-align: center;
  }}
  .artist-genre {{
      font-size: 0.78rem;
      color: {PALETTE['muted']};
      text-align: center;
      margin-top: 0.2rem;
  }}

  /* ── Sidebar ── */
  .sidebar-section {{
      border-top: 1px solid {PALETTE['border']};
      padding-top: 1rem;
      margin-top: 1rem;
  }}
  .sidebar-label {{
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: {PALETTE['muted']};
      margin-bottom: 0.5rem;
  }}

  /* ── Streamlit overrides ── */
  [data-testid="stMetric"] {{
      background: {PALETTE['card']};
      border: 1px solid {PALETTE['border']};
      border-radius: 10px;
      padding: 0.8rem 1rem;
  }}
  [data-testid="stMetricValue"] {{ color: {PALETTE['lime']}; font-weight: 800; }}
  [data-testid="stMetricDelta"] {{ color: {PALETTE['teal']}; }}
  div[data-testid="stDataFrame"] > div {{ border-radius: 8px; }}
  .stButton > button {{
      background: {PALETTE['lime']};
      color: {PALETTE['bg']};
      font-weight: 700;
      border: none;
      border-radius: 8px;
      padding: 0.6rem 1.2rem;
      width: 100%;
      transition: opacity 0.15s;
  }}
  .stButton > button:hover {{ opacity: 0.85; }}
  h1, h2, h3 {{ color: {PALETTE['text']}; }}
  .stSelectbox label, .stSlider label {{ color: {PALETTE['muted']} !important; }}
  [data-testid="stPlotlyChart"] {{ border-radius: 8px; overflow: hidden; }}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# 2. COUCHE BASE DE DONNÉES
# ══════════════════════════════════════════════════════════════════════════

# ── 2.1  Configuration de la connexion ────────────────────────────────────
#
# Pour basculer vers PostgreSQL / Supabase, il suffit de définir la variable
# d'environnement DATABASE_URL :
#   export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
#
# Si elle est absente → SQLite local (fichier music_manager.db)
#
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_FILE = Path("music_manager.db")


def _get_connection():
    """
    Retourne une connexion SQLite ou PostgreSQL selon DATABASE_URL.
    Toujours fermer la connexion après usage (context manager recommandé).
    """
    if DATABASE_URL.startswith("postgresql"):
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
        except ImportError:
            st.error("psycopg2 non installé. Lancez : pip install psycopg2-binary")
            st.stop()
        return conn, "pg"
    else:
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"


def _placeholder_sql(db_type: str) -> str:
    """Retourne le bon placeholder paramétré selon le moteur."""
    return "%s" if db_type == "pg" else "?"


# ── 2.2  Initialisation de la base ────────────────────────────────────────

def init_db() -> None:
    """
    Crée la table 'historique_artistes' si elle n'existe pas.
    Idempotente — peut être appelée à chaque démarrage.
    """
    conn, db_type = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historique_artistes (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            date_enregistrement DATE        NOT NULL,
            artiste_name       TEXT        NOT NULL,
            spotify_id         TEXT        NOT NULL,
            followers_count    INTEGER     NOT NULL,
            popularity_score   INTEGER     NOT NULL
        )
    """)
    conn.commit()
    conn.close()


# ── 2.3  Seeding fictif ───────────────────────────────────────────────────

def seed_fake_history(roster: list[dict]) -> None:
    """
    Si la table est vide, génère 12 mois de données simulées pour chaque
    artiste du roster avec une progression réaliste (tendance + bruit aléatoire).

    Les followers croissent selon un modèle sigmoïde léger + variations
    hebdomadaires pour imiter la dynamique réelle d'une base de fans.
    """
    conn, _ = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM historique_artistes")
    count = cursor.fetchone()[0]

    if count > 0:
        conn.close()
        return  # Déjà peuplé, on ne fait rien

    today = date.today()
    rows = []

    for artist in roster:
        base_followers = artist["followers_base"]
        base_popularity = artist["popularity_base"]
        random.seed(artist["spotify_id"])  # Reproductible par artiste

        for days_ago in range(365, -1, -7):          # Un point par semaine
            record_date = today - timedelta(days=days_ago)
            progress = (365 - days_ago) / 365        # 0.0 → 1.0

            # Croissance organique + bruit aléatoire (±3 %)
            noise_f = random.uniform(-0.03, 0.05)
            noise_p = random.uniform(-2, 3)
            followers = int(base_followers * (1 + 0.35 * progress + noise_f))
            popularity = min(100, int(base_popularity + 12 * progress + noise_p))

            rows.append((
                record_date.isoformat(),
                artist["name"],
                artist["spotify_id"],
                max(0, followers),
                max(0, min(100, popularity)),
            ))

    cursor.executemany("""
        INSERT INTO historique_artistes
            (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score)
        VALUES (?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()


# ── 2.4  Lecture de l'historique ─────────────────────────────────────────

def get_artist_history(
    spotify_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
) -> pd.DataFrame:
    """
    Retourne l'historique complet (ou filtré) d'un artiste sous forme de DataFrame.

    Colonnes : date_enregistrement | followers_count | popularity_score
    """
    conn, db_type = _get_connection()
    ph = _placeholder_sql(db_type)

    query = f"""
        SELECT date_enregistrement, followers_count, popularity_score
        FROM   historique_artistes
        WHERE  spotify_id = {ph}
    """
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


# ── 2.5  Insertion d'une nouvelle ligne (sync quotidienne) ────────────────

def insert_daily_stats(
    artiste_name: str,
    spotify_id: str,
    followers_count: int,
    popularity_score: int,
    record_date: date | None = None,
) -> None:
    """
    Insère une ligne de statistiques datée d'aujourd'hui (ou date fournie).
    Utilisée lors de la simulation de synchronisation API hebdomadaire.
    """
    if record_date is None:
        record_date = date.today()

    conn, db_type = _get_connection()
    ph = _placeholder_sql(db_type)
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO historique_artistes
            (date_enregistrement, artiste_name, spotify_id, followers_count, popularity_score)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
    """, (record_date.isoformat(), artiste_name, spotify_id, followers_count, popularity_score))
    conn.commit()
    conn.close()


def get_latest_stats(spotify_id: str) -> dict:
    """Retourne la dernière entrée connue pour un artiste."""
    conn, _ = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT followers_count, popularity_score, date_enregistrement
        FROM   historique_artistes
        WHERE  spotify_id = ?
        ORDER  BY date_enregistrement DESC
        LIMIT  1
    """, (spotify_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"followers_count": 0, "popularity_score": 0, "date_enregistrement": None}


def get_previous_stats(spotify_id: str, n: int = 2) -> dict | None:
    """Retourne l'avant-dernière entrée pour calculer le delta."""
    conn, _ = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT followers_count, popularity_score
        FROM   historique_artistes
        WHERE  spotify_id = ?
        ORDER  BY date_enregistrement DESC
        LIMIT  ?
    """, (spotify_id, n))
    rows = cursor.fetchall()
    conn.close()
    if len(rows) >= n:
        return dict(rows[-1])
    return None


# ══════════════════════════════════════════════════════════════════════════
# 3. DONNÉES MOCKÉES DU ROSTER
# ══════════════════════════════════════════════════════════════════════════

ROSTER = [
    {
        "name": "KITO",
        "spotify_id": "kito_001",
        "genre": "Rap Français / Afrotrap",
        "followers_base": 28_400,
        "popularity_base": 42,
        "photo_url": "https://via.placeholder.com/150/C8F135/0D0F14?text=KITO",
        "audio_profile": {
            "Acoustique": 0.12,
            "Liveness": 0.21,
            "Speechiness": 0.38,
            "Énergie": 0.82,
            "Dansabilité": 0.74,
        },
    },
    {
        "name": "LYRA NOVA",
        "spotify_id": "lyra_002",
        "genre": "R&B / Soul",
        "followers_base": 61_200,
        "popularity_base": 57,
        "photo_url": "https://via.placeholder.com/150/9B6DFF/E8EAF0?text=LYRA",
        "audio_profile": {
            "Acoustique": 0.45,
            "Liveness": 0.14,
            "Speechiness": 0.08,
            "Énergie": 0.63,
            "Dansabilité": 0.81,
        },
    },
    {
        "name": "BLAZE 77",
        "spotify_id": "blaze_003",
        "genre": "Drill / Trap",
        "followers_base": 112_000,
        "popularity_base": 68,
        "photo_url": "https://via.placeholder.com/150/FF7A50/0D0F14?text=BZ77",
        "audio_profile": {
            "Acoustique": 0.05,
            "Liveness": 0.09,
            "Speechiness": 0.29,
            "Énergie": 0.91,
            "Dansabilité": 0.69,
        },
    },
    {
        "name": "SOLÈNE M",
        "spotify_id": "solene_004",
        "genre": "Pop Électro / Indie",
        "followers_base": 43_800,
        "popularity_base": 51,
        "photo_url": "https://via.placeholder.com/150/00E5CC/0D0F14?text=SM",
        "audio_profile": {
            "Acoustique": 0.31,
            "Liveness": 0.17,
            "Speechiness": 0.06,
            "Énergie": 0.71,
            "Dansabilité": 0.77,
        },
    },
]

# Référence marché fixe pour le Radar Chart
MARKET_REFERENCE = {
    "Acoustique": 0.25,
    "Liveness": 0.18,
    "Speechiness": 0.15,
    "Énergie": 0.72,
    "Dansabilité": 0.70,
}

ROSTER_DICT = {a["name"]: a for a in ROSTER}


def generate_mock_top10(artist: dict) -> pd.DataFrame:
    """Génère un Top 10 fictif cohérent avec le profil de l'artiste."""
    random.seed(artist["spotify_id"] + "_top10")
    adj = ["Nuit", "Feu", "Ombre", "Lumière", "Rue", "Rêve", "Zone", "Pulse",
           "Flow", "Ciel", "Vague", "Soleil", "Brise", "Storm", "Echo"]
    nouns = ["Éternelle", "Sans fin", "Perdue", "Cachée", "Dorée", "Froide",
             "Libre", "Sauvage", "Secrète", "Ultime", "Profonde", "Vivante"]

    tracks = []
    for i in range(10):
        pop = max(10, min(99, random.gauss(artist["popularity_base"] - i * 4, 8)))
        energy = max(0.05, min(0.98, random.gauss(artist["audio_profile"]["Énergie"], 0.12)))
        dance = max(0.05, min(0.98, random.gauss(artist["audio_profile"]["Dansabilité"], 0.10)))
        tracks.append({
            "🎵  Titre":      f"{random.choice(adj)} {random.choice(nouns)}",
            "Popularité":   int(pop),
            "Énergie":      round(energy, 2),
            "Dansabilité":  round(dance, 2),
            "Durée":        f"{random.randint(2, 4)}:{random.randint(10, 59):02d}",
        })

    df = pd.DataFrame(tracks)
    df.index = range(1, 11)
    return df


# ══════════════════════════════════════════════════════════════════════════
# 4. FONCTIONS D'AFFICHAGE STREAMLIT / PLOTLY
# ══════════════════════════════════════════════════════════════════════════

def _plotly_layout(title: str = "", height: int = 320) -> dict:
    """Template Plotly cohérent avec la charte graphique Studio Nuit."""
    return dict(
        paper_bgcolor=PALETTE["chart_bg"],
        plot_bgcolor=PALETTE["chart_bg"],
        font=dict(family="Inter, Segoe UI, sans-serif", color=PALETTE["text"], size=12),
        title=dict(text=title, font=dict(size=14, color=PALETTE["text"]), x=0),
        height=height,
        margin=dict(l=16, r=16, t=40 if title else 16, b=16),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=PALETTE["border"],
            font=dict(size=11),
        ),
        xaxis=dict(
            gridcolor=PALETTE["border"],
            linecolor=PALETTE["border"],
            tickfont=dict(color=PALETTE["muted"], size=11),
        ),
        yaxis=dict(
            gridcolor=PALETTE["border"],
            linecolor=PALETTE["border"],
            tickfont=dict(color=PALETTE["muted"], size=11),
        ),
    )


# ── Section 1 : Head-Up Display ──────────────────────────────────────────

def section_hud(artist: dict) -> None:
    st.markdown("""
        <div class='section-card'>
          <div class='section-label'>Section 01</div>
          <div class='section-title'>Head-Up Display — Santé Globale</div>
        </div>
    """, unsafe_allow_html=True)

    latest = get_latest_stats(artist["spotify_id"])
    previous = get_previous_stats(artist["spotify_id"])

    followers = latest["followers_count"]
    popularity = latest["popularity_score"]
    last_update = latest.get("date_enregistrement", "N/A")

    delta_f = followers - previous["followers_count"] if previous else 0
    delta_p = popularity - previous["popularity_score"] if previous else 0

    col_photo, col_followers, col_popularity, col_info = st.columns([1.6, 2, 2, 2])

    with col_photo:
        st.markdown(f"""
            <div style="text-align:center; padding: 0.5rem;">
              <img src="{artist['photo_url']}" class="artist-photo"
                   onerror="this.src='https://via.placeholder.com/110/161920/6B7280?text=?'"/>
              <div class="artist-name">{artist['name']}</div>
              <div class="artist-genre">{artist['genre']}</div>
            </div>
        """, unsafe_allow_html=True)

    with col_followers:
        st.metric(
            label="👥 Followers Spotify",
            value=f"{followers:,}".replace(",", " "),
            delta=f"{delta_f:+,} vs. précédent".replace(",", " "),
        )

    with col_popularity:
        bar = "█" * int(popularity / 10) + "░" * (10 - int(popularity / 10))
        st.metric(
            label="🔥 Score de Popularité",
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
              <div style="font-size:1.1rem;font-weight:700;color:{PALETTE['text']};margin:0.4rem 0;">
                {last_update}
              </div>
              <div class="metric-label" style="margin-top:0.8rem;">Spotify ID</div>
              <div style="font-size:0.8rem;color:{PALETTE['muted']};font-family:monospace;">
                {artist['spotify_id']}
              </div>
              <div class="metric-label" style="margin-top:0.8rem;">Genre</div>
              <div style="font-size:0.82rem;color:{PALETTE['teal']};">
                {artist['genre']}
              </div>
            </div>
        """, unsafe_allow_html=True)


# ── Section 2 : Le Chansonomètre ─────────────────────────────────────────

def section_chansonometre(artist: dict) -> None:
    st.markdown("""
        <div class='section-card'>
          <div class='section-label'>Section 02</div>
          <div class='section-title'>Le Chansonomètre — Analyse du Catalogue</div>
        </div>
    """, unsafe_allow_html=True)

    top10 = generate_mock_top10(artist)

    col_table, col_scatter = st.columns([1, 1.2], gap="large")

    with col_table:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem;'>"
            f"🏆 Top 10 Hits</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            top10,
            use_container_width=True,
            height=340,
            column_config={
                "Popularité": st.column_config.ProgressColumn(
                    "Popularité",
                    min_value=0,
                    max_value=100,
                    format="%d",
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
        fig_scatter = px.scatter(
            top10.reset_index().rename(columns={"index": "Rang"}),
            x="Énergie",
            y="Dansabilité",
            size="Popularité",
            color="Popularité",
            hover_name="🎵  Titre",
            color_continuous_scale=[
                [0, PALETTE["purple"]],
                [0.5, PALETTE["teal"]],
                [1, PALETTE["lime"]],
            ],
            size_max=30,
        )
        fig_scatter.update_layout(**_plotly_layout(height=340))
        fig_scatter.update_coloraxes(showscale=False)
        fig_scatter.update_traces(
            marker=dict(line=dict(color=PALETTE["bg"], width=1.5)),
        )
        st.plotly_chart(fig_scatter, use_container_width=True)


# ── Section 3 : Tendances temporelles ────────────────────────────────────

# Correspondance label UI → alias Pandas resample
_RESAMPLE_ALIAS: dict[str, str] = {
    "Jour":   "D",
    "Semaine": "W",
    "Mois":   "ME",
    "Année":  "YE",
}

# Couleurs RGBA standard (compatibles Plotly / Python 3.14+)
# Lime  #C8F135  → rgb(200, 241, 53)
# Muted #6B7280  → rgb(107, 114, 128)
_FILL_LIME  = "rgba(200, 241, 53, 0.08)"   # remplace f"{PALETTE['lime']}18"
_FILL_MUTED = "rgba(107, 114, 128, 0.12)"  # remplace f"{PALETTE['muted']}20"
_FILL_RADAR = "rgba(200, 241, 53, 0.14)"   # remplace f"{PALETTE['lime']}25"


def section_trends(
    artist: dict,
    date_from: date,
    date_to: date,
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
        # En-tête + sélecteur de granularité sur la même ligne visuelle
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.3rem;'>"
            f"📈 Streams estimés (base de données)</div>",
            unsafe_allow_html=True,
        )

        granularity = st.radio(
            label="Agrégation temporelle",
            options=list(_RESAMPLE_ALIAS.keys()),
            index=1,               # "Semaine" par défaut
            horizontal=True,
            label_visibility="collapsed",
        )

        df_hist = get_artist_history(artist["spotify_id"], date_from, date_to)

        if df_hist.empty:
            st.info("Aucune donnée dans la plage temporelle sélectionnée.")
        else:
            # ── Calcul des streams estimés ─────────────────────────────
            # Hypothèse métier : chaque follower génère en moyenne
            # 12,5 streams par période (benchmark industrie indé 2024).
            df_hist["streams_estimated"] = df_hist["followers_count"] * 12.5

            # ── Rééchantillonnage Pandas selon la granularité choisie ──
            alias = _RESAMPLE_ALIAS[granularity]
            df_hist = df_hist.set_index("date_enregistrement")
            df_resampled = df_hist.resample(alias).agg({
                "streams_estimated": "sum",    # Cumul des streams sur la période
                "popularity_score":  "mean",   # Score moyen sur la période
            }).dropna().reset_index()
            df_resampled.rename(
                columns={"date_enregistrement": "date"}, inplace=True
            )

            # ── Construction du graphique dual-axe ────────────────────
            fig_line = go.Figure()

            # Axe gauche — Streams (lime, remplissage rgba)
            fig_line.add_trace(go.Scatter(
                x=df_resampled["date"],
                y=df_resampled["streams_estimated"],
                mode="lines",
                name="Streams estimés",
                line=dict(color=PALETTE["lime"], width=2.5),
                fill="tozeroy",
                fillcolor=_FILL_LIME,          # ← rgba valide, plus de hex+alpha
                hovertemplate=(
                    "<b>%{x|%d %b %Y}</b><br>"
                    "Streams : <b>%{y:,.0f}</b><extra></extra>"
                ),
            ))

            # Axe droit — Score de popularité (purple, pointillé)
            fig_line.add_trace(go.Scatter(
                x=df_resampled["date"],
                y=df_resampled["popularity_score"],
                mode="lines",
                name="Popularité",
                yaxis="y2",
                line=dict(color=PALETTE["purple"], width=1.8, dash="dot"),
                hovertemplate=(
                    "Popularité : <b>%{y:.1f}</b>/100<extra></extra>"
                ),
            ))

            fig_line.update_layout(
                **_plotly_layout(height=360),
                yaxis=dict(
                    title="Streams estimés",
                    gridcolor=PALETTE["border"],
                    tickfont=dict(color=PALETTE["muted"]),
                ),
                yaxis2=dict(
                    title="Popularité /100",
                    overlaying="y",
                    side="right",
                    range=[0, 100],
                    showgrid=False,
                    tickfont=dict(color=PALETTE["purple"]),
                ),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0
                ),
            )
            st.plotly_chart(fig_line, use_container_width=True)

    # ── Radar Chart ───────────────────────────────────────────────────────
    with col_radar:
        st.markdown(
            f"<div style='font-size:0.78rem;color:{PALETTE['muted']};font-weight:600;"
            f"letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem;'>"
            f"🕸️ Profil Audio vs. Marché</div>",
            unsafe_allow_html=True,
        )
        profile = artist["audio_profile"]
        categories = list(profile.keys())
        categories_closed = categories + [categories[0]]  # Fermer le polygone

        artist_vals = list(profile.values())
        market_vals = [MARKET_REFERENCE[c] for c in categories]

        fig_radar = go.Figure()

        fig_radar.add_trace(go.Scatterpolar(
            r=[v * 100 for v in market_vals] + [market_vals[0] * 100],
            theta=categories_closed,
            fill="toself",
            fillcolor=_FILL_MUTED,             # ← rgba valide
            line=dict(color=PALETTE["muted"], width=1.5, dash="dot"),
            name="Standard marché",
        ))

        fig_radar.add_trace(go.Scatterpolar(
            r=[v * 100 for v in artist_vals] + [artist_vals[0] * 100],
            theta=categories_closed,
            fill="toself",
            fillcolor=_FILL_RADAR,             # ← rgba valide
            line=dict(color=PALETTE["lime"], width=2.5),
            name=artist["name"],
        ))

        fig_radar.update_layout(
            polar=dict(
                bgcolor=PALETTE["chart_bg"],
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    tickfont=dict(color=PALETTE["muted"], size=9),
                    gridcolor=PALETTE["border"],
                    linecolor=PALETTE["border"],
                ),
                angularaxis=dict(
                    tickfont=dict(color=PALETTE["text"], size=11),
                    linecolor=PALETTE["border"],
                    gridcolor=PALETTE["border"],
                ),
            ),
            paper_bgcolor=PALETTE["chart_bg"],
            font=dict(color=PALETTE["text"]),
            height=360,
            margin=dict(l=30, r=30, t=30, b=30),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5,
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
    seed_fake_history(ROSTER)

    # ── 5.2  SIDEBAR ──────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
            <div style="padding: 0.5rem 0 1rem;">
              <div style="font-size:0.65rem;font-weight:700;letter-spacing:0.15em;
                          text-transform:uppercase;color:{PALETTE['muted']};">
                  MUSIC MANAGER
              </div>
              <div style="font-size:1.35rem;font-weight:800;color:{PALETTE['text']};">
                  Dashboard<span style="color:{PALETTE['lime']};">.</span>
              </div>
            </div>
        """, unsafe_allow_html=True)

        # Sélecteur d'artiste
        st.markdown(f"<div class='sidebar-label'>🎤 Artiste</div>", unsafe_allow_html=True)
        artist_name = st.selectbox(
            label="Sélectionner un artiste",
            options=[a["name"] for a in ROSTER],
            label_visibility="collapsed",
        )
        artist = ROSTER_DICT[artist_name]

        # Filtre temporel
        st.markdown("<div class='sidebar-section'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sidebar-label'>📅 Fenêtre temporelle</div>", unsafe_allow_html=True)

        today = date.today()
        min_date = today - timedelta(days=365)

        date_range = st.slider(
            label="Période d'analyse",
            min_value=min_date,
            max_value=today,
            value=(min_date, today),
            format="MMM YYYY",
            label_visibility="collapsed",
        )
        date_from, date_to = date_range

        st.caption(f"Du **{date_from.strftime('%d %b %Y')}** au **{date_to.strftime('%d %b %Y')}**")

        # Simulation synchro API
        st.markdown("<div class='sidebar-section'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='sidebar-label'>🔄 Synchronisation Spotify</div>",
            unsafe_allow_html=True,
        )

        if st.button("▶  Simuler la synchro hebdomadaire"):
            latest = get_latest_stats(artist["spotify_id"])
            new_followers = int(latest["followers_count"] * random.uniform(1.005, 1.025))
            new_popularity = min(100, latest["popularity_score"] + random.randint(-1, 3))

            insert_daily_stats(
                artiste_name=artist["name"],
                spotify_id=artist["spotify_id"],
                followers_count=new_followers,
                popularity_score=new_popularity,
            )
            st.success(
                f"✅ Synchronisation OK — {today.strftime('%d/%m/%Y')}\n\n"
                f"Followers : **{new_followers:,}**  |  Popularité : **{new_popularity}/100**"
            )
            st.rerun()

        # Infos DB
        st.markdown("<div class='sidebar-section'></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sidebar-label'>🗄️ Base de données</div>", unsafe_allow_html=True)

        db_label = "PostgreSQL" if DATABASE_URL.startswith("postgresql") else f"SQLite — {DB_FILE.name}"
        st.markdown(
            f"<div style='font-size:0.75rem;color:{PALETTE['teal']};'>"
            f"Moteur actif : <strong>{db_label}</strong></div>",
            unsafe_allow_html=True,
        )

        conn, _ = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM historique_artistes")
        nb_rows = cursor.fetchone()[0]
        conn.close()
        st.caption(f"{nb_rows} enregistrements au total dans la base.")

    # ── 5.3  EN-TÊTE PRINCIPAL ────────────────────────────────────────────
    st.markdown(f"""
        <div class="subtitle-tag">DIGITAL NEXT — Music Intelligence</div>
        <div class="main-title">
            Tableau de bord <span>{artist_name}</span>
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
            Données simulées à des fins de démonstration
        </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
