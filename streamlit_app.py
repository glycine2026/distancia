import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")

st.title("Plataforma logística de destinos")

# =========================
# Inputs económicos
# =========================

st.sidebar.header("Parámetros económicos")

tarifa_km = st.sidebar.number_input("Tarifa por km", value=0.15)
precio = st.sidebar.number_input("Precio", value=200)

paritaria = st.sidebar.number_input("Paritaria", value=3.0)
secada = st.sidebar.number_input("Secada", value=4.0)

comision = st.sidebar.number_input("Comisión (%)", value=1.0) / 100

# =========================
# Coordenadas
# =========================

st.sidebar.header("Campo")

lat_campo = st.sidebar.number_input("Lat campo", value=-37.0)
lon_campo = st.sidebar.number_input("Lon campo", value=-59.0)

st.sidebar.header("Destino")

lat_dest = st.sidebar.number_input("Lat destino", value=-33.0)
lon_dest = st.sidebar.number_input("Lon destino", value=-60.0)

# =========================
# Calcular ruta
# =========================

url = f"http://router.project-osrm.org/route/v1/driving/{lon_campo},{lat_campo};{lon_dest},{lat_dest}?overview=full&geometries=geojson"

r = requests.get(url)

data = r.json()

distancia_km = data["routes"][0]["distance"] / 1000

geometry = data["routes"][0]["geometry"]["coordinates"]

# =========================
# Calculo flete
# =========================

flete = distancia_km * tarifa_km

precio_neto = precio - flete - paritaria - secada - (comision * precio)

gasto_comercial = (precio - precio_neto) / precio

# =========================
# Mostrar resultados
# =========================

col1, col2, col3 = st.columns(3)

col1.metric("Distancia (km)", round(distancia_km,1))
col2.metric("Flete", round(flete,2))
col3.metric("Precio Neto", round(precio_neto,2))

st.metric("Gasto Comercial (%)", round(gasto_comercial*100,2))

# =========================
# Mapa
# =========================

mapa = folium.Map(location=[lat_campo, lon_campo], zoom_start=6)

folium.Marker(
    [lat_campo, lon_campo],
    tooltip="Campo",
    icon=folium.Icon(color="green")
).add_to(mapa)

folium.Marker(
    [lat_dest, lon_dest],
    tooltip="Destino",
    icon=folium.Icon(color="red")
).add_to(mapa)

# convertir ruta
route = [[coord[1], coord[0]] for coord in geometry]

folium.PolyLine(route, color="blue", weight=4).add_to(mapa)

st_folium(mapa, width=900, height=500)
