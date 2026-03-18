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
tarifas = tarifas.dropna(subset=["Kilómetros", "Importe"]).sort_values("Kilómetros")

# =========================
# Función tarifas
# =========================

def buscar_importe_por_km(km, tabla_tarifas):
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
        else:
            return None
    except:
        return None

# =========================
# Sidebar global
# =========================

st.sidebar.header("Parámetros base")

tipo_cambio = st.sidebar.number_input("Tipo de cambio (ARS/USD)", value=1380.0)
precio = st.sidebar.number_input("Precio (USD)", value=200.0)

# Valores por defecto (para inicializar destinos)
paritaria_base = st.sidebar.number_input("Paritaria base", value=3.0)
secada_base = st.sidebar.number_input("Secada base", value=4.0)
comision_base_pct = st.sidebar.number_input("Comisión base (%)", value=1.0)

comision_base = comision_base_pct / 100

# =========================
# Selección campo
# =========================

st.title("Simulador logístico")

campos = sorted(df["Campo"].dropna().unique())
campo = st.selectbox("Campo", campos)

df_campo = df[df["Campo"] == campo].copy()

# Coordenadas automáticas
fila_campo = df_campo.iloc[0]
lat_campo = fila_campo["Lat"]
lon_campo = fila_campo["Lon"]

if pd.isna(lat_campo) or pd.isna(lon_campo):
    st.error("⚠️ Este campo no tiene coordenadas")
else:
    st.caption(f"📍 Campo: {round(lat_campo,4)}, {round(lon_campo,4)}")

# =========================
# Destinos base
# =========================

destinos_excel = sorted(df_campo["Destino"].unique())

st.markdown("---")
st.info("👉 Si el destino ya está en la lista, NO cargar manual")

# =========================
# Destino manual
# =========================

st.subheader("➕ Agregar destino nuevo")

col1, col2 = st.columns(2)

with col1:
    lat_dest = st.number_input("Lat destino", value=-34.0, format="%.6f")

with col2:
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
            st.success(f"{round(km_manual,1)} km")

            if "destinos_manuales" not in st.session_state:
                st.session_state.destinos_manuales = []

            st.session_state.destinos_manuales.append({
                "Destino": nombre_destino,
                "Km": km_manual
            })

        else:
            st.error("Error calculando distancia")

# =========================
# Unificar destinos
# =========================

destinos_manual = []
if "destinos_manuales" in st.session_state:
    destinos_manual = [d["Destino"] for d in st.session_state.destinos_manuales]

destinos = st.multiselect(
    "Destinos a comparar",
    options=destinos_excel + destinos_manual
)

# =========================
# PARAMETROS POR DESTINO
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

    with st.expander(f"{destino}", expanded=False):

        c1, c2 = st.columns(2)

        with c1:
            st.session_state.param_destinos[destino]["paritaria"] = st.number_input(
                f"Paritaria",
                value=float(st.session_state.param_destinos[destino]["paritaria"]),
                key=f"paritaria_{destino}"
            )

            st.session_state.param_destinos[destino]["secada"] = st.number_input(
                f"Secada",
                value=float(st.session_state.param_destinos[destino]["secada"]),
                key=f"secada_{destino}"
            )

        with c2:
            comision_pct_dest = st.number_input(
                f"Comisión %",
                value=float(st.session_state.param_destinos[destino]["comision"] * 100),
                key=f"comision_{destino}"
            )

            st.session_state.param_destinos[destino]["comision"] = comision_pct_dest / 100

            st.session_state.param_destinos[destino]["contraflete"] = st.number_input(
                f"Contraflete USD",
                value=float(st.session_state.param_destinos[destino]["contraflete"]),
                key=f"contra_{destino}"
            )

# =========================
# CÁLCULOS
# =========================

resultados = []

for destino in destinos:

    if destino in df_campo["Destino"].values:
        km = float(df_campo[df_campo["Destino"] == destino].iloc[0]["Km"])
    else:
        km = next(
            d["Km"]
            for d in st.session_state["destinos_manuales"]
            if d["Destino"] == destino
        )

    importe_ars = buscar_importe_por_km(km, tarifas)
    flete_usd = importe_ars / tipo_cambio

    params = st.session_state.param_destinos[destino]

    precio_neto = (
        precio
        - flete_usd
        - params["paritaria"]
        - params["secada"]
        - params["contraflete"]
        - (precio * params["comision"])
    )

    gasto_comercial = (precio - precio_neto) / precio if precio != 0 else 0

    resultados.append({
        "Destino": destino,
        "Km": round(km, 1),
        "Flete USD": round(flete_usd, 2),
        "Precio Neto": round(precio_neto, 2),
        "Gasto Comercial %": round(gasto_comercial * 100, 2)
    })

# =========================
# RESULTADOS
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
        f"Precio Neto: {best['Precio Neto']} USD"
    )

else:
    st.info("Seleccioná destinos")
