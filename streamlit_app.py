import time
import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Simulador logístico", layout="wide")

# =========================
# Cargar Excel
# =========================
@st.cache_data
def cargar_datos():
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

    return df, tarifas


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
@st.cache_data(ttl=86400, show_spinner=False)
def distancia_osrm(lat1, lon1, lat2, lon2):
    url = (
        f"https://router.project-osrm.org/route/v1/driving/"
        f"{lon1},{lat1};{lon2},{lat2}?overview=false"
    )

    for intento in range(3):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "routes" in data and len(data["routes"]) > 0:
                return data["routes"][0]["distance"] / 1000

            return None

        except requests.exceptions.Timeout:
            if intento < 2:
                time.sleep(2)
            else:
                return None

        except requests.exceptions.RequestException:
            return None

        except Exception:
            return None

    return None


# =========================
# Carga inicial
# =========================
try:
    df, tarifas = cargar_datos()
except Exception as e:
    st.error(f"Error cargando el archivo Excel: {e}")
    st.stop()


# =========================
# Session state
# =========================
if "destinos_manuales" not in st.session_state:
    st.session_state.destinos_manuales = []

if "param_destinos" not in st.session_state:
    st.session_state.param_destinos = {}

if "resultados" not in st.session_state:
    st.session_state.resultados = None


# =========================
# Sidebar
# =========================
st.sidebar.header("Parámetros económicos")

tipo_cambio = st.sidebar.number_input("Tipo de cambio (ARS/USD)", value=1380.0)
precio = st.sidebar.number_input("Precio (USD)", value=200.0)

catac = st.sidebar.selectbox(
    "Escala CATAC",
    options=sorted(tarifas["CATAC"].dropna().unique())
)

tipo_catac = st.sidebar.radio(
    "Tipo de tarifa",
    ["CATAC llena", "CATAC con descuento"]
)

if tipo_catac == "CATAC con descuento":
    descuento_pct = st.sidebar.number_input("Descuento (%)", value=8.0)
else:
    descuento_pct = 0.0

st.sidebar.caption(f"CATAC seleccionada: {catac}")

paritaria_base = st.sidebar.number_input("Paritaria base", value=3.0)
secada_base = st.sidebar.number_input("Secada base", value=4.0)
comision_base_pct = st.sidebar.number_input("Comisión base (%)", value=1.0)

comision_base = comision_base_pct / 100


# =========================
# Selección campo
# =========================
st.title("Simulador logístico")

campos_disponibles = sorted(df["Campo"].dropna().unique())
campo = st.selectbox("Campo", campos_disponibles)

df_campo = df[df["Campo"] == campo]

if df_campo.empty:
    st.error("No se encontraron datos para el campo seleccionado.")
    st.stop()

fila_campo = df_campo.iloc[0]
lat_campo = fila_campo["Lat"]
lon_campo = fila_campo["Lon"]

if pd.isna(lat_campo) or pd.isna(lon_campo):
    st.error("⚠️ Campo sin coordenadas")
    st.stop()
else:
    st.caption(f"📍 Campo: {round(lat_campo, 4)}, {round(lon_campo, 4)}")


# =========================
# Destinos existentes
# =========================
destinos_excel = sorted(df_campo["Destino"].dropna().unique())

st.markdown("---")
st.info("👉 Si el destino ya está en la lista, no cargar manualmente")


# =========================
# Agregar destino nuevo
# =========================
st.subheader("➕ Agregar destino nuevo")

with st.form("form_destino_manual"):
    lat_dest = st.number_input("Lat destino", value=-34.0, format="%.6f")
    lon_dest = st.number_input("Lon destino", value=-58.0, format="%.6f")
    nombre_destino = st.text_input("Nombre del destino")
    agregar_destino = st.form_submit_button("Agregar destino")

if agregar_destino:
    nombre_limpio = nombre_destino.strip()

    nombres_existentes = destinos_excel + [
        d["Destino"] for d in st.session_state.destinos_manuales
    ]

    if nombre_limpio == "":
        st.warning("Ingresá un nombre")
    elif nombre_limpio in nombres_existentes:
        st.warning("Ese destino ya existe")
    else:
        with st.spinner("Calculando distancia..."):
            km_manual = distancia_osrm(lat_campo, lon_campo, lat_dest, lon_dest)

        if km_manual is not None:
            st.session_state.destinos_manuales.append({
                "Destino": nombre_limpio,
                "Km": km_manual
            })
            st.success(f"Destino agregado: {round(km_manual, 1)} km")
        else:
            st.error("No se pudo calcular la distancia")


# =========================
# Unificar destinos
# =========================
destinos_manual = [d["Destino"] for d in st.session_state.destinos_manuales]

destinos = st.multiselect(
    "Destinos a comparar",
    options=destinos_excel + destinos_manual
)


# =========================
# Parámetros por destino
# =========================
st.markdown("### ⚙️ Configuración por destino")

for destino in destinos:
    if destino not in st.session_state.param_destinos:
        st.session_state.param_destinos[destino] = {
            "precio":       float(precio),
            "paritaria":    float(paritaria_base),
            "secada":       float(secada_base),
            "comision":     float(comision_base),
            "flete_manual": 0.0,
            "contraflete":  0.0
        }
    else:
        if "precio" not in st.session_state.param_destinos[destino]:
            st.session_state.param_destinos[destino]["precio"] = float(precio)
        if "flete_manual" not in st.session_state.param_destinos[destino]:
            st.session_state.param_destinos[destino]["flete_manual"] = 0.0

    p = st.session_state.param_destinos[destino]

    if f"pr_{destino}" not in st.session_state:
        st.session_state[f"pr_{destino}"] = float(p["precio"])
    if f"p_{destino}" not in st.session_state:
        st.session_state[f"p_{destino}"] = float(p["paritaria"])
    if f"s_{destino}" not in st.session_state:
        st.session_state[f"s_{destino}"] = float(p["secada"])
    if f"c_{destino}" not in st.session_state:
        st.session_state[f"c_{destino}"] = float(p["comision"] * 100)
    if f"fm_{destino}" not in st.session_state:
        st.session_state[f"fm_{destino}"] = float(p["flete_manual"])
    if f"cf_{destino}" not in st.session_state:
        st.session_state[f"cf_{destino}"] = float(p["contraflete"])

    with st.expander(destino):
        st.number_input("Precio USD",        key=f"pr_{destino}")
        st.number_input("Paritaria",         key=f"p_{destino}")
        st.number_input("Secada",            key=f"s_{destino}")
        st.number_input("Comisión %",        key=f"c_{destino}")
        st.number_input("Flete manual USD",  key=f"fm_{destino}")
        st.number_input("Contraflete USD",   key=f"cf_{destino}")


# =========================
# Cálculo
# =========================
st.markdown("---")
calcular = st.button("Calcular comparación", type="primary")

if calcular:
    if not destinos:
        st.warning("Seleccioná al menos un destino.")
    else:
        tarifas_filtradas = tarifas[tarifas["CATAC"] == catac]

        resultados = []

        for destino in destinos:

            if destino in df_campo["Destino"].values:
                km = float(df_campo[df_campo["Destino"] == destino].iloc[0]["Km"])
            else:
                km = next(d["Km"] for d in st.session_state.destinos_manuales if d["Destino"] == destino)

            importe_ars = buscar_importe_por_km(km, tarifas_filtradas)

            if tipo_catac == "CATAC con descuento":
                importe_ars *= (1 - descuento_pct / 100)

            flete_catac_usd = importe_ars / tipo_cambio

            precio_dest       = float(st.session_state[f"pr_{destino}"])
            paritaria_dest    = float(st.session_state[f"p_{destino}"])
            secada_dest       = float(st.session_state[f"s_{destino}"])
            comision_dest     = float(st.session_state[f"c_{destino}"]) / 100
            flete_manual_dest = float(st.session_state[f"fm_{destino}"])
            contraflete_dest  = float(st.session_state[f"cf_{destino}"])

            comision_usd    = precio_dest * comision_dest
            flete_total_usd = flete_catac_usd + flete_manual_dest + contraflete_dest

            precio_neto = (
                precio_dest
                - flete_total_usd
                - paritaria_dest
                - secada_dest
                - comision_usd
            )

            if precio_dest != 0:
                gasto_comercial = (precio_dest - precio_neto) / precio_dest
            else:
                gasto_comercial = 0

            resultados.append({
                "Destino":           destino,
                "Km":                round(km, 1),
                "Precio USD":        round(precio_dest, 2),
                "Flete CATAC USD":   round(flete_catac_usd, 2),
                "Flete Manual USD":  round(flete_manual_dest, 2),
                "Contraflete USD":   round(contraflete_dest, 2),
                "Flete Total USD":   round(flete_total_usd, 2),
                "Paritaria":         round(paritaria_dest, 2),
                "Secada":            round(secada_dest, 2),
                "Comisión USD":      round(comision_usd, 2),
                "Precio Neto":       round(precio_neto, 2),
                "Gasto Comercial %": round(gasto_comercial * 100, 2)
            })

        df_res = pd.DataFrame(resultados)
        df_res = df_res.sort_values("Precio Neto", ascending=False).reset_index(drop=True)

        mejor = df_res.iloc[0]["Precio Neto"]
        df_res["Ahorro vs mejor USD"] = (mejor - df_res["Precio Neto"]).round(2)

        st.session_state.resultados = df_res


# =========================
# Mostrar resultados
# =========================
if st.session_state.resultados is not None:
    df_res = st.session_state.resultados

    st.subheader("Comparación de destinos")
    st.dataframe(df_res, use_container_width=True, hide_index=True)

    if not df_res.empty:
        st.success(f"Mejor destino: {df_res.iloc[0]['Destino']}")
