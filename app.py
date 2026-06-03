import streamlit as st
from bs4 import BeautifulSoup
import json
from datetime import datetime
import pytz
import re

def extract_high_impact_events(html_content, timezone_source):
    soup = BeautifulSoup(html_content, 'html.parser')
    events = []
    
    table = soup.find('table', class_='calendar__table')
    if not table:
        return None

    rows = table.find_all('tr')
    
    current_date_str = ""
    current_year = "2026" 

    for row in rows:
        # Gestion de la date (Rowspan)
        date_cell = row.find('td', class_='calendar__date')
        if date_cell:
            raw_date = date_cell.get_text(strip=True)
            current_date_str = re.sub(r'^(Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+', '', raw_date)

        # Filtre strict Impact Rouge
        impact_icon = row.find('span', class_='icon--ff-impact-red')
        if not impact_icon:
            continue

        try:
            # Devise
            currency_cell = row.find('td', class_='calendar__currency')
            currency = currency_cell.get_text(strip=True) if currency_cell else "Unknown"

            # Nom de l'événement
            event_title = row.find('span', class_='calendar__event-title')
            event_name = event_title.get_text(strip=True) if event_title else "Unknown Event"

            # Heure
            time_cell = row.find('td', class_='calendar__time')
            time_str = ""
            if time_cell:
                time_text = time_cell.get_text(strip=True)
                time_match = re.search(r'(\d{1,2}:\d{2}[ap]m)', time_text)
                if time_match:
                    time_str = time_match.group(1)

            if not current_date_str or not time_str:
                continue

            # --- LOGIQUE DE CONVERSION TEMPORELLE ---
            # 1. On crée la date naïve (ex: "Jun 1 3:00pm 2026")
            full_datetime_str = f"{current_date_str} {time_str} {current_year}"
            local_dt = datetime.strptime(full_datetime_str, "%b %d %I:%M%p %Y")
            
            # 2. On lui assigne la timezone source (UTC+1)
            src_tz = pytz.timezone(timezone_source)
            localized_dt = src_tz.localize(local_dt)
            
            # 3. On convertit en UTC (On soustrait l'heure de décalage)
            utc_dt = localized_dt.astimezone(pytz.utc)
            
            datetime_utc = utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

            events.append({
                "currency": currency,
                "event_name": event_name,
                "datetime_utc": datetime_utc
            })
        except Exception:
            continue 

    return {
        "events": events,
        "timezone_source": timezone_source
    }

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Forex Calendar to JSON", page_icon="📅")

st.title("📅 Forex Factory $\rightarrow$ `calendar.json`")
st.markdown("""
L'application convertit vos heures locales en **UTC strict** pour éviter tout décalage dans vos outils de trading.
""")

# On place Europe/Paris (UTC+1) en premier et par défaut
timezone_input = st.selectbox(
    "Votre Timezone (Source du fichier HTML) :",
    ["Europe/Paris", "Europe/London", "America/New_York", "Asia/Tokyo", "UTC"],
    index=0 # Sélectionne Europe/Paris par défaut
)

uploaded_file = st.file_uploader("Uploader le fichier .html", type="html")

if uploaded_file:
    html_content = uploaded_file.read().decode("utf-8")
    
    with st.spinner('Calcul du décalage UTC en cours...'):
        result = extract_high_impact_events(html_content, timezone_input)

    if result and result['events']:
        st.success(f"✅ {len(result['events'])} événements High-Impact extraits et convertis en UTC.")
        
        st.json(result)
        
        json_data = json.dumps(result, indent=2)
        st.download_button(
            label="📥 Télécharger calendar.json",
            data=json_//L'encodage est géré par Streamlit
            data=json_data,
            file_name="calendar.json",
            mime="application/json"
        )
    elif result and not result['events']:
        st.warning("Aucun événement à Impact Rouge trouvé.")
    else:
        st.error("Fichier HTML invalide.")
