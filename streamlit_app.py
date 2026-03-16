import streamlit as st
import pandas as pd

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
# Función para buscar tarifa
# =========================

def buscar_importe_por_km(km: float, tabla_tarifas: pd.DataFrame) -> float:
    """
    Busca el Importe correspondiente a la distancia.
    Toma la fila con 'Kilómetros' menor o igual al km consultado.
    Si el km es menor que el mínimo, toma la primera tarifa.
    """
    fila = tabla_tarifas[tabla_tarifas["Kilómetros"] <= km]

    if fila.empty:
        return float(tabla_tarifas.iloc[0]["Importe"])

    return float(fila.iloc[-1]["Importe"])

# =========================
# Sidebar parámetros
# =========================

st.sidebar.header("Parámetros económicos")

tipo_cambio = st.sidebar.number_input(
    "Tipo de cambio (ARS/USD)",
    min_value=1.0,
    value=1380.0,
    step=1.0
)

precio = st.sidebar.number_input(
    "Precio (USD)",
    min_value=0.0,
    value=200.0,
    step=1.0
)

paritaria = st.sidebar.number_input(
    "Paritaria (USD)",
    min_value=0.0,
    value=3.0,
    step=0.5
)

secada = st.sidebar.number_input(
    "Secada (USD)",
    min_value=0.0,
    value=4.0,
    step=0.5
)

comision_pct = st.sidebar.number_input(
    "Comisión (%)",
    value=1.0,
    step=0.1
)

comision = comision_pct / 100

# =========================
# Selección campo
# =========================

st.title("Simulador logístico")

campos = sorted(df["Campo"].dropna().unique().tolist())

campo = st.selectbox("Campo", campos)

df_campo = df[df["Campo"] == campo].copy()

# =========================
# Selección destinos
# =========================

destinos_disponibles = sorted(df_campo["Destino"].dropna().unique().tolist())

destinos = st.multiselect(
    "Destinos a comparar",
    options=destinos_disponibles
)

# =========================
# Cálculos
# =========================

resultados = []

for destino in destinos:
    row = df_campo[df_campo["Destino"] == destino].iloc[0]

    km = float(row["Km"])

    # Buscar el importe correcto según la distancia
    importe_ars = buscar_importe_por_km(km, tarifas)

    # Convertir a USD con el tipo de cambio elegido
    flete_usd = importe_ars / tipo_cambio

    # Precio neto: Precio - Flete - Paritaria - Secada - (Precio * Comisión)
    precio_neto = (
        precio
        - flete_usd
        - paritaria
        - secada
        - (precio * comision)
    )

    # Gasto comercial = (Precio - Precio Neto) / Precio
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

    # Mejor destino = mayor precio neto
    df_res = df_res.sort_values("Precio Neto", ascending=False).reset_index(drop=True)

    mejor_precio_neto = df_res.loc[0, "Precio Neto"]
    df_res["Ahorro vs mejor USD"] = (mejor_precio_neto - df_res["Precio Neto"]).round(2)

    st.subheader("Comparación de destinos")

    st.dataframe(df_res, use_container_width=True, hide_index=True)

    mejor = df_res.iloc[0]

    st.success(
        f"Mejor destino: {mejor['Destino']} | "
        f"Flete: {mejor['Flete USD']} USD | "
        f"Precio Neto: {mejor['Precio Neto']} USD"
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
