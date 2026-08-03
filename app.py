# stdlib
import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

# third-party
import pytz
import requests
import streamlit as st

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
JSON_URL   = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE_TTL  = 300
CASABLANCA = pytz.timezone("Africa/Casablanca")

# NOTE (audit) : cette matrice ne couvre QUE les 8 devises Forex Factory
# (USD, EUR, GBP, JPY, CAD, AUD, NZD, CHF, + CNY hérité). Chaque paire listée
# est un fait mécanique (la devise déclenchée fait partie de la paire), pas
# un jugement de marché. Aucun indice (DAX, SP500, US30, NAS100) ni métal
# (XAUUSD) n'a été ajouté : ni le JSON Forex Factory ni aucun fichier fourni
# ne documente cette corrélation. L'ajouter aurait constitué une donnée
# inventée — exclu explicitement de cette correction.
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

# Renommage (ex-PRIORITY_ICON) : ces icônes/labels décrivent UNIQUEMENT la
# proximité temporelle de l'événement, jamais son impact Forex Factory.
# L'impact réel est TOUJOURS "High" ici (filtré en amont, cf. `all_events`) —
# affiché séparément et fixé dans l'UI, jamais mélangé à ces valeurs.
TIME_ICON = {"IMMINENT":"⏱️","SOON":"⏳","LATER":"📅","PAST":"⚫"}

def get_session(t_utc: datetime) -> str:
    # Les sessions de trading (Londres/NY) sont conventionnellement définies
    # en UTC : on garde volontairement l'heure UTC ici, pas l'heure locale
    # Casablanca, pour ne pas fausser le calcul de session.
    h = t_utc.hour
    london, ny = 7 <= h < 16, 13 <= h < 22
    if london and ny:
        return "OVERLAP"
    if london:
        return "LONDON"
    if ny:
        return "NEW YORK"
    if 0 <= h < 9:
        return "ASIAN"
    return "OFF"

def fmt_until(h: float) -> str:
    if h <= 0:
        return "PASSED"
    total_min = int(h * 60)
    hh, mm = divmod(total_min, 60)
    if hh == 0:
        return f"{mm}m"
    if hh < 24:
        return f"{hh}h {mm}m"
    return f"{hh//24}d {hh%24}h {mm}m"

@st.cache_data(ttl=CACHE_TTL)
def fetch_raw() -> List[Dict]:
    try:
        r = requests.get(JSON_URL, timeout=15)
        r.raise_for_status()
        return r.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Fetch failed: %s", e)
        return []

def enrich(event: Dict, event_time_ref_utc: datetime) -> Optional[Dict]:
    try:
        t_utc = datetime.fromisoformat(event.get("date","").replace("Z","+00:00"))
        if t_utc.tzinfo is None:
            t_utc = pytz.UTC.localize(t_utc)
        else:
            t_utc = t_utc.astimezone(pytz.UTC)

        # Heure locale Casablanca — UNIQUEMENT pour l'affichage. Tous les
        # calculs temporels (hours_until, is_upcoming, tri, session) restent
        # basés sur t_utc / event_time_ref_utc, donc inchangés.
        t_local = t_utc.astimezone(CASABLANCA)

        h   = (t_utc - event_time_ref_utc).total_seconds() / 3600
        ccy = event.get("country","")

        # time_proximity (ex-"priority") : décrit QUAND l'événement a lieu,
        # jamais SON impact. Les mots "HIGH"/"MEDIUM" ont été bannis de ce
        # champ pour ne plus entrer en collision avec le champ "impact" de
        # Forex Factory (qui, lui, est toujours "High" dans ce flux).
        time_proximity = ("PAST"     if h <= 0 else
                           "IMMINENT" if h <= 6 else
                           "SOON"     if h <= 48 else "LATER")

        return {
            "currency":            ccy,
            "event_name":          event.get("title","").strip(),
            "datetime_utc":        t_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date_display":        t_local.strftime("%Y-%m-%d"),
            "time_display":        t_local.strftime("%H:%M") + " (Africa/Casablanca)",
            "day_of_week":         t_local.strftime("%A").upper(),
            "impact":              (event.get("impact") or "High").lower(),
            "forecast":            event.get("forecast","") or "—",
            "previous":            event.get("previous","") or "—",
            "actual":              event.get("actual","") or "—",
            "hours_until":         round(h, 2),
            "hours_until_display": fmt_until(h),
            "is_upcoming":         h > 0,
            "time_proximity":      time_proximity,
            "session":             get_session(t_utc),
            "pairs_affected":      PAIRS_MAP.get(ccy, []),
        }
    except (ValueError, KeyError, AttributeError) as e:
        logger.warning("Skip: %s", e)
        return None

# ── DATA ──
raw_data = fetch_raw()
now_utc   = datetime.now(pytz.UTC)
now_local = now_utc.astimezone(CASABLANCA)

if not raw_data:
    st.error("⚠ Cannot reach Forex Factory API.")
    st.stop()

# Filtre source d'impact Forex Factory — INCHANGÉ, vérifié à l'audit.
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
    # Défaut passé à True : la vue hebdomadaire doit correspondre à la
    # semaine complète du PDF de référence (qui n'exclut pas les événements
    # déjà passés dans la semaine). Voir aussi le filtre TIME PROXIMITY
    # ci-dessous : "PAST" y est inclus par défaut pour que ce bouton ait
    # réellement un effet visible (sinon les événements passés resteraient
    # masqués par l'autre filtre, malgré ce bouton — bug de couplage corrigé
    # ici).
    show_past = st.checkbox("Show past events", value=True)

    st.caption("TIME PROXIMITY")
    sel_time = st.multiselect("Time proximity", ["IMMINENT","SOON","LATER","PAST"],
                              default=["IMMINENT","SOON","LATER","PAST"],
                              label_visibility="collapsed")
    st.divider()
    st.caption(f"LAST REFRESH\n{now_utc.strftime('%Y-%m-%d %H:%M UTC')}")

    if st.button("🔄 Vider le cache"):
        st.cache_data.clear()
        st.rerun()

# ── FILTERS ──
filtered = all_events.copy()
if sel_ccy:
    filtered = [e for e in filtered if e["currency"] in sel_ccy]
if sel_sess:
    filtered = [e for e in filtered if e["session"] in sel_sess]
if not show_past:
    filtered = [e for e in filtered if e["is_upcoming"]]
filtered = [e for e in filtered if e["time_proximity"] in sel_time]

# ── SUMMARY BY DAY ──
# Construit à partir de 'filtered' (== champ "events" du JSON final), pas de
# 'all_events', pour qu'un lecteur (LLM ou humain) ne voie jamais un
# événement listé dans summary_by_day qui soit absent de "events".
daily = defaultdict(list)
for ev in filtered:
    daily[ev["datetime_utc"][:10]].append(f"{ev['currency']} – {ev['event_name']}")
summary_by_day = dict(sorted(daily.items()))

# ── EVENTS ENGINE ──
# DÉCISION D'AUDIT EXPLICITE (à confirmer si vous voulez un autre
# comportement) : la source reste 'all_events', PAS 'filtered'.
# Raison : ce champ alimente "le reste du pipeline" de décision. S'il suivait
# les filtres devise/session choisis ponctuellement par un opérateur dans le
# dashboard, un événement à haut impact pourrait disparaître du flux machine
# simplement parce qu'un humain a décoché une devise pour SA propre vue —
# une régression silencieuse pour le pipeline. Seul le filtre temporel
# (fenêtre ±72h) s'applique ici, pas les filtres UI.
events_engine = [
    e for e in all_events
    if e["is_upcoming"] or e["hours_until"] >= -72
]

# ── FINAL JSON ──
final_json = {
    "metadata": {
        "generated_at_utc":  now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source":            "Forex Factory Official JSON",
        "timezone":          "UTC (backend) / Africa/Casablanca (display fields)",
        "total_high_impact": len(all_events),
        "upcoming_count":    sum(1 for e in all_events if e["is_upcoming"]),
        "imminent_count":    sum(1 for e in all_events if e["time_proximity"] == "IMMINENT"),
        "filters_applied":   {"currencies": sel_ccy, "sessions": sel_sess,
                              "show_past": show_past, "time_proximity": sel_time},
        "engine_events_count": len(events_engine),
    },
    "events":         filtered,
    "events_engine":  events_engine,
    "summary_by_day": summary_by_day,
}
json_str = json.dumps(final_json, indent=2, ensure_ascii=False)

# ── BANNIÈRE (native, sans HTML) ──
st.title("📡 FOREX CALENDAR — HIGH IMPACT")
st.caption(
    f"BLUESTAR SYSTEM · MODULE 04 · LIVE FEED · FOREX FACTORY JSON · "
    f"AUTO-REFRESH 5 MIN · {now_local.strftime('%A %d %B %Y — %H:%M')} (Africa/Casablanca)"
)

total    = len(all_events)
upcoming = sum(1 for e in all_events if e["is_upcoming"])
imminent_ct = sum(1 for e in all_events if e["time_proximity"] == "IMMINENT")
soon_ct     = sum(1 for e in all_events if e["time_proximity"] == "SOON")

k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("📊 TOTAL EVENTS",     total)
k2.metric("🟢 UPCOMING",         upcoming)
k3.metric("⏱️ IMMINENT ≤ 6H",    imminent_ct)
k4.metric("⏳ SOON ≤ 48H",       soon_ct)
k5.metric("🔍 FILTERED VIEW",    len(filtered))

st.divider()

col_main, col_side = st.columns([4, 1])

with col_side:
    st.caption("EXPORT")
    st.download_button(
        label="📥  DOWNLOAD calendar.json",
        data=json_str,
        file_name="calendar.json",
        mime="application/json",
        use_container_width=True,
    )
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

with col_main:

    days_grouped = defaultdict(list)
    for ev in filtered:
        days_grouped[ev["date_display"]].append(ev)

    if not filtered:
        st.info("No events match current filters.")
    else:
        for day_key in sorted(
            days_grouped.keys(),
            key=lambda d: (not any(e["is_upcoming"] for e in days_grouped[d]), d)
        ):
            day_evs = days_grouped[day_key]
            dt      = datetime.fromisoformat(day_key)
            upcoming_ct = sum(1 for e in day_evs if e["is_upcoming"])

            # Bannière de jour : native, sans <span>/unsafe_allow_html.
            st.markdown(f"#### 📅 {dt.strftime('%A, %B %d %Y').upper()}")
            st.caption(f"{len(day_evs)} event(s) · {upcoming_ct} upcoming")

            for ev in day_evs:
                p   = ev["time_proximity"]
                s   = ev["session"]
                ccy = ev["currency"]

                icon_t   = TIME_ICON.get(p, "🕐")
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

                with st.container():
                    c_time, c_info, c_pairs = st.columns([1, 3, 2])

                    with c_time:
                        st.markdown(f"### {ev['time_display']}")
                        st.caption(cd)

                    with c_info:
                        # Impact fixe (garanti par le filtre en amont) +
                        # proximité temporelle dynamique. \u00A0 = espace
                        # insécable Unicode, pas une entité HTML : rendu
                        # correctement par le markdown natif, sans
                        # unsafe_allow_html.
                        st.markdown(
                            f"🔴 **HIGH IMPACT** \u00A0\u00A0 {icon_t} **{p}** "
                            f"\u00A0\u00A0 {icon_s} {s} \u00A0\u00A0 {icon_ccy} **{ccy}**"
                        )
                        st.markdown(f"**{ev['event_name']}**")
                        st.caption(fcst_line)

                    with c_pairs:
                        st.caption("PAIRS AFFECTED")
                        st.markdown(f"`{pairs_str}`" if pairs_str else "_—_")

                st.divider()

with st.expander("🔍  VIEW FULL JSON — LLM READY"):
    st.code(json_str, language="json")

st.caption("BLUESTAR SYSTEM · FOREX CALENDAR · HIGH IMPACT ONLY · SOURCE: FOREX FACTORY")
