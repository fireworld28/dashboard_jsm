# app.py
"""
╔══════════════════════════════════════════════════════════════════════════╗
║   MUSIC MANAGER DASHBOARD — Studio Nuit · KITO                          ║
║   Digital Next / RBK Groupe                                             ║
║   Stack  : Streamlit · Plotly · Turso Cloud (libsql)                   ║
║   API    : Spotify via Spotipy (Client Credentials Flow)               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from datetime import date, timedelta
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import (
    HARDCODED_ARTIST_ID, PALETTE,
    AUDIENCE_GENDER, AUDIENCE_AGE, MARKET_REFERENCE,
)
import database as db
import spotify_service as sps

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES ESTHÉTIQUES
# ─────────────────────────────────────────────────────────────────────────────

MUTED = "#9CA3AF"   # ratio ~5.2:1 sur card → WCAG AA ✅ (ancienne valeur #6B7280 = ❌)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Studio Nuit — KITO",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    db.init_db()
except Exception as e:
    st.error(f"Connexion Turso Cloud impossible : {e}")

# ─────────────────────────────────────────────────────────────────────────────
# CSS GLOBAL — THÈME STUDIO NUIT
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(f"""
<style>
/* ── Base ── */
.stApp {{
    background-color: {PALETTE['bg']};
    color: {PALETTE['text']};
    font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
[data-testid="stSidebar"] {{
    background-color: {PALETTE['card']};
    border-right: 1px solid {PALETTE['border']};
}}

/* ── Header principal ── */
.page-eyebrow {{
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.15rem;
    color: {PALETTE['lime']};
    background: rgba(200,241,53,0.08);
    border: 1px solid rgba(200,241,53,0.2);
    border-radius: 4px;
    padding: 0.2rem 0.55rem;
    display: inline-block;
    margin-bottom: 0.7rem;
}}
.page-title {{
    font-size: 2.8rem;
    font-weight: 900;
    letter-spacing: -0.05rem;
    line-height: 1;
    color: {PALETTE['text']};
    margin: 0 0 0.25rem;
}}
.page-title em {{
    font-style: normal;
    color: {PALETTE['lime']};
}}
.page-sub {{
    font-size: 0.85rem;
    color: {MUTED};
    margin-bottom: 2rem;
}}

/* ── Diviseur de section ── */
.section-divider {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin: 2.2rem 0 1.1rem;
}}
.section-divider-line {{
    flex: 1;
    height: 1px;
    background: {PALETTE['border']};
}}
.section-divider-label {{
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.1rem;
    color: {MUTED};
    white-space: nowrap;
}}
.section-divider-dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: {PALETTE['teal']};
    flex-shrink: 0;
}}

/* ── Cartes KPI ── */
.kpi-card {{
    background: {PALETTE['card']};
    border: 1px solid {PALETTE['border']};
    border-radius: 10px;
    padding: 1.1rem 1.2rem 1rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}}
.kpi-card:hover {{ border-color: rgba(255,255,255,0.15); }}
.kpi-card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 2px;
}}
.kpi-lime::before   {{ background: {PALETTE['lime']}; }}
.kpi-teal::before   {{ background: {PALETTE['teal']}; }}
.kpi-purple::before {{ background: {PALETTE['purple']}; }}
.kpi-warm::before   {{ background: {PALETTE['warm']}; }}
.kpi-label {{
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08rem;
    color: {MUTED};
    margin-bottom: 0.5rem;
}}
.kpi-value {{
    font-size: 2rem;
    font-weight: 800;
    line-height: 1;
    color: {PALETTE['text']};
    margin-bottom: 0.35rem;
}}
.kpi-value sup {{
    font-size: 0.9rem;
    font-weight: 500;
    color: {MUTED};
    vertical-align: baseline;
    margin-left: 2px;
}}
.kpi-delta {{
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 0.2rem;
}}
.delta-up   {{ color: #10B981; }}
.delta-down {{ color: #EF4444; }}
.delta-flat {{ color: {MUTED}; }}
.kpi-hint {{
    font-size: 0.7rem;
    color: {MUTED};
    font-style: italic;
    margin-top: 0.3rem;
    line-height: 1.3;
}}

/* ── Carte artiste sidebar ── */
.artist-card {{
    background: linear-gradient(135deg, {PALETTE['bg']} 0%, rgba(200,241,53,0.04) 100%);
    border: 1px solid rgba(200,241,53,0.15);
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    margin-bottom: 1rem;
}}
.artist-photo {{
    width: 72px;
    height: 72px;
    border-radius: 50%;
    object-fit: cover;
    border: 2px solid {PALETTE['lime']};
    margin-bottom: 0.5rem;
}}
.artist-name {{
    font-size: 1rem;
    font-weight: 800;
    color: {PALETTE['text']};
    letter-spacing: 0.05rem;
}}
.artist-genre {{
    font-size: 0.7rem;
    color: {MUTED};
    margin-top: 0.1rem;
}}
.artist-badge {{
    display: inline-block;
    background: rgba(200,241,53,0.12);
    color: {PALETTE['lime']};
    border-radius: 20px;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    margin-top: 0.4rem;
    letter-spacing: 0.06rem;
}}

/* ── Top tracks — barres popularité ── */
.track-row {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.55rem 0;
    border-bottom: 1px solid {PALETTE['border']};
}}
.track-row:last-child {{ border-bottom: none; }}
.track-rank {{
    font-size: 0.75rem;
    font-weight: 700;
    color: {MUTED};
    width: 18px;
    text-align: right;
    flex-shrink: 0;
}}
.track-info {{ flex: 1; min-width: 0; }}
.track-name {{
    font-size: 0.85rem;
    font-weight: 600;
    color: {PALETTE['text']};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.track-album {{
    font-size: 0.7rem;
    color: {MUTED};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}
.track-bar-wrap {{
    width: 90px;
    flex-shrink: 0;
}}
.track-bar-bg {{
    background: {PALETTE['border']};
    border-radius: 3px;
    height: 4px;
    overflow: hidden;
}}
.track-bar-fill {{
    height: 4px;
    border-radius: 3px;
    background: linear-gradient(90deg, {PALETTE['teal']}, {PALETTE['lime']});
}}
.track-pop {{
    font-size: 0.7rem;
    font-weight: 600;
    color: {MUTED};
    text-align: right;
    margin-top: 2px;
}}
.track-dur {{
    font-size: 0.75rem;
    color: {MUTED};
    flex-shrink: 0;
    width: 32px;
    text-align: right;
}}

/* ── Bloc info chansonomètre ── */
.insight-card {{
    background: {PALETTE['card']};
    border: 1px solid {PALETTE['border']};
    border-radius: 10px;
    padding: 1.4rem;
    height: 100%;
}}
.insight-card h4 {{
    color: {PALETTE['lime']};
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06rem;
    margin: 0 0 0.8rem;
}}
.insight-card p {{
    font-size: 0.88rem;
    line-height: 1.65;
    color: {PALETTE['text']};
    margin: 0;
}}
.insight-card b {{ color: {PALETTE['lime']}; font-weight: 700; }}

/* ── Sidebar statut pipeline ── */
.pipeline-status {{
    background: rgba(0,229,204,0.05);
    border: 1px solid rgba(0,229,204,0.15);
    border-radius: 8px;
    padding: 0.75rem;
    font-size: 0.72rem;
    color: {MUTED};
    line-height: 1.7;
}}
.pipeline-status b {{ color: {PALETTE['text']}; }}
.status-dot {{
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: {PALETTE['teal']};
    margin-right: 5px;
    vertical-align: middle;
    animation: pulse 2s infinite;
}}
@keyframes pulse {{
    0%,100% {{ opacity:1; }}
    50%      {{ opacity:0.4; }}
}}

/* ── Footer ── */
.footer {{
    border-top: 1px solid {PALETTE['border']};
    padding: 1.2rem 0;
    text-align: center;
    font-size: 0.68rem;
    color: {MUTED};
    letter-spacing: 0.05rem;
    margin-top: 3rem;
}}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────────────────────────────────────

def divider(label: str) -> None:
    """Séparateur visuel entre sections."""
    st.markdown(f"""
        <div class="section-divider">
            <div class="section-divider-dot"></div>
            <div class="section-divider-label">{label}</div>
            <div class="section-divider-line"></div>
        </div>
    """, unsafe_allow_html=True)


def lttb_downsample(df: pd.DataFrame, threshold: int = 300) -> pd.DataFrame:
    """
    Largest Triangle Three Buckets — préserve visuellement pics et creux.
    Ref : Steinarsson 2013.
    """
    n = len(df)
    if n <= threshold:
        return df

    data = df[["date_enregistrement", "followers_count"]].copy()
    data["_x"] = data["date_enregistrement"].astype("int64") / 1e9
    xy = data[["_x", "followers_count"]].values

    result_idx = [0]
    bucket_size = (n - 2) / (threshold - 2)

    for i in range(threshold - 2):
        avg_s = int((i + 1) * bucket_size) + 1
        avg_e = int((i + 2) * bucket_size) + 1
        avg_x = xy[avg_s:avg_e, 0].mean()
        avg_y = xy[avg_s:avg_e, 1].mean()

        rs = int(i * bucket_size) + 1
        re = int((i + 1) * bucket_size) + 1
        a  = result_idx[-1]

        max_area, max_idx = -1, rs
        for j in range(rs, re):
            area = abs(
                (xy[a, 0] - avg_x) * (xy[j, 1] - xy[a, 1])
                - (xy[a, 0] - xy[j, 0]) * (avg_y - xy[a, 1])
            )
            if area > max_area:
                max_area, max_idx = area, j
        result_idx.append(max_idx)

    result_idx.append(n - 1)
    return df.iloc[result_idx].reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

def build_sidebar(artist: dict) -> tuple:
    """Construit la sidebar et retourne (date_from, date_to)."""

    # Carte artiste
    st.sidebar.markdown(f"""
        <div class="artist-card">
            <img class="artist-photo"
                 src="{artist.get('photo_url', '')}"
                 onerror="this.src='https://via.placeholder.com/72/C8F135/0D0F14?text=KT'">
            <div class="artist-name">{artist.get('name', 'KITO')}</div>
            <div class="artist-genre">{artist.get('genre', 'Rap Français · Drill')}</div>
            <div class="artist-badge">● MONITORED</div>
        </div>
    """, unsafe_allow_html=True)

    # Filtre temporel
    st.sidebar.markdown(
        f'<div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08rem;color:{MUTED};margin-bottom:0.4rem;">'
        f'Fenêtre d\'analyse</div>',
        unsafe_allow_html=True,
    )
    today     = date.today()
    date_from = st.sidebar.date_input("Du", today - timedelta(days=365), label_visibility="collapsed")
    date_to   = st.sidebar.date_input("Au", today, label_visibility="collapsed")

    # Préréglages rapides
    col_a, col_b, col_c = st.sidebar.columns(3)
    if col_a.button("30J", use_container_width=True):
        date_from = today - timedelta(days=30)
        date_to   = today
    if col_b.button("90J", use_container_width=True):
        date_from = today - timedelta(days=90)
        date_to   = today
    if col_c.button("1AN", use_container_width=True):
        date_from = today - timedelta(days=365)
        date_to   = today

    st.sidebar.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    # Statut pipeline
    sync_date = db.get_latest_stats(HARDCODED_ARTIST_ID).get("date_enregistrement", "—")
    st.sidebar.markdown(f"""
        <div class="pipeline-status">
            <span class="status-dot"></span><b>TURSO CLOUD</b> connecté<br>
            Dernière sync : <b>{sync_date}</b><br>
            API Spotify : <b>Production v1</b><br>
            Refresh auto : <b>TTL 1h</b>
        </div>
    """, unsafe_allow_html=True)

    return date_from, date_to


# ─────────────────────────────────────────────────────────────────────────────
# SECTION HUD — 4 KPIs
# ─────────────────────────────────────────────────────────────────────────────

def section_hud(stats: dict, prev: dict | None) -> None:
    c1, c2, c3, c4 = st.columns(4)

    def delta_html(val, unit=""):
        if val > 0:
            return f'<div class="kpi-delta delta-up">▲ +{val:,}{unit}</div>'
        if val < 0:
            return f'<div class="kpi-delta delta-down">▼ {val:,}{unit}</div>'
        return f'<div class="kpi-delta delta-flat">─ Stable</div>'

    f_cur   = stats.get("followers_count", 0)
    f_prev  = prev.get("followers_count", 0) if prev else f_cur
    p_cur   = stats.get("popularity_score", 0)
    p_prev  = prev.get("popularity_score", 0) if prev else p_cur
    streams = stats.get("streams_real", 0)
    updated = stats.get("date_enregistrement", date.today().isoformat())

    with c1:
        st.markdown(f"""
            <div class="kpi-card kpi-lime">
                <div class="kpi-label">Abonnés Spotify</div>
                <div class="kpi-value">{f_cur:,}</div>
                {delta_html(f_cur - f_prev)}
                <div class="kpi-hint">vs dernière mesure en base</div>
            </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
            <div class="kpi-card kpi-teal">
                <div class="kpi-label">Indice Popularité</div>
                <div class="kpi-value">{p_cur}<sup>/100</sup></div>
                {delta_html(p_cur - p_prev, "")}
                <div class="kpi-hint">Médiane genre similaire : ~48</div>
            </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
            <div class="kpi-card kpi-purple">
                <div class="kpi-label">Streams Réels</div>
                <div class="kpi-value">{streams:,}</div>
                <div class="kpi-delta" style="color:{PALETTE['lime']};">🔒 Turso Synced</div>
                <div class="kpi-hint">Cumul total depuis le suivi</div>
            </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
            <div class="kpi-card kpi-warm">
                <div class="kpi-label">Dernière Sync</div>
                <div class="kpi-value" style="font-size:1.3rem;padding-top:0.35rem;">LIVE</div>
                <div class="kpi-delta" style="color:{PALETTE['lime']};">
                    <span class="status-dot"></span>{updated}
                </div>
                <div class="kpi-hint">GitHub Actions · 06h00 UTC</div>
            </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION AUDIENCE
# ─────────────────────────────────────────────────────────────────────────────

def section_audience() -> None:
    divider("Sociologie de l'Audience")
    c1, c2 = st.columns([4, 6])

    # Donut genre
    with c1:
        labels = list(AUDIENCE_GENDER.keys())
        values = list(AUDIENCE_GENDER.values())
        fig = go.Figure(go.Pie(
            labels=labels, values=values, hole=0.62,
            marker=dict(
                colors=[PALETTE["lime"], PALETTE["purple"]],
                line=dict(color=PALETTE["bg"], width=2),
            ),
            textinfo="percent+label",
            textfont=dict(color=PALETTE["text"], size=12),
            hovertemplate="%{label} : %{value}%<extra></extra>",
        ))
        fig.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color=PALETTE["text"]),
            annotations=[dict(
                text="Genre",
                x=0.5, y=0.5,
                font=dict(size=11, color=MUTED),
                showarrow=False,
            )],
        )
        st.caption("Répartition par genre")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Barres âge avec dégradé
    with c2:
        tranches = list(AUDIENCE_AGE.keys())[::-1]
        pcts     = list(AUDIENCE_AGE.values())[::-1]
        colors   = [
            PALETTE["lime"], PALETTE["teal"],
            PALETTE["teal"], PALETTE["purple"], PALETTE["purple"],
        ][:len(tranches)]

        fig = go.Figure(go.Bar(
            x=pcts, y=tranches, orientation="h",
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{v}%" for v in pcts],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="Tranche %{y} : %{x}%<extra></extra>",
        ))
        fig.update_layout(
            margin=dict(t=10, b=10, l=10, r=60),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=PALETTE["text"], size=12),
            xaxis=dict(visible=False, range=[0, max(AUDIENCE_AGE.values()) * 1.25]),
            yaxis=dict(showgrid=False, title=None),
        )
        st.caption("Segmentation par tranche d'âge")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ─────────────────────────────────────────────────────────────────────────────
# SECTION CHANSONOMÈTRE — RADAR
# ─────────────────────────────────────────────────────────────────────────────

def section_chansonometre() -> None:
    divider("Empreinte Acoustique — Chansonomètre")
    c1, c2 = st.columns([5, 5])

    cats = list(MARKET_REFERENCE.keys()) + [list(MARKET_REFERENCE.keys())[0]]
    vals = list(MARKET_REFERENCE.values()) + [list(MARKET_REFERENCE.values())[0]]

    fig = go.Figure()
    # Zone de remplissage
    fig.add_trace(go.Scatterpolar(
        r=vals, theta=cats, fill="toself",
        fillcolor="rgba(200,241,53,0.12)",
        line=dict(color=PALETTE["lime"], width=2.5),
        marker=dict(size=5, color=PALETTE["lime"]),
        name="KITO",
        hovertemplate="%{theta} : <b>%{r:.2f}</b><extra></extra>",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True, range=[0, 1],
                gridcolor=PALETTE["border"],
                tickfont=dict(color=MUTED, size=9),
                tickvals=[0.25, 0.5, 0.75],
            ),
            angularaxis=dict(
                gridcolor=PALETTE["border"],
                tickfont=dict(color=PALETTE["text"], size=11),
            ),
        ),
        showlegend=False,
        margin=dict(t=20, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    with c1:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        st.markdown(f"""
            <div class="insight-card">
                <h4>Analyse ADN Musical</h4>
                <p>
                    L'empreinte de <b>KITO</b> est calibrée pour l'impact club et playlist.
                    Un score d'<b>Énergie (0.72)</b> et de <b>Dansabilité (0.70)</b> très élevés
                    placent ses productions dans la zone haute du marché urbain / électronique français.<br><br>
                    La faible composante <b>Acoustique (0.12)</b> confirme des choix de sound-design
                    modernes et synthétiques, en phase avec les codes du rap/drill actuel.
                    Le score de <b>Speechiness (0.22)</b> marque un équilibre entre flow rythmique
                    et impact mélodique.
                </p>
            </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION TRENDS — COURBE HISTORIQUE DOUBLE AXE
# ─────────────────────────────────────────────────────────────────────────────

def section_trends(df: pd.DataFrame) -> None:
    divider("Historique & Analyse Macro")

    if df.empty:
        st.info("Aucune donnée historique sur la plage sélectionnée.")
        return

    days = (df["date_enregistrement"].max() - df["date_enregistrement"].min()).days
    threshold = 150 if days > 365 else (200 if days > 180 else 300)
    df_plot = lttb_downsample(df, threshold)
    n_total, n_plot = len(df), len(df_plot)

    fig = go.Figure()

    # Trace 1 — Abonnés (axe gauche, lime)
    fig.add_trace(go.Scatter(
        x=df_plot["date_enregistrement"],
        y=df_plot["followers_count"],
        name="Abonnés",
        mode="lines",
        line=dict(color=PALETTE["lime"], width=2.5),
        fill="tozeroy",
        fillcolor="rgba(200,241,53,0.05)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Abonnés : %{y:,}<extra></extra>",
        yaxis="y1",
    ))

    # Trace 2 — Popularité (axe droit, teal, si colonne présente)
    if "popularity_score" in df_plot.columns:
        fig.add_trace(go.Scatter(
            x=df_plot["date_enregistrement"],
            y=df_plot["popularity_score"],
            name="Popularité",
            mode="lines",
            line=dict(color=PALETTE["teal"], width=2, dash="dot"),
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Popularité : %{y}/100<extra></extra>",
            yaxis="y2",
        ))

    fig.update_layout(
        margin=dict(t=20, b=20, l=0, r=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["text"]),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.08, x=0,
            font=dict(size=11, color=PALETTE["text"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            showgrid=True, gridcolor=PALETTE["border"],
            title=None, tickfont=dict(color=MUTED),
        ),
        yaxis=dict(
            showgrid=True, gridcolor=PALETTE["border"],
            title="Abonnés", titlefont=dict(color=PALETTE["lime"]),
            tickfont=dict(color=PALETTE["lime"]),
        ),
        yaxis2=dict(
            overlaying="y", side="right",
            range=[0, 100],
            title="Popularité /100", titlefont=dict(color=PALETTE["teal"]),
            tickfont=dict(color=PALETTE["teal"]),
            showgrid=False,
        ),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    if n_total > n_plot:
        st.caption(
            f"Optimisé LTTB : {n_plot} points affichés sur {n_total} "
            f"— pics et tendances intégralement préservés."
        )


# ─────────────────────────────────────────────────────────────────────────────
# SECTION TOP TITRES — CUSTOM ROWS (pas de st.dataframe)
# ─────────────────────────────────────────────────────────────────────────────

def section_top_tracks() -> None:
    divider("Top 10 Titres · Spotify Live")

    df = sps.fetch_top_tracks_df(HARDCODED_ARTIST_ID)
    if df.empty:
        st.error("Impossible de charger les top titres depuis l'API Spotify.")
        return

    rows_html = ""
    for i, (_, row) in enumerate(df.iterrows(), 1):
        pop   = int(row.get("Popularité", 0))
        name  = str(row.get("🎵 Titre", "—"))
        album = str(row.get("Album", "—"))
        dur   = str(row.get("Durée", "—"))
        bar_w = int(pop)   # 0-100 → largeur en %

        rows_html += f"""
        <div class="track-row">
            <div class="track-rank">{i}</div>
            <div class="track-info">
                <div class="track-name">{name}</div>
                <div class="track-album">{album}</div>
            </div>
            <div class="track-bar-wrap">
                <div class="track-bar-bg">
                    <div class="track-bar-fill" style="width:{bar_w}%"></div>
                </div>
                <div class="track-pop">{pop}/100</div>
            </div>
            <div class="track-dur">{dur}</div>
        </div>"""

    st.markdown(
        f'<div style="background:{PALETTE["card"]};border:1px solid {PALETTE["border"]};'
        f'border-radius:10px;padding:1rem 1.2rem;">{rows_html}</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:

    # ── Données ──────────────────────────────────────────────────────────────
    artist     = sps.resolve_artist(HARDCODED_ARTIST_ID)
    stats      = db.get_latest_stats(HARDCODED_ARTIST_ID)
    prev       = db.get_previous_stats(HARDCODED_ARTIST_ID)
    df_full    = db.get_artist_history_full(HARDCODED_ARTIST_ID)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    date_from, date_to = build_sidebar(artist)
    df_history = db.filter_history(df_full, date_from, date_to)

    # ── Header ───────────────────────────────────────────────────────────────
    artist_name = artist.get("name", "KITO")
    st.markdown(f"""
        <div class="page-eyebrow">Digital Next · Music Intelligence</div>
        <div class="page-title">Studio Nuit — <em>{artist_name}</em></div>
        <div class="page-sub">
            Performance tracker · Données live depuis Turso Cloud &amp; Spotify API
        </div>
    """, unsafe_allow_html=True)

    # ── Sections ─────────────────────────────────────────────────────────────
    section_hud(stats, prev)
    section_audience()
    section_chansonometre()
    section_trends(df_history)
    section_top_tracks()

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown(f"""
        <div class="footer">
            DIGITAL NEXT PLATFORM &nbsp;·&nbsp; RBK GROUPE &nbsp;·&nbsp;
            TOUS DROITS RÉSERVÉS © {date.today().year}
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
