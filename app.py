import streamlit as st
import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict
import pytz
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ===================== PAGE CONFIG =====================
st.set_page_config(
    page_title="BLUESTAR · Forex Calendar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================== BLOOMBERG DARK TERMINAL CSS =====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

/* ── ROOT VARIABLES ── */
:root {
    --bg-void:     #030507;
    --bg-base:     #080c10;
    --bg-panel:    #0d1117;
    --bg-surface:  #111820;
    --bg-elevated: #161e28;
    --border:      #1e2d3d;
    --border-dim:  #162030;
    --cyan:        #00d4ff;
    --cyan-dim:    #007ea8;
    --cyan-glow:   rgba(0,212,255,0.12);
    --amber:       #f5a623;
    --amber-dim:   #8a5c10;
    --amber-glow:  rgba(245,166,35,0.10);
    --green:       #00e676;
    --green-dim:   #00512a;
    --red:         #ff3b5c;
    --red-dim:     #6b1020;
    --white:       #e8f0f8;
    --muted:       #4a6070;
    --subtle:      #2a3a4a;
    --font-mono:   'IBM Plex Mono', monospace;
    --font-sans:   'IBM Plex Sans', sans-serif;
}

/* ── GLOBAL RESET ── */
html, body, [class*="css"] {
    background-color: var(--bg-base) !important;
    color: var(--white) !important;
    font-family: var(--font-mono) !important;
}

.stApp { background: var(--bg-base) !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb { background: var(--cyan-dim); border-radius: 2px; }

/* ── HEADER TERMINAL ── */
.terminal-header {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-top: 2px solid var(--cyan);
    padding: 20px 28px 16px;
    margin-bottom: 20px;
    font-family: var(--font-mono);
}
.terminal-header .brand {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 4px;
    color: var(--cyan);
    text-transform: uppercase;
}
.terminal-header h1 {
    font-size: 22px !important;
    font-weight: 700 !important;
    color: var(--white) !important;
    margin: 4px 0 6px !important;
    letter-spacing: 1px;
}
.terminal-header .subtitle {
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 1px;
}
.terminal-header .live-dot {
    display: inline-block;
    width: 6px; height: 6px;
    background: var(--green);
    border-radius: 50%;
    margin-right: 6px;
    animation: pulse 1.8s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(0,230,118,0.4); }
    50% { opacity: 0.7; box-shadow: 0 0 0 5px rgba(0,230,118,0); }
}

/* ── KPI STRIP ── */
.kpi-row {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
}
.kpi-card {
    flex: 1;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    padding: 14px 18px;
    font-family: var(--font-mono);
}
.kpi-card.accent-cyan  { border-left: 3px solid var(--cyan); }
.kpi-card.accent-amber { border-left: 3px solid var(--amber); }
.kpi-card.accent-green { border-left: 3px solid var(--green); }
.kpi-card.accent-red   { border-left: 3px solid var(--red); }
.kpi-label {
    font-size: 9px;
    color: var(--muted);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 4px;
}
.kpi-value {
    font-size: 26px;
    font-weight: 700;
    line-height: 1;
}
.kpi-value.cyan  { color: var(--cyan); }
.kpi-value.amber { color: var(--amber); }
.kpi-value.green { color: var(--green); }
.kpi-value.red   { color: var(--red); }

/* ── EVENT TABLE ── */
.events-table {
    width: 100%;
    border-collapse: collapse;
    font-family: var(--font-mono);
    font-size: 12px;
}
.events-table thead tr {
    background: var(--bg-elevated);
    border-bottom: 1px solid var(--cyan-dim);
}
.events-table th {
    padding: 10px 12px;
    text-align: left;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--muted);
}
.events-table tbody tr {
    border-bottom: 1px solid var(--border-dim);
    transition: background 0.15s;
}
.events-table tbody tr:hover {
    background: var(--bg-elevated);
}
.events-table td {
    padding: 10px 12px;
    vertical-align: middle;
}

/* ── PRIORITY BADGES ── */
.badge {
    display: inline-block;
    padding: 2px 8px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}
.badge-critical { background: rgba(255,59,92,0.15); color: var(--red);   border: 1px solid rgba(255,59,92,0.3); }
.badge-high     { background: rgba(245,166,35,0.12); color: var(--amber); border: 1px solid rgba(245,166,35,0.3); }
.badge-medium   { background: rgba(0,212,255,0.08); color: var(--cyan);  border: 1px solid rgba(0,212,255,0.2); }
.badge-past     { background: rgba(74,96,112,0.15); color: var(--muted); border: 1px solid var(--border); }

/* ── SESSION BADGES ── */
.session {
    display: inline-block;
    padding: 1px 6px;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
}
.session-london { background: rgba(0,212,255,0.10); color: var(--cyan);  border: 1px solid rgba(0,212,255,0.2); }
.session-ny     { background: rgba(245,166,35,0.10); color: var(--amber); border: 1px solid rgba(245,166,35,0.2); }
.session-overlap{ background: rgba(0,230,118,0.10); color: var(--green); border: 1px solid rgba(0,230,118,0.25); }
.session-asian  { background: rgba(180,100,255,0.10); color: #b46cff; border: 1px solid rgba(180,100,255,0.2); }
.session-off    { background: transparent; color: var(--muted); border: 1px solid var(--border); }

/* ── CURRENCY TAG ── */
.ccy {
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 1px;
    padding: 2px 6px;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
}
.ccy-USD { color: var(--amber); border-color: var(--amber-dim); }
.ccy-EUR { color: var(--cyan); border-color: var(--cyan-dim); }
.ccy-GBP { color: #7dd3fc; border-color: #1e4060; }
.ccy-JPY { color: #f87171; border-color: #4a1020; }
.ccy-CAD { color: #fb923c; border-color: #4a2010; }
.ccy-AUD { color: #a3e635; border-color: #304a10; }
.ccy-NZD { color: #86efac; border-color: #204030; }
.ccy-CHF { color: #c4b5fd; border-color: #302050; }
.ccy-CNY { color: #fca5a5; border-color: #401010; }

/* ── SECTION HEADER ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0 12px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
    color: var(--muted);
    text-transform: uppercase;
}
.section-header .line {
    flex: 1;
    height: 1px;
    background: var(--border);
}
.section-header .icon { color: var(--cyan); }

/* ── DAY DIVIDER ── */
.day-divider {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-left: 3px solid var(--amber);
    padding: 7px 14px;
    margin: 16px 0 0;
    font-size: 10px;
    font-weight: 700;
    color: var(--amber);
    letter-spacing: 2px;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.day-divider .day-count {
    font-size: 9px;
    color: var(--muted);
    font-weight: 400;
}

/* ── TIME COUNTDOWN ── */
.countdown-positive { color: var(--green); font-size: 11px; }
.countdown-critical { color: var(--red);   font-size: 11px; font-weight: 700; }
.countdown-past     { color: var(--muted); font-size: 11px; }

/* ── FORECAST DELTA ── */
.forecast-value { color: var(--white); font-size: 11px; }
.prev-value     { color: var(--muted); font-size: 10px; }

/* ── PAIRS AFFECTED ── */
.pair-chip {
    display: inline-block;
    font-size: 9px;
    font-weight: 600;
    padding: 1px 5px;
    color: var(--muted);
    border: 1px solid var(--border);
    margin: 1px 2px 1px 0;
    letter-spacing: 0.5px;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: var(--bg-panel) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * {
    font-family: var(--font-mono) !important;
    color: var(--white) !important;
}
.sidebar-section {
    padding: 12px 0;
    border-bottom: 1px solid var(--border-dim);
    margin-bottom: 8px;
}
.sidebar-label {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 2px;
    color: var(--muted);
    text-transform: uppercase;
    margin-bottom: 8px;
}

/* ── DOWNLOAD BUTTON ── */
.stDownloadButton > button {
    background: var(--cyan-glow) !important;
    border: 1px solid var(--cyan) !important;
    color: var(--cyan) !important;
    font-family: var(--font-mono) !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    padding: 10px 20px !important;
    border-radius: 0 !important;
    width: 100% !important;
    transition: all 0.2s !important;
}
.stDownloadButton > button:hover {
    background: rgba(0,212,255,0.20) !important;
    box-shadow: 0 0 16px rgba(0,212,255,0.20) !important;
}

/* ── STREAMLIT OVERRIDES ── */
.stButton > button {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    color: var(--white) !important;
    font-family: var(--font-mono) !important;
    font-size: 11px !important;
    border-radius: 0 !important;
}
.stButton > button:hover {
    border-color: var(--cyan) !important;
    color: var(--cyan) !important;
}
.stSelectbox label, .stMultiSelect label, .stCheckbox label {
    font-size: 10px !important;
    color: var(--muted) !important;
    letter-spacing: 1px !important;
    font-family: var(--font-mono) !important;
}
[data-testid="stMetric"] {
    background: var(--bg-panel) !important;
    border: 1px solid var(--border) !important;
    padding: 12px !important;
}
div[data-testid="stAlert"] {
    background: var(--bg-panel) !important;
    border: 1px solid var(--border) !important;
    border-left: 3px solid var(--cyan) !important;
    border-radius: 0 !important;
    font-family: var(--font-mono) !important;
    font-size: 11px !important;
}
.stExpander {
    border: 1px solid var(--border) !important;
    border-radius: 0 !important;
    background: var(--bg-panel) !important;
}
hr { border-color: var(--border) !important; }
.stCaption { color: var(--muted) !important; font-family: var(--font-mono) !important; font-size: 10px !important; }

/* ── MULTISELECT TAGS ── */
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--cyan-dim) !important;
    border-radius: 0 !important;
}

/* ── SUMMARY BOX ── */
.summary-box {
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-left: 3px solid var(--cyan);
    padding: 16px 18px;
    font-family: var(--font-mono);
    font-size: 11px;
    line-height: 1.7;
    color: var(--white);
}
.summary-box .day-row {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 6px 0;
    border-bottom: 1px solid var(--border-dim);
}
.summary-box .day-row:last-child { border-bottom: none; }
.summary-box .day-label {
    min-width: 80px;
    color: var(--amber);
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 1px;
}
.summary-box .day-events { color: var(--muted); font-size: 10px; }

/* ── PAIRS TABLE ── */
.pairs-affected-cell { line-height: 1.8; }

/* Grid columns fix */
div[data-testid="column"] { padding: 0 8px !important; }
</style>
""", unsafe_allow_html=True)

# ===================== CONFIG =====================
JSON_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE_TTL = 300

PAIRS_MAP = {
    "USD": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CAD", "AUD/USD", "NZD/USD", "USD/CHF"],
    "EUR": ["EUR/USD", "EUR/GBP", "EUR/JPY", "EUR/CHF", "EUR/CAD", "EUR/AUD", "EUR/NZD"],
    "GBP": ["GBP/USD", "EUR/GBP", "GBP/JPY", "GBP/CHF", "GBP/CAD", "GBP/AUD", "GBP/NZD"],
    "JPY": ["USD/JPY", "EUR/JPY", "GBP/JPY", "AUD/JPY", "NZD/JPY", "CAD/JPY", "CHF/JPY"],
    "CAD": ["USD/CAD", "EUR/CAD", "GBP/CAD", "AUD/CAD", "NZD/CAD", "CAD/JPY", "CAD/CHF"],
    "AUD": ["AUD/USD", "EUR/AUD", "GBP/AUD", "AUD/JPY", "AUD/CAD", "AUD/NZD", "AUD/CHF"],
    "NZD": ["NZD/USD", "EUR/NZD", "GBP/NZD", "NZD/JPY", "AUD/NZD", "NZD/CAD", "NZD/CHF"],
    "CHF": ["USD/CHF", "EUR/CHF", "GBP/CHF", "CHF/JPY", "AUD/CHF", "NZD/CHF", "CAD/CHF"],
    "CNY": ["USD/CNY", "EUR/CNY"],
}

def get_session(event_time_utc: datetime) -> str:
    hour = event_time_utc.hour
    # Asian: 00:00-08:59 UTC
    # London: 07:00-15:59 UTC
    # NY: 13:00-21:59 UTC
    # Overlap: 13:00-15:59 UTC
    london = 7 <= hour < 16
    ny = 13 <= hour < 22
    if london and ny:
        return "OVERLAP"
    elif london:
        return "LONDON"
    elif ny:
        return "NEW YORK"
    elif 0 <= hour < 9:
        return "ASIAN"
    else:
        return "OFF"

def format_hours_until(h: float) -> str:
    if h < 0:
        return "PASSED"
    total_min = int(h * 60)
    hh, mm = divmod(total_min, 60)
    if hh == 0:
        return f"{mm}m"
    elif hh < 24:
        return f"{hh}h {mm}m"
    else:
        days = hh // 24
        rem_h = hh % 24
        return f"{days}d {rem_h}h"

@st.cache_data(ttl=CACHE_TTL)
def fetch_raw_calendar() -> List[Dict]:
    try:
        resp = requests.get(JSON_URL, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Calendar fetch failed: {e}")
        return []

def enrich_event(event: Dict, now_utc: datetime) -> Optional[Dict]:
    try:
        raw_date = event.get("date", "")
        event_time = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        if event_time.tzinfo is None:
            event_time = pytz.UTC.localize(event_time)

        time_until = (event_time - now_utc).total_seconds() / 3600
        session = get_session(event_time)
        ccy = event.get("country", "")
        pairs = PAIRS_MAP.get(ccy, [])

        # Priority
        if not (time_until > 0):
            priority = "PAST"
        elif time_until <= 6:
            priority = "CRITICAL"
        elif time_until <= 48:
            priority = "HIGH"
        else:
            priority = "MEDIUM"

        return {
            "currency": ccy,
            "event_name": event.get("title", "").strip(),
            "datetime_utc": event_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date_display": event_time.strftime("%Y-%m-%d"),
            "time_display": event_time.strftime("%H:%M UTC"),
            "day_of_week": event_time.strftime("%A").upper(),
            "impact": (event.get("impact") or "High").lower(),
            "forecast": event.get("forecast", "") or "—",
            "previous": event.get("previous", "") or "—",
            "actual": event.get("actual", "") or "—",
            "hours_until": round(time_until, 2),
            "hours_until_display": format_hours_until(time_until),
            "is_upcoming": time_until > 0,
            "priority": priority,
            "session": session,
            "pairs_affected": pairs,
        }
    except Exception as e:
        logger.warning(f"Skipping event due to parse error: {e} | raw={event}")
        return None

# ===================== DATA LOAD =====================
raw_data = fetch_raw_calendar()
now_utc = datetime.now(pytz.UTC)

if not raw_data:
    st.error("⚠ Failed to fetch Forex Factory calendar. API may be unavailable.")
    st.stop()

all_high_impact = []
for ev in raw_data:
    if ev.get("impact") == "High":
        enriched = enrich_event(ev, now_utc)
        if enriched:
            all_high_impact.append(enriched)

all_high_impact.sort(key=lambda x: (not x["is_upcoming"], x["datetime_utc"]))

# ===================== SIDEBAR FILTERS =====================
with st.sidebar:
    st.markdown('<div class="sidebar-label">⬡ BLUESTAR SYSTEM</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:18px;font-weight:700;color:#00d4ff;margin-bottom:20px;">FOREX CALENDAR</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label" style="margin-top:16px;">CURRENCY FILTER</div>', unsafe_allow_html=True)
    all_currencies = sorted(set(e["currency"] for e in all_high_impact))
    selected_currencies = st.multiselect(
        "Currencies",
        options=all_currencies,
        default=all_currencies,
        label_visibility="collapsed"
    )

    st.markdown('<div class="sidebar-label" style="margin-top:16px;">SESSION FILTER</div>', unsafe_allow_html=True)
    all_sessions = ["LONDON", "NEW YORK", "OVERLAP", "ASIAN", "OFF"]
    selected_sessions = st.multiselect(
        "Sessions",
        options=all_sessions,
        default=all_sessions,
        label_visibility="collapsed"
    )

    st.markdown('<div class="sidebar-label" style="margin-top:16px;">STATUS</div>', unsafe_allow_html=True)
    show_past = st.checkbox("Show past events", value=False)

    st.markdown('<div class="sidebar-label" style="margin-top:16px;">PRIORITY</div>', unsafe_allow_html=True)
    selected_priorities = st.multiselect(
        "Priority",
        options=["CRITICAL", "HIGH", "MEDIUM"],
        default=["CRITICAL", "HIGH", "MEDIUM"],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown('<div class="sidebar-label">LAST REFRESH</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:11px;color:#4a6070;">{now_utc.strftime("%Y-%m-%d %H:%M UTC")}</div>', unsafe_allow_html=True)

# ===================== APPLY FILTERS =====================
filtered = all_high_impact.copy()
if selected_currencies:
    filtered = [e for e in filtered if e["currency"] in selected_currencies]
if selected_sessions:
    filtered = [e for e in filtered if e["session"] in selected_sessions]
if not show_past:
    filtered = [e for e in filtered if e["is_upcoming"]]
filtered = [e for e in filtered if (e["priority"] in selected_priorities or (not e["is_upcoming"] and show_past))]

# ===================== SUMMARY_BY_DAY =====================
daily = defaultdict(list)
for ev in all_high_impact:
    day = ev["datetime_utc"][:10]
    daily[day].append(f"{ev['currency']} – {ev['event_name']}")
summary_by_day = {day: evs for day, evs in sorted(daily.items())}

# ===================== FINAL JSON =====================
final_json = {
    "metadata": {
        "generated_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Forex Factory Official JSON",
        "timezone": "UTC",
        "total_high_impact": len(all_high_impact),
        "upcoming_count": sum(1 for e in all_high_impact if e["is_upcoming"]),
        "critical_count": sum(1 for e in all_high_impact if e["priority"] == "CRITICAL"),
        "filters_applied": {
            "currencies": selected_currencies,
            "sessions": selected_sessions,
            "show_past": show_past,
        }
    },
    "events": filtered,
    "summary_by_day": summary_by_day
}
json_str = json.dumps(final_json, indent=2, ensure_ascii=False)

# ===================== TERMINAL HEADER =====================
st.markdown(f"""
<div class="terminal-header">
    <div class="brand">BLUESTAR SYSTEM · MODULE 04</div>
    <h1>FOREX FACTORY — HIGH IMPACT CALENDAR</h1>
    <div class="subtitle">
        <span class="live-dot"></span>
        LIVE FEED · SOURCE: FOREX FACTORY OFFICIAL JSON · REFRESHES EVERY 5 MIN · {now_utc.strftime("%A %d %B %Y — %H:%M UTC")}
    </div>
</div>
""", unsafe_allow_html=True)

# ===================== KPI STRIP =====================
upcoming = sum(1 for e in all_high_impact if e["is_upcoming"])
critical = sum(1 for e in all_high_impact if e["priority"] == "CRITICAL")
high = sum(1 for e in all_high_impact if e["priority"] == "HIGH")
total = len(all_high_impact)

st.markdown(f"""
<div class="kpi-row">
    <div class="kpi-card accent-cyan">
        <div class="kpi-label">Total Events</div>
        <div class="kpi-value cyan">{total}</div>
    </div>
    <div class="kpi-card accent-green">
        <div class="kpi-label">Upcoming</div>
        <div class="kpi-value green">{upcoming}</div>
    </div>
    <div class="kpi-card accent-red">
        <div class="kpi-label">Critical ≤6h</div>
        <div class="kpi-value red">{critical}</div>
    </div>
    <div class="kpi-card accent-amber">
        <div class="kpi-label">High ≤48h</div>
        <div class="kpi-value amber">{high}</div>
    </div>
    <div class="kpi-card accent-cyan">
        <div class="kpi-label">Filtered View</div>
        <div class="kpi-value cyan">{len(filtered)}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ===================== COLUMNS: TABLE + EXPORT =====================
col_main, col_side = st.columns([4, 1])

with col_side:
    st.markdown('<div class="sidebar-label" style="margin-bottom:10px;">EXPORT</div>', unsafe_allow_html=True)
    st.download_button(
        label="📥 DOWNLOAD calendar.json",
        data=json_str,
        file_name="calendar.json",
        mime="application/json",
        use_container_width=True
    )
    st.markdown(f'<div style="font-size:9px;color:#4a6070;margin-top:6px;letter-spacing:1px;">{len(filtered)} events · {len(json_str)//1024}KB</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label" style="margin-top:20px;margin-bottom:10px;">WEEKLY SUMMARY</div>', unsafe_allow_html=True)
    summary_html = '<div class="summary-box">'
    for day, evs in summary_by_day.items():
        dt = datetime.fromisoformat(day)
        day_label = dt.strftime("%a %d").upper()
        evs_text = " · ".join(evs[:3])
        if len(evs) > 3:
            evs_text += f" +{len(evs)-3}"
        summary_html += f"""
        <div class="day-row">
            <div class="day-label">{day_label}</div>
            <div class="day-events">{evs_text}</div>
        </div>"""
    summary_html += '</div>'
    st.markdown(summary_html, unsafe_allow_html=True)

with col_main:
    # Group by day
    days_grouped = defaultdict(list)
    for ev in filtered:
        days_grouped[ev["date_display"]].append(ev)

    if not filtered:
        st.markdown('<div style="text-align:center;padding:60px;color:#4a6070;font-size:13px;letter-spacing:2px;">NO EVENTS MATCH CURRENT FILTERS</div>', unsafe_allow_html=True)
    else:
        for day_key in sorted(days_grouped.keys(), key=lambda d: (days_grouped[d][0]["is_upcoming"] == False, d)):
            day_evs = days_grouped[day_key]
            dt = datetime.fromisoformat(day_key)
            day_label = dt.strftime("%A, %B %d %Y").upper()
            upcoming_ct = sum(1 for e in day_evs if e["is_upcoming"])

            st.markdown(f"""
            <div class="day-divider">
                <span>📅 &nbsp;{day_label}</span>
                <span class="day-count">{len(day_evs)} events · {upcoming_ct} upcoming</span>
            </div>
            """, unsafe_allow_html=True)

            # Build table
            rows_html = ""
            for ev in day_evs:
                # Priority badge
                p = ev["priority"]
                p_class = {"CRITICAL":"badge-critical","HIGH":"badge-high","MEDIUM":"badge-medium","PAST":"badge-past"}.get(p,"badge-past")
                badge = f'<span class="badge {p_class}">{p}</span>'

                # Session badge
                s = ev["session"]
                s_class = {"LONDON":"session-london","NEW YORK":"session-ny","OVERLAP":"session-overlap","ASIAN":"session-asian"}.get(s,"session-off")
                session_badge = f'<span class="session {s_class}">{s}</span>'

                # Currency tag
                ccy = ev["currency"]
                ccy_class = f"ccy-{ccy}" if f"ccy-{ccy}" in ["ccy-USD","ccy-EUR","ccy-GBP","ccy-JPY","ccy-CAD","ccy-AUD","ccy-NZD","ccy-CHF","ccy-CNY"] else ""
                ccy_tag = f'<span class="ccy {ccy_class}">{ccy}</span>'

                # Countdown
                if ev["is_upcoming"]:
                    ct_class = "countdown-critical" if p == "CRITICAL" else "countdown-positive"
                    countdown = f'<span class="{ct_class}">T−{ev["hours_until_display"]}</span>'
                else:
                    countdown = '<span class="countdown-past">PAST</span>'

                # Pairs
                pairs_html = "".join(f'<span class="pair-chip">{pair}</span>' for pair in ev["pairs_affected"][:4])

                rows_html += f"""
                <tr>
                    <td>{ev["time_display"]}<br>{countdown}</td>
                    <td>{ccy_tag}</td>
                    <td style="max-width:220px;">{ev["event_name"]}</td>
                    <td>{badge}</td>
                    <td>{session_badge}</td>
                    <td>
                        <span class="forecast-value">{ev["forecast"]}</span><br>
                        <span class="prev-value">prev {ev["previous"]}</span>
                    </td>
                    <td class="pairs-affected-cell">{pairs_html}</td>
                </tr>"""

            st.markdown(f"""
            <table class="events-table">
                <thead>
                    <tr>
                        <th>TIME / T−</th>
                        <th>CCY</th>
                        <th>EVENT</th>
                        <th>PRIORITY</th>
                        <th>SESSION</th>
                        <th>FCST / PREV</th>
                        <th>PAIRS AFFECTED</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
            """, unsafe_allow_html=True)

# ===================== JSON EXPANDER =====================
with st.expander("🔍 VIEW FULL JSON PAYLOAD — LLM READY"):
    st.code(json_str, language="json")

st.markdown('<div style="text-align:center;padding:20px 0 8px;font-size:9px;letter-spacing:2px;color:#2a3a4a;">BLUESTAR SYSTEM · FOREX CALENDAR MODULE · HIGH IMPACT ONLY · DATA: FOREX FACTORY</div>', unsafe_allow_html=True)
