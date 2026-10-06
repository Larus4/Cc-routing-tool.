import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Cross-Connect Routing Tool",
    page_icon="🔌",
    layout="centered",
)

st.title("🔌 Cross-Connect Routing Tool")
st.write(
    "Geben Sie die Daten für Kunde A und Kunde Z ein, um den Pfad zu berechnen:"
)

# ------------------- KUNDE A -------------------
st.subheader("📍 Kunde A (Startpunkt)")
col_a1, col_a2 = st.columns(2)
with col_a1:
  raum_a = st.text_input("Raum A", value="FR4:0G")
  rack_a = st.text_input("Rack A", value="0575")
with col_a2:
  pp_a = st.text_input("PP-Nummer A (Pflichtfeld)*", value="PP:0575:1193161")
  port_a = st.number_input(
      "Port/Faser A", min_value=1, max_value=864, value=12
  )

# ------------------- KUNDE Z -------------------
st.subheader("🎯 Kunde Z (Zielpunkt)")
col_z1, col_z2 = st.columns(2)
with col_z1:
  raum_z = st.text_input("Raum Z", value="CZ1")
  rack_z = st.text_input("Rack Z", value="0709")
with col_z2:
  pp_z = st.text_input("PP-Nummer Z (Pflichtfeld)*", value="PP:0709:1234567")
  port_z = st.number_input(
      "Port/Faser Z", min_value=1, max_value=864, value=12
  )

st.markdown("---")

# ------------------- BERECHNUNG -------------------
if st.button("🚀 Pfad & Routing berechnen", use_container_width=True):
  if not pp_a or not pp_z:
    st.error("⚠️ Bitte geben Sie für beide Seiten die PP-Nummer an!")
  else:
    st.success("Pfad erfolgreich berechnet!")

    st.markdown("### 🗺️ Pfadverlauf:")
    st.info(f"""
        **1. Startpunkt:**  
        Raum `{raum_a}` | Rack `{rack_a}` | `{pp_a}` | Port `{port_a}`
        """)

    st.markdown("⬇️ *Interne Trunk-Verbindung*")

    st.info(f"""
        **2. Zielpunkt:**  
        Raum `{raum_z}` | Rack `{rack_z}` | `{pp_z}` | Port `{port_z}`
        """)

