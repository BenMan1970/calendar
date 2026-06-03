import streamlit as st
import requests
import json
from datetime import datetime
import pytz

st.set_page_config(page_title="Forex Factory High Impact Calendar", layout="wide")
st.title("📅 Forex Factory - High Impact Events (Red)")
st.markdown("**Extraction automatique des événements à fort impact pour la semaine en cours**")

# ===================== CONFIG =====================
JSON_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# =================================================

@st.cache_data(ttl=300)  # Cache 5 minutes
def fetch_calendar():
    try:
        response = requests.get(JSON_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erreur lors de la récupération des données : {e}")
        return None

def convert_to_utc(event_date_str: str) -> str:
    """Convertit la date du JSON (format America/New_York) en UTC ISO 8601"""
    try:
        # Format exemple : "2026-06-01T10:00:00-04:00"
        dt = datetime.fromisoformat(event_date_str)
        # Conversion en UTC
        utc_dt = dt.astimezone(pytz.UTC)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except:
        return None

# ===================== MAIN =====================
data = fetch_calendar()

if data:
    # Filtrage High Impact uniquement
    high_impact_events = [
        event for event in data 
        if event.get("impact") == "High"
    ]

    st.success(f"**{len(high_impact_events)} événements High Impact** détectés cette semaine.")

    # Construction du JSON au format demandé
    events_list = []
    for event in high_impact_events:
        utc_time = convert_to_utc(event["date"])
        if utc_time:
            events_list.append({
                "currency": event["country"],
                "event_name": event["title"].strip(),
                "datetime_utc": utc_time
            })

    final_json = {
        "events": sorted(events_list, key=lambda x: x["datetime_utc"]),  # Tri chronologique
        "timezone_source": "America/New_York"
    }

    # Affichage
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Événements High Impact")
        for ev in final_json["events"]:
            st.write(f"**{ev['datetime_utc']}** | **{ev['currency']}** | {ev['event_name']}")

    with col2:
        st.subheader("Actions")
        if st.button("📥 Télécharger calendar.json", type="primary"):
            json_str = json.dumps(final_json, indent=2, ensure_ascii=False)
            st.download_button(
                label="Cliquez ici pour télécharger",
                data=json_str,
                file_name="calendar.json",
                mime="application/json"
            )

    # Option d'affichage brut
    with st.expander("Voir le JSON complet"):
        st.json(final_json)

else:
    st.warning("Impossible de récupérer le calendrier. Vérifiez votre connexion.")

st.caption("Source : Forex Factory • Mise à jour automatique • Format optimisé pour moteur de trading")
