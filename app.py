# app.py
"""
╔══════════════════════════════════════════════════════════════════════════╗
║   MUSIC MANAGER DASHBOARD — Studio Nuit · KITO                          ║
║   Digital Next / RBK Groupe                                             ║
║   Stack  : Streamlit · Plotly · Turso Cloud (libsql-client)            ║
║   API    : Spotify via Spotipy (resolve_artist uniquement)             ║
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

MUTED = "#9CA3AF"

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

st.markdown(f"""
<style>
.stApp {{
    background-color: {PALETTE['bg']};
    color: {PALETTE['text']};
    font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
[data-testid="stSidebar"] {{
    background-color: {PALETTE['card']};
    border-right: 1px solid {PALETTE['border']};
}}
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
.footer {{
    border-top: 1px solid {PALETTE['border']};
    padding: 1.2rem 0;
    text-align: center;
    font-size: 0.68rem;
    color: {MUTED};
    letter-spacing: 0.05rem;
    margin-top: 3rem;
}}
/* ── Tableau Discographie ── */
.disco-table {{
    width: 100%;
    border-collapse: collapse;
}}
.disco-table th {{
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08rem;
    color: {MUTED};
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid {PALETTE['border']};
    text-align: left;
}}
.disco-table td {{
    font-size: 0.85rem;
    color: {PALETTE['text']};
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid {PALETTE['border']};
}}
.disco-table tr:last-child td {{ border-bottom: none; }}
.disco-table tr:hover td {{ background: rgba(255,255,255,0.02); }}
.disco-title {{ font-weight: 600; }}
.disco-album {{ color: {MUTED}; font-size: 0.78rem; }}
.disco-bar-bg {{
    background: {PALETTE['border']};
    border-radius: 3px;
    height: 4px;
    width: 80px;
    overflow: hidden;
    display: inline-block;
    vertical-align: middle;
    margin-right: 6px;
}}
.disco-bar-fill {{
    height: 4px;
    border-radius: 3px;
    background: linear-gradient(90deg, {PALETTE['teal']}, {PALETTE['lime']});
    display: block;
}}
</style>
""", unsafe_allow_html=True)


# ── UTILITAIRES ───────────────────────────────────────────────────────────────

def divider(label: str) -> None:
    st.markdown(f"""
        <div class="section-divider">
            <div class="section-divider-dot"></div>
            <div class="section-divider-label">{label}</div>
            <div class="section-divider-line"></div>
        </div>
    """, unsafe_allow_html=True)


def lttb_downsample(df: pd.DataFrame, col_y: str, threshold: int = 300) -> pd.DataFrame:
    """LTTB — préserve pics et creux visuellement (Steinarsson 2013)."""
    n = len(df)
    if n <= threshold:
        return df

    data = df[["date_enregistrement", col_y]].copy()
    data["_x"] = data["date_enregistrement"].astype("int64") / 1e9
    xy = data[["_x", col_y]].values

    result_idx  = [0]
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


# ── SIDEBAR ───────────────────────────────────────────────────────────────────

def build_sidebar(artist: dict, sync_date: str) -> tuple:
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

    st.sidebar.markdown(
        f'<div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.08rem;color:{MUTED};margin-bottom:0.4rem;">'
        f'Fenêtre d\'analyse</div>',
        unsafe_allow_html=True,
    )
    today     = date.today()
    date_from = st.sidebar.date_input("Du", today - timedelta(days=365), label_visibility="collapsed")
    date_to   = st.sidebar.date_input("Au", today, label_visibility="collapsed")

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
    st.sidebar.markdown(f"""
        <div class="pipeline-status">
            <span class="status-dot"></span><b>TURSO CLOUD</b> connecté<br>
            Dernière sync : <b>{sync_date}</b><br>
            GitHub Actions : <b>06h00 UTC</b><br>
            Refresh cache : <b>TTL 1h</b>
        </div>
    """, unsafe_allow_html=True)

    return date_from, date_to


# ── HUD ───────────────────────────────────────────────────────────────────────

def section_hud(stats: dict, prev: dict | None) -> None:
    c1, c2, c3, c4 = st.columns(4)

    def delta_html(val):
        if val > 0:
            return f'<div class="kpi-delta delta-up">▲ +{val:,}</div>'
        if val < 0:
            return f'<div class="kpi-delta delta-down">▼ {val:,}</div>'
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
                {delta_html(p_cur - p_prev)}
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


# ── AUDIENCE ──────────────────────────────────────────────────────────────────

def section_audience() -> None:
    divider("Sociologie de l'Audience")
    c1, c2 = st.columns([4, 6])

    with c1:
        fig = go.Figure(go.Pie(
            labels=list(AUDIENCE_GENDER.keys()),
            values=list(AUDIENCE_GENDER.values()),
            hole=0.62,
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
            annotations=[dict(text="Genre", x=0.5, y=0.5,
                              font=dict(size=11, color=MUTED), showarrow=False)],
        )
        st.caption("Répartition par genre")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        tranches = list(AUDIENCE_AGE.keys())[::-1]
        pcts     = list(AUDIENCE_AGE.values())[::-1]
        colors   = [PALETTE["lime"], PALETTE["teal"], PALETTE["teal"],
                    PALETTE["purple"], PALETTE["purple"]][:len(tranches)]
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


# ── CHANSONOMÈTRE ─────────────────────────────────────────────────────────────

def section_chansonometre() -> None:
    divider("Empreinte Acoustique — Chansonomètre")
    c1, c2 = st.columns([5, 5])

    cats = list(MARKET_REFERENCE.keys()) + [list(MARKET_REFERENCE.keys())[0]]
    vals = list(MARKET_REFERENCE.values()) + [list(MARKET_REFERENCE.values())[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals, theta=cats, fill="toself",
        fillcolor="rgba(200,241,53,0.12)",
        line=dict(color=PALETTE["lime"], width=2.5),
        marker=dict(size=5, color=PALETTE["lime"]),
        hovertemplate="%{theta} : <b>%{r:.2f}</b><extra></extra>",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 1],
                            gridcolor=PALETTE["border"],
                            tickfont=dict(color=MUTED, size=9),
                            tickvals=[0.25, 0.5, 0.75]),
            angularaxis=dict(gridcolor=PALETTE["border"],
                             tickfont=dict(color=PALETTE["text"], size=11)),
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
                    modernes et synthétiques. Le score de <b>Speechiness (0.22)</b> marque un équilibre
                    entre flow rythmique et impact mélodique.
                </p>
            </div>
        """, unsafe_allow_html=True)


# ── TRENDS — DOUBLE AXE ABONNÉS + POPULARITÉ ─────────────────────────────────

def section_trends(df: pd.DataFrame) -> None:
    divider("Historique Turso Cloud — Abonnés & Popularité")

    if df.empty:
        st.info("Aucune donnée en base pour la plage sélectionnée. Lance une sync GitHub Actions pour alimenter Turso.")
        return

    n_points = len(df)
    days     = (df["date_enregistrement"].max() - df["date_enregistrement"].min()).days

    # Downsampling LTTB adaptatif selon la plage
    threshold = 150 if days > 365 else (200 if days > 180 else min(300, n_points))
    df_f = lttb_downsample(df, "followers_count", threshold)
    df_p = lttb_downsample(df, "popularity_score", threshold) if "popularity_score" in df.columns else df_f

    fig = go.Figure()

    # ── Trace Abonnés (lime, fill) ──
    fig.add_trace(go.Scatter(
        x=df_f["date_enregistrement"],
        y=df_f["followers_count"],
        name="Abonnés",
        mode="lines+markers",
        line=dict(color=PALETTE["lime"], width=2.5),
        marker=dict(size=4, color=PALETTE["lime"]),
        fill="tozeroy",
        fillcolor="rgba(200,241,53,0.06)",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Abonnés : <b>%{y:,}</b><extra></extra>",
        yaxis="y1",
    ))

    # ── Trace Popularité (teal, pointillés, axe droit) ──
    if "popularity_score" in df_p.columns and df_p["popularity_score"].sum() > 0:
        fig.add_trace(go.Scatter(
            x=df_p["date_enregistrement"],
            y=df_p["popularity_score"],
            name="Popularité /100",
            mode="lines+markers",
            line=dict(color=PALETTE["teal"], width=2, dash="dot"),
            marker=dict(size=4, color=PALETTE["teal"]),
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Popularité : <b>%{y}/100</b><extra></extra>",
            yaxis="y2",
        ))

    fig.update_layout(
        margin=dict(t=30, b=20, l=0, r=70),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["text"]),
        hovermode="x unified",
        legend=dict(
            orientation="h", y=1.12, x=0,
            font=dict(size=11, color=PALETTE["text"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(
            showgrid=True, gridcolor=PALETTE["border"],
            title=None, tickfont=dict(color=MUTED),
            showline=True, linecolor=PALETTE["border"],
        ),
        yaxis=dict(
            showgrid=True, gridcolor=PALETTE["border"],
            title="Abonnés", titlefont=dict(color=PALETTE["lime"], size=11),
            tickfont=dict(color=PALETTE["lime"]),
            showline=True, linecolor=PALETTE["border"],
        ),
        yaxis2=dict(
            overlaying="y", side="right",
            range=[0, 100],
            title="Popularité /100",
            titlefont=dict(color=PALETTE["teal"], size=11),
            tickfont=dict(color=PALETTE["teal"]),
            showgrid=False,
        ),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Résumé statistique sous le graphe
    col1, col2, col3 = st.columns(3)
    with col1:
        first = int(df["followers_count"].iloc[0])
        last  = int(df["followers_count"].iloc[-1])
        gain  = last - first
        sign  = "+" if gain >= 0 else ""
        st.metric("Progression sur la période", f"{sign}{gain:,} abonnés")
    with col2:
        st.metric("Points de données", f"{n_points} jours enregistrés")
    with col3:
        if "popularity_score" in df.columns:
            avg_pop = round(df["popularity_score"].mean(), 1)
            st.metric("Popularité moyenne", f"{avg_pop}/100")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main() -> None:

    # Données
    artist   = sps.resolve_artist(HARDCODED_ARTIST_ID)
    stats    = db.get_latest_stats(HARDCODED_ARTIST_ID)
    prev     = db.get_previous_stats(HARDCODED_ARTIST_ID)
    df_full  = db.get_artist_history_full(HARDCODED_ARTIST_ID)

    sync_date       = stats.get("date_enregistrement", "—")
    date_from, date_to = build_sidebar(artist, sync_date)
    df_history      = db.filter_history(df_full, date_from, date_to)

    # Header
    artist_name = artist.get("name", "KITO")
    st.markdown(f"""
        <div class="page-eyebrow">Digital Next · Music Intelligence</div>
        <div class="page-title">Studio Nuit — <em>{artist_name}</em></div>
        <div class="page-sub">
            Performance tracker · Données Turso Cloud · Sync quotidienne GitHub Actions
        </div>
    """, unsafe_allow_html=True)

    section_hud(stats, prev)
    section_audience()
    section_chansonometre()
    section_trends(df_history)

    st.markdown(f"""
        <div class="footer">
            DIGITAL NEXT PLATFORM &nbsp;·&nbsp; RBK GROUPE &nbsp;·&nbsp;
            TOUS DROITS RÉSERVÉS © {date.today().year}
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
