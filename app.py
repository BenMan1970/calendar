import streamlit as st
from bs4 import BeautifulSoup
import json
from datetime import datetime
import pytz
import re

def extract_high_impact_events(html_content, timezone_source):
    soup = BeautifulSoup(html_content, 'html.parser')
    events = []
    
    # On cible la table principale du calendrier
    table = soup.find('table', class_='calendar__table')
    if not table:
        return None

    rows = table.find_all('tr')
    
    # VARIABLES D'ÉTAT : Pour éviter le décalage dû aux rowspan (cellules fusionnées)
    current_date_str = ""
    current_year = "2026" # Par défaut, peut être extrait dynamiquement si besoin

    for row in rows:
        # 1. GESTION DE LA DATE (Cohérence logique)
        # Si la ligne contient une cellule de date, on met à jour notre "mémoire"
        date_cell = row.find('td', class_='calendar__date')
        if date_cell:
            # Extraction du texte (ex: "Mon Jun 1") et nettoyage des jours de la semaine
            raw_date = date_cell.get_text(strip=True)
            # On retire "Sun", "Mon", etc. pour ne garder que "Jun 1"
            current_date_str = re.sub(r'^(Sun|Mon|Tue|Wed|Thu|Fri|Sat)\s+', '', raw_date)

        # 2. FILTRE IMPACT ROUGE (Strictement High Impact)
        # On vérifie la présence de la classe spécifique à l'impact rouge
        impact_icon = row.find('span', class_='icon--ff-impact-red')
        if not impact_icon:
            continue

        # 3. EXTRACTION DES DONNÉES PAR CLASSES (Évite les décalages d'index de colonnes)
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
                # On nettoie pour ne garder que l'heure (ex: "3:00pm") et ignorer "Up Next"
                time_text = time_cell.get_text(strip=True)
                time_match = re.search(r'(\d{1,2}:\d{2}[ap]m)', time_text)
                if time_match:
                    time_str = time_match.group(1)

            # Sécurité : On ignore la ligne s'il manque la date ou l'heure
            if not current_date_str or not time_str:
                continue

            # 4. CALCUL DU TIMEZONE ET ISO 8601
            # Construction de la chaîne: "Jun 1 3:00pm 2026"
            full_datetime_str = f"{current_date_str} {time_str} {current_year}"
            
            # Conversion en objet datetime (Naïf)
            local_dt = datetime.strptime(full_datetime_str, "%b %d %I:%M%p %Y")
            
            # Localisation selon la timezone source et conversion en UTC
            src_tz = pytz.timezone(timezone_source)
            localized_dt = src_tz.localize(local_dt)
            utc_dt = localized_dt.astimezone(pytz.utc)
            
            # Format ISO 8601 strict
            datetime_utc = utc_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

            events.append({
                "currency": currency,
                "event_name": event_name,
                "datetime_utc": datetime_utc
            })
        except Exception:
            continue # On saute la ligne si une erreur de parsing survient

    return {
        "events": events,
        "timezone_source": timezone_source
    }

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Forex Calendar to JSON", page_icon="📅")

st.title("📅 Forex Factory $\rightarrow$ `calendar.json`")
st.markdown("""
Cette application extrait uniquement les événements à **Impact Rouge** d'un fichier HTML Forex Factory.
L'algorithme gère les cellules fusionnées (`rowspan`) pour garantir qu'aucun événement n'est associé à la mauvaise date.
""")

# Paramètre de timezone (Essentiel pour la cohérence UTC)
timezone_input = st.selectbox(
    "Timezone source du fichier HTML :",
    ["Europe/London", "America/New_York", "Asia/Tokyo", "UTC"],
    index=0
)

uploaded_file = st.file_uploader("Uploader le fichier .html", type="html")

if uploaded_file:
    html_content = uploaded_file.read().decode("utf-8")
    
    with st.spinner('Traitement logique en cours...'):
        result = extract_high_impact_events(html_content, timezone_input)

    if result:
        st.success(f"✅ {len(result['events'])} événements High-Impact extraits.")
        
        # Aperçu du JSON
        st.json(result)
        
        # Génération du fichier de sortie
        json_data = json.dumps(result, indent=2)
        
        st.download_button(
            label="📥 Télécharger calendar.json",
            data=json_//S l'encodage correct
            data=json_data,
            file_name="calendar.json",
            mime="application/json"
        )
    else:
        st.error("Aucun événement High-Impact trouvé ou fichier HTML invalide.")
