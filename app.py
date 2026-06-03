import streamlit as st
import requests
import json
from datetime import datetime
from collections import defaultdict
import pytz
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="BLUESTAR · Forex Calendar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');
:root {
    --bg-base:#080c10; --bg-panel:#0d1117; --bg-surface:#111820; --bg-elevated:#161e28;
    --border:#1e2d3d; --border-dim:#162030;
    --cyan:#00d4ff; --cyan-dim:#007ea8; --cyan-glow:rgba(0,212,255,0.12);
    --amber:#f5a623; --amber-dim:#8a5c10;
    --green:#00e676; --red:#ff3b5c;
    --white:#e8f0f8; --muted:#4a6070;
    --font-mono:'IBM Plex Mono',monospace; --font-sans:'IBM Plex Sans',sans-serif;
}
html,body,[class*="css"]{background-color:var(--bg-base)!important;color:var(--white)!important;font-family:var(--font-mono)!important;}
.stApp{background:var(--bg-base)!important;}
::-webkit-scrollbar{width:4px;height:4px;} ::-webkit-scrollbar-track{background:var(--bg-base);} ::-webkit-scrollbar-thumb{background:var(--cyan-dim);}

.terminal-header{background:var(--bg-panel);border:1px solid var(--border);border-top:2px solid var(--cyan);padding:20px 28px 16px;margin-bottom:20px;}
.terminal-header .brand{font-size:11px;font-weight:600;letter-spacing:4px;color:var(--cyan);text-transform:uppercase;}
.terminal-header h1{font-size:22px!important;font-weight:700!important;color:var(--white)!important;margin:4px 0 6px!important;letter-spacing:1px;}
.terminal-header .subtitle{font-size:11px;color:var(--muted);letter-spacing:1px;}
.live-dot{display:inline-block;width:6px;height:6px;background:var(--green);border-radius:50%;margin-right:6px;animation:pulse 1.8s infinite;}
@keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 rgba(0,230,118,.4);}50%{opacity:.7;box-shadow:0 0 0 5px rgba(0,230,118,0);}}

.kpi-row{display:flex;gap:12px;margin-bottom:20px;}
.kpi-card{flex:1;background:var(--bg-panel);border:1px solid var(--border);padding:14px 18px;}
.kpi-card.accent-cyan{border-left:3px solid var(--cyan);} .kpi-card.accent-amber{border-left:3px solid var(--amber);} .kpi-card.accent-green{border-left:3px solid var(--green);} .kpi-card.accent-red{border-left:3px solid var(--red);}
.kpi-label{font-size:9px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin-bottom:4px;}
.kpi-value{font-size:26px;font-weight:700;line-height:1;}
.kpi-value.cyan{color:var(--cyan);} .kpi-value.amber{color:var(--amber);} .kpi-value.green{color:var(--green);} .kpi-value.red{color:var(--red);}

.day-divider{background:var(--bg-elevated);border:1px solid var(--border);border-left:3px solid var(--amber);padding:7px 14px;margin:16px 0 4px;font-size:10px;font-weight:700;color:var(--amber);letter-spacing:2px;text-transform:uppercase;display:flex;align-items:center;justify-content:space-between;}
.day-count{font-size:9px;color:var(--muted);font-weight:400;}

.summary-box{background:var(--bg-panel);border:1px solid var(--border);border-left:3px solid var(--cyan);padding:14px 16px;font-size:11px;line-height:1.7;}
.summary-box .day-row{display:flex;gap:12px;padding:5px 0;border-bottom:1px solid var(--border-dim);}
.summary-box .day-row:last-child{border-bottom:none;}
.summary-box .day-label{min-width:60px;color:var(--amber);font-weight:700;font-size:10px;letter-spacing:1px;flex-shrink:0;}
.summary-box .day-events{color:var(--muted);font-size:10px;}

.sidebar-label{font-size:9px;font-weight:600;letter-spacing:2px;color:var(--muted);text-transform:uppercase;margin-bottom:8px;}
[data-testid="stSidebar"]{background:var(--bg-panel)!important;border-right:1px solid var(--border)!important;}
[data-testid="stSidebar"] *{font-family:var(--font-mono)!important;color:var(--white)!important;}

.stDownloadButton>button{background:var(--cyan-glow)!important;border:1px solid var(--cyan)!important;color:var(--cyan)!important;font-family:var(--font-mono)!important;font-size:11px!important;font-weight:600!important;letter-spacing:1.5px!important;text-transform:uppercase!important;padding:10px 20px!important;border-radius:0!important;width:100%!important;}
.stDownloadButton>button:hover{background:rgba(0,212,255,.20)!important;box-shadow:0 0 16px rgba(0,212,255,.20)!important;}
.stButton>button{background:var(--bg-elevated)!important;border:1px solid var(--border)!important;color:var(--white)!important;font-family:var(--font-mono)!important;font-size:11px!important;border-radius:0!important;}
.stSelectbox label,.stMultiSelect label,.stCheckbox label{font-size:10px!important;color:var(--muted)!important;letter-spacing:1px!important;font-family:var(--font-mono)!important;}
.stExpander{border:1px solid var(--border)!important;border-radius:0!important;background:var(--bg-panel)!important;}
.stCaption{color:var(--muted)!important;font-family:var(--font-mono)!important;font-size:10px!important;}
[data-testid="stMultiSelect"] [data-baseweb="tag"]{background:var(--bg-elevated)!important;border:1px solid var(--cyan-dim)!important;border-radius:0!important;}
div[data-testid="column"]{padding:0 8px!important;}
</style>
""", unsafe_allow_html=True)

# ── CONFIG ──
JSON_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE_TTL = 300

PAIRS_MAP = {
    "USD": ["EUR/USD","GBP/USD","USD/JPY","USD/CAD","AUD/USD","NZD/USD","USD/CHF"],
    "EUR": ["EUR/USD","EUR/GBP","EUR/JPY","EUR/CHF","EUR/CAD","EUR/AUD","EUR/NZD"],
    "GBP": ["GBP/USD","EUR/GBP","GBP/JPY","GBP/CHF","GBP/CAD","GBP/AUD","GBP/NZD"],
    "JPY": ["USD/JPY","EUR/JPY","GBP/JPY","AUD/JPY","NZD/JPY","CAD/JPY","CHF/JPY"],
    "CAD": ["USD/CAD","EUR/CAD","GBP/CAD","AUD/CAD","NZD/CAD","CAD/JPY","CAD/CHF"],
    "AUD": ["AUD/USD","EUR/AUD","GBP/AUD","AUD/JPY","AUD/CAD","AUD/NZD","AUD/CHF"],
    "NZD": ["NZD/USD","EUR/NZD","GBP/NZD","NZD/JPY","AUD/NZD","NZD/CAD","NZD/CHF"],
    "CHF": ["USD/CHF","EUR/CHF","GBP/CHF","CHF/JPY","AUD/CHF","NZD/CHF","CAD/CHF"],
    "CNY": ["USD/CNY","EUR/CNY"],
}

CCY_COLORS = {
    "USD":"#f5a623","EUR":"#00d4ff","GBP":"#7dd3fc",
    "JPY":"#f87171","CAD":"#fb923c","AUD":"#a3e635",
    "NZD":"#86efac","CHF":"#c4b5fd","CNY":"#fca5a5",
}

def get_session(t: datetime) -> str:
    h = t.hour
    london = 7 <= h < 16
    ny = 13 <= h < 22
    if london and ny: return "OVERLAP"
    if london:        return "LONDON"
    if ny:            return "NEW YORK"
    if 0 <= h < 9:   return "ASIAN"
    return "OFF"

def fmt_until(h: float) -> str:
    if h < 0: return "PASSED"
    total_min = int(h * 60)
    hh, mm = divmod(total_min, 60)
    if hh == 0:        return f"{mm}m"
    if hh < 24:        return f"{hh}h {mm}m"
    return f"{hh//24}d {hh%24}h"

@st.cache_data(ttl=CACHE_TTL)
def fetch_raw() -> List[Dict]:
    try:
        r = requests.get(JSON_URL, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        return []

def enrich(event: Dict, now_utc: datetime) -> Optional[Dict]:
    try:
        t = datetime.fromisoformat(event.get("date","").replace("Z","+00:00"))
        if t.tzinfo is None: t = pytz.UTC.localize(t)
        h = (t - now_utc).total_seconds() / 3600
        ccy = event.get("country","")
        priority = "PAST" if h <= 0 else ("CRITICAL" if h <= 6 else ("HIGH" if h <= 48 else "MEDIUM"))
        return {
            "currency": ccy,
            "event_name": event.get("title","").strip(),
            "datetime_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date_display": t.strftime("%Y-%m-%d"),
            "time_display": t.strftime("%H:%M UTC"),
            "day_of_week": t.strftime("%A").upper(),
            "impact": (event.get("impact") or "High").lower(),
            "forecast": event.get("forecast","") or "—",
            "previous": event.get("previous","") or "—",
            "actual": event.get("actual","") or "—",
            "hours_until": round(h, 2),
            "hours_until_display": fmt_until(h),
            "is_upcoming": h > 0,
            "priority": priority,
            "session": get_session(t),
            "pairs_affected": PAIRS_MAP.get(ccy, []),
        }
    except Exception as e:
        logger.warning(f"Skip event: {e}")
        return None

# ── DATA ──
raw_data = fetch_raw()
now_utc  = datetime.now(pytz.UTC)

if not raw_data:
    st.error("⚠ Failed to fetch Forex Factory calendar.")
    st.stop()

all_events = [e for ev in raw_data if ev.get("impact") == "High" for e in [enrich(ev, now_utc)] if e]
all_events.sort(key=lambda x: (not x["is_upcoming"], x["datetime_utc"]))

# ── SIDEBAR ──
with st.sidebar:
    st.markdown('<div class="sidebar-label">⬡ BLUESTAR SYSTEM</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:18px;font-weight:700;color:#00d4ff;margin-bottom:20px;">FOREX CALENDAR</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label" style="margin-top:16px;">CURRENCY FILTER</div>', unsafe_allow_html=True)
    all_ccy = sorted(set(e["currency"] for e in all_events))
    sel_ccy = st.multiselect("Currencies", all_ccy, default=all_ccy, label_visibility="collapsed")

    st.markdown('<div class="sidebar-label" style="margin-top:16px;">SESSION FILTER</div>', unsafe_allow_html=True)
    sel_sess = st.multiselect("Sessions", ["LONDON","NEW YORK","OVERLAP","ASIAN","OFF"],
                              default=["LONDON","NEW YORK","OVERLAP","ASIAN","OFF"], label_visibility="collapsed")

    st.markdown('<div class="sidebar-label" style="margin-top:16px;">STATUS</div>', unsafe_allow_html=True)
    show_past = st.checkbox("Show past events", value=False)

    st.markdown('<div class="sidebar-label" style="margin-top:16px;">PRIORITY</div>', unsafe_allow_html=True)
    sel_prio = st.multiselect("Priority", ["CRITICAL","HIGH","MEDIUM"],
                              default=["CRITICAL","HIGH","MEDIUM"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<div class="sidebar-label">LAST REFRESH</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:11px;color:#4a6070;">{now_utc.strftime("%Y-%m-%d %H:%M UTC")}</div>', unsafe_allow_html=True)

# ── FILTERS ──
filtered = all_events.copy()
if sel_ccy:   filtered = [e for e in filtered if e["currency"] in sel_ccy]
if sel_sess:  filtered = [e for e in filtered if e["session"] in sel_sess]
if not show_past: filtered = [e for e in filtered if e["is_upcoming"]]
filtered = [e for e in filtered if e["priority"] in sel_prio or (not e["is_upcoming"] and show_past)]

# ── SUMMARY BY DAY ──
daily = defaultdict(list)
for ev in all_events:
    daily[ev["datetime_utc"][:10]].append(f"{ev['currency']} – {ev['event_name']}")
summary_by_day = {d: evs for d, evs in sorted(daily.items())}

# ── FINAL JSON ──
final_json = {
    "metadata": {
        "generated_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "Forex Factory Official JSON",
        "timezone": "UTC",
        "total_high_impact": len(all_events),
        "upcoming_count": sum(1 for e in all_events if e["is_upcoming"]),
        "critical_count": sum(1 for e in all_events if e["priority"] == "CRITICAL"),
        "filters_applied": {"currencies": sel_ccy, "sessions": sel_sess, "show_past": show_past},
    },
    "events": filtered,
    "summary_by_day": summary_by_day,
}
json_str = json.dumps(final_json, indent=2, ensure_ascii=False)

# ── HEADER ──
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

# ── KPIs ──
total    = len(all_events)
upcoming = sum(1 for e in all_events if e["is_upcoming"])
critical = sum(1 for e in all_events if e["priority"] == "CRITICAL")
high     = sum(1 for e in all_events if e["priority"] == "HIGH")

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card accent-cyan"><div class="kpi-label">Total Events</div><div class="kpi-value cyan">{total}</div></div>
  <div class="kpi-card accent-green"><div class="kpi-label">Upcoming</div><div class="kpi-value green">{upcoming}</div></div>
  <div class="kpi-card accent-red"><div class="kpi-label">Critical ≤6h</div><div class="kpi-value red">{critical}</div></div>
  <div class="kpi-card accent-amber"><div class="kpi-label">High ≤48h</div><div class="kpi-value amber">{high}</div></div>
  <div class="kpi-card accent-cyan"><div class="kpi-label">Filtered View</div><div class="kpi-value cyan">{len(filtered)}</div></div>
</div>
""", unsafe_allow_html=True)

# ── LAYOUT ──
col_main, col_side = st.columns([4, 1])

# ── EXPORT COLUMN ──
with col_side:
    st.markdown('<div class="sidebar-label" style="margin-bottom:10px;">EXPORT</div>', unsafe_allow_html=True)
    st.download_button(
        label="📥 DOWNLOAD calendar.json",
        data=json_str,
        file_name="calendar.json",
        mime="application/json",
        use_container_width=True,
    )
    st.markdown(f'<div style="font-size:9px;color:#4a6070;margin-top:6px;letter-spacing:1px;">{len(filtered)} events · {len(json_str)//1024}KB</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-label" style="margin-top:20px;margin-bottom:10px;">WEEKLY SUMMARY</div>', unsafe_allow_html=True)
    summary_html = '<div class="summary-box">'
    for day, evs in summary_by_day.items():
        dt = datetime.fromisoformat(day)
        lbl = dt.strftime("%a %d").upper()
        txt = " · ".join(evs[:3]) + (f" +{len(evs)-3}" if len(evs) > 3 else "")
        summary_html += f'<div class="day-row"><div class="day-label">{lbl}</div><div class="day-events">{txt}</div></div>'
    summary_html += '</div>'
    st.markdown(summary_html, unsafe_allow_html=True)

# ── EVENTS COLUMN ──
with col_main:

    days_grouped = defaultdict(list)
    for ev in filtered:
        days_grouped[ev["date_display"]].append(ev)

    if not filtered:
        st.markdown('<div style="text-align:center;padding:60px;color:#4a6070;font-size:13px;letter-spacing:2px;">NO EVENTS MATCH CURRENT FILTERS</div>', unsafe_allow_html=True)
    else:
        for day_key in sorted(days_grouped.keys(), key=lambda d: (not days_grouped[d][0]["is_upcoming"], d)):
            day_evs = days_grouped[day_key]
            dt = datetime.fromisoformat(day_key)
            day_label = dt.strftime("%A, %B %d %Y").upper()
            upcoming_ct = sum(1 for e in day_evs if e["is_upcoming"])

            # Day header
            st.markdown(f"""
            <div class="day-divider">
              <span>📅 &nbsp;{day_label}</span>
              <span class="day-count">{len(day_evs)} event(s) · {upcoming_ct} upcoming</span>
            </div>""", unsafe_allow_html=True)

            # ── One card per event ──
            for ev in day_evs:
                p   = ev["priority"]
                s   = ev["session"]
                ccy = ev["currency"]

                # Priority colors
                p_cfg = {
                    "CRITICAL": ("#ff3b5c", "rgba(255,59,92,0.13)",  "1px solid rgba(255,59,92,0.35)"),
                    "HIGH":     ("#f5a623", "rgba(245,166,35,0.10)", "1px solid rgba(245,166,35,0.30)"),
                    "MEDIUM":   ("#00d4ff", "rgba(0,212,255,0.07)",  "1px solid rgba(0,212,255,0.20)"),
                    "PAST":     ("#4a6070", "rgba(74,96,112,0.08)",  "1px solid #1e2d3d"),
                }
                p_color, p_bg, p_border = p_cfg.get(p, p_cfg["MEDIUM"])

                # Session colors
                s_cfg = {
                    "LONDON":   ("#00d4ff", "rgba(0,212,255,0.10)",   "1px solid rgba(0,212,255,0.25)"),
                    "NEW YORK": ("#f5a623", "rgba(245,166,35,0.10)",  "1px solid rgba(245,166,35,0.25)"),
                    "OVERLAP":  ("#00e676", "rgba(0,230,118,0.10)",   "1px solid rgba(0,230,118,0.25)"),
                    "ASIAN":    ("#b46cff", "rgba(180,108,255,0.10)", "1px solid rgba(180,108,255,0.25)"),
                    "OFF":      ("#4a6070", "transparent",             "1px solid #1e2d3d"),
                }
                s_color, s_bg, s_border = s_cfg.get(s, s_cfg["OFF"])

                ccy_color = CCY_COLORS.get(ccy, "#e8f0f8")
                cd_color  = "#ff3b5c" if p == "CRITICAL" else ("#00e676" if ev["is_upcoming"] else "#4a6070")
                cd_label  = f"T − {ev['hours_until_display']}" if ev["is_upcoming"] else "PASSED"

                # Pairs chips
                pairs_html = "".join(
                    f'<span style="display:inline-block;font-size:9px;font-weight:600;'
                    f'padding:1px 6px;color:#4a6070;border:1px solid #1e2d3d;margin:2px 3px 2px 0;">'
                    f'{pair}</span>'
                    for pair in ev["pairs_affected"][:4]
                )

                # Actual field (only if published)
                actual_html = ""
                if ev["actual"] != "—":
                    actual_html = (
                        f'&nbsp;&nbsp;<span style="color:#4a6070;font-size:9px;letter-spacing:1px;">ACT&nbsp;</span>'
                        f'<span style="color:#00e676;font-weight:700;">{ev["actual"]}</span>'
                    )

                st.markdown(f"""
<div style="background:#0d1117;border:1px solid #1e2d3d;border-left:3px solid {p_color};
            margin:5px 0;padding:14px 18px;font-family:'IBM Plex Mono',monospace;">

  <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-bottom:10px;">

    <div style="min-width:95px;flex-shrink:0;">
      <div style="font-size:16px;font-weight:700;color:#e8f0f8;letter-spacing:1px;">{ev['time_display']}</div>
      <div style="font-size:11px;color:{cd_color};font-weight:600;margin-top:3px;">{cd_label}</div>
    </div>

    <div style="font-size:13px;font-weight:700;letter-spacing:2px;padding:4px 10px;
                color:{ccy_color};background:#111820;border:1px solid #1e2d3d;flex-shrink:0;">
      {ccy}
    </div>

    <div style="flex:1;font-size:14px;font-weight:600;color:#e8f0f8;letter-spacing:0.3px;min-width:160px;">
      {ev['event_name']}
    </div>

  </div>

  <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">

    <span style="font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
                 padding:3px 9px;color:{p_color};background:{p_bg};border:{p_border};">{p}</span>

    <span style="font-size:9px;font-weight:600;letter-spacing:1px;
                 padding:3px 8px;color:{s_color};background:{s_bg};border:{s_border};">{s}</span>

    <div style="width:1px;height:16px;background:#1e2d3d;flex-shrink:0;"></div>

    <div style="font-size:11px;color:#e8f0f8;">
      <span style="color:#4a6070;font-size:9px;letter-spacing:1px;">FCST&nbsp;</span>{ev['forecast']}
      &nbsp;&nbsp;
      <span style="color:#4a6070;font-size:9px;letter-spacing:1px;">PREV&nbsp;</span><span style="color:#4a6070;">{ev['previous']}</span>
      {actual_html}
    </div>

    <div style="width:1px;height:16px;background:#1e2d3d;flex-shrink:0;"></div>

    <div>{pairs_html}</div>

  </div>
</div>""", unsafe_allow_html=True)

# ── JSON VIEWER ──
with st.expander("🔍 VIEW FULL JSON PAYLOAD — LLM READY"):
    st.code(json_str, language="json")

st.markdown(
    '<div style="text-align:center;padding:20px 0 8px;font-size:9px;letter-spacing:2px;color:#2a3a4a;">'
    'BLUESTAR SYSTEM · FOREX CALENDAR MODULE · HIGH IMPACT ONLY · DATA: FOREX FACTORY</div>',
    unsafe_allow_html=True
)
