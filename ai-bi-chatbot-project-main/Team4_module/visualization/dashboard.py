def run_dashboard():
    import streamlit as st
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import time
    from datetime import datetime, timedelta

    from visualization.config import DATA_PATH
    from visualization.nlp_bridge import ask_question, get_bridge_status
    from visualization.insights import (
        top_country_insight,
        country_contribution_insight,
        top_product_insight,
        lowest_product_insight,
        top_customer_insight,
        customer_concentration_insight,
        revenue_trend_insight,
        peak_month_insight,
        dealsize_insight,
    )

    # ══════════════════════════════════════════════════════════════════════════════
    # PAGE CONFIG
    # ══════════════════════════════════════════════════════════════════════════════
    st.set_page_config(
        page_title="NexusBI · Intelligence Platform",
        layout="wide",
        initial_sidebar_state="expanded",
        page_icon="⚡",
    )

    # ══════════════════════════════════════════════════════════════════════════════
    # THEME STATE
    # ══════════════════════════════════════════════════════════════════════════════
    if 'theme' not in st.session_state:
        st.session_state['theme'] = 'dark'

    is_dark = st.session_state['theme'] == 'dark'

    # ── Theme color tokens ──
    if is_dark:
        BG_APP        = "#080B14"
        BG_SIDEBAR    = "#0D1117"
        BG_CARD       = "#111827"
        BG_CARD2      = "linear-gradient(145deg, #111827, #0D1117)"
        BORDER        = "rgba(255,255,255,0.06)"
        BORDER_HOVER  = "rgba(255,255,255,0.12)"
        TEXT_PRIMARY  = "#F1F5F9"
        TEXT_SECONDARY= "#94A3B8"
        TEXT_MUTED    = "#475569"
        TEXT_FAINT    = "#334155"
        PLOT_BG       = "rgba(0,0,0,0)"
        GRID_COLOR    = "#1E293B"
        TICK_COLOR    = "#475569"
        TOPBAR_BORDER = "rgba(255,255,255,0.05)"
        FOOTER_BORDER = "rgba(255,255,255,0.04)"
        TOGGLE_ICON   = "☀️"
        TOGGLE_LABEL  = "Light Mode"
        SB_SECTION_C  = "#1E293B"
        ACTIVITY_BG   = "rgba(255,255,255,0.02)"
        ACTIVITY_BORDER= "rgba(255,255,255,0.05)"
        ACTIVITY_HOVER = "rgba(255,255,255,0.04)"
        GEO_BAR_BG    = "rgba(255,255,255,0.05)"
        PERF_TH_C     = "#334155"
        PERF_TD_C     = "#94A3B8"
        PERF_TD1_C    = "#E2E8F0"
        PERF_TR_HOVER = "rgba(255,255,255,0.02)"
        PERF_BORDER   = "rgba(255,255,255,0.03)"
        PERF_H_BORDER = "rgba(255,255,255,0.05)"
        KPI_SUB_C     = "#334155"
        SEC_BADGE_BG  = "rgba(99,102,241,0.1)"
        SEC_BADGE_BORDER="rgba(99,102,241,0.2)"
        INSIGHT_BG    = "#111827"
        INSIGHT_BORDER= "rgba(255,255,255,0.06)"
        INSIGHT_HOVER = "rgba(255,255,255,0.12)"
        INSIGHT_C     = "#94A3B8"
        INSIGHT_STRONG= "#E2E8F0"
        EXEC_LABEL_C  = "#334155"
        EXEC_LI_C     = "#64748B"
        EXEC_STRONG_C = "#E2E8F0"
        EXEC_MINI_BG_1= "rgba(99,102,241,0.06)"
        EXEC_MINI_BD_1= "rgba(99,102,241,0.15)"
        EXEC_MINI_BG_2= "rgba(16,185,129,0.06)"
        EXEC_MINI_BD_2= "rgba(16,185,129,0.15)"
        EXEC_MINI_BG_3= "rgba(245,158,11,0.06)"
        EXEC_MINI_BD_3= "rgba(245,158,11,0.15)"
        EXEC_MINI_BG_4= "rgba(236,72,153,0.06)"
        EXEC_MINI_BD_4= "rgba(236,72,153,0.15)"
        CHART_TITLE_C = "#E2E8F0"
        CHART_SUB_C   = "#475569"
        GEO_COUNTRY_C = "#E2E8F0"
        GEO_VAL_C     = "#94A3B8"
        TS_BADGE_BG   = "rgba(255,255,255,0.04)"
        TS_BADGE_BD   = "rgba(255,255,255,0.07)"
        TS_BADGE_C    = "#475569"
        SB_STAR_C     = "#F1F5F9"
        SB_TAG_C      = "#334155"
        SB_DIV_BG     = "rgba(255,255,255,0.04)"
        SB_USER_BORDER= "rgba(255,255,255,0.04)"
        SB_NAME_C     = "#CBD5E1"
        SB_ROLE_C     = "#334155"
        SB_NAV_C      = "#475569"
        SB_NAV_ACT_C  = "#E2E8F0"
        SB_NAV_ACT_BG = "rgba(99,102,241,0.08)"
        HEATMAP_CMAP  = sns.light_palette("#6366F1", n_colors=12, as_cmap=True)
        FIG_PATCH_BG  = 'none'
        AX_FACE_BG    = 'none'
        AX_LABEL_C    = "#475569"
        AX_TICK_C     = "#475569"
        AX_CBAR_C     = "#475569"
        HM_LINE_C     = "#0D1117"
        FOOTER_LOGO_C = "#1E293B"
        FOOTER_TEXT_C = "#1E293B"
        DATA_CARD_BG  = "#111827"
        DATA_CARD_BD  = "rgba(255,255,255,0.06)"
        NODATA_TITLE  = "#F1F5F9"
        NODATA_SUB    = "#475569"
    else:
        BG_APP        = "#F0F4F8"
        BG_SIDEBAR    = "#FFFFFF"
        BG_CARD       = "#FFFFFF"
        BG_CARD2      = "linear-gradient(145deg, #FFFFFF, #F8FAFC)"
        BORDER        = "rgba(0,0,0,0.08)"
        BORDER_HOVER  = "rgba(0,0,0,0.16)"
        TEXT_PRIMARY  = "#0F172A"
        TEXT_SECONDARY= "#475569"
        TEXT_MUTED    = "#64748B"
        TEXT_FAINT    = "#94A3B8"
        PLOT_BG       = "rgba(0,0,0,0)"
        GRID_COLOR    = "#E2E8F0"
        TICK_COLOR    = "#64748B"
        TOPBAR_BORDER = "rgba(0,0,0,0.07)"
        FOOTER_BORDER = "rgba(0,0,0,0.06)"
        TOGGLE_ICON   = "🌙"
        TOGGLE_LABEL  = "Dark Mode"
        SB_SECTION_C  = "#94A3B8"
        ACTIVITY_BG   = "rgba(0,0,0,0.02)"
        ACTIVITY_BORDER= "rgba(0,0,0,0.07)"
        ACTIVITY_HOVER = "rgba(0,0,0,0.04)"
        GEO_BAR_BG    = "rgba(0,0,0,0.06)"
        PERF_TH_C     = "#94A3B8"
        PERF_TD_C     = "#475569"
        PERF_TD1_C    = "#0F172A"
        PERF_TR_HOVER = "rgba(0,0,0,0.02)"
        PERF_BORDER   = "rgba(0,0,0,0.04)"
        PERF_H_BORDER = "rgba(0,0,0,0.08)"
        KPI_SUB_C     = "#94A3B8"
        SEC_BADGE_BG  = "rgba(99,102,241,0.08)"
        SEC_BADGE_BORDER="rgba(99,102,241,0.2)"
        INSIGHT_BG    = "#FFFFFF"
        INSIGHT_BORDER= "rgba(0,0,0,0.07)"
        INSIGHT_HOVER = "rgba(0,0,0,0.1)"
        INSIGHT_C     = "#475569"
        INSIGHT_STRONG= "#0F172A"
        EXEC_LABEL_C  = "#94A3B8"
        EXEC_LI_C     = "#475569"
        EXEC_STRONG_C = "#0F172A"
        EXEC_MINI_BG_1= "rgba(99,102,241,0.06)"
        EXEC_MINI_BD_1= "rgba(99,102,241,0.2)"
        EXEC_MINI_BG_2= "rgba(16,185,129,0.06)"
        EXEC_MINI_BD_2= "rgba(16,185,129,0.2)"
        EXEC_MINI_BG_3= "rgba(245,158,11,0.06)"
        EXEC_MINI_BD_3= "rgba(245,158,11,0.2)"
        EXEC_MINI_BG_4= "rgba(236,72,153,0.06)"
        EXEC_MINI_BD_4= "rgba(236,72,153,0.2)"
        CHART_TITLE_C = "#0F172A"
        CHART_SUB_C   = "#64748B"
        GEO_COUNTRY_C = "#0F172A"
        GEO_VAL_C     = "#475569"
        TS_BADGE_BG   = "rgba(0,0,0,0.04)"
        TS_BADGE_BD   = "rgba(0,0,0,0.08)"
        TS_BADGE_C    = "#64748B"
        SB_STAR_C     = "#0F172A"
        SB_TAG_C      = "#CBD5E1"
        SB_DIV_BG     = "rgba(0,0,0,0.06)"
        SB_USER_BORDER= "rgba(0,0,0,0.06)"
        SB_NAME_C     = "#0F172A"
        SB_ROLE_C     = "#94A3B8"
        SB_NAV_C      = "#64748B"
        SB_NAV_ACT_C  = "#0F172A"
        SB_NAV_ACT_BG = "rgba(99,102,241,0.06)"
        HEATMAP_CMAP  = sns.light_palette("#4F46E5", n_colors=12, as_cmap=True)
        FIG_PATCH_BG  = 'white'
        AX_FACE_BG    = '#F8FAFC'
        AX_LABEL_C    = "#64748B"
        AX_TICK_C     = "#64748B"
        AX_CBAR_C     = "#64748B"
        HM_LINE_C     = "#E2E8F0"
        FOOTER_LOGO_C = "#94A3B8"
        FOOTER_TEXT_C = "#94A3B8"
        DATA_CARD_BG  = "#FFFFFF"
        DATA_CARD_BD  = "rgba(0,0,0,0.08)"
        NODATA_TITLE  = "#0F172A"
        NODATA_SUB    = "#64748B"

    sns.set_theme(style="white")

    # ══════════════════════════════════════════════════════════════════════════════
    # GLOBAL CSS
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stApp"] {{
        font-family: 'DM Sans', sans-serif !important;
        background: {BG_APP} !important;
        color: {TEXT_SECONDARY} !important;
        transition: background 0.3s, color 0.3s;
    }}

    #MainMenu, footer, header {{ visibility: hidden !important; }}
    [data-testid="stToolbar"] {{ display: none !important; }}
    [data-testid="stSidebarNav"] {{ display: none !important; }}
    [data-testid="stDecoration"] {{ display: none !important; }}

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {{
        background: {BG_SIDEBAR} !important;
        border-right: 1px solid {BORDER} !important;
        width: 268px !important;
        transition: background 0.3s;
    }}
    [data-testid="stSidebar"] * {{ color: {TEXT_SECONDARY} !important; }}
    [data-testid="stSidebarContent"] {{ padding: 0 !important; }}

    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown p {{
        color: {TEXT_MUTED} !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        letter-spacing: 1px !important;
        text-transform: uppercase !important;
    }}

    [data-testid="stSidebar"] [data-baseweb="select"] > div {{
        background: {'rgba(255,255,255,0.03)' if is_dark else 'rgba(0,0,0,0.03)'} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 8px !important;
        color: {TEXT_SECONDARY} !important;
    }}

    [data-testid="stSidebar"] [data-baseweb="input"] {{
        background: {'rgba(255,255,255,0.04)' if is_dark else 'rgba(0,0,0,0.03)'} !important;
        border-radius: 8px !important;
        border: 1px solid {BORDER} !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="input"] input {{
        color: {TEXT_PRIMARY} !important;
        background: transparent !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="input"] svg {{ fill: {TEXT_MUTED} !important; }}
    [data-testid="stSidebar"] .stDateInput {{ margin-bottom: 10px !important; }}
    [data-testid="stSidebar"] [data-baseweb="tag"] {{
        background: rgba(99,102,241,0.2) !important;
        border-radius: 6px !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="tag"] span {{ color: #A5B4FC !important; }}

    /* ── Main container ── */
    .main .block-container {{
        padding: 0 36px 48px 36px !important;
        max-width: 100% !important;
    }}

    /* ── Top nav bar ── */
    .topbar {{
        display: flex; align-items: center; justify-content: space-between;
        padding: 18px 0 22px;
        border-bottom: 1px solid {TOPBAR_BORDER};
        margin-bottom: 28px;
    }}
    .topbar-left {{ display: flex; align-items: center; gap: 16px; }}
    .page-title {{
        font-family: 'Syne', sans-serif;
        font-size: 22px; font-weight: 800;
        color: {TEXT_PRIMARY}; letter-spacing: -0.5px;
    }}
    .page-title span {{ color: #6366F1; }}
    .live-badge {{
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(34,197,94,0.10); border: 1px solid rgba(34,197,94,0.2);
        border-radius: 100px; padding: 4px 10px;
        font-size: 11px; font-weight: 600; color: #22C55E;
    }}
    .live-dot {{
        width: 6px; height: 6px; border-radius: 50%;
        background: #22C55E;
        animation: pulse 1.8s ease-in-out infinite;
    }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50% {{ opacity: 0.4; transform: scale(0.8); }}
    }}
    .topbar-right {{ display: flex; align-items: center; gap: 12px; }}
    .ts-badge {{
        font-family: 'DM Mono', monospace; font-size: 12px;
        color: {TS_BADGE_C}; background: {TS_BADGE_BG};
        border: 1px solid {TS_BADGE_BD};
        border-radius: 8px; padding: 6px 12px;
    }}

    /* ── Topbar theme toggle button ── */
    .topbar-toggle-col {{
        display: flex;
        align-items: center;
        padding-top: 8px;
    }}
    .topbar-toggle-col .stButton > button {{
        background: {('rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.05)')} !important;
        color: {TEXT_SECONDARY} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        padding: 7px 14px !important;
        white-space: nowrap !important;
        transition: all 0.2s !important;
        box-shadow: none !important;
        height: auto !important;
        line-height: 1.4 !important;
    }}
    .topbar-toggle-col .stButton > button:hover {{
        background: {('rgba(255,255,255,0.10)' if is_dark else 'rgba(0,0,0,0.08)')} !important;
        border-color: {BORDER_HOVER} !important;
        transform: none !important;
    }}

    /* ── KPI Cards ── */
    .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }}
    .kpi-card {{
        background: {BG_CARD2};
        border-radius: 16px; padding: 20px 22px;
        border: 1px solid {BORDER};
        position: relative; overflow: hidden;
        transition: transform 0.2s, border-color 0.2s, background 0.3s;
    }}
    .kpi-card:hover {{ transform: translateY(-2px); border-color: {BORDER_HOVER}; }}
    .kpi-card::before {{
        content: ''; position: absolute;
        top: 0; left: 0; right: 0; height: 2px;
        border-radius: 16px 16px 0 0;
    }}
    .kpi-card.c1::before {{ background: linear-gradient(90deg, #6366F1, #8B5CF6); }}
    .kpi-card.c2::before {{ background: linear-gradient(90deg, #10B981, #34D399); }}
    .kpi-card.c3::before {{ background: linear-gradient(90deg, #F59E0B, #FBBF24); }}
    .kpi-card.c4::before {{ background: linear-gradient(90deg, #EC4899, #F472B6); }}

    .kpi-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }}
    .kpi-icon {{
        width: 36px; height: 36px; border-radius: 10px;
        display: flex; align-items: center; justify-content: center; font-size: 16px;
    }}
    .kpi-card.c1 .kpi-icon {{ background: rgba(99,102,241,0.15); }}
    .kpi-card.c2 .kpi-icon {{ background: rgba(16,185,129,0.15); }}
    .kpi-card.c3 .kpi-icon {{ background: rgba(245,158,11,0.15); }}
    .kpi-card.c4 .kpi-icon {{ background: rgba(236,72,153,0.15); }}

    .kpi-trend-badge {{
        font-size: 11px; font-weight: 600; padding: 3px 8px;
        border-radius: 100px;
    }}
    .trend-up  {{ background: rgba(16,185,129,0.12);  color: #10B981; }}
    .trend-down {{ background: rgba(239,68,68,0.10);  color: #EF4444; }}
    .trend-neu  {{ background: rgba(99,102,241,0.12);  color: #818CF8; }}

    .kpi-label {{
        font-size: 10px; font-weight: 700; letter-spacing: 1.2px;
        text-transform: uppercase; color: {TEXT_MUTED}; margin-bottom: 4px;
    }}
    .kpi-value {{
        font-family: 'Syne', sans-serif;
        font-size: 28px; font-weight: 800; color: {TEXT_PRIMARY};
        letter-spacing: -0.8px; line-height: 1;
    }}
    .kpi-sub {{ font-size: 12px; color: {KPI_SUB_C}; margin-top: 6px; }}

    /* ── Section headers ── */
    .sec-row {{
        display: flex; align-items: center; justify-content: space-between;
        margin: 32px 0 16px;
    }}
    .sec-header {{
        font-family: 'Syne', sans-serif;
        font-size: 16px; font-weight: 700; color: {TEXT_PRIMARY};
        letter-spacing: -0.3px;
    }}
    .sec-badge {{
        font-size: 11px; font-weight: 600; padding: 4px 10px;
        border-radius: 100px; color: #6366F1;
        background: {SEC_BADGE_BG};
        border: 1px solid {SEC_BADGE_BORDER};
    }}

    /* ── Chart cards ── */
    .chart-card {{
        background: {BG_CARD};
        border-radius: 16px; padding: 22px 24px;
        border: 1px solid {BORDER};
        margin-bottom: 20px;
        transition: background 0.3s, border-color 0.3s;
    }}
    .chart-title {{
        font-family: 'Syne', sans-serif;
        font-size: 14px; font-weight: 700; color: {CHART_TITLE_C}; margin-bottom: 3px;
    }}
    .chart-sub {{ font-size: 12px; color: {CHART_SUB_C}; margin-bottom: 14px; }}

    /* ── Insight pills ── */
    .insight-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
    .insight-pill {{
        background: {INSIGHT_BG}; border-radius: 12px; padding: 14px 16px;
        border: 1px solid {INSIGHT_BORDER};
        font-size: 13px; color: {INSIGHT_C}; line-height: 1.6;
        transition: border-color 0.2s, background 0.3s;
    }}
    .insight-pill:hover {{ border-color: {INSIGHT_HOVER}; }}
    .insight-pill .pill-icon {{
        font-size: 18px; margin-bottom: 8px; display: block;
    }}
    .insight-pill strong {{ color: {INSIGHT_STRONG}; }}
    .insight-pill.green  {{ border-left: 3px solid #10B981; }}
    .insight-pill.blue   {{ border-left: 3px solid #6366F1; }}
    .insight-pill.amber  {{ border-left: 3px solid #F59E0B; }}
    .insight-pill.red    {{ border-left: 3px solid #EF4444; }}
    .insight-pill.purple {{ border-left: 3px solid #A855F7; }}

    /* ── Alert banner ── */
    .alert-banner {{
        display: flex; align-items: center; gap: 12px;
        background: rgba(245,158,11,0.08);
        border: 1px solid rgba(245,158,11,0.2);
        border-radius: 12px; padding: 12px 18px;
        margin-bottom: 20px; font-size: 13px; color: #FCD34D;
    }}

    /* ── Activity feed ── */
    .activity-feed {{ display: flex; flex-direction: column; gap: 12px; }}
    .activity-item {{
        display: flex; align-items: center; gap: 12px;
        padding: 12px 14px; border-radius: 12px;
        background: {ACTIVITY_BG};
        border: 1px solid {ACTIVITY_BORDER};
        font-size: 13px; color: {TEXT_SECONDARY};
        transition: background 0.2s;
    }}
    .activity-item:hover {{ background: {ACTIVITY_HOVER}; }}
    .activity-avatar {{
        width: 32px; height: 32px; border-radius: 50%;
        background: linear-gradient(135deg, #6366F1, #8B5CF6);
        display: flex; align-items: center; justify-content: center;
        font-size: 13px; font-weight: 700; color: white;
        flex-shrink: 0;
    }}
    .activity-name {{ color: {TEXT_PRIMARY}; font-weight: 600; }}
    .activity-time {{ font-size: 11px; color: {TEXT_FAINT}; margin-top: 1px; }}
    .activity-amount {{
        margin-left: auto; font-family: 'DM Mono', monospace;
        font-size: 12px; color: #10B981; font-weight: 600;
    }}

    /* ── Geo table ── */
    .geo-row {{
        display: flex; align-items: center; gap: 10px;
        padding: 10px 0; border-bottom: 1px solid {BORDER};
        font-size: 13px;
    }}
    .geo-row:last-child {{ border-bottom: none; }}
    .geo-flag {{ font-size: 18px; }}
    .geo-country {{ color: {GEO_COUNTRY_C}; font-weight: 500; }}
    .geo-bar-wrap {{
        flex: 1; height: 4px; background: {GEO_BAR_BG};
        border-radius: 4px; overflow: hidden;
    }}
    .geo-bar {{ height: 100%; border-radius: 4px; background: linear-gradient(90deg, #6366F1, #8B5CF6); }}
    .geo-val {{ color: {GEO_VAL_C}; font-family: 'DM Mono', monospace; font-size: 12px; }}

    /* ── Performance table ── */
    .perf-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .perf-table th {{
        font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
        color: {PERF_TH_C}; padding: 8px 12px; text-align: left;
        border-bottom: 1px solid {PERF_H_BORDER};
    }}
    .perf-table td {{ padding: 10px 12px; color: {PERF_TD_C}; border-bottom: 1px solid {PERF_BORDER}; }}
    .perf-table td:first-child {{ color: {PERF_TD1_C}; font-weight: 500; }}
    .perf-table tr:hover td {{ background: {PERF_TR_HOVER}; }}
    .status-dot {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 6px; }}
    .dot-green {{ background: #10B981; }}
    .dot-amber {{ background: #F59E0B; }}
    .dot-red   {{ background: #EF4444; }}

    /* ── Download button ── */
    .stDownloadButton > button {{
        background: linear-gradient(135deg, #6366F1, #8B5CF6) !important;
        color: white !important; border: none !important;
        border-radius: 10px !important; padding: 10px 24px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important; font-size: 14px !important;
        box-shadow: 0 4px 20px rgba(99,102,241,0.3) !important;
        transition: all 0.2s !important;
    }}
    .stDownloadButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px rgba(99,102,241,0.4) !important;
    }}

    /* ── Sidebar logout button ── */
    [data-testid="stSidebar"] .stButton > button {{
        background: rgba(239,68,68,0.08) !important;
        color: #EF4444 !important; border: 1px solid rgba(239,68,68,0.2) !important;
        border-radius: 8px !important; width: 100% !important;
        font-size: 13px !important; font-weight: 600 !important;
        padding: 8px 16px !important;
    }}

    /* ── Scrollbar ── */
    ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: {'rgba(255,255,255,0.08)' if is_dark else 'rgba(0,0,0,0.12)'}; border-radius: 4px; }}

    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {{ border-radius: 12px !important; overflow: hidden !important; }}

    /* ── Selectbox ── */
    [data-baseweb="select"] > div {{
        background: {'rgba(255,255,255,0.03)' if is_dark else 'rgba(0,0,0,0.03)'} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 8px !important;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════════
    # LOAD DATA
    # ══════════════════════════════════════════════════════════════════════════════
    @st.cache_data(ttl=30)
    def load_data():
        _df = pd.read_csv(DATA_PATH)
        _df['orderdate'] = pd.to_datetime(_df['orderdate'])
        return _df

    df = load_data()

    # ══════════════════════════════════════════════════════════════════════════════
    # SESSION STATE
    # ══════════════════════════════════════════════════════════════════════════════
    if 'last_refresh' not in st.session_state:
        st.session_state['last_refresh'] = datetime.now()
    if 'refresh_count' not in st.session_state:
        st.session_state['refresh_count'] = 0
    if 'alerts_dismissed' not in st.session_state:
        st.session_state['alerts_dismissed'] = False

    # ══════════════════════════════════════════════════════════════════════════════
    # SIDEBAR
    # ══════════════════════════════════════════════════════════════════════════════
    with st.sidebar:
        st.markdown(f"""
        <style>
        .sb-brand {{
            padding: 24px 20px 18px;
            border-bottom: 1px solid {BORDER};
            margin-bottom: 4px;
        }}
        .sb-logo {{
            font-family: 'Syne', sans-serif;
            font-size: 18px; font-weight: 800; color: {SB_STAR_C} !important;
            letter-spacing: -0.4px;
        }}
        .sb-logo span {{ color: #6366F1 !important; }}
        .sb-tagline {{ font-size: 11px; color: {SB_TAG_C} !important; margin-top: 4px; }}
        .sb-nav-item {{
            display: flex; align-items: center; gap: 10px;
            padding: 9px 20px; font-size: 13px; font-weight: 500;
            color: {SB_NAV_C} !important; cursor: pointer;
            transition: all 0.15s; letter-spacing: 0;
            text-transform: none !important;
        }}
        .sb-nav-item.active {{
            color: {SB_NAV_ACT_C} !important; background: {SB_NAV_ACT_BG};
            border-right: 2px solid #6366F1;
        }}
        .sb-section {{
            font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
            text-transform: uppercase; color: {SB_SECTION_C} !important;
            padding: 18px 20px 8px;
        }}
        .sb-divider {{ height: 1px; background: {SB_DIV_BG}; margin: 12px 0; }}
        .sb-user {{
            padding: 14px 20px;
            display: flex; align-items: center; gap: 10px;
            border-top: 1px solid {SB_USER_BORDER};
        }}
        .sb-avatar {{
            width: 32px; height: 32px; border-radius: 50%;
            background: linear-gradient(135deg, #6366F1, #8B5CF6);
            display: flex; align-items: center; justify-content: center;
            font-size: 13px; font-weight: 700; color: white !important;
            flex-shrink: 0;
        }}
        .sb-username {{ font-size: 13px; font-weight: 600; color: {SB_NAME_C} !important; }}
        .sb-role {{ font-size: 11px; color: {SB_ROLE_C} !important; }}
        </style>

        <div class="sb-brand">
            <div class="sb-logo">Nexus<span>BI</span></div>
            <div class="sb-tagline">Business Intelligence Platform</div>
        </div>
        <div class="sb-nav-item active">⚡ &nbsp; Overview</div>
        <div class="sb-nav-item">📈 &nbsp; Revenue</div>
        <div class="sb-nav-item">🌍 &nbsp; Geography</div>
        <div class="sb-nav-item">👥 &nbsp; Customers</div>
        <div class="sb-nav-item">📦 &nbsp; Products</div>
        <div class="sb-nav-item">🔔 &nbsp; Alerts</div>
        """, unsafe_allow_html=True)

        st.markdown(f'<div class="sb-section">📅 Date Range</div>', unsafe_allow_html=True)
        start_date = st.date_input("Start", df['orderdate'].min(), label_visibility="collapsed")
        end_date   = st.date_input("End",   df['orderdate'].max(), label_visibility="collapsed")

        st.markdown(f'<div class="sb-divider"></div><div class="sb-section">🌍 Countries</div>', unsafe_allow_html=True)
        country_filter = st.multiselect(
            "Country", df['country'].unique(),
            default=df['country'].unique(),
            label_visibility="collapsed",
        )

        st.markdown(f'<div class="sb-divider"></div><div class="sb-section">📦 Product Lines</div>', unsafe_allow_html=True)
        product_filter = st.multiselect(
            "Product", df['productline'].unique(),
            default=df['productline'].unique(),
            label_visibility="collapsed",
        )

        # ── Refresh controls ──
        st.markdown(f'<div class="sb-divider"></div><div class="sb-section">🔄 Live Refresh</div>', unsafe_allow_html=True)
        auto_refresh = st.toggle("Auto-refresh (30s)", value=False)
        refresh_interval = st.selectbox(
            "Interval", ["15s", "30s", "60s", "5 min"],
            index=1, label_visibility="collapsed"
        )

        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)

        # ── Filter summary ──
        n_countries = len(country_filter)
        n_products  = len(product_filter)
        last_ref = st.session_state['last_refresh'].strftime('%H:%M:%S')
        st.markdown(f"""
        <div style="padding: 10px 20px;">
            <div style="font-size:11px;color:{SB_SECTION_C};margin-bottom:8px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;">Filter Summary</div>
            <div style="font-size:12px;color:{TEXT_MUTED};line-height:2;">
                {n_countries} countr{'y' if n_countries==1 else 'ies'}<br>
                {n_products} product line{'s' if n_products!=1 else ''}<br>
                <span style="font-family:'DM Mono',monospace;font-size:11px;color:{TEXT_FAINT};">Last sync {last_ref}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── User info ──
        username = st.session_state.get('user', 'Analyst')
        st.markdown(f"""
        <div class="sb-user">
            <div class="sb-avatar">{username[0].upper()}</div>
            <div>
                <div class="sb-username">{username}</div>
                <div class="sb-role">Business Analyst</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚪 Log Out"):
            st.session_state.logged_in = False
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════════
    # APPLY FILTERS
    # ══════════════════════════════════════════════════════════════════════════════
    filtered_df = df[
        (df['orderdate'] >= pd.to_datetime(start_date)) &
        (df['orderdate'] <= pd.to_datetime(end_date)) &
        (df['country'].isin(country_filter)) &
        (df['productline'].isin(product_filter))
    ]

    if filtered_df.empty:
        st.markdown(f"""
        <div style="text-align:center;padding:120px 0;">
            <div style="font-size:52px;margin-bottom:16px;">🔍</div>
            <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:{NODATA_TITLE};margin-bottom:8px;">
                No data matches your filters
            </div>
            <div style="font-size:14px;color:{NODATA_SUB};">
                Adjust the filters in the sidebar to explore your data.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ══════════════════════════════════════════════════════════════════════════════
    # AUTO-REFRESH LOGIC
    # ══════════════════════════════════════════════════════════════════════════════
    interval_map = {"15s": 15, "30s": 30, "60s": 60, "5 min": 300}
    if auto_refresh:
        seconds_since = (datetime.now() - st.session_state['last_refresh']).seconds
        if seconds_since >= interval_map[refresh_interval]:
            st.session_state['last_refresh'] = datetime.now()
            st.session_state['refresh_count'] += 1
            st.cache_data.clear()
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════════
    # TOP BAR  (theme toggle button lives here, right side)
    # ══════════════════════════════════════════════════════════════════════════════
    now_str = datetime.now().strftime("%a %d %b %Y · %H:%M:%S")

    topbar_col, toggle_col = st.columns([9, 1], gap="small")

    with topbar_col:
        st.markdown(f"""
        <div class="topbar">
            <div class="topbar-left">
                <div class="page-title">Revenue <span>Intelligence</span></div>
                <div class="live-badge">
                    <div class="live-dot"></div>
                    LIVE
                </div>
            </div>
            <div class="topbar-right">
                <div class="ts-badge">🕐 {now_str}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with toggle_col:
        st.markdown('<div class="topbar-toggle-col">', unsafe_allow_html=True)
        if st.button(f"{TOGGLE_ICON} {TOGGLE_LABEL}", key="topbar_theme_toggle"):
            st.session_state['theme'] = 'light' if is_dark else 'dark'
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════════
    # ANOMALY ALERTS
    # ══════════════════════════════════════════════════════════════════════════════
    monthly_kpi = filtered_df.groupby(
        filtered_df['orderdate'].dt.to_period('M')
    )['sales'].sum()

    if len(monthly_kpi) >= 3:
        last_m  = monthly_kpi.iloc[-1]
        prev_m  = monthly_kpi.iloc[-2]
        avg_m   = monthly_kpi.mean()
        pct_chg = ((last_m - prev_m) / prev_m * 100) if prev_m > 0 else 0

        if abs(pct_chg) > 20 and not st.session_state['alerts_dismissed']:
            direction = "spike" if pct_chg > 0 else "drop"
            emoji     = "📈" if pct_chg > 0 else "📉"
            st.markdown(f"""
            <div class="alert-banner">
                <span style="font-size:18px;">{emoji}</span>
                <div>
                    <strong>Anomaly Detected</strong> — Revenue {direction} of
                    <strong>{abs(pct_chg):.1f}%</strong> in the most recent period
                    vs previous month (${last_m:,.0f} vs ${prev_m:,.0f}).
                    Consider reviewing for seasonality or data quality.
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════════
    # KPI METRICS
    # ══════════════════════════════════════════════════════════════════════════════
    total_sales  = filtered_df['sales'].sum()
    orders       = filtered_df['ordernumber'].nunique()
    avg_sales    = filtered_df['sales'].mean()
    total_qty    = filtered_df['quantityordered'].sum() if 'quantityordered' in filtered_df.columns else 0

    monthly_ts   = monthly_kpi.to_timestamp()
    growth       = monthly_ts.pct_change().mean() * 100 if len(monthly_ts) > 1 else 0
    growth_dir   = "trend-up" if growth >= 0 else "trend-down"
    growth_sym   = f"↑ {abs(growth):.1f}%" if growth >= 0 else f"↓ {abs(growth):.1f}%"

    col1, col2, col3, col4 = st.columns(4, gap="medium")
    with col1:
        st.markdown(f"""
        <div class="kpi-card c1">
            <div class="kpi-header">
                <div class="kpi-icon">💰</div>
                <span class="kpi-trend-badge trend-neu">Filtered</span>
            </div>
            <div class="kpi-label">Total Revenue</div>
            <div class="kpi-value">${total_sales:,.0f}</div>
            <div class="kpi-sub">Across all selected markets</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card c2">
            <div class="kpi-header">
                <div class="kpi-icon">📦</div>
                <span class="kpi-trend-badge trend-up">Unique</span>
            </div>
            <div class="kpi-label">Total Orders</div>
            <div class="kpi-value">{orders:,}</div>
            <div class="kpi-sub">Order transactions processed</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="kpi-card c3">
            <div class="kpi-header">
                <div class="kpi-icon">📊</div>
                <span class="kpi-trend-badge trend-neu">Per Order</span>
            </div>
            <div class="kpi-label">Avg Order Value</div>
            <div class="kpi-value">${avg_sales:,.0f}</div>
            <div class="kpi-sub">Mean revenue per transaction</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="kpi-card c4">
            <div class="kpi-header">
                <div class="kpi-icon">📈</div>
                <span class="kpi-trend-badge {growth_dir}">{growth_sym}</span>
            </div>
            <div class="kpi-label">Avg Monthly Growth</div>
            <div class="kpi-value">{growth:+.1f}%</div>
            <div class="kpi-sub">Month-over-month average</div>
        </div>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════════
    # PLOTLY LAYOUT FACTORY
    # ══════════════════════════════════════════════════════════════════════════════
    def pl(height=300, xgrid=False, ygrid=True):
        return dict(
            paper_bgcolor=PLOT_BG,
            plot_bgcolor=PLOT_BG,
            font=dict(family="DM Sans", size=12, color=TICK_COLOR),
            margin=dict(l=8, r=8, t=24, b=8),
            height=height,
            legend=dict(
                bgcolor="rgba(0,0,0,0)", font=dict(color=TICK_COLOR),
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            xaxis=dict(showgrid=xgrid, zeroline=False, linecolor=GRID_COLOR, tickfont=dict(color=TICK_COLOR)),
            yaxis=dict(showgrid=ygrid, gridcolor=GRID_COLOR, zeroline=False, tickfont=dict(color=TICK_COLOR)),
        )

    PALETTE = ["#6366F1", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6", "#06B6D4", "#F97316", "#14B8A6"]

    # ══════════════════════════════════════════════════════════════════════════════
    # SECTION 1 — REVENUE TREND + ACTIVITY FEED
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown("""
    <div class="sec-row">
        <div class="sec-header">📈 Revenue Trend</div>
        <span class="sec-badge">Live · 30s refresh</span>
    </div>
    """, unsafe_allow_html=True)

    col_trend, col_activity = st.columns([3, 1], gap="medium")

    with col_trend:
        ma_vals = monthly_ts.rolling(window=3).mean().values
        monthly_plot = monthly_ts.reset_index()
        monthly_plot.columns = ['date', 'revenue']
        monthly_plot['date'] = monthly_plot['date'].astype(str)

        rolling_std  = monthly_ts.rolling(window=3).std().values
        rolling_mean = monthly_ts.rolling(window=3).mean().values
        upper_band   = rolling_mean + 2 * np.where(np.isnan(rolling_std), 0, rolling_std)
        lower_band   = np.maximum(rolling_mean - 2 * np.where(np.isnan(rolling_std), 0, rolling_std), 0)

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=monthly_plot['date'].tolist() + monthly_plot['date'].tolist()[::-1],
            y=upper_band.tolist() + lower_band.tolist()[::-1],
            fill='toself', fillcolor='rgba(99,102,241,0.06)',
            line=dict(color='rgba(0,0,0,0)'), name='2σ Band', showlegend=True,
            hoverinfo='skip',
        ))
        fig_trend.add_trace(go.Scatter(
            x=monthly_plot['date'], y=monthly_plot['revenue'],
            mode='lines', name='Revenue',
            line=dict(color='#6366F1', width=2.5),
            fill='tozeroy', fillcolor='rgba(99,102,241,0.08)',
        ))
        fig_trend.add_trace(go.Scatter(
            x=monthly_plot['date'], y=ma_vals,
            mode='lines', name='3M Moving Avg',
            line=dict(color='#10B981', width=2, dash='dot'),
        ))
        layout_t = pl(300)
        layout_t['xaxis']['tickangle'] = -25
        fig_trend.update_layout(**layout_t)
        fig_trend.update_traces(hovertemplate='%{x}<br><b>$%{y:,.0f}</b><extra></extra>')

        st.markdown(f"""
        <div class="chart-card">
            <div class="chart-title">Monthly Revenue with 3M Moving Average &amp; Confidence Band</div>
            <div class="chart-sub">Shaded area = 2σ volatility envelope · Green dashes = trend smoothing</div>
        </div>
        """, unsafe_allow_html=True)
        # ── FIX: render chart OUTSIDE the HTML block ──
        st.plotly_chart(fig_trend, width='stretch', config={"displayModeBar": False})

    with col_activity:
        # ── FIX: build each activity item as a separate st.markdown call inside a container ──
        recent = filtered_df.nlargest(6, 'sales')[['customername', 'sales', 'orderdate']].copy()
        colors = ["#6366F1", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6", "#06B6D4"]

        st.markdown(f"""
        <div class="chart-card">
            <div class="chart-title">Recent Activity</div>
            <div class="chart-sub">Top transactions</div>
        </div>
        """, unsafe_allow_html=True)

        for i, (_, row) in enumerate(recent.iterrows()):
            initials = ''.join([w[0] for w in str(row['customername']).split()[:2]]).upper()
            mins_ago = (i + 1) * 9
            bg = colors[i % len(colors)]
            st.markdown(f"""
            <div class="activity-item">
                <div class="activity-avatar" style="background:linear-gradient(135deg,{bg},{bg}99);">{initials}</div>
                <div style="flex:1;min-width:0;">
                    <div class="activity-name" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:12px;">{row['customername'][:18]}</div>
                    <div class="activity-time">{mins_ago}m ago</div>
                </div>
                <div class="activity-amount">+${row['sales']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════════
    # SECTION 2 — COUNTRY + PRODUCT + DEAL SIZE
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sec-row"><div class="sec-header">🌍 Market &amp; Product Performance</div></div>', unsafe_allow_html=True)

    col_c, col_p, col_d = st.columns([2, 2, 1.2], gap="medium")

    with col_c:
        country_data = (
            filtered_df.groupby('country')['sales'].sum()
            .reset_index().sort_values('sales', ascending=True).tail(8)
        )
        max_c = country_data['sales'].max()
        flags = {
            "USA": "🇺🇸", "France": "🇫🇷", "Spain": "🇪🇸", "Australia": "🇦🇺",
            "UK": "🇬🇧", "Germany": "🇩🇪", "Italy": "🇮🇹", "Japan": "🇯🇵",
            "Finland": "🇫🇮", "Norway": "🇳🇴", "Sweden": "🇸🇪", "Denmark": "🇩🇰",
            "Belgium": "🇧🇪", "Austria": "🇦🇹", "Switzerland": "🇨🇭", "Singapore": "🇸🇬",
            "Canada": "🇨🇦", "Ireland": "🇮🇪", "Philippines": "🇵🇭",
        }

        # ── FIX: render header once, then each row separately ──
        st.markdown(f"""
        <div class="chart-card">
            <div class="chart-title">Revenue by Country</div>
            <div class="chart-sub">Top 8 markets</div>
        </div>
        """, unsafe_allow_html=True)

        for _, row in country_data.iloc[::-1].iterrows():
            pct  = (row['sales'] / max_c) * 100
            flag = flags.get(row['country'], "🌐")
            st.markdown(f"""
            <div class="geo-row">
                <span class="geo-flag">{flag}</span>
                <span class="geo-country" style="min-width:80px;font-size:12px;">{row['country']}</span>
                <div class="geo-bar-wrap"><div class="geo-bar" style="width:{pct:.0f}%;"></div></div>
                <span class="geo-val">${row['sales']/1e3:.0f}K</span>
            </div>
            """, unsafe_allow_html=True)

    with col_p:
        product_data = (
            filtered_df.groupby('productline')['sales'].sum()
            .reset_index().sort_values('sales', ascending=False)
        )
        fig_p = go.Figure(go.Bar(
            x=product_data['productline'],
            y=product_data['sales'],
            marker=dict(
                color=product_data['sales'],
                colorscale=[[0, "#1E1B4B"], [0.5, "#6366F1"], [1, "#A5B4FC"]],
                showscale=False,
            ),
            text=[f"${v/1e3:.0f}K" for v in product_data['sales']],
            textposition='outside', textfont=dict(color=TICK_COLOR, size=11),
        ))
        layout_p = pl(260)
        layout_p['margin']['b'] = 40
        fig_p.update_layout(**layout_p)
        fig_p.update_traces(hovertemplate='<b>%{x}</b><br>$%{y:,.0f}<extra></extra>')

        st.markdown(f"""
        <div class="chart-card">
            <div class="chart-title">Revenue by Product Line</div>
            <div class="chart-sub">Comparative performance</div>
        </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(fig_p, width='stretch', config={"displayModeBar": False})

    with col_d:
        if 'dealsize' in filtered_df.columns:
            deal_data = filtered_df.groupby('dealsize')['sales'].sum().reset_index()
            fig_d = go.Figure(go.Pie(
                labels=deal_data['dealsize'],
                values=deal_data['sales'],
                hole=0.62,
                marker=dict(colors=["#6366F1", "#10B981", "#F59E0B"], line=dict(color=BG_CARD, width=2)),
                textinfo='percent',
                textfont=dict(size=11, color=TEXT_SECONDARY),
            ))
            total_d = deal_data['sales'].sum()
            fig_d.update_layout(
                paper_bgcolor=PLOT_BG, font=dict(family="DM Sans"),
                showlegend=True, height=280,
                margin=dict(l=0, r=0, t=0, b=0),
                legend=dict(
                    bgcolor="rgba(0,0,0,0)", font=dict(color=TICK_COLOR, size=11),
                    orientation="v", x=0.5, xanchor="center",
                )
            )
            fig_d.add_annotation(
                text=f"${total_d/1e6:.1f}M", x=0.5, y=0.5,
                font=dict(family="Syne", size=16, color=TEXT_PRIMARY),
                showarrow=False
            )
            st.markdown(f"""
            <div class="chart-card">
                <div class="chart-title">Deal Size Mix</div>
                <div class="chart-sub">Revenue distribution</div>
            </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(fig_d, width='stretch', config={"displayModeBar": False})

    # ══════════════════════════════════════════════════════════════════════════════
    # SECTION 3 — TOP CUSTOMERS + YoY COMPARISON
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sec-row"><div class="sec-header">👥 Customer Intelligence</div></div>', unsafe_allow_html=True)

    col_cust, col_yoy = st.columns([3, 2], gap="medium")

    with col_cust:
        top_cust = (
            filtered_df.groupby('customername')['sales']
            .agg(['sum', 'count', 'mean'])
            .reset_index()
            .nlargest(8, 'sum')
            .sort_values('sum', ascending=True)
        )
        fig_cust = go.Figure(go.Bar(
            x=top_cust['sum'], y=top_cust['customername'],
            orientation='h',
            marker=dict(
                color=top_cust['sum'],
                colorscale=[[0, "#052e16"], [0.5, "#10B981"], [1, "#34D399"]],
                showscale=False,
            ),
            text=[f"${v/1e3:.0f}K" for v in top_cust['sum']],
            textposition='inside', textfont=dict(color="white", size=11),
        ))
        lc = pl(300)
        lc.pop('yaxis', None)
        fig_cust.update_layout(**lc)
        fig_cust.update_yaxes(showgrid=False, zeroline=False, tickfont=dict(color=TICK_COLOR, size=11))
        fig_cust.update_xaxes(showgrid=True, gridcolor=GRID_COLOR)
        fig_cust.update_traces(hovertemplate='<b>%{y}</b><br>Revenue: $%{x:,.0f}<extra></extra>')

        st.markdown(f"""
        <div class="chart-card">
            <div class="chart-title">Top 8 Customers by Revenue</div>
            <div class="chart-sub">Highest value accounts in filtered period</div>
        </div>
        """, unsafe_allow_html=True)
        st.plotly_chart(fig_cust, width='stretch', config={"displayModeBar": False})

    with col_yoy:
        if 'year_id' in filtered_df.columns:
            yoy = filtered_df.groupby('year_id')['sales'].sum().reset_index()
            yoy.columns = ['Year', 'Revenue']
            yoy['YoY%'] = yoy['Revenue'].pct_change() * 100

            # ── FIX: build complete table HTML as one string, emit once ──
            table_rows_html = ""
            for _, row in yoy.iterrows():
                yoy_str  = f"{row['YoY%']:+.1f}%" if not pd.isna(row['YoY%']) else "—"
                dot_cls  = "dot-green" if not pd.isna(row['YoY%']) and row['YoY%'] >= 0 else "dot-red"
                color    = "#10B981" if not pd.isna(row['YoY%']) and row['YoY%'] >= 0 else "#EF4444"
                table_rows_html += (
                    f"<tr>"
                    f"<td>{int(row['Year'])}</td>"
                    f"<td>${row['Revenue']/1e6:.2f}M</td>"
                    f"<td><span style='color:{color};font-weight:600;'>{yoy_str}</span></td>"
                    f"<td><span class='status-dot {dot_cls}'></span></td>"
                    f"</tr>"
                )

            st.markdown(f"""
            <div class="chart-card">
                <div class="chart-title">Year-over-Year Performance</div>
                <div class="chart-sub">Annual revenue and growth rates</div>
                <table class="perf-table">
                    <thead>
                        <tr>
                            <th>Year</th><th>Revenue</th><th>YoY Growth</th><th>Status</th>
                        </tr>
                    </thead>
                    <tbody>{table_rows_html}</tbody>
                </table>
            </div>
            """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════════
    # SECTION 4 — HEATMAP + PRODUCT TREND
    # ══════════════════════════════════════════════════════════════════════════════
    if 'month_id' in filtered_df.columns and 'year_id' in filtered_df.columns:
        st.markdown('<div class="sec-row"><div class="sec-header">🔥 Seasonality &amp; Trends</div></div>', unsafe_allow_html=True)

        col_heat, col_prod_trend = st.columns([3, 2], gap="medium")

        with col_heat:
            pivot = filtered_df.pivot_table(
                values='sales', index='month_id', columns='year_id', aggfunc='sum'
            )
            month_labels = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                            7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
            pivot.index = [month_labels.get(m, m) for m in pivot.index]

            fig_heat, ax = plt.subplots(figsize=(10, 4))
            fig_heat.patch.set_facecolor(FIG_PATCH_BG)
            ax.set_facecolor(AX_FACE_BG)
            sns.heatmap(
                pivot, annot=True, fmt=".0f", ax=ax,
                cmap=HEATMAP_CMAP,
                linewidths=0.8, linecolor=HM_LINE_C,
                cbar_kws={"shrink": 0.7, "aspect": 20},
            )
            ax.set_xlabel("Year",  fontsize=11, color=AX_LABEL_C)
            ax.set_ylabel("Month", fontsize=11, color=AX_LABEL_C)
            ax.tick_params(labelsize=10, colors=AX_TICK_C)
            ax.collections[0].colorbar.ax.tick_params(colors=AX_CBAR_C)
            plt.tight_layout()

            st.markdown(f"""
            <div class="chart-card">
                <div class="chart-title">Month × Year Revenue Heatmap</div>
                <div class="chart-sub">Identify seasonal peaks and valleys across years</div>
            </div>
            """, unsafe_allow_html=True)
            st.pyplot(fig_heat, width='stretch')

        with col_prod_trend:
            prod_monthly = (
                filtered_df.groupby([filtered_df['orderdate'].dt.to_period('Q'), 'productline'])['sales']
                .sum().reset_index()
            )
            prod_monthly['orderdate'] = prod_monthly['orderdate'].astype(str)
            fig_pt = px.line(
                prod_monthly, x='orderdate', y='sales', color='productline',
                color_discrete_sequence=PALETTE,
                markers=True,
            )
            lpt = pl(290)
            lpt['xaxis']['tickangle'] = -25
            fig_pt.update_layout(**lpt)
            fig_pt.update_traces(hovertemplate='Q: %{x}<br>$%{y:,.0f}<extra></extra>', marker_size=5)

            st.markdown(f"""
            <div class="chart-card">
                <div class="chart-title">Product Line Quarterly Trend</div>
                <div class="chart-sub">Quarterly revenue by product category</div>
            </div>
            """, unsafe_allow_html=True)
            st.plotly_chart(fig_pt, width='stretch', config={"displayModeBar": False})

    # ══════════════════════════════════════════════════════════════════════════════
    # SECTION 5 — AI INSIGHTS
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sec-row"><div class="sec-header">💡 AI-Generated Insights</div><span class="sec-badge">Powered by data analysis</span></div>', unsafe_allow_html=True)

    insights = [
        ("green",  "🏆", top_country_insight(filtered_df)),
        ("blue",   "🌐", country_contribution_insight(filtered_df)),
        ("green",  "📦", top_product_insight(filtered_df)),
        ("red",    "⚠️", lowest_product_insight(filtered_df)),
        ("blue",   "👤", top_customer_insight(filtered_df)),
        ("purple", "🔗", customer_concentration_insight(filtered_df)),
        ("green",  "📈", revenue_trend_insight(filtered_df)),
        ("amber",  "📅", peak_month_insight(filtered_df)),
        ("purple", "💼", dealsize_insight(filtered_df)),
    ]

    rows = [insights[i:i+3] for i in range(0, len(insights), 3)]
    for row in rows:
        cols = st.columns(3, gap="medium")
        for col, (color, icon, text) in zip(cols, row):
            with col:
                st.markdown(f"""
                <div class="insight-pill {color}">
                    <span class="pill-icon">{icon}</span>
                    {text}
                </div>
                """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════════
    # SECTION — AI CHAT INTERFACE  (Teams 2 + 3 integration)
    # ══════════════════════════════════════════════════════════════════════════════

    from visualization.nlp_bridge import ask_question, get_bridge_status

    if 'chat_history' not in st.session_state:
        st.session_state['chat_history'] = []

    bridge = get_bridge_status()

    # ── Status badges ──
    def _status_pill(label, status):
        color  = "#10B981" if status == "online" else "#EF4444"
        bg     = "rgba(16,185,129,0.10)" if status == "online" else "rgba(239,68,68,0.08)"
        border = "rgba(16,185,129,0.25)" if status == "online" else "rgba(239,68,68,0.20)"
        dot    = "●"
        return (
            f"<span style='display:inline-flex;align-items:center;gap:5px;"
            f"background:{bg};border:1px solid {border};border-radius:100px;"
            f"padding:3px 10px;font-size:11px;font-weight:600;color:{color};margin-right:6px;'>"
            f"<span style='font-size:8px;'>{dot}</span>{label}</span>"
        )

    st.markdown(
        '<div class="sec-row">'
        '<div class="sec-header">💬 AI Chat</div>'
        '<span class="sec-badge">Ask anything about your data</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    status_html = (
        _status_pill("NLP models",       bridge["nlp_models"])
        + _status_pill("NLP utils",      bridge["nlp_utils"])
        + _status_pill("Analytics API",  bridge["analytics_engine"])
    )
    st.markdown(
        f"<div style='margin-bottom:14px;'>{status_html}</div>",
        unsafe_allow_html=True,
    )

    # ── Suggested questions ──
    SUGGESTIONS = [
        "Top 5 products by revenue",
        "Compare 2003 vs 2004 sales",
        "Predict next month sales",
        "Which country generates most profit?",
    ]

    st.markdown(
        f"<div style='font-size:11px;font-weight:700;letter-spacing:1px;"
        f"text-transform:uppercase;color:{TEXT_MUTED};margin-bottom:8px;'>Suggested</div>",
        unsafe_allow_html=True,
    )
    sug_cols = st.columns(len(SUGGESTIONS), gap="small")
    for col, suggestion in zip(sug_cols, SUGGESTIONS):
        with col:
            if st.button(suggestion, key=f"sug_{suggestion}"):
                st.session_state['chat_history'].append({
                    "role": "user", "text": suggestion
                })
                with st.spinner("Thinking..."):
                    result = ask_question(suggestion)
                st.session_state['chat_history'].append({
                    "role": "assistant",
                    "text": result["response"],
                    "intent": result["intent"],
                    "confidence": result["confidence"],
                    "chart_data": result["chart_data"],
                })
                st.rerun()

    # ── Chat history ──
    st.markdown(
        f"<div class='chart-card' style='margin-top:12px;min-height:120px;'>",
        unsafe_allow_html=True,
    )

    if not st.session_state['chat_history']:
        st.markdown(
            f"<div style='text-align:center;padding:32px 0;"
            f"color:{TEXT_MUTED};font-size:13px;'>"
            f"Ask a question about your data above, or try a suggestion."
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        for msg_idx,msg in enumerate(st.session_state['chat_history']):
            if msg["role"] == "user":
                st.markdown(
                    f"<div style='display:flex;justify-content:flex-end;margin-bottom:10px;'>"
                    f"<div style='background:rgba(99,102,241,0.12);border:1px solid rgba(99,102,241,0.2);"
                    f"border-radius:12px 12px 2px 12px;padding:10px 14px;max-width:70%;"
                    f"font-size:13px;color:{TEXT_PRIMARY};'>{msg['text']}</div></div>",
                    unsafe_allow_html=True,
                )
            else:
                intent_badge = ""
                if msg.get("intent"):
                    conf_pct = int(msg.get("confidence", 0) * 100)
                    conf_color = "#10B981" if conf_pct >= 80 else "#F59E0B" if conf_pct >= 50 else "#EF4444"
                    intent_badge = (
                        f"<div style='font-size:10px;color:{TEXT_MUTED};margin-bottom:6px;"
                        f"font-family:\"DM Mono\",monospace;'>"
                        f"Intent: <span style='color:{conf_color};'>{msg['intent']}</span> "
                        f"· {conf_pct}% confidence</div>"
                    )

                response_html = msg["text"].replace("\n", "<br>")
                st.markdown(
                    f"<div style='display:flex;gap:10px;margin-bottom:12px;'>"
                    f"<div style='width:28px;height:28px;border-radius:50%;"
                    f"background:linear-gradient(135deg,#6366F1,#8B5CF6);"
                    f"display:flex;align-items:center;justify-content:center;"
                    f"font-size:12px;color:white;flex-shrink:0;font-weight:700;'>AI</div>"
                    f"<div style='flex:1;'>"
                    f"{intent_badge}"
                    f"<div style='background:{BG_CARD};border:1px solid {BORDER};"
                    f"border-radius:2px 12px 12px 12px;padding:10px 14px;"
                    f"font-size:13px;color:{TEXT_SECONDARY};line-height:1.7;'>"
                    f"{response_html}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

                # ── Auto chart: render if chart_data was returned ──
                chart_data = msg.get("chart_data")
                if chart_data and len(chart_data) > 0:
                    import pandas as pd
                    import plotly.express as px
                    df_chart = pd.DataFrame(chart_data)
                    numeric_cols = df_chart.select_dtypes(include="number").columns.tolist()
                    category_cols = df_chart.select_dtypes(exclude="number").columns.tolist()
                    if numeric_cols and category_cols:
                        fig_chat = px.bar(
                            df_chart,
                            x=category_cols[0],
                            y=numeric_cols[0],
                            color_discrete_sequence=["#6366F1"],
                        )
                        fig_chat.update_layout(
                            paper_bgcolor=PLOT_BG, plot_bgcolor=PLOT_BG,
                            font=dict(family="DM Sans", color=TICK_COLOR),
                            margin=dict(l=8, r=8, t=16, b=8),
                            height=220,
                            xaxis=dict(showgrid=False, tickfont=dict(color=TICK_COLOR)),
                            yaxis=dict(showgrid=True, gridcolor=GRID_COLOR,
                                    tickfont=dict(color=TICK_COLOR)),
                        )
                        st.plotly_chart(fig_chat, use_container_width='stretch',
                                        config={"displayModeBar": False},
                                        key=f"chat_chart_{msg_idx}")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Text input ──
    with st.form("chat_form", clear_on_submit=True):
        chat_col, btn_col = st.columns([5, 1], gap="small")
        with chat_col:
            user_input = st.text_input(
                "Question",
                placeholder='e.g. "Top 5 countries by revenue" or "Forecast next quarter"',
                label_visibility="collapsed",
            )
        with btn_col:
            submitted = st.form_submit_button("Ask →")

        if submitted and user_input.strip():
            st.session_state['chat_history'].append({
                "role": "user", "text": user_input.strip()
            })
            with st.spinner("Analysing..."):
                result = ask_question(user_input.strip())
            st.session_state['chat_history'].append({
                "role": "assistant",
                "text": result["response"],
                "intent": result["intent"],
                "confidence": result["confidence"],
                "chart_data": result["chart_data"],
            })
            st.rerun()

    # Clear chat button
    if st.session_state['chat_history']:
        if st.button("🗑 Clear chat", key="clear_chat"):
            st.session_state['chat_history'] = []
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════════
    # SECTION 6 — EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sec-row"><div class="sec-header">🧠 Executive Summary</div></div>', unsafe_allow_html=True)

    trend_word    = "growing 📈" if growth > 0 else "contracting 📉"
    top_country   = filtered_df.groupby('country')['sales'].sum().idxmax()
    top_product   = filtered_df.groupby('productline')['sales'].sum().idxmax()
    top_cust_name = filtered_df.groupby('customername')['sales'].sum().idxmax()

    st.markdown(f"""
    <div class="chart-card">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
            <div>
                <div style="font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:{EXEC_LABEL_C};margin-bottom:12px;">Business Health</div>
                <ul style="font-size:13px;color:{EXEC_LI_C};line-height:2.4;padding-left:18px;">
                    <li>Revenue is currently <strong style="color:{EXEC_STRONG_C};">{trend_word}</strong> at avg
                        <strong style="color:#6366F1;">{growth:+.2f}%</strong> MoM growth</li>
                    <li>Top market: <strong style="color:{EXEC_STRONG_C};">{top_country}</strong> — leads all geographies</li>
                    <li>Best performing line: <strong style="color:{EXEC_STRONG_C};">{top_product}</strong></li>
                    <li>Key account: <strong style="color:{EXEC_STRONG_C};">{top_cust_name}</strong></li>
                </ul>
            </div>
            <div>
                <div style="font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:{EXEC_LABEL_C};margin-bottom:12px;">Quick Stats</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
                    <div style="background:{EXEC_MINI_BG_1};border:1px solid {EXEC_MINI_BD_1};border-radius:10px;padding:12px;">
                        <div style="font-size:10px;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Countries</div>
                        <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:#A5B4FC;">{len(country_filter)}</div>
                    </div>
                    <div style="background:{EXEC_MINI_BG_2};border:1px solid {EXEC_MINI_BD_2};border-radius:10px;padding:12px;">
                        <div style="font-size:10px;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Products</div>
                        <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:#34D399;">{filtered_df['productline'].nunique()}</div>
                    </div>
                    <div style="background:{EXEC_MINI_BG_3};border:1px solid {EXEC_MINI_BD_3};border-radius:10px;padding:12px;">
                        <div style="font-size:10px;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Customers</div>
                        <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:#FBBF24;">{filtered_df['customername'].nunique()}</div>
                    </div>
                    <div style="background:{EXEC_MINI_BG_4};border:1px solid {EXEC_MINI_BD_4};border-radius:10px;padding:12px;">
                        <div style="font-size:10px;color:{TEXT_MUTED};text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">Orders</div>
                        <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:#F472B6;">{orders:,}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════════
    # SECTION 7 — DATA PREVIEW + EXPORT
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="sec-row"><div class="sec-header">📋 Data Explorer</div></div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="chart-card">
        <div class="chart-title">Filtered Dataset</div>
        <div class="chart-sub">Showing first 50 of {len(filtered_df):,} rows · {len(filtered_df.columns)} columns</div>
    </div>
    """, unsafe_allow_html=True)
    st.dataframe(filtered_df.head(50), width='stretch', hide_index=True)

    col_dl1, col_dl2, _ = st.columns([1, 1, 4], gap="medium")
    with col_dl1:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"nexusbi_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )
    with col_dl2:
        summary_csv = filtered_df.describe().to_csv()
        st.download_button(
            label="📊 Export Summary Stats",
            data=summary_csv,
            file_name=f"nexusbi_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

    # ══════════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown(f"""
    <div style="margin-top:48px;padding:20px 0;border-top:1px solid {FOOTER_BORDER};
        display:flex;align-items:center;justify-content:space-between;">
        <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:700;color:{FOOTER_LOGO_C};">
            Nexus<span style="color:#6366F1;">BI</span>
        </div>
        <div style="font-size:12px;color:{FOOTER_TEXT_C};">
            Business Intelligence Platform · All data is confidential
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════════
    # AUTO-REFRESH TICKER
    # ══════════════════════════════════════════════════════════════════════════════
    if auto_refresh:
        seconds_left = interval_map[refresh_interval] - (datetime.now() - st.session_state['last_refresh']).seconds
        seconds_left = max(0, seconds_left)
        st.markdown(f"""
        <div style="position:fixed;bottom:16px;right:20px;z-index:999;
            background:{BG_SIDEBAR};border:1px solid rgba(99,102,241,0.3);
            border-radius:100px;padding:6px 14px;font-size:11px;
            color:#6366F1;font-family:'DM Mono',monospace;
            box-shadow:0 4px 20px rgba(99,102,241,0.15);">
            🔄 Next refresh in {seconds_left}s
        </div>
        """, unsafe_allow_html=True)
        time.sleep(1)
        st.rerun()
