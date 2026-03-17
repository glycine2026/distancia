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

# Normalización de tipos
df["Km"] = pd.to_numeric(df["Km"], errors="coerce")
tarifas["Kilómetros"] = pd.to_numeric(tarifas["Kilómetros"], errors="coerce")
tarifas["Importe"] = pd.to_numeric(tarifas["Importe"], errors="coerce")

df = df.dropna(subset=["Campo", "Destino", "Km"])
tarifas = tarifas.dropna(subset=["Kilómetros", "Importe"]).sort_values("Kilómetros")

# =========================
# Función tarifas
# =========================

def buscar_importe_por_km(km: float, tabla_tarifas: pd.DataFrame) -> float:
    fila = tabla_tarifas[tabla_tarifas["Kilómetros"] <= km]

    if fila.empty:
        return float(tabla_tarifas.iloc[0]["Importe"])

    return float(fila.iloc[-1]["Importe"])

# =========================
# Función OSRM (distancia real)
# =========================

def distancia_osrm(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"

        response = requests.get(url, timeout=10)
        data = response.json()

        if "routes" in data and len(data["routes"]) > 0:
            distancia_m = data["routes"][0]["distance"]
            return distancia_m / 1000  # ✅ KM

        else:
            return None

    except:
        return None

# =========================
# Sidebar parámetros
# =========================

st.sidebar.header("Parámetros económicos")

tipo_cambio = st.sidebar.number_input("Tipo de cambio (ARS/USD)", value=1380.0)
precio = st.sidebar.number_input("Precio (USD)", value=200.0)
paritaria = st.sidebar.number_input("Paritaria (USD)", value=3.0)
secada = st.sidebar.number_input("Secada (USD)", value=4.0)
comision_pct = st.sidebar.number_input("Comisión (%)", value=1.0)

comision = comision_pct / 100

# =========================
# Selección campo
# =========================

st.title("Simulador logístico")

campos = sorted(df["Campo"].dropna().unique())
campo = st.selectbox("Campo", campos)

df_campo = df[df["Campo"] == campo].copy()

# =========================
# DESTINO MANUAL (OSRM)
# =========================

st.markdown("---")
st.subheader("➕ Agregar destino manual")

col1, col2 = st.columns(2)

with col1:
    lat_campo = st.number_input("Lat campo", value=-35.0, format="%.6f")
    lon_campo = st.number_input("Lon campo", value=-60.0, format="%.6f")

with col2:
    lat_dest = st.number_input("Lat destino", value=-34.0, format="%.6f")
    lon_dest = st.number_input("Lon destino", value=-58.0, format="%.6f")

nombre_destino = st.text_input("Nombre del destino nuevo")

if st.button("Calcular distancia y agregar"):

    if nombre_destino == "":
        st.warning("Ingresá un nombre para el destino")
    else:
        km_manual = distancia_osrm(lat_campo, lon_campo, lat_dest, lon_dest)

        if km_manual:
            st.success(f"Distancia por ruta: {round(km_manual,1)} km")

            if "destinos_manuales" not in st.session_state:
                st.session_state.destinos_manuales = []

            st.session_state.destinos_manuales.append({
                "Destino": nombre_destino,
                "Km": km_manual
            })
        else:
            st.error("No se pudo calcular la distancia")

# =========================
# Selección destinos
# =========================

destinos_excel = sorted(df_campo["Destino"].unique())

destinos_manual = []
if "destinos_manuales" in st.session_state:
    destinos_manual = [d["Destino"] for d in st.session_state.destinos_manuales]

destinos = st.multiselect(
    "Destinos a comparar",
    options=destinos_excel + destinos_manual
)

# =========================
# Cálculos
# =========================

resultados = []

for destino in destinos:

    # KM desde Excel o manual
    if destino in df_campo["Destino"].values:
        km = float(df_campo[df_campo["Destino"] == destino].iloc[0]["Km"])
    else:
        km = next(
            d["Km"]
            for d in st.session_state["destinos_manuales"]
            if d["Destino"] == destino
        )

    # tarifa por tramo
    importe_ars = buscar_importe_por_km(km, tarifas)

    # flete USD
    flete_usd = importe_ars / tipo_cambio

    # precio neto
    precio_neto = (
        precio
        - flete_usd
        - paritaria
        - secada
        - (precio * comision)
    )

    gasto_comercial = (precio - precio_neto) / precio if precio != 0 else 0

    resultados.append({
        "Destino": destino,
        "Km": round(km, 1),
        "Importe ARS": round(importe_ars, 2),
        "Flete USD": round(flete_usd, 2),
        "Precio Neto": round(precio_neto, 2),
        "Gasto Comercial %": round(gasto_comercial * 100, 2)
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

    best = df_res.iloc[0]

    st.success(
        f"Mejor destino: {best['Destino']} | "
        f"Flete: {best['Flete USD']} USD | "
        f"Precio Neto: {best['Precio Neto']} USD"
    )

    csv = df_res.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "Descargar comparación",
        csv,
        "comparacion_destinos.csv",
        "text/csv"
    )

else:
    st.info("Seleccioná uno o más destinos para comparar.")
