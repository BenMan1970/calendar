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

# Only safe global CSS — no complex inline injection
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    background-color: #080c10 !important;
    color: #e8f0f8 !important;
    font-family: 'IBM Plex Mono', monospace !important;
}
.stApp { background: #080c10 !important; }

[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid #1e2d3d !important;
}
[data-testid="stSidebar"] * { font-family: 'IBM Plex Mono', monospace !important; }

.stMultiSelect label, .stCheckbox label, .stSelectbox label {
    font-size: 10px !important; color: #4a6070 !important;
    letter-spacing: 1px !important; text-transform: uppercase !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background: #161e28 !important;
    border: 1px solid #007ea8 !important;
    border-radius: 0 !important;
}
.stDownloadButton > button {
    background: rgba(0,212,255,0.10) !important;
    border: 1px solid #00d4ff !important;
    color: #00d4ff !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 11px !important; font-weight: 600 !important;
    letter-spacing: 1.5px !important; text-transform: uppercase !important;
    border-radius: 0 !important; width: 100% !important;
}
.stExpander { border: 1px solid #1e2d3d !important; border-radius: 0 !important; }
div[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 28px !important; font-weight: 700 !important;
}
div[data-testid="stMetricLabel"] {
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 9px !important; letter-spacing: 2px !important;
    text-transform: uppercase !important; color: #4a6070 !important;
}
hr { border-color: #1e2d3d !important; }
::-webkit-scrollbar { width: 4px; } 
::-webkit-scrollbar-thumb { background: #007ea8; }
</style>
""", unsafe_allow_html=True)

# ── CONFIG ──
JSON_URL  = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
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

CCY_EMOJI = {
    "USD":"🇺🇸","EUR":"🇪🇺","GBP":"🇬🇧","JPY":"🇯🇵",
    "CAD":"🇨🇦","AUD":"🇦🇺","NZD":"🇳🇿","CHF":"🇨🇭","CNY":"🇨🇳",
}

SESSION_EMOJI = {
    "LONDON":"🇬🇧","NEW YORK":"🗽","OVERLAP":"⚡","ASIAN":"🌏","OFF":"💤",
}

PRIORITY_ICON = {"CRITICAL":"🔴","HIGH":"🟡","MEDIUM":"🔵","PAST":"⚫"}

def get_session(t: datetime) -> str:
    h = t.hour
    london, ny = 7 <= h < 16, 13 <= h < 22
    if london and ny: return "OVERLAP"
    if london:        return "LONDON"
    if ny:            return "NEW YORK"
    if 0 <= h < 9:   return "ASIAN"
    return "OFF"

def fmt_until(h: float) -> str:
    # FIX #3: h == 0.0 (event exactement maintenant) doit aussi retourner "PASSED"
    # pour rester cohérent avec is_upcoming qui utilise h > 0
    if h <= 0: return "PASSED"
    total_min = int(h * 60)
    hh, mm = divmod(total_min, 60)
    if hh == 0:    return f"{mm}m"
    if hh < 24:    return f"{hh}h {mm}m"
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
        if t.tzinfo is None:
            t = pytz.UTC.localize(t)
        h    = (t - now_utc).total_seconds() / 3600
        ccy  = event.get("country","")
        prio = ("PAST"     if h <= 0 else
                "CRITICAL" if h <= 6 else
                "HIGH"     if h <= 48 else "MEDIUM")
        return {
            "currency":          ccy,
            "event_name":        event.get("title","").strip(),
            "datetime_utc":      t.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date_display":      t.strftime("%Y-%m-%d"),
            "time_display":      t.strftime("%H:%M UTC"),
            "day_of_week":       t.strftime("%A").upper(),
            "impact":            (event.get("impact") or "High").lower(),
            "forecast":          event.get("forecast","") or "—",
            "previous":          event.get("previous","") or "—",
            "actual":            event.get("actual","") or "—",
            "hours_until":       round(h, 2),
            "hours_until_display": fmt_until(h),
            "is_upcoming":       h > 0,
            "priority":          prio,
            "session":           get_session(t),
            "pairs_affected":    PAIRS_MAP.get(ccy, []),
        }
    except Exception as e:
        logger.warning(f"Skip: {e}")
        return None

# ── DATA ──
raw_data = fetch_raw()
now_utc  = datetime.now(pytz.UTC)

if not raw_data:
    st.error("⚠ Cannot reach Forex Factory API.")
    st.stop()

all_events = [e for ev in raw_data
              if ev.get("impact") == "High"
              for e in [enrich(ev, now_utc)] if e]
all_events.sort(key=lambda x: (not x["is_upcoming"], x["datetime_utc"]))

# ── SIDEBAR ──
with st.sidebar:
    st.caption("⬡ BLUESTAR SYSTEM")
    st.markdown("### FOREX CALENDAR")
    st.divider()

    st.caption("CURRENCY FILTER")
    all_ccy = sorted(set(e["currency"] for e in all_events))
    sel_ccy = st.multiselect("Currencies", all_ccy, default=all_ccy,
                             label_visibility="collapsed")

    st.caption("SESSION FILTER")
    all_sess = ["LONDON","NEW YORK","OVERLAP","ASIAN","OFF"]
    sel_sess = st.multiselect("Sessions", all_sess, default=all_sess,
                              label_visibility="collapsed")

    st.caption("STATUS")
    show_past = st.checkbox("Show past events", value=False)

    st.caption("PRIORITY")
    # FIX #1: "PAST" est maintenant une option explicite dans le filtre priorité,
    # cohérent avec la valeur assignée dans enrich(). Par défaut désélectionné
    # pour ne pas afficher les passés quand show_past=False.
    sel_prio = st.multiselect("Priority", ["CRITICAL","HIGH","MEDIUM","PAST"],
                              default=["CRITICAL","HIGH","MEDIUM"],
                              label_visibility="collapsed")
    st.divider()
    st.caption(f"LAST REFRESH\n{now_utc.strftime('%Y-%m-%d %H:%M UTC')}")

# ── FILTERS ──
filtered = all_events.copy()
if sel_ccy:  filtered = [e for e in filtered if e["currency"] in sel_ccy]
if sel_sess: filtered = [e for e in filtered if e["session"] in sel_sess]
# FIX #1 (suite): Le filtre show_past contrôle la visibilité des passés, et
# sel_prio s'applique uniformément à tous les événements sans exception.
# On garde show_past comme garde-fou indépendant pour l'UX.
if not show_past:
    filtered = [e for e in filtered if e["is_upcoming"]]
filtered = [e for e in filtered if e["priority"] in sel_prio]

# ── SUMMARY BY DAY ──
daily = defaultdict(list)
for ev in all_events:
    daily[ev["datetime_utc"][:10]].append(f"{ev['currency']} – {ev['event_name']}")
summary_by_day = {d: evs for d, evs in sorted(daily.items())}

# ── FINAL JSON ──
final_json = {
    "metadata": {
        "generated_at_utc":  now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source":            "Forex Factory Official JSON",
        "timezone":          "UTC",
        "total_high_impact": len(all_events),
        "upcoming_count":    sum(1 for e in all_events if e["is_upcoming"]),
        "critical_count":    sum(1 for e in all_events if e["priority"] == "CRITICAL"),
        "filters_applied":   {"currencies": sel_ccy, "sessions": sel_sess,
                              "show_past": show_past},
    },
    "events":         filtered,
    "summary_by_day": summary_by_day,
}
json_str = json.dumps(final_json, indent=2, ensure_ascii=False)

# ══════════════════════════════════════════════
# HEADER — safe single-block html
# ══════════════════════════════════════════════
st.markdown(
    f"<div style='background:#0d1117;border-top:2px solid #00d4ff;"
    f"border:1px solid #1e2d3d;padding:18px 24px 14px;margin-bottom:16px;'>"
    f"<div style='font-size:10px;font-weight:600;letter-spacing:4px;color:#00d4ff;'>BLUESTAR SYSTEM · MODULE 04</div>"
    f"<div style='font-size:20px;font-weight:700;color:#e8f0f8;margin:4px 0 5px;'>FOREX FACTORY — HIGH IMPACT CALENDAR</div>"
    f"<div style='font-size:10px;color:#4a6070;'>● LIVE FEED · FOREX FACTORY JSON · AUTO-REFRESH 5 MIN"
    f" · {now_utc.strftime('%A %d %B %Y — %H:%M UTC')}</div>"
    f"</div>",
    unsafe_allow_html=True
)

# ── KPIs via native st.metric ──
total    = len(all_events)
upcoming = sum(1 for e in all_events if e["is_upcoming"])
critical = sum(1 for e in all_events if e["priority"] == "CRITICAL")
high_ct  = sum(1 for e in all_events if e["priority"] == "HIGH")

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("📊 TOTAL EVENTS",   total)
k2.metric("🟢 UPCOMING",       upcoming)
k3.metric("🔴 CRITICAL ≤ 6H",  critical)
k4.metric("🟡 HIGH ≤ 48H",     high_ct)
k5.metric("🔍 FILTERED VIEW",  len(filtered))

st.divider()

# ── LAYOUT ──
col_main, col_side = st.columns([4, 1])

# ══════════════════════════════════════════════
# EXPORT COLUMN
# ══════════════════════════════════════════════
with col_side:
    st.caption("EXPORT")
    st.download_button(
        label="📥  DOWNLOAD calendar.json",
        data=json_str,
        file_name="calendar.json",
        mime="application/json",
        use_container_width=True,
    )
    # FIX #4: Affichage correct de la taille — "< 1 KB" si moins d'1 KB
    kb = len(json_str) // 1024
    size_str = f"{kb} KB" if kb > 0 else "< 1 KB"
    st.caption(f"{len(filtered)} events · {size_str}")

    st.divider()
    st.caption("WEEKLY SUMMARY")
    for day, evs in summary_by_day.items():
        dt  = datetime.fromisoformat(day)
        lbl = dt.strftime("%a %d").upper()
        st.markdown(f"**{lbl}**")
        for line in evs[:3]:
            st.caption(f"· {line}")
        if len(evs) > 3:
            st.caption(f"  +{len(evs)-3} more")

# ══════════════════════════════════════════════
# EVENTS COLUMN  — 100% native Streamlit
# ══════════════════════════════════════════════
with col_main:

    days_grouped = defaultdict(list)
    for ev in filtered:
        days_grouped[ev["date_display"]].append(ev)

    if not filtered:
        st.info("No events match current filters.")
    else:
        # FIX #2: Tri stable basé sur l'ensemble du groupe (any upcoming),
        # pas sur le seul premier élément qui peut être passé même si
        # d'autres events du même jour sont upcoming.
        for day_key in sorted(
            days_grouped.keys(),
            key=lambda d: (not any(e["is_upcoming"] for e in days_grouped[d]), d)
        ):
            day_evs = days_grouped[day_key]
            dt      = datetime.fromisoformat(day_key)
            upcoming_ct = sum(1 for e in day_evs if e["is_upcoming"])

            # ── Day header ──
            st.markdown(
                f"#### 📅 {dt.strftime('%A, %B %d %Y').upper()}"
                f"  <span style='font-size:11px;color:#4a6070;font-weight:400;'>"
                f"— {len(day_evs)} event(s) · {upcoming_ct} upcoming</span>",
                unsafe_allow_html=True
            )

            for ev in day_evs:
                p   = ev["priority"]
                s   = ev["session"]
                ccy = ev["currency"]

                icon_p   = PRIORITY_ICON.get(p, "🔵")
                icon_s   = SESSION_EMOJI.get(s, "🕐")
                icon_ccy = CCY_EMOJI.get(ccy, "🏦")

                cd = f"T − {ev['hours_until_display']}" if ev["is_upcoming"] else "PASSED"

                pairs_str = "  ·  ".join(ev["pairs_affected"][:4])
                if len(ev["pairs_affected"]) > 4:
                    pairs_str += " ···"

                fcst   = ev["forecast"]
                prev   = ev["previous"]
                actual = ev["actual"]
                fcst_line  = f"Forecast **{fcst}** · Prev {prev}"
                if actual != "—":
                    fcst_line += f" · ✅ Actual **{actual}**"

                # ── Card: 3-column native layout ──
                with st.container():
                    c_time, c_info, c_pairs = st.columns([1, 3, 2])

                    with c_time:
                        st.markdown(f"### {ev['time_display']}")
                        st.caption(cd)

                    with c_info:
                        st.markdown(
                            f"{icon_p} **{p}** &nbsp;&nbsp; {icon_s} {s} &nbsp;&nbsp; {icon_ccy} **{ccy}**",
                            unsafe_allow_html=True
                        )
                        st.markdown(f"**{ev['event_name']}**")
                        st.caption(fcst_line)

                    with c_pairs:
                        st.caption("PAIRS AFFECTED")
                        st.markdown(f"`{pairs_str}`" if pairs_str else "_—_")

                st.divider()

# ── JSON VIEWER ──
with st.expander("🔍  VIEW FULL JSON — LLM READY"):
    st.code(json_str, language="json")

st.caption("BLUESTAR SYSTEM · FOREX CALENDAR · HIGH IMPACT ONLY · SOURCE: FOREX FACTORY")
