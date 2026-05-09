"""
Multi-Sport Player Performance Profiling System
Streamlit Dashboard — Color palette: Deep Royal Blue (#1A1F8C) + Bold Red (#E8293A) + White
"""
import os
import sys
import time
import streamlit as st

# ── Path setup ───────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from modules import cricket as cricket_mod
from modules import football as football_mod
from utils.helpers import (
    get_last_updated, get_flag_emoji, get_role_icon,
    format_market_value, performance_color, trend_indicator, safe_float
)
from utils.visualizations import (
    radar_chart, line_chart, comparison_bar_chart,
    dual_radar_chart, form_gauge, mini_sparkline
)
from api.data_fetcher import get_player_data_with_fallback, check_api_health, get_last_refresh_time, diagnose_api
from api.update_data import (
    update_data, get_last_update_timestamp, get_data_age_days, auto_update_if_needed
)
from models.ml_models import train_and_save_models, predict_score, get_peer_cluster

# ── Page configuration ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="SportsPulse | Performance Profiler",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS — England/Shoty Colour Scheme ─────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=Barlow:wght@400;500;600&display=swap');

/* ── Root palette ── */
:root {
    --bg-deep:    #060B3A;
    --bg-mid:     #0F1566;
    --bg-surface: #1A1F8C;
    --red:        #E8293A;
    --red-dark:   #B81E2C;
    --white:      #FFFFFF;
    --gold:       #FFD700;
    --blue-lt:    #4A5FE8;
    --muted:      rgba(255,255,255,0.55);
}

/* ── Base ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--bg-deep) !important;
    font-family: 'Barlow', sans-serif;
    color: var(--white);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A0F50 0%, #060B3A 100%) !important;
    border-right: 2px solid var(--red);
}
[data-testid="stSidebar"] * { color: var(--white) !important; }

/* ── Headings ── */
h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2 {
    font-family: 'Barlow Condensed', sans-serif !important;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}

/* ── Metric cards ── */
[data-testid="stMetricValue"] {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
    color: var(--white) !important;
}
[data-testid="stMetricLabel"] {
    color: var(--muted) !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

/* ── Buttons ── */
.stButton > button {
    background: var(--red) !important;
    color: var(--white) !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'Barlow Condensed', sans-serif !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    transition: background 0.2s, transform 0.1s;
}
.stButton > button:hover {
    background: var(--red-dark) !important;
    transform: translateY(-1px);
}

/* ── Select boxes ── */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background-color: var(--bg-mid) !important;
    border: 1px solid rgba(232,41,58,0.5) !important;
    border-radius: 4px !important;
    color: var(--white) !important;
}

/* ── Text input ── */
.stTextInput > div > div > input {
    background-color: var(--bg-mid) !important;
    border: 1px solid rgba(232,41,58,0.5) !important;
    color: var(--white) !important;
    border-radius: 4px !important;
}

/* ── Dividers ── */
hr { border-color: rgba(232,41,58,0.35) !important; }

/* ── Custom components ── */
.stat-card {
    background: linear-gradient(135deg, var(--bg-surface) 0%, var(--bg-mid) 100%);
    border: 1px solid rgba(232,41,58,0.4);
    border-radius: 8px;
    padding: 16px 20px;
    text-align: center;
    transition: border-color 0.2s, transform 0.15s;
}
.stat-card:hover {
    border-color: var(--red);
    transform: translateY(-2px);
}
.stat-val {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2rem;
    font-weight: 900;
    color: var(--white);
    line-height: 1;
}
.stat-label {
    font-size: 0.7rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 4px;
}
.player-header {
    background: linear-gradient(135deg, var(--bg-surface), var(--bg-mid));
    border: 2px solid var(--red);
    border-radius: 12px;
    padding: 28px 36px;
    position: relative;
    overflow: hidden;
}
.player-header::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 160px; height: 160px;
    background: radial-gradient(circle, rgba(232,41,58,0.25), transparent 70%);
    border-radius: 50%;
}
.player-name {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 3rem;
    font-weight: 900;
    color: var(--white);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    line-height: 1;
    margin: 0;
}
.player-meta {
    font-size: 0.85rem;
    color: var(--muted);
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.badge {
    display: inline-block;
    background: var(--red);
    color: var(--white);
    font-family: 'Barlow Condensed', sans-serif;
    font-weight: 700;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    padding: 3px 10px;
    border-radius: 3px;
    margin-right: 6px;
}
.insight-card {
    background: var(--bg-mid);
    border-left: 4px solid var(--red);
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin-bottom: 8px;
    font-size: 0.9rem;
}
.strength-card {
    border-left-color: #00FF88 !important;
}
.weakness-card {
    border-left-color: var(--gold) !important;
}
.section-title {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--white);
    border-bottom: 2px solid var(--red);
    padding-bottom: 6px;
    margin-bottom: 16px;
}
.winner-banner {
    background: linear-gradient(90deg, var(--red), var(--red-dark));
    border-radius: 8px;
    padding: 16px 24px;
    text-align: center;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 1.8rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--white);
}
.status-pill {
    display: inline-block;
    background: rgba(0,255,136,0.15);
    border: 1px solid rgba(0,255,136,0.4);
    color: #00FF88;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-family: 'Barlow Condensed', sans-serif;
    letter-spacing: 0.06em;
}
.status-pill.offline {
    background: rgba(255,215,0,0.12);
    border-color: rgba(255,215,0,0.4);
    color: var(--gold);
}
.logo-text {
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 2.2rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    line-height: 1;
}
.logo-sport {
    color: var(--red);
}
.logo-pulse {
    color: var(--white);
}
.peer-chip {
    display: inline-block;
    background: rgba(74,95,232,0.25);
    border: 1px solid rgba(74,95,232,0.5);
    color: #8FA4FF;
    padding: 3px 10px;
    border-radius: 16px;
    font-size: 0.8rem;
    margin: 3px;
}
.compare-winner {
    color: var(--gold);
    font-weight: 700;
}
.tab-content { padding: 12px 0; }
</style>
""", unsafe_allow_html=True)


# ── Data loading with caching ─────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_all_data():
    base = os.path.join(ROOT, "data")
    cricket_df  = cricket_mod.load_cricket_data(os.path.join(base, "cricket.csv"))
    football_df = football_mod.load_football_data(os.path.join(base, "football.csv"))
    return cricket_df, football_df


@st.cache_resource(show_spinner=False)
def get_trained_models(cricket_df, football_df):
    return train_and_save_models(cricket_df, football_df)


# ── App state ─────────────────────────────────────────────────────────────────
if "last_refresh" not in st.session_state:
    st.session_state["last_refresh"] = get_last_refresh_time()
if "refresh_count" not in st.session_state:
    st.session_state["refresh_count"] = 0


# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading sports data..."):
    cricket_df, football_df = load_all_data()
    model_results = get_trained_models(cricket_df, football_df)


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="logo-text">
        <span class="logo-sport">Sport</span><span class="logo-pulse">Pulse</span>
    </div>
    <div style="color: rgba(255,255,255,0.45); font-size:0.72rem; letter-spacing:0.1em;
                text-transform:uppercase; margin-bottom:20px;">
        Performance Profiling System
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Sport selector
    sport = st.selectbox(
        "🏆 SELECT SPORT",
        ["Cricket 🏏", "Football ⚽"],
        key="sport_select"
    )
    is_cricket = "Cricket" in sport

    df       = cricket_df if is_cricket else football_df
    sport_id = "cricket" if is_cricket else "football"
    mod      = cricket_mod if is_cricket else football_mod

    st.markdown("---")

    # Player search
    search_query = st.text_input(
        "🔍 SEARCH PLAYER",
        placeholder="Type player name...",
        key="search_input"
    )

    # Player selection
    if search_query:
        results = mod.search_players(df, search_query)
        if results:
            player_options = {f"{r['name']} — {r['team']}": r["player_id"] for r in results}
        else:
            player_options = {}
            st.warning("No players found.")
    else:
        all_players = df[["player_id", "name", "team"]].to_dict("records")
        player_options = {f"{r['name']} — {r['team']}": r["player_id"] for r in all_players}

    selected_label = st.selectbox("👤 SELECT PLAYER", list(player_options.keys()), key="player_select")
    selected_id    = player_options.get(selected_label)

    st.markdown("---")

    # Mode
    mode = st.radio(
        "📊 VIEW MODE",
        ["Profile", "Analysis", "Comparison"],
        horizontal=False,
        key="view_mode"
    )

    # Compare player (only shown in Comparison mode)
    compare_id = None
    if mode == "Comparison":
        others = {k: v for k, v in player_options.items() if v != selected_id}
        compare_label = st.selectbox("⚔️ COMPARE WITH", list(others.keys()), key="compare_select")
        compare_id = others.get(compare_label)

    st.markdown("---")

    # ── UPDATE DATA — writes new stats permanently to CSV ─────────────────
    if st.button("⚡ UPDATE DATA", use_container_width=True, key="btn_update"):
        with st.spinner(f"Updating {sport_id} data…"):
            result = update_data(sport_id)
        if result["success"]:
            load_all_data.clear()          # bust Streamlit cache so new CSV is read
            get_trained_models.clear()     # retrain ML on fresh data
            st.session_state["last_refresh"]    = get_last_refresh_time()
            st.session_state["refresh_count"]  += 1
            st.session_state["last_update_msg"] = result["message"]
            st.session_state["last_update_src"] = result["source"]
            st.rerun()
        else:
            st.error(result["message"])

    # ── REFRESH VIEW — reload from disk without writing ──────────────────
    col_r1, col_r2 = st.columns([3, 1])
    with col_r1:
        if st.button("🔄 REFRESH VIEW", use_container_width=True, key="btn_refresh"):
            load_all_data.clear()
            st.session_state["last_refresh"]   = get_last_refresh_time()
            st.session_state["refresh_count"] += 1
            st.rerun()
    with col_r2:
        st.markdown(
            f"<div style='font-size:0.7rem; color:rgba(255,255,255,0.4); padding-top:8px;'>"
            f"#{st.session_state['refresh_count']}</div>",
            unsafe_allow_html=True,
        )

    # ── Status panel ──────────────────────────────────────────────────────
    api_status  = check_api_health(sport_id)
    pill_class  = "status-pill" if api_status["available"] else "status-pill offline"
    pill_text   = "LIVE API" if api_status["available"] else "DATASET MODE"

    last_update_ts  = get_last_update_timestamp(sport_id)
    age_days        = get_data_age_days(sport_id)
    age_label       = f"{age_days}d old" if age_days is not None else "never updated"
    age_color       = "#FF4444" if (age_days or 0) >= 7 else "rgba(255,255,255,0.35)"

    update_msg  = st.session_state.get("last_update_msg", "")
    update_src  = st.session_state.get("last_update_src", "")
    src_icon    = "🌐" if update_src == "sportmonks_api" else "🔧" if update_src == "simulated" else ""

    # Colour-code HTTP status
    http_code  = api_status.get("http_code")
    code_color = "#00FF88" if http_code == 200 else "#FF4444" if http_code in (401, 403) else "#FFD700"
    code_label = f"HTTP {http_code}" if http_code else "no response"

    st.markdown(f"""
    <div style="margin-top:8px;">
        <span class="{pill_class}">{pill_text}</span>
        &nbsp;
        <span style="font-size:0.7rem; color:{age_color}; font-family:'Barlow Condensed',sans-serif;">
            {age_label}
        </span>
        <div style="font-size:0.63rem; color:rgba(255,255,255,0.35); margin-top:5px; line-height:1.5;">
            <b style="color:rgba(255,255,255,0.55);">Status:</b>
            <span style="color:{code_color};">{code_label}</span>
            &nbsp;·&nbsp;{api_status.get('latency_ms', 0):.0f}ms<br/>
            <span title="{api_status.get('endpoint','')}"
                  style="color:rgba(255,255,255,0.4); font-size:0.6rem;">
                {api_status.get('status','')[:48]}
            </span>
        </div>
        <div style="font-size:0.63rem; color:rgba(255,255,255,0.35); margin-top:4px;">
            <b style="color:rgba(255,255,255,0.55);">Last Updated:</b><br/>
            {last_update_ts}
        </div>
        {f'<div style="font-size:0.68rem; color:#00FF88; margin-top:5px;">{src_icon} {update_msg}</div>'
         if update_msg else ''}
    </div>
    """, unsafe_allow_html=True)

    # ── Expandable debug panel ────────────────────────────────────────────
    with st.expander("🔍 API Debug", expanded=not api_status["available"]):
        diag = diagnose_api()
        ok_color = "#00FF88" if diag["ok"] else "#FF4444"
        st.markdown(f"""
        <div style="font-size:0.75rem; line-height:1.9; color:rgba(255,255,255,0.85);">
            <b>Status:</b>
            <span style="color:{ok_color}; font-weight:700;">
                {'✅ API Connected' if diag['ok'] else '❌ ' + diag['problem']}
            </span><br/>
            <b>Key set:</b> {'✅ Yes' if os.getenv('SPORTMONKS_API_KEY') else '❌ No'}<br/>
            <b>HTTP code:</b>
            <span style="color:{code_color}; font-family:monospace;">{code_label}</span>
            &nbsp;·&nbsp;{api_status.get('latency_ms', 0):.0f}ms<br/>
            <b>Endpoint:</b>
            <span style="font-family:monospace; font-size:0.65rem; color:rgba(255,255,255,0.5);">
                {api_status.get('endpoint','—')}
            </span>
        </div>
        """, unsafe_allow_html=True)

        if not diag["ok"]:
            st.error(f"**Problem:** {diag['problem']}")
            st.info(f"**How to fix:**\n\n{diag['fix']}")
            if diag.get("detail"):
                with st.expander("Raw API response", expanded=False):
                    st.code(diag["detail"], language=None)

    # ── Auto-update banner (stale data warning) ───────────────────────────
    if age_days is not None and age_days >= 7:
        st.markdown("""
        <div style="background:rgba(232,41,58,0.15); border:1px solid rgba(232,41,58,0.4);
                    border-radius:6px; padding:8px 10px; margin-top:8px;
                    font-size:0.72rem; color:#FFB3B3;">
            ⚠️ Data is 7+ days old.<br/>Click <b>UPDATE DATA</b> to refresh.
        </div>
        """, unsafe_allow_html=True)


# ── Guard: no player selected ─────────────────────────────────────────────────
if not selected_id:
    st.markdown("""
    <div style="text-align:center; padding:80px 0;">
        <div style="font-family:'Barlow Condensed',sans-serif; font-size:3.5rem;
                    font-weight:900; color:#E8293A; text-transform:uppercase;">
            SportsPulse
        </div>
        <div style="color:rgba(255,255,255,0.5); margin-top:8px; font-size:1rem;">
            Search and select a player from the sidebar to begin.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Load player data ──────────────────────────────────────────────────────────
raw_player = mod.get_player_profile(df, selected_id)
if not raw_player:
    st.error("Player data not found.")
    st.stop()

player, data_source, is_live = get_player_data_with_fallback(raw_player, sport_id)

role_key  = "position" if not is_cricket else "role"
role_val  = player.get(role_key, "")
flag      = get_flag_emoji(player.get("nationality", ""))
role_icon = get_role_icon(role_val, sport_id)


# ══════════════════════════════════════════════════════════════════════════════
# HEADER — always visible
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="player-header">
    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px;">
        <div>
            <p class="player-name">{flag} {player.get('name','')}</p>
            <p class="player-meta">
                {role_icon} {role_val} &nbsp;|&nbsp;
                🏟️ {player.get('team','')} &nbsp;|&nbsp;
                🌍 {player.get('nationality','')} &nbsp;|&nbsp;
                🎂 Age {player.get('age','')}
            </p>
            <div style="margin-top:10px;">
                <span class="badge">{'Cricket 🏏' if is_cricket else 'Football ⚽'}</span>
                <span class="badge" style="background:#0F1566; border:1px solid #E8293A;">
                    {role_val}
                </span>
                <span class="badge" style="background:#FFD700; color:#060B3A;">
                    💰 {format_market_value(safe_float(player.get('market_value',0)))}
                </span>
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-family:'Barlow Condensed',sans-serif; font-size:0.7rem;
                        color:rgba(255,255,255,0.4); text-transform:uppercase;">Data Source</div>
            <div style="font-size:0.85rem; color:rgba(255,255,255,0.7);">{data_source}</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE: PROFILE
# ══════════════════════════════════════════════════════════════════════════════
if mode == "Profile":
    key_stats = mod.get_key_stats(player)

    # ── Stat cards ────────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">Key Statistics</div>', unsafe_allow_html=True)
    cols = st.columns(len(key_stats))
    for col, (label, value) in zip(cols, key_stats.items()):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-val">{value}</div>
                <div class="stat-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Charts row ────────────────────────────────────────────────────────────
    col_l, col_r = st.columns([1, 1], gap="medium")

    with col_l:
        st.markdown('<div class="section-title">Skills Radar</div>', unsafe_allow_html=True)
        radar_data = mod.get_radar_data(player)
        fig_radar = radar_chart(radar_data["axes"], radar_data["values"], player.get("name", ""))
        st.plotly_chart(fig_radar, use_container_width=True, config={"displayModeBar": False})

    with col_r:
        st.markdown('<div class="section-title">Season Performance</div>', unsafe_allow_html=True)
        ts_data = mod.get_time_series(player)
        fig_line = line_chart(ts_data["labels"], ts_data["values"],
                              player.get("name", ""), ts_data["metric"])
        st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})

    # ── Form gauge + similar players ─────────────────────────────────────────
    col_g, col_p = st.columns([1, 2], gap="medium")

    with col_g:
        st.markdown('<div class="section-title">Form Score</div>', unsafe_allow_html=True)
        form_val = safe_float(player.get("form_score", 75))
        fig_gauge = form_gauge(form_val, player.get("name", ""))
        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

    with col_p:
        st.markdown('<div class="section-title">Similar Players</div>', unsafe_allow_html=True)
        peers = get_peer_cluster(df, selected_id, sport_id)
        if peers:
            chips = "".join([f'<span class="peer-chip">👤 {p}</span>' for p in peers])
            st.markdown(f"""
            <div style="padding:16px; background:var(--bg-mid,#0F1566);
                        border:1px solid rgba(74,95,232,0.4); border-radius:8px; margin-top:8px;">
                <div style="font-size:0.75rem; color:rgba(255,255,255,0.45); margin-bottom:8px;
                            text-transform:uppercase; letter-spacing:0.1em;">
                    Players in the same performance cluster:
                </div>
                {chips}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No similar players found in current dataset.")


# ══════════════════════════════════════════════════════════════════════════════
# MODE: ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "Analysis":
    insights = mod.generate_ai_insights(player)

    # ── Performance rating ────────────────────────────────────────────────────
    rating      = insights["performance_rating"]
    trend       = insights["form_trend"]
    rating_col  = performance_color(rating)
    trend_icon  = trend_indicator(trend)

    col_score, col_trend, col_pred = st.columns(3)
    with col_score:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="color:{rating_col}; font-size:2.8rem;">{rating}</div>
            <div class="stat-label">AI Performance Rating</div>
        </div>
        """, unsafe_allow_html=True)
    with col_trend:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-val" style="font-size:2.2rem;">{trend_icon} {trend}</div>
            <div class="stat-label">Current Form Trend</div>
        </div>
        """, unsafe_allow_html=True)
    with col_pred:
        # ML prediction
        model_data = model_results.get(sport_id, {})
        if model_data.get("trained"):
            ml_score = predict_score(player, model_data)
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-val" style="color:#4A5FE8; font-size:2.8rem;">{ml_score}</div>
                <div class="stat-label">ML Predicted Score</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="stat-card">
                <div class="stat-val" style="color:rgba(255,255,255,0.4);">—</div>
                <div class="stat-label">ML Model Unavailable</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Insights columns ─────────────────────────────────────────────────────
    col_str, col_wk, col_ins = st.columns(3, gap="medium")

    with col_str:
        st.markdown('<div class="section-title" style="color:#00FF88;">💪 Strengths</div>',
                    unsafe_allow_html=True)
        for s in insights["strengths"]:
            st.markdown(f'<div class="insight-card strength-card">{s}</div>',
                        unsafe_allow_html=True)

    with col_wk:
        st.markdown('<div class="section-title" style="color:#FFD700;">⚠️ Weaknesses</div>',
                    unsafe_allow_html=True)
        for w in insights["weaknesses"]:
            st.markdown(f'<div class="insight-card weakness-card">{w}</div>',
                        unsafe_allow_html=True)

    with col_ins:
        st.markdown('<div class="section-title">🔍 Key Insights</div>', unsafe_allow_html=True)
        for i in insights["insights"]:
            st.markdown(f'<div class="insight-card">{i}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Season chart ─────────────────────────────────────────────────────────
    st.markdown('<div class="section-title">📈 Season Trend Analysis</div>', unsafe_allow_html=True)
    ts_data = mod.get_time_series(player)
    fig_line = line_chart(ts_data["labels"], ts_data["values"],
                          player.get("name", ""), ts_data["metric"])
    st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})

    # ── Consistency analysis ──────────────────────────────────────────────────
    ts_vals = [v for v in ts_data["values"] if v > 0]
    if len(ts_vals) >= 2:
        import statistics
        std_dev = round(statistics.stdev(ts_vals), 1) if len(ts_vals) > 1 else 0
        mean_v  = round(statistics.mean(ts_vals), 1)
        cv      = round((std_dev / mean_v * 100), 1) if mean_v > 0 else 0

        st.markdown('<div class="section-title">📊 Consistency Analysis</div>',
                    unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        metric_label = ts_data["metric"]
        c1.metric(f"Mean {metric_label}", mean_v)
        c2.metric("Std Deviation", std_dev)
        c3.metric("Coeff. Variation", f"{cv}%",
                  delta=f"{'Consistent' if cv < 20 else 'Volatile'}",
                  delta_color="normal" if cv < 20 else "inverse")
        c4.metric("Seasons Tracked", len(ts_vals))


# ══════════════════════════════════════════════════════════════════════════════
# MODE: COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "Comparison":
    if not compare_id:
        st.info("Select a player to compare with from the sidebar.")
        st.stop()

    comp_data = mod.compare_players(df, selected_id, compare_id)
    if not comp_data:
        st.error("Comparison data unavailable.")
        st.stop()

    p1 = comp_data["player1"]
    p2 = comp_data["player2"]

    # ── Winner banner ─────────────────────────────────────────────────────────
    winner = comp_data["overall_winner"]
    st.markdown(f"""
    <div class="winner-banner">
        🏆 Overall Edge: {winner}
        <span style="font-size:1rem; opacity:0.7; margin-left:12px;">
            ({comp_data['p1_wins']} vs {comp_data['p2_wins']} metrics)
        </span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Head-to-head key stats ────────────────────────────────────────────────
    st.markdown('<div class="section-title">📋 Head-to-Head Stats</div>', unsafe_allow_html=True)

    stats_p1 = mod.get_key_stats(p1)
    stats_p2 = mod.get_key_stats(p2)

    # Align keys
    all_keys = list(dict.fromkeys(list(stats_p1.keys()) + list(stats_p2.keys())))

    header_cols = st.columns([3, 1, 1, 3])
    header_cols[0].markdown(f"<div style='text-align:center; font-family:\"Barlow Condensed\",sans-serif; "
                             f"font-size:1.3rem; font-weight:800;'>{p1.get('name','')}</div>",
                             unsafe_allow_html=True)
    header_cols[1].markdown("<div style='text-align:center; color:rgba(255,255,255,0.4);'>vs</div>",
                            unsafe_allow_html=True)
    header_cols[3].markdown(f"<div style='text-align:center; font-family:\"Barlow Condensed\",sans-serif; "
                             f"font-size:1.3rem; font-weight:800;'>{p2.get('name','')}</div>",
                             unsafe_allow_html=True)

    for key in all_keys:
        v1 = stats_p1.get(key, "—")
        v2 = stats_p2.get(key, "—")
        try:
            highlight1 = "compare-winner" if float(v1) > float(v2) else ""
            highlight2 = "compare-winner" if float(v2) > float(v1) else ""
        except (TypeError, ValueError):
            highlight1 = highlight2 = ""

        row_cols = st.columns([3, 1, 1, 3])
        row_cols[0].markdown(f"<div style='text-align:center; font-size:1.5rem; font-family:\"Barlow Condensed\",sans-serif;' "
                             f"class='{highlight1}'>{v1}</div>", unsafe_allow_html=True)
        row_cols[1].markdown(f"<div style='text-align:center; font-size:0.75rem; color:rgba(255,255,255,0.5); "
                             f"padding-top:6px; text-transform:uppercase;'>{key}</div>", unsafe_allow_html=True)
        row_cols[2].markdown("<div></div>", unsafe_allow_html=True)
        row_cols[3].markdown(f"<div style='text-align:center; font-size:1.5rem; font-family:\"Barlow Condensed\",sans-serif;' "
                             f"class='{highlight2}'>{v2}</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    col_bar, col_rad = st.columns(2, gap="medium")

    with col_bar:
        st.markdown('<div class="section-title">📊 Bar Comparison</div>', unsafe_allow_html=True)
        fig_bar = comparison_bar_chart(
            comp_data["labels"], comp_data["p1_values"], comp_data["p2_values"],
            p1.get("name", "P1"), p2.get("name", "P2"), comp_data["winner_flags"]
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    with col_rad:
        st.markdown('<div class="section-title">🎯 Skills Overlap</div>', unsafe_allow_html=True)
        r1 = mod.get_radar_data(p1)
        r2 = mod.get_radar_data(p2)
        fig_dual = dual_radar_chart(
            r1["axes"], r1["values"], r2["values"],
            p1.get("name", "P1"), p2.get("name", "P2")
        )
        st.plotly_chart(fig_dual, use_container_width=True, config={"displayModeBar": False})

    # ── Season trends side by side ────────────────────────────────────────────
    st.markdown('<div class="section-title">📈 Season Trend Comparison</div>',
                unsafe_allow_html=True)
    col_t1, col_t2 = st.columns(2, gap="medium")

    ts1 = mod.get_time_series(p1)
    ts2 = mod.get_time_series(p2)

    with col_t1:
        fig1 = line_chart(ts1["labels"], ts1["values"], p1.get("name", ""), ts1["metric"])
        st.plotly_chart(fig1, use_container_width=True, config={"displayModeBar": False})

    with col_t2:
        fig2 = line_chart(ts2["labels"], ts2["values"], p2.get("name", ""), ts2["metric"])
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

    # ── AI insights both players ──────────────────────────────────────────────
    st.markdown('<div class="section-title">🤖 AI Insights — Head to Head</div>',
                unsafe_allow_html=True)
    ins1 = mod.generate_ai_insights(p1)
    ins2 = mod.generate_ai_insights(p2)

    ai_col1, ai_col2 = st.columns(2, gap="medium")

    with ai_col1:
        st.markdown(f"<div style='font-family:\"Barlow Condensed\",sans-serif; font-size:1.1rem; "
                    f"font-weight:700; color:#E8293A; margin-bottom:8px;'>{p1.get('name','')}</div>",
                    unsafe_allow_html=True)
        for s in ins1["strengths"]:
            st.markdown(f'<div class="insight-card strength-card">💪 {s}</div>',
                        unsafe_allow_html=True)
        for w in ins1["weaknesses"][:1]:
            st.markdown(f'<div class="insight-card weakness-card">⚠️ {w}</div>',
                        unsafe_allow_html=True)

    with ai_col2:
        st.markdown(f"<div style='font-family:\"Barlow Condensed\",sans-serif; font-size:1.1rem; "
                    f"font-weight:700; color:#4A5FE8; margin-bottom:8px;'>{p2.get('name','')}</div>",
                    unsafe_allow_html=True)
        for s in ins2["strengths"]:
            st.markdown(f'<div class="insight-card strength-card">💪 {s}</div>',
                        unsafe_allow_html=True)
        for w in ins2["weaknesses"][:1]:
            st.markdown(f'<div class="insight-card weakness-card">⚠️ {w}</div>',
                        unsafe_allow_html=True)


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center; color:rgba(255,255,255,0.3); font-size:0.72rem;
            font-family:'Barlow Condensed',sans-serif; letter-spacing:0.08em; padding:8px 0;">
    SPORTSPULSE PERFORMANCE PROFILING SYSTEM &nbsp;|&nbsp; CRICKET 🏏 &amp; FOOTBALL ⚽
    &nbsp;|&nbsp; POWERED BY PYTHON + STREAMLIT
</div>
""", unsafe_allow_html=True)
