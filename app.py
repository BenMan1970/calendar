import streamlit as st
from bs4 import BeautifulSoup
import json
from datetime import datetime
import pytz
import re

def extract_high_impact_events(html_content, timezone_source):
    soup = BeautifulSoup(html_content, 'html.parser')
    events = []
    
    # Cible la table principale du calendrier
    table = soup.find('table', class_='calendar__table')
    if not table:
        return None

    rows = table.find_all('tr')
    
    # Variables d'état pour gérer les cellules fusionnées (rowspan)
    current_date_str = ""
    current_year = "2026" 

    for row in rows:
        # 1. GESTION DE LA DATE : On mémorise la date dès qu'on en trouve une
        date_cell = row.find('td', class_='calendar__date')
        if date_cell:
            # Nettoyage : on enlève le jour de la semaine (Mon, Tue...) pour garder "Jun 1"
            raw_date = date_cell.get_text(strip=True)
            current_date_str = re.sub(r'^(Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+', '', raw_date)

        # 2. FILTRE IMPACT ROUGE : On ignore tout ce qui n'est pas "High Impact"
        impact_icon = row.find('span', class_='icon--ff-impact-red')
        if not impact_icon:
            continue

        # 3. EXTRACTION DES DONNÉES (Par classes CSS pour éviter les décalages)
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
                # Regex pour capturer uniquement le format "3:00pm"
                time_match = re.search(r'(\d{1,2}:\d{2}[ap]m)', time_text)
                if time_match:
                    time_str = time_match.group(1)

            # Sécurité : On ignore si la date ou l'heure est manquante
            if not current_date_str or not time_str:
                continue

            # 4. CONVERSION UTC ISO 8601
            # Format: "Jun 1 3:00pm 2026"
            full_datetime_str = f"{current_date_str} {time_str} {current_year}"
            local_dt = datetime.strptime(full_datetime_str, "%b %d %I:%M%p %Y")
            
            # Localisation -> UTC
            src_tz = pytz.timezone(timezone_source)
            localized_dt = src_tz.localize(local_dt)
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
Cette application transforme un fichier HTML Forex Factory en un fichier JSON structuré.
- **Filtre :** Uniquement les événements à **Impact Rouge**.
- **Logique :** Gestion automatique des dates fusionnées pour éviter tout décalage.
""")

# Sélection de la timezone
timezone_input = st.selectbox(
    "Timezone source du fichier HTML :",
    ["Europe/London", "America/New_York", "Asia/Tokyo", "UTC"],
    index=0
)

uploaded_file = st.file_uploader("Uploader le fichier .html", type="html")

if uploaded_file:
    html_content = uploaded_file.read().decode("utf-8")
    
    with st.spinner('Traitement des données...'):
        result = extract_high_impact_events(html_content, timezone_input)

    if result and result['events']:
        st.success(f"✅ {len(result['events'])} événements High-Impact extraits.")
        
        # Affichage du résultat
        st.json(result)
        
        # Bouton de téléchargement
        json_data = json.dumps(result, indent=2)
        st.download_button(
            label="📥 Télécharger calendar.json",
            data=json_data,
            file_name="calendar.json",
            mime="application/json"
        )
    elif result and not result['events']:
        st.warning("Le fichier a été analysé, mais aucun événement à Impact Rouge n'a été trouvé.")
    else:
        st.error("Le fichier HTML n'est pas valide ou ne contient pas de table de calendrier.")
