# app.py
"""
╔══════════════════════════════════════════════════════════════════════════╗
║   MUSIC MANAGER DASHBOARD — Moniteur Dédié KITO                         ║
║   Auteur  : Digital Next / RBK Groupe                                   ║
║   Stack   : Streamlit · Plotly · Turso Cloud (libsql)                   ║
║   API     : Spotify via Spotipy (Client Credentials Flow)               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Imports de tes modules de configuration et services
from config import HARDCODED_ARTIST_ID, PALETTE, AUDIENCE_GENDER, AUDIENCE_AGE, MARKET_REFERENCE
import database as db
import spotify_service as sps

# ── CONFIGURATION STREAMLIT & STYLE "STUDIO NUIT" ─────────────────────────
st.set_page_config(
    page_title="Music Intelligence — KITO",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation de la base Turso Cloud
try:
    db.init_db()
except Exception as e:
    st.error(f"Impossible de synchroniser avec Turso Cloud : {e}")

# Injection CSS pour le look & feel Premium
st.markdown(f"""
    <style>
    /* Global Background & Core overrides */
    .stApp {{
        background-color: {PALETTE['bg']};
        color: {PALETTE['text']};
    }}
    [data-testid="stSidebar"] {{
        background-color: {PALETTE['card']};
        border-right: 1px solid {PALETTE['border']};
    }}
    
    /* Typography & Custom Tags */
    .main-title {{
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 2.6rem;
        font-weight: 800;
        letter-spacing: -0.04rem;
        color: {PALETTE['text']};
        margin-bottom: 0.2rem;
    }}
    .main-title span {{
        color: {PALETTE['lime']};
    }}
    .subtitle-tag {{
        background-color: {PALETTE['border']};
        color: {PALETTE['lime']};
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12rem;
        padding: 0.25rem 0.6rem;
        border-radius: 4px;
        display: inline-block;
        margin-bottom: 0.6rem;
    }}
    .section-header {{
        font-size: 1.25rem;
        font-weight: 700;
        color: {PALETTE['text']};
        border-left: 3px solid {PALETTE['teal']};
        padding-left: 0.6rem;
        margin: 1.8rem 0 1rem 0;
    }}
    
    /* Premium KPI Cards Container */
    .kpi-container {{
        background-color: {PALETTE['card']};
        border: 1px solid {PALETTE['border']};
        border-radius: 8px;
        padding: 1.2rem;
        text-align: left;
        position: relative;
        overflow: hidden;
    }}
    .kpi-container::after {{
        content: "";
        position: absolute;
        top: 0; left: 0; width: 4px; height: 100%;
    }}
    .kpi-lime::after {{ background-color: {PALETTE['lime']}; }}
    .kpi-teal::after {{ background-color: {PALETTE['teal']}; }}
    .kpi-purple::after {{ background-color: {PALETTE['purple']}; }}
    .kpi-warm::after {{ background-color: {PALETTE['warm']}; }}
    
    .kpi-label {{
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.06rem;
        color: {PALETTE['muted']};
        margin-bottom: 0.3rem;
    }}
    .kpi-val {{
        font-size: 1.8rem;
        font-weight: 700;
        color: {PALETTE['text']};
        line-height: 1.1;
    }}
    .kpi-delta {{
        font-size: 0.8rem;
        margin-top: 0.2rem;
        font-weight: 600;
    }}
    .delta-up {{ color: #10B981; }}
    .delta-down {{ color: #EF4444; }}
    
    /* Fix built-in Streamlit elements to fit dark UI */
    div[data-testid="stMetricValue"] {{ color: {PALETTE['text']} !important; }}
    </style>
""", unsafe_allow_html=True)


# ── SECTION FUNCTIONS ─────────────────────────────────────────────────────

def section_hud(artist_name, stats, prev_stats):
    """Affiche les cartes KPI (HUD) avec gestion des deltas réels."""
    c1, c2, c3, c4 = st.columns(4)
    
    # 1. Abonnés
    f_current = stats.get("followers_count", 0)
    f_prev = prev_stats.get("followers_count", 0) if prev_stats else f_current
    f_delta = f_current - f_prev
    f_delta_html = f'<div class="kpi-delta delta-up">▲ +{f_delta:,}</div>' if f_delta > 0 else (f'<div class="kpi-delta delta-down">▼ {f_delta:,}</div>' if f_delta < 0 else '<div class="kpi-delta" style="color:#6B7280;">─ Stable</div>')
    
    with c1:
        st.markdown(f"""
            <div class="kpi-container kpi-lime">
                <div class="kpi-label">Abonnés Spotify</div>
                <div class="kpi-val">{f_current:,}</div>
                {f_delta_html}
            </div>
        """, unsafe_allow_html=True)

    # 2. Popularité
    p_current = stats.get("popularity_score", 0)
    p_prev = prev_stats.get("popularity_score", 0) if prev_stats else p_current
    p_delta = p_current - p_prev
    p_delta_html = f'<div class="kpi-delta delta-up">▲ +{p_delta}</div>' if p_delta > 0 else (f'<div class="kpi-delta delta-down">▼ {p_delta}</div>' if p_delta < 0 else '<div class="kpi-delta" style="color:#6B7280;">─ Stable</div>')
    
    with c2:
        st.markdown(f"""
            <div class="kpi-container kpi-teal">
                <div class="kpi-label">Indice Popularité</div>
                <div class="kpi-val">{p_current}<span style="font-size:1rem;color:{PALETTE['muted']};">/100</span></div>
                {p_delta_html}
            </div>
        """, unsafe_allow_html=True)

    # 3. Flux d'écoute (Streams réels / cumulés)
    streams_current = stats.get("streams_real", 0)
    with c3:
        st.markdown(f"""
            <div class="kpi-container kpi-purple">
                <div class="kpi-label">Streams Réels (Cumul)</div>
                <div class="kpi-val">{streams_current:,}</div>
                <div class="kpi-delta" style="color:{PALETTE['lime']};">🔒 Cloud Synced</div>
            </div>
        """, unsafe_allow_html=True)

    # 4. Statut Système
    sync_date = stats.get("date_enregistrement", date.today().isoformat())
    with c4:
        st.markdown(f"""
            <div class="kpi-container kpi-warm">
                <div class="kpi-label">Statut Pipeline</div>
                <div class="kpi-val" style="font-size:1.4rem;padding-top:0.3rem;">CLOUD SYNC</div>
                <div class="kpi-delta" style="color:{PALETTE['lime']};">Mis à jour le {sync_date}</div>
            </div>
        """, unsafe_allow_html=True)


def section_audience_demographics():
    """Affiche les graphiques démographiques en Donut et Barres horizontales."""
    st.markdown('<div class="section-header">Structure & Sociologie de l\'Audience</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([4, 6])
    
    with c1:
        df_g = pd.DataFrame(list(AUDIENCE_GENDER.items()), columns=["Genre", "Part"])
        fig_g = px.pie(
            df_g, names="Genre", values="Part", hole=0.6,
            color_discrete_sequence=[PALETTE["lime"], PALETTE["purple"]]
        )
        fig_g.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value}%<extra></extra>")
        fig_g.update_layout(
            showlegend=False, margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor=PALETTE["chart_bg"], plot_bgcolor=PALETTE["chart_bg"],
            font=dict(color=PALETTE["text"])
        )
        st.write("**Répartition par Genre (Estimations)**")
        st.plotly_chart(fig_g, use_container_width=True, config={"displayModeBar": False})
        
    with c2:
        df_a = pd.DataFrame(list(AUDIENCE_AGE.items()), columns=["Tranche", "Pourcentage"]).iloc[::-1]
        fig_a = px.bar(df_a, x="Pourcentage", y="Tranche", orientation='h', text="Pourcentage")
        fig_a.update_traces(
            marker_color=PALETTE["teal"], marker_line_color=PALETTE["border"],
            texttemplate='%{text}%', textposition='outside', cliponaxis=False,
            hovertemplate="Tranche %{y} : %{x}%<extra></extra>"
        )
        fig_a.update_layout(
            margin=dict(t=10, b=10, l=10, r=80),
            paper_bgcolor=PALETTE["chart_bg"], plot_bgcolor=PALETTE["chart_bg"],
            font=dict(color=PALETTE["text"]),
            xaxis=dict(showgrid=False, visible=False, range=[0, max(AUDIENCE_AGE.values())*1.2]),
            yaxis=dict(showgrid=False, title=None)
        )
        st.write("**Segmentation par Tranches d'Âge**")
        st.plotly_chart(fig_a, use_container_width=True, config={"displayModeBar": False})


def section_chansonometre():
    """Affiche le profil d'empreinte musicale (Radar / Polar chart Plotly)."""
    st.markdown('<div class="section-header">Le Chansonomètre — Empreinte Acoustique</div>', unsafe_allow_html=True)
    
    categories = list(MARKET_REFERENCE.keys())
    values = list(MARKET_REFERENCE.values())
    
    # Clôturer le graphique radar sur lui-même
    categories.append(categories[0])
    values.append(values[0])
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself',
        name='Profil KITO',
        fillcolor='rgba(200, 241, 53, 0.2)',
        line=dict(color=PALETTE["lime"], width=2),
        hovertemplate="%{theta} : %{r}<extra></extra>"
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1.0], gridcolor=PALETTE["border"], tickfont=dict(color=PALETTE["muted"])),
            angularaxis=dict(gridcolor=PALETTE["border"], tickfont=dict(color=PALETTE["text"]))
        ),
        showlegend=False, margin=dict(t=30, b=20, l=10, r=10),
        paper_bgcolor=PALETTE["chart_bg"],
    )
    
    c1, c2 = st.columns([5, 5])
    with c1:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with c2:
        st.markdown(f"""
            <div style="background-color:{PALETTE['card']}; border:1px solid {PALETTE['border']}; 
                        border-radius:8px; padding:1.5rem; margin-top:2rem;">
                <h4 style="color:{PALETTE['lime']}; margin-top:0;">Analyse Directionnelle Artistique</h4>
                <p style="font-size:0.9rem; line-height:1.6; color:{PALETTE['text']};">
                    L'ADN musical de <b>KITO</b> est résolument calibré pour l'efficacité club et playlist d'impact. 
                    Avec un score d'<b>Énergie (0.72)</b> et de <b>Dansabilité (0.70)</b> très élevés, les productions se placent en parfaite adéquation avec les attentes actuelles du marché urbain / électronique français. 
                    La faible composante acoustique confirme des choix de sound-design modernes et synthétiques assumés.
                </p>
            </div>
        """, unsafe_allow_html=True)


def section_trends(df_history):
    """Courbe historique connectée à Turso Cloud (Correction du line width)."""
    st.markdown('<div class="section-header">Courbes Historiques & Analyse Macro</div>', unsafe_allow_html=True)
    
    if df_history.empty:
        st.warning("Aucune donnée historique trouvée sur Turso Cloud pour générer les graphiques temporels.")
        return

    # Graphique d'évolution temporelle avec Plotly
    fig = px.line(
        df_history, x="date_enregistrement", y="followers_count",
        labels={"date_enregistrement": "Date", "followers_count": "Abonnés Totaux"}
    )
    
    # Correction majeure de syntaxe ici pour encapsuler line color & width
    fig.update_traces(
        line=dict(color=PALETTE["lime"], width=3),
        hovertemplate="Date : %{x}<br>Abonnés : %{y:,}<extra></extra>"
    )
    
    fig.update_layout(
        margin=dict(t=20, b=20, l=10, r=10),
        paper_bgcolor=PALETTE["chart_bg"], plot_bgcolor=PALETTE["chart_bg"],
        font=dict(color=PALETTE["text"]),
        xaxis=dict(showgrid=True, gridcolor=PALETTE["border"], title=None),
        yaxis=dict(showgrid=True, gridcolor=PALETTE["border"], title=None)
    )
    
    st.plotly_chart(fig, use_container_width=True)


# ── MAIN APPLICATION PIPELINE ────────────────────────────────────────────

def main():
    # ── 1. SIDEBAR FILTER ────────────────────────────────────────────────
    st.sidebar.markdown(f'<div style="text-align:center; padding:1rem 0;"><span style="color:{PALETTE["lime"]}; font-weight:800; font-size:1.2rem;">DIGITAL NEXT PLATFORM</span></div>', unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    st.sidebar.subheader("Filtre Temporel Macro")
    today = date.today()
    date_from = st.sidebar.date_input("Date de début", today - timedelta(days=365))
    date_to = st.sidebar.date_input("Date de fin", today)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"""
        <div style="font-size:0.75rem; color:{PALETTE['muted']}; line-height:1.4;">
            <b>Node Connecté :</b> Turso Remote Cloud DB<br>
            <b>API Target :</b> Spotify Production Graph v1<br>
            <b>Mode :</b> Mono-Artiste Permanent
        </div>
    """, unsafe_allow_html=True)

    # ── 2. DATA ACQUISITION FROM TURSO ────────────────────────────────────
    stats = db.get_latest_stats(HARDCODED_ARTIST_ID)
    prev_stats = db.get_previous_stats(HARDCODED_ARTIST_ID)
    df_history = db.get_artist_history(HARDCODED_ARTIST_ID, date_from=date_from, date_to=date_to)

    artist_name = "KITO"

    # ── 3. HEADER PRINCIPAL ───────────────────────────────────────────────
    st.markdown(f"""
        <div class="subtitle-tag">DIGITAL NEXT — Music Intelligence</div>
        <div class="main-title">
            Tableau de bord <span>{artist_name}</span>
        </div>
        <div style="color:{PALETTE['muted']}; font-size:0.9rem; margin:0.4rem 0 1.8rem;">
            Analyse de performance · Données lues en temps réel depuis Turso Cloud
        </div>
    """, unsafe_allow_html=True)

    # ── 4. INJECTION DES SECTIONS PREMIUM ─────────────────────────────────
    section_hud(artist_name, stats, prev_stats)
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    
    section_audience_demographics()
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    
    section_chansonometre()
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    
    section_trends(df_history)

    # Section Top Titres Live depuis l'API Spotify
    st.markdown('<div class="section-header">Top 10 Titres les plus écoutés (Spotify Live)</div>', unsafe_allow_html=True)
    df_tracks = sps.fetch_top_tracks_df(HARDCODED_ARTIST_ID)
    if not df_tracks.empty:
        st.dataframe(df_tracks, use_container_width=True, hide_index=True)
    else:
        st.error("Impossible de charger le Top Titres en direct de l'API Spotify.")

    # ── 5. FOOTER ────────────────────────────────────────────────────────
    st.markdown(f"""
        <div style="border-top:1px solid {PALETTE['border']}; margin-top:2.5rem;
                    padding-top:1rem; text-align:center;
                    font-size:0.72rem; color:{PALETTE['muted']}; padding-bottom:1.5rem;">
            DIGITAL NEXT PLATFORM · PROPRIÉTÉ EXCLUSIVE DE RBK GROUPE · TOUS DROITS RÉSERVÉS © {date.today().year}
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()