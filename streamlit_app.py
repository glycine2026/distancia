import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Simulador logístico", layout="wide")

# =========================
# Cargar Excel
# =========================

df = pd.read_excel("km_26.xlsx", sheet_name="Hoja1")
tarifas = pd.read_excel("km_26.xlsx", sheet_name="Hoja2")

df.columns = df.columns.str.strip()
tarifas.columns = tarifas.columns.str.strip()

df["Km"] = pd.to_numeric(df["Km"], errors="coerce")
df["Lat"] = pd.to_numeric(df["Lat"], errors="coerce")
df["Lon"] = pd.to_numeric(df["Lon"], errors="coerce")

tarifas["Kilómetros"] = pd.to_numeric(tarifas["Kilómetros"], errors="coerce")
tarifas["Importe"] = pd.to_numeric(tarifas["Importe"], errors="coerce")

df = df.dropna(subset=["Campo", "Destino", "Km"])
tarifas = tarifas.dropna(subset=["CATAC", "Kilómetros", "Importe"])

# =========================
# Función tarifas
# =========================

def buscar_importe_por_km(km, tabla_tarifas):
    tabla_tarifas = tabla_tarifas.sort_values("Kilómetros")
    fila = tabla_tarifas[tabla_tarifas["Kilómetros"] <= km]

    if fila.empty:
        return float(tabla_tarifas.iloc[0]["Importe"])

    return float(fila.iloc[-1]["Importe"])

# =========================
# Función OSRM
# =========================

def distancia_osrm(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "routes" in data and len(data["routes"]) > 0:
            return data["routes"][0]["distance"] / 1000
        return None
    except:
        return None

# =========================
# Sidebar
# =========================

st.sidebar.header("Parámetros económicos")

tipo_cambio = st.sidebar.number_input("Tipo de cambio (ARS/USD)", value=1380.0)
precio = st.sidebar.number_input("Precio (USD)", value=200.0)

# CATAC
catac = st.sidebar.selectbox(
    "Escala CATAC",
    options=sorted(tarifas["CATAC"].unique())
)

tipo_catac = st.sidebar.radio(
    "Tipo de tarifa",
    ["CATAC llena", "CATAC con descuento"]
)

# Descuento dinámico
if tipo_catac == "CATAC con descuento":
    descuento_pct = st.sidebar.number_input("Descuento (%)", value=8.0)
else:
    descuento_pct = 0.0

st.sidebar.caption(f"CATAC seleccionada: {catac}")

# Valores base
paritaria_base = st.sidebar.number_input("Paritaria base", value=3.0)
secada_base = st.sidebar.number_input("Secada base", value=4.0)
comision_base_pct = st.sidebar.number_input("Comisión base (%)", value=1.0)

comision_base = comision_base_pct / 100

# =========================
# Selección campo
# =========================

st.title("Simulador logístico")

campo = st.selectbox("Campo", sorted(df["Campo"].unique()))
df_campo = df[df["Campo"] == campo]

fila_campo = df_campo.iloc[0]
lat_campo = fila_campo["Lat"]
lon_campo = fila_campo["Lon"]

if pd.isna(lat_campo) or pd.isna(lon_campo):
    st.error("⚠️ Campo sin coordenadas")
else:
    st.caption(f"📍 Campo: {round(lat_campo,4)}, {round(lon_campo,4)}")

# =========================
# Destinos
# =========================

destinos_excel = sorted(df_campo["Destino"].unique())

st.markdown("---")
st.info("👉 Si el destino ya está en la lista, NO cargar manual")

# =========================
# Destino manual
# =========================

st.subheader("➕ Agregar destino nuevo")

lat_dest = st.number_input("Lat destino", value=-34.0, format="%.6f")
lon_dest = st.number_input("Lon destino", value=-58.0, format="%.6f")

nombre_destino = st.text_input("Nombre del destino")

if st.button("Agregar destino"):

    if nombre_destino.strip() == "":
        st.warning("Ingresá un nombre")

    elif nombre_destino in destinos_excel:
        st.warning("Ese destino ya existe")

    else:
        km_manual = distancia_osrm(lat_campo, lon_campo, lat_dest, lon_dest)

        if km_manual:
            if "destinos_manuales" not in st.session_state:
                st.session_state.destinos_manuales = []

            st.session_state.destinos_manuales.append({
                "Destino": nombre_destino,
                "Km": km_manual
            })

            st.success(f"{round(km_manual,1)} km")
        else:
            st.error("Error calculando distancia")

# =========================
# Unificar destinos
# =========================

destinos_manual = [d["Destino"] for d in st.session_state.get("destinos_manuales", [])]

destinos = st.multiselect(
    "Destinos a comparar",
    options=destinos_excel + destinos_manual
)

# =========================
# Parámetros por destino
# =========================

if "param_destinos" not in st.session_state:
    st.session_state.param_destinos = {}

st.markdown("### ⚙️ Configuración por destino")

for destino in destinos:

    if destino not in st.session_state.param_destinos:
        st.session_state.param_destinos[destino] = {
            "paritaria": paritaria_base,
            "secada": secada_base,
            "comision": comision_base,
            "contraflete": 0.0
        }

    with st.expander(destino):

        p = st.session_state.param_destinos[destino]

        p["paritaria"] = st.number_input(f"Paritaria", value=p["paritaria"], key=f"p_{destino}")
        p["secada"] = st.number_input(f"Secada", value=p["secada"], key=f"s_{destino}")

        com_pct = st.number_input(f"Comisión %", value=p["comision"]*100, key=f"c_{destino}")
        p["comision"] = com_pct / 100

        p["contraflete"] = st.number_input(f"Contraflete USD", value=p["contraflete"], key=f"cf_{destino}")

# =========================
# Cálculos
# =========================

tarifas_filtradas = tarifas[tarifas["CATAC"] == catac]

resultados = []

for destino in destinos:

    if destino in df_campo["Destino"].values:
        km = float(df_campo[df_campo["Destino"] == destino].iloc[0]["Km"])
    else:
        km = next(d["Km"] for d in st.session_state["destinos_manuales"] if d["Destino"] == destino)

    importe_ars = buscar_importe_por_km(km, tarifas_filtradas)

    # aplicar descuento variable
    if tipo_catac == "CATAC con descuento":
        importe_ars *= (1 - descuento_pct / 100)

    flete_usd = importe_ars / tipo_cambio

    p = st.session_state.param_destinos[destino]

    precio_neto = (
        precio
        - flete_usd
        - p["paritaria"]
        - p["secada"]
        - p["contraflete"]
        - (precio * p["comision"])
    )

    resultados.append({
        "Destino": destino,
        "Km": round(km,1),
        "Flete USD": round(flete_usd,2),
        "Precio Neto": round(precio_neto,2)
    })

# =========================
# Resultados
# =========================

if resultados:

    df_res = pd.DataFrame(resultados)
    df_res = df_res.sort_values("Precio Neto", ascending=False).reset_index(drop=True)

    mejor = df_res.iloc[0]["Precio Neto"]
    df_res["Ahorro vs mejor USD"] = (mejor - df_res["Precio Neto"]).round(2)

    st.subheader("Comparación de destinos")
    st.dataframe(df_res, use_container_width=True, hide_index=True)

    st.success(f"Mejor destino: {df_res.iloc[0]['Destino']}")

else:
    st.info("Seleccioná destinos")
