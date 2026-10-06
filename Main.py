from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Cross-Connect Routing Tool", page_icon="🔌", layout="centered"
)

# ------------------- GOOGLE SHEETS ANBINDUNG -------------------
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1pK3J9V0CSQ7EmTZ90effqRmUV7GhjCwpDhKQrtvTL1k/edit?usp=drivesdk"


@st.cache_data(ttl=30)  # Live-Update alle 30 Sekunden
def load_trunk_data(sheet_url):
  if "DEIN_GOOGLE_SHEETS_LINK_HIER" in sheet_url or not sheet_url:
    st.warning("⚠️ Bitte trage deinen Google Sheets Link ein!")
    return []
  try:
    csv_url = sheet_url.replace("/edit?usp=sharing", "/gviz/tq?tqx=out:csv")
    csv_url = csv_url.replace(
        "/edit?usp=drivesdk", "/gviz/tq?tqx=out:csv"
    ).replace("/edit#gid=", "/gviz/tq?tqx=out:csv&gid=")
    if "/gviz/tq" not in csv_url:
      csv_url = csv_url.split("/edit")[0] + "/gviz/tq?tqx=out:csv"

    df = pd.read_csv(csv_url)
    df.fillna("", inplace=True)
    df.columns = [c.strip().lower() for c in df.columns]

    for col in ["quelle_pp", "ziel_pp"]:
      if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    return df.to_dict(orient="records")
  except Exception as e:
    st.error(f"⚠️ Fehler beim Laden der Google Sheet Daten: {e}")
    return []


TRUNK_DATABASE = load_trunk_data(GOOGLE_SHEET_URL)


# ------------------- DOPPELPORT-FORMATIERUNG -------------------
def get_dual_port_str(port_num):
  if port_num <= 0:
    return "Frei wählbar / Range"
  p = int(port_num)
  if p % 2 != 0:
    p1, p2 = p, p + 1
  else:
    p1, p2 = p - 1, p
  return f"Port {p1}/{p2}"


# ------------------- TEMPORÄRE SPERRLISTE -------------------
if "blocked_panels" not in st.session_state:
  st.session_state.blocked_panels = {}

now = datetime.now()
st.session_state.blocked_panels = {
    pp: exp
    for pp, exp in st.session_state.blocked_panels.items()
    if exp > now
}

# ------------------- BENUTZEROBERFLÄCHE -------------------
st.title("🔌 Cross-Connect Routing Tool")
st.caption("Dynamic Shortest-Path | Flexible Port-Mapping & IBX Auto-Routing")

st.subheader("📍 Startpunkt (A-Side)")
pp_a = st.text_input(
    "PP-Nummer A (Pflichtfeld)*",
    value="",
    placeholder="z.B. PP:0303:1408622",
)
port_a_input = st.number_input(
    "Port / Faser A (z. B. 1 für Port 1/2)*",
    min_value=0,
    max_value=864,
    value=1,
)

st.markdown("---")

st.subheader("🎯 Zielpunkt (Z-Side)")
target_mode = st.radio(
    "Ziel-Spezifikation wählen:",
    ["Ziel-IBX suchen (schnellster Pfad)", "Konkretes Z-Panel angeben"],
)

pp_z = ""
target_ibx = ""

if target_mode == "Konkretes Z-Panel angeben":
  pp_z = st.text_input(
      "PP-Nummer Z*", value="", placeholder="z.B. PP:0201:999999"
  )
else:
  target_ibx = st.text_input(
      "Ziel-IBX eingeben (z.B. FR2, FR5, FR7)*",
      value="",
      placeholder="z.B. FR2",
  ).strip()

st.markdown("---")


# ------------------- ROUTING ALGORITHMUS (BFS) -------------------
def find_route(start_pp, blocked_set, target_z="", target_ibx_str=""):
  queue = [[start_pp]]
  visited = set(blocked_set)
  visited.add(start_pp)

  target_ibx_clean = target_ibx_str.upper() if target_ibx_str else ""

  while queue:
    path = queue.pop(0)
    node = path[-1]

    if target_z and node == target_z:
      return path

    if target_ibx_clean:
      last_link = next(
          (
              item
              for item in TRUNK_DATABASE
              if item.get("ziel_pp") == node or item.get("quelle_pp") == node
          ),
          None,
      )
      if last_link:
        node_raum = (
            last_link.get("ziel_raum", "")
            if last_link.get("ziel_pp") == node
            else last_link.get("quelle_raum", "")
        )
        if target_ibx_clean in node_raum.upper():
          return path

    next_hops = [
        link
        for link in TRUNK_DATABASE
        if link.get("quelle_pp") == node and link.get("ziel_pp") not in visited
    ]

    for link in next_hops:
      next_node = link["ziel_pp"]
      visited.add(next_node)
      new_path = list(path)
      new_path.append(next_node)
      queue.append(new_path)

  return [start_pp]


# ------------------- ROUTING BERECHNEN -------------------
if st.button("🚀 Pfad ermitteln", use_container_width=True):
  if not pp_a:
    st.error("⚠️️ Bitte gib mindestens die PP-Nummer A ein!")
  elif target_mode == "Konkretes Z-Panel angeben" and not pp_z:
    st.error("⚠️ Bitte gib die PP-Nummer Z ein!")
  elif target_mode == "Ziel-IBX suchen (schnellster Pfad)" and not target_ibx:
    st.error("⚠️ Bitte gib das Ziel-IBX ein!")
  else:
    active_blocked = set(st.session_state.blocked_panels.keys())
    route_pps = find_route(
        pp_a.strip(),
        active_blocked,
        target_z=pp_z.strip(),
        target_ibx_str=target_ibx,
    )

    if len(route_pps) == 1 and (pp_z or target_ibx):
      st.error(
          "❌ Kein passender Pfad in der Datenbank gefunden! Bitte überprüfe die"
          " Einträge in Google Sheets."
      )
    else:
      st.success("✅ Path erfolgreich ermittelt!")

      if active_blocked:
        st.warning(
            f"⛔ **Aktive Umleitungen wegen VOLL:**"
            f" {', '.join(active_blocked)}"
        )

      st.markdown("### 🗺️ Routing-Pfad & Port-Zuordnung:")

      total_steps = len(route_pps)

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
          port_info = (
              f"🔒 **Eingangs-Port:** `{get_dual_port_str(port_a_input)}`"
          )
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

          # Port-Zuordnung aus Sheet auslesen falls vorhanden
          q_port = hop_link.get("quelle_port", "") if hop_link else ""
          z_port = hop_link.get("ziel_port", "") if hop_link else ""
          p_range = hop_link.get("port_range", "") if hop_link else ""

          if z_port:
            port_info = f"📌 **Gemappter Ziel-Port:** `{z_port}` (von Quelle `{q_port or get_dual_port_str(port_a_input)}`)"
          elif p_range:
            port_info = (
                f"🔓 **Trunk-Range (frei wählbar):** `{p_range}` (Start-Ref:"
                f" `{get_dual_port_str(port_a_input)}`)"
            )
          else:
            port_info = (
                f"🔒 **1:1 Durchschaltung:**"
                f" `{get_dual_port_str(port_a_input)}`"
            )

        st.info(f"""
                **Step {idx + 1}: {current_pp}**  
                * 📍 **Raum:** `{raum}` | **Rack:** `{rack}` | **HE:** `{he}`  
                * 🔌 **Port / Belegung:** {port_info}
                """)

        if idx > 0:
          if st.button(
              f"❌ Panel {current_pp} als VOLL markieren (1 Woche umleiten)",
              key=f"block_{current_pp}",
          ):
            st.session_state.blocked_panels[current_pp] = (
                datetime.now() + timedelta(days=7)
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
