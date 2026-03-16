import streamlit as st
import pandas as pd

st.set_page_config(page_title="Simulador logístico", layout="wide")

# =========================
# Cargar Excel
# =========================

df = pd.read_excel("km_26.xlsx", sheet_name="Hoja1")
tarifas = pd.read_excel("km_26.xlsx", sheet_name="Hoja2")

# limpiar nombres columnas
df.columns = df.columns.str.strip()
tarifas.columns = tarifas.columns.str.strip()

# ordenar tarifas por km
tarifas = tarifas.sort_values("Kilómetros")

# =========================
# Parámetros económicos
# =========================

st.sidebar.header("Parámetros económicos")

precio = st.sidebar.number_input("Precio (USD)", value=200.0)

paritaria = st.sidebar.number_input("Paritaria (USD)", value=3.0)

secada = st.sidebar.number_input("Secada (USD)", value=4.0)

comision = st.sidebar.number_input("Comisión (%)", value=1.0) / 100

# =========================
# Selección campo
# =========================

st.title("Simulador logístico")

campo = st.selectbox(
    "Campo",
    sorted(df["Campo"].unique())
)

df_campo = df[df["Campo"] == campo]

# =========================
# Selección destinos
# =========================

destinos = st.multiselect(
    "Destinos a comparar",
    sorted(df_campo["Destino"].unique())
)

resultados = []

# =========================
# Cálculos
# =========================

for destino in destinos:

    row = df_campo[df_campo["Destino"] == destino].iloc[0]

    km = row["Km"]

    # buscar tarifa según distancia
    tarifa_row = tarifas[tarifas["Kilómetros"] <= km].iloc[-1]

    flete_usd = tarifa_row["Importe"]

    # cálculo económico
    precio_neto = (
        precio
        - flete_usd
        - paritaria
        - secada
        - (precio * comision)
    )

    gasto_comercial = (precio - precio_neto) / precio

    resultados.append({
        "Destino": destino,
        "Km": km,
        "Flete USD": round(flete_usd,2),
        "Precio Neto": round(precio_neto,2),
        "Gasto Comercial %": round(gasto_comercial*100,2)
    })

# =========================
# Resultados
# =========================

if resultados:

    df_res = pd.DataFrame(resultados)

    # ranking
    df_res = df_res.sort_values("Precio Neto", ascending=False)

    mejor_precio = df_res.iloc[0]["Precio Neto"]

    df_res["Ahorro vs mejor USD"] = (
        df_res["Precio Neto"] - mejor_precio
    )

    st.subheader("Comparación de destinos")

    st.dataframe(df_res, use_container_width=True)

    mejor = df_res.iloc[0]

    st.success(
        f"Mejor destino: {mejor['Destino']} | Precio Neto: {mejor['Precio Neto']} USD"
    )

    # descarga
    csv = df_res.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "Descargar comparación",
        csv,
        "comparacion_destinos.csv",
        "text/csv"
    )
