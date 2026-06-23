# app.py
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import HARDCODED_ARTIST_ID, PALETTE, AUDIENCE_GENDER, AUDIENCE_AGE, MARKET_REFERENCE
import database as db
import spotify_service as spot

# Configuration de la page globale
st.set_page_config(
    page_title="Music Manager Dashboard",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Petit CSS résiduel uniquement pour les composants personnalisés (Title/Cards badge)
st.markdown(f"""
<style>
  .main-title {{ font-size: 2.4rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.1; }}
  .main-title span {{ color: {PALETTE['lime']}; }}
  .subtitle-tag {{
      display: inline-block; background: {PALETTE['lime']}22; color: {PALETTE['lime']};
      font-size: 0.72rem; font-weight: 600; letter-spacing: 0.12em;
      text-transform: uppercase; padding: 3px 10px; border-radius: 4px; margin-bottom: 0.6rem;
  }}
  .metric-box {{ background: {PALETTE['card']}; border: 1px solid {PALETTE['border']}; border-radius: 10px; padding: 1rem 1.2rem; text-align: center; }}
  .metric-label {{ font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: {PALETTE['muted']}; margin-bottom: 0.3rem; }}
  .artist-photo {{ width: 110px; height: 110px; border-radius: 50%; object-fit: cover; border: 3px solid {PALETTE['lime']}; display: block; margin: 0 auto 0.8rem; }}
  .artist-name {{ font-size: 1.5rem; font-weight: 800; text-align: center; }}
  .artist-genre {{ font-size: 0.78rem; color: {PALETTE['muted']}; text-align: center; margin-top: 0.2rem; }}
</style>
""", unsafe_allow_html=True)

def section_hud(artist: dict):
    st.subheader("Section 01 — Santé Globale")
    latest = db.get_latest_stats(artist["spotify_id"])
    previous = db.get_previous_stats(artist["spotify_id"])
    
    followers = latest["followers_count"] or artist.get("followers_base", 0)
    popularity = latest["popularity_score"] or artist.get("popularity_base", 0)
    last_update = latest.get("date_enregistrement") or "—"
    
    delta_f = followers - previous["followers_count"] if previous else 0
    delta_p = popularity - previous["popularity_score"] if previous else 0
    
    col_photo, col_followers, col_popularity, col_info = st.columns([1.6, 2, 2, 2])
    
    with col_photo:
        st.markdown(f"""
        <div style="text-align:center;">
            <img src="{artist['photo_url']}" class="artist-photo"/>
            <div class="artist-name">{artist['name']}</div>
            <div class="artist-genre">{artist['genre']}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_followers:
        st.metric(
            label="👥 Followers Spotify",
            value=f"{followers:,}".replace(",", " "),
            delta=f"{delta_f:+,} vs. hier".replace(",", " ")
        )
        
    with col_popularity:
        st.metric(
            label="🔥 Score de Popularité",
            value=f"{popularity} / 100",
            delta=f"{delta_p:+d} pts vs. hier"
        )
        
    with col_info:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-label">Dernière synchro</div>
            <div style="font-size:1.05rem; font-weight:700; margin:0.4rem 0;">{last_update}</div>
            <div class="metric-label">Spotify ID</div>
            <div style="font-size:0.72rem; color:{PALETTE['muted']}; font-family:monospace;">{artist['spotify_id']}</div>
        </div>
        """, unsafe_allow_html=True)

def section_demographics():
    st.subheader("Section 02 — Démographie de l'Audience")
    col_gender, col_age = st.columns([1, 1.6], gap="large")
    
    with col_gender:
        fig = go.Figure(go.Pie(
            labels=list(AUDIENCE_GENDER.keys()), values=list(AUDIENCE_GENDER.values()),
            hole=0.6, marker=dict(colors=[PALETTE["lime"], PALETTE["purple"]])
        ))
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=250, showlegend=True, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        
    with col_age:
        df_age = pd.DataFrame(list(AUDIENCE_AGE.items()), columns=["Tranche", "Pourcentage"])
        fig_age = px.bar(df_age, x="Tranche", y="Pourcentage", color_discrete_sequence=[PALETTE["teal"]])
        fig_age.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=250, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_age, use_container_width=True)

def section_chansonometre(artist: dict):
    st.subheader("Section 03 — Analyse d'Empreinte Sonore (Top 10)")
    profile = spot.fetch_audio_profile(artist["spotify_id"])
    
    categories = list(profile.keys())
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=list(profile.values()), theta=categories, fill='toself', name=artist["name"], marker=dict(color=PALETTE["lime"])))
    fig.add_trace(go.Scatterpolar(r=list(MARKET_REFERENCE.values()), theta=categories, fill='toself', name='Moyenne Marché', marker=dict(color=PALETTE["muted"])))
    
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=True, height=350, paper_bgcolor="rgba(0,0,0,0)")
    
    col_radar, col_table = st.columns([1, 1.4])
    with col_radar:
        st.plotly_chart(fig, use_container_width=True)
    with col_table:
        df_tracks = spot.fetch_top_tracks_df(artist["spotify_id"])
        st.dataframe(df_tracks, use_container_width=True)

# 🧠 APPLIQUER UN FRAGMENT : Isoler l'analyse temporelle pour éviter les rechargements complets de l'application !
@st.fragment
def section_trends_isolee(artist: dict):
    st.subheader("Section 04 — Courbes d'Évolution Temporelle")
    
    # Sélections locales (les changements ici ne rechargent QUE cette section)
    col_d1, col_d2, col_resample = st.columns([1, 1, 1])
    with col_d1:
        date_from = st.date_input("Date de début", value=date.today() - timedelta(days=90))
    with col_d2:
        date_to = st.date_input("Date de fin", value=date.today())
    with col_resample:
        grain = st.selectbox("Agrégation", ["Jour", "Semaine", "Mois"])
    
    # Lecture optimisée depuis la base
    df_hist = db.get_artist_history(artist["spotify_id"], date_from, date_to)
    
    if not df_hist.empty:
        _ALIAS = {"Jour": "D", "Semaine": "W", "Mois": "ME"}
        df_resampled = df_hist.set_index("date_enregistrement").resample(_ALIAS[grain]).mean().reset_index()
        
        fig_followers = px.line(df_resampled, x="date_enregistrement", y="followers_count", title="Progression des Abonnés", color_discrete_sequence=[PALETTE["lime"]])
        fig_followers.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_followers, use_container_width=True)
    else:
        st.info("Aucune donnée sur la période sélectionnée.")

def main():
    # Affichage du loader professionnel (Status Orchestrator)
    with st.status("🚀 Alignement des systèmes intelligents...", expanded=True) as status:
        st.write("Initialisation de la base de données...")
        db.init_db()
        st.write("Résolution du profil de l'artiste...")
        artist = spot.resolve_artist(HARDCODED_ARTIST_ID)
        st.write("Vérification des historiques disponibles...")
        db.ensure_artist_has_history(artist)
        status.update(label="⚡ Systèmes synchronisés !", state="complete", expanded=False)

    # Header de marque
    st.markdown(f"""
        <div class="subtitle-tag">DIGITAL NEXT — Music Intelligence</div>
        <div class="main-title">Tableau de bord de Performance <span>{artist['name']}</span></div>
        <br>
    """, unsafe_allow_html=True)

    # Rendu ordonné des composants
    section_hud(artist)
    st.divider()
    section_demographics()
    st.divider()
    section_chansonometre(artist)
    st.divider()
    
    # Appel de notre fragment isolé
    section_trends_isolee(artist)

if __name__ == "__main__":
    main()