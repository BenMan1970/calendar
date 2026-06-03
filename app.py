import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pytz
from typing import List, Dict

st.set_page_config(page_title="Forex High Impact Calendar - Pro", layout="wide")
st.title("📅 Forex Factory High Impact Calendar - Version Optimisée Trading")
st.markdown("**Extraction intelligente pour moteur de trading + LLM**")

# ===================== CONFIG =====================
JSON_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CACHE_TTL = 300  # 5 minutes

# =================================================

@st.cache_data(ttl=CACHE_TTL)
def fetch_raw_calendar() -> List[Dict]:
    try:
        resp = requests.get(JSON_URL, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Erreur récupération données : {e}")
        return []

def enrich_event(event: Dict, now_utc: datetime) -> Dict:
    """Enrichit un événement avec des métadonnées utiles pour trading/LLM"""
    try:
        event_time = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
        if event_time.tzinfo is None:
            event_time = pytz.UTC.localize(event_time)
        
        time_until = (event_time - now_utc).total_seconds() / 3600  # heures

        return {
            "currency": event["country"],
            "event_name": event["title"].strip(),
            "datetime_utc": event_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "datetime_local": event_time.strftime("%Y-%m-%d %H:%M (%Z)"),
            "impact": event.get("impact", "High"),
            "forecast": event.get("forecast", ""),
            "previous": event.get("previous", ""),
            "hours_until": round(time_until, 2),
            "is_upcoming": time_until > 0,
            "day_of_week": event_time.strftime("%A"),
            "priority": "CRITICAL" if time_until <= 6 else "HIGH" if time_until <= 48 else "MEDIUM"
        }
    except:
        return None

# ===================== MAIN =====================
raw_data = fetch_raw_calendar()
now_utc = datetime.now(pytz.UTC)

# Filtrage + Enrichissement
high_impact = []
for event in raw_data:
    if event.get("impact") == "High":
        enriched = enrich_event(event, now_utc)
        if enriched:
            high_impact.append(enriched)

# Tri intelligent : Upcoming d'abord, puis chronologique
high_impact.sort(key=lambda x: (not x["is_upcoming"], x["datetime_utc"]))

final_json = {
    "metadata": {
        "generated_at_utc": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_high_impact": len(high_impact),
        "upcoming_count": sum(1 for e in high_impact if e["is_upcoming"]),
        "timezone_source": "America/New_York",
        "source": "Forex Factory Official JSON"
    },
    "events": high_impact,
    "summary_by_day": {}
}

# Résumé par jour (très utile pour LLM)
from collections import defaultdict
daily = defaultdict(list)
for ev in high_impact:
    day = ev["datetime_utc"][:10]
    daily[day].append(ev["currency"] + " - " + ev["event_name"])

final_json["summary_by_day"] = {day: events for day, events in sorted(daily.items())}

# ===================== INTERFACE =====================
col1, col2 = st.columns([3, 1])

with col1:
    st.success(f"**{len(high_impact)} événements High Impact** | {final_json['metadata']['upcoming_count']} à venir")
    
    for ev in final_json["events"][:15]:  # Affichage limité
        status = "🟢 À venir" if ev["is_upcoming"] else "🔴 Passé"
        st.write(f"{status} **{ev['datetime_utc']}** | **{ev['currency']}** | {ev['event_name']} | Priority: **{ev['priority']}**")

with col2:
    st.subheader("Export")
    if st.button("📥 Télécharger calendar.json", type="primary"):
        json_str = json.dumps(final_json, indent=2, ensure_ascii=False)
        st.download_button(
            label="Confirmer le téléchargement",
            data=json_str,
            file_name="calendar.json",
            mime="application/json"
        )

with st.expander("Voir JSON complet (prêt pour LLM)"):
    st.json(final_json)

st.caption("Optimisé pour systèmes de trading & agents LLM • Mise à jour automatique")
