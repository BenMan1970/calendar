import streamlit as st
from bs4 import BeautifulSoup
import json
from datetime import datetime
import pytz
import re

def extract_high_impact_events(html_content, timezone_source):
    soup = BeautifulSoup(html_content, 'html.parser')
    events = []
    
    # On récupère TOUTES les lignes du document
    rows = soup.find_all('tr')
    if not rows:
        return None

    # Variables d'état pour gérer les dates fusionnées (rowspan)
    current_date_str = ""
    current_year = "2026" # Année définie selon vos données

    for row in rows:
        # 1. GESTION DE LA DATE
        # On cherche une cellule qui contient la date (ex: "Mon Jun 1")
        date_cell = row.find('td', class_='calendar__date')
        if date_cell:
            raw_date = date_cell.get_text(strip=True)
            # On retire le jour (Mon, Tue...) pour ne garder que "Jun 1"
            current_date_str = re.sub(r'^(Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+', '', raw_date)

        # 2. FILTRE IMPACT ROUGE
        # On cherche l'icône rouge n'importe où dans la ligne
        impact_red = row.find('span', class_='icon--ff-impact-red')
        if not impact_red:
            continue

        # 3. EXTRACTION DES DONNÉES
        try:
            # Devise : on cherche la cellule avec la classe currency
            currency_cell = row.find('td', class_='calendar__currency')
            currency = currency_cell.get_text(strip=True) if currency_cell else "Unknown"

            # Nom de l'événement : on cherche le titre
            event_title = row.find('span', class_='calendar__event-title')
            event_name = event_title.get_text(strip=True) if event_title else "Unknown Event"

            # Heure : on cherche la cellule time
            time_cell = row.find('td', class_='calendar__time')
            time_str = ""
            if time_cell:
                time_text = time_cell.get_text(strip=True)
                # Extraction du format "3:00pm" ou "14:00"
                time_match = re.search(r'(\d{1,2}:\d{2}(?:[ap]m)?)', time_text)
                if time_match:
                    time_str = time_match.group(1)

            # Sécurité : on ignore si la date ou l'heure est manquante
            if not current_date_str or not time_str:
                continue

            # 4. CONVERSION TEMPORELLE STRICTE
            # Format source: "Jun 1 3:00pm 2026"
            # On gère le cas où l'heure est au format 24h ou 12h
            try:
                if 'am' in time_str.lower() or 'pm' in time_str.lower():
                    dt_format = "%b %d %I:%M%p %Y"
                else:
                    dt_format = "%b %d %H:%M %Y"
                
                full_datetime_str = f"{current_date_str} {time_str} {current_year}"
                local_dt = datetime.strptime(full_datetime_str, dt_format)
            except ValueError:
                continue
            
            # Application de la Timezone source -> Conversion UTC
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
st.markdown("L'application extrait les événements **High-Impact (Rouges)** et les convertit en **UTC strict**.")

# Timezone source
timezone_input = st.selectbox(
    "Timezone source du fichier HTML :",
    ["Europe/Paris", "Europe/London", "America/New_York", "Asia/Tokyo", "UTC"],
    index=0 
)

uploaded_file = st.file_uploader("Uploader le fichier .html", type="html")

if uploaded_file:
    html_content = uploaded_file.read().decode("utf-8")
    
    with st.spinner('Analyse du fichier...'):
        result = extract_high_impact_events(html_content, timezone_input)

    if result and result['events']:
        st.success(f"✅ {len(result['events'])} événements High-Impact extraits.")
        
        # Affichage du JSON
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
        st.warning("Aucun événement à Impact Rouge trouvé dans ce fichier.")
    else:
        st.error("Impossible de trouver la structure du calendrier dans le fichier HTML.")
   
