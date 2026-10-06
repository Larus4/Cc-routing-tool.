from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Cross-Connect Routing Tool", page_icon="🔌", layout="centered"
)

# ------------------- GOOGLE SHEETS ANBINDUNG -------------------
# FÜGE HIER DEINEN KOPIERTEN GOOGLE SHEETS LINK EIN:
GOOGLE_SHEET_URL = https://docs.google.com/spreadsheets/d/1pK3J9V0CSQ7EmTZ90effqRmUV7GhjCwpDhKQrtvTL1k/edit?usp=drivesdk


@st.cache_data(ttl=30)  # Aktualisiert alle 30 Sekunden live aus Google Sheets
def load_trunk_data(sheet_url):
  if "DEIN_GOOGLE_SHEETS_LINK_HIER" in sheet_url or not sheet_url:
    st.warning("⚠️ Bitte trage deinen Google Sheets Link in die main.py ein!")
    return []
  try:
    # Wandelt den Teilen-Link automatisch in einen CSV-Export-Link um
    csv_url = sheet_url.replace("/edit?usp=sharing", "/gviz/tq?tqx=out:csv")
    csv_url = csv_url.replace("/edit#gid=", "/gviz/tq?tqx=out:csv&gid=")
    if "/gviz/tq" not in csv_url:
      csv_url = csv_url.split("/edit")[0] + "/gviz/tq?tqx=out:csv"

    df = pd.read_csv(csv_url)
    df.fillna("", inplace=True)

    # Spaltennamen zur Sicherheit bereinigen
    df.columns = [c.strip().lower() for c in df.columns]

    for col in ["quelle_pp", "ziel_pp"]:
      if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    return df.to_dict(orient="records")
  except Exception as e:
    st.error(f"⚠️ Fehler beim Laden der Google Sheet Daten: {e}")
    return []


TRUNK_DATABASE = load_trunk_data(GOOGLE_SHEET_URL)

# ------------------- TEMPORÄRE SPERRLISTE -------------------
if "blocked_panels" not in st.session_state:
  st.session_state.blocked_panels = {}

now = datetime.now()
st.session_state.blocked_panels = {
    pp: exp
    for pp, exp in st.session_state.blocked_panels.items()
    if exp > now
}

# ------------------- INPUT-FORMULAR -------------------
st.title("🔌 Cross-Connect Routing Tool")
st.caption("Live-Anbindung an Google Sheets | Dynamic Routing")

st.subheader("📍 Startpunkt")
pp_a = st.text_input(
    "PP-Nummer A (Pflichtfeld)*",
    value="",
    placeholder="z.B. PP:0303:1408622",
)
port_a_input = st.number_input(
    "Port / Faser A (Optional - 0 für komplette Range)",
    min_value=0,
    max_value=864,
    value=0,
)

st.markdown("---")


# ------------------- ROUTING-LOGIK -------------------
def find_route_bfs(start_pp, blocked_set):
  queue = [[start_pp]]
  visited = set(blocked_set)

  while queue:
    path = queue.pop(0)
    node = path[-1]

    next_hops = [
        link
        for link in TRUNK_DATABASE
        if link.get("quelle_pp") == node and link.get("ziel_pp") not in visited
    ]

    if not next_hops:
      return path

    for link in next_hops:
      visited.add(link["ziel_pp"])
      new_path = list(path)
      new_path.append(link["ziel_pp"])
      queue.append(new_path)

  return [start_pp]


# ------------------- ROUTING BERECHNEN -------------------
if st.button("🚀 Pfad ermitteln", use_container_width=True):
  if not pp_a:
    st.error("⚠️ Bitte gib mindestens die PP-Nummer A ein!")
  else:
    active_blocked = set(st.session_state.blocked_panels.keys())
    route_pps = find_route_bfs(pp_a.strip(), active_blocked)

    st.success("✅ Pfad erfolgreich berechnet!")

    if active_blocked:
      st.warning(
          f"⛔ **Aktive Umleitungen wegen voll/gesperrt:**"
          f" {', '.join(active_blocked)}"
      )

    st.markdown("### 🗺️ Routing-Pfad & Standort-Details:")

    for idx, current_pp in enumerate(route_pps):
      link_details = next(
          (
              item
              for item in TRUNK_DATABASE
              if item.get("quelle_pp") == current_pp
              or item.get("ziel_pp") == current_pp
          ),
          None,
      )

      if idx == 0:
        raum = (
            link_details.get("quelle_raum", "N/A")
            if link_details
            else "Aus PP ableitbar"
        )
        rack = (
            link_details.get("quelle_rack", "N/A")
            if link_details
            else "Aus PP ableitbar"
        )
        he = link_details.get("quelle_he", "N/A") if link_details else "N/A"
      else:
        prev_pp = route_pps[idx - 1]
        hop_link = next(
            (
                item
                for item in TRUNK_DATABASE
                if item.get("quelle_pp") == prev_pp
                and item.get("ziel_pp") == current_pp
            ),
            None,
        )
        raum = hop_link.get("ziel_raum", "N/A") if hop_link else "N/A"
        rack = hop_link.get("ziel_rack", "N/A") if hop_link else "N/A"
        he = hop_link.get("ziel_he", "N/A") if hop_link else "N/A"

      port_display = (
          f"Port `{port_a_input}`"
          if port_a_input > 0
          else f"Faserbereich `{link_details.get('port_range', 'Alle Ports') if link_details else 'Alle Ports'}`"
      )

      st.info(f"""
            **Step {idx + 1}: {current_pp}**  
            * 📍 **Raum:** `{raum}` | **Rack:** `{rack}` | **HE:** `{he}`  
            * 🔌 **Port / Bereich:** {port_display}
            """)

      if idx > 0:
        if st.button(
            f"❌ Panel {current_pp} als VOLL markieren (1 Woche umleiten)",
            key=f"block_{current_pp}",
        ):
          st.session_state.blocked_panels[current_pp] = datetime.now() + timedelta(
              days=7
          )
          st.rerun()

# ------------------- GESPERRTE PANELS VERWALTEN -------------------
if st.session_state.blocked_panels:
  with st.expander("🛠️ Verwaltete/Gesperrte Panels (Auto-Delete nach 7 Tagen)"):
    for pp, exp in list(st.session_state.blocked_panels.items()):
      col1, col2 = st.columns([3, 1])
      with col1:
        st.write(f"• **{pp}** (Gesperrt bis: {exp.strftime('%d.%m.%Y %H:%M')})")
      with col2:
        if st.button("Freigeben", key=f"unblock_{pp}"):
          del st.session_state.blocked_panels[pp]
          st.rerun()

