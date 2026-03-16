import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

# =========================
# Cargar Excel
# =========================

df = pd.read_excel("km_26.xlsx", sheet_name="Hoja1")
tarifas = pd.read_excel("km_26.xlsx", sheet_name="Hoja2")

df.columns = df.columns.str.strip()

# =========================
# Parámetros
# =========================

st.sidebar.header("Parámetros económicos")

tarifa_km = tarifas.iloc[0]["Importe"]

tipo_cambio = st.sidebar.number_input(
    "Tipo de cambio USD",
    value=1000.0
)

precio = st.sidebar.number_input(
    "Precio",
    value=200.0
)

paritaria = st.sidebar.number_input(
    "Paritaria",
    value=3.0
)

secada = st.sidebar.number_input(
    "Secada",
    value=4.0
)

comision = st.sidebar.number_input(
    "Comisión (%)",
    value=1.0
) / 100

# =========================
# Selección campo
# =========================

st.title("Simulador logístico")

campos = sorted(df["Campo"].unique())

campo = st.selectbox(
    "Campo",
    campos
)

df_campo = df[df["Campo"] == campo]

# =========================
# Destino
# =========================

destinos = sorted(df_campo["Destino"].unique())

destino = st.selectbox(
    "Destino",
    destinos
)

row = df_campo[df_campo["Destino"] == destino].iloc[0]

km = row["Km"]
zona = row["Zona"]
localidad = row["Localidad"]

# =========================
# Calcular flete
# =========================

df["flete_calculado"] = df["Km"] * tarifa_km

flete = km * tarifa_km
flete_usd = flete / tipo_cambio

# =========================
# Precio Neto
# =========================

precio_neto = precio - flete - paritaria - secada - (precio * comision)

# =========================
# Gasto comercial
# =========================

gasto_comercial = (precio - precio_neto) / precio

# =========================
# Promedios
# =========================

prom_localidad = df[
    df["Localidad-Destino"] == row["Localidad-Destino"]
]["flete_calculado"].mean()

prom_zona = df[
    df["Zona-Destino"] == row["Zona-Destino"]
]["flete_calculado"].mean()

# =========================
# Resultados
# =========================

col1,col2,col3 = st.columns(3)

col1.metric("Km", round(km,1))
col2.metric("Flete ($)", round(flete,2))
col3.metric("Flete USD", round(flete_usd,2))

st.subheader("Resultado económico")

c1,c2 = st.columns(2)

c1.metric("Precio Neto", round(precio_neto,2))
c2.metric("Gasto Comercial %", round(gasto_comercial*100,2))

# =========================
# Promedios logísticos
# =========================

st.subheader("Comparación logística")

p1,p2 = st.columns(2)

p1.metric(
    "Promedio localidad",
    round(prom_localidad,2)
)

p2.metric(
    "Promedio zona",
    round(prom_zona,2)
)

# =========================
# Tabla resumen
# =========================

st.subheader("Reporte")

resultado = pd.DataFrame({

    "Campo":[campo],
    "Destino":[destino],
    "Km":[km],
    "Flete promedio":[round(flete,2)],
    "Paritaria":[paritaria],
    "Secada":[secada],
    "Comisión":[comision],
    "Precio":[precio],
    "Precio Neto":[round(precio_neto,2)],
    "Gasto Comercial %":[round(gasto_comercial*100,2)]

})

st.dataframe(resultado, use_container_width=True)

# =========================
# Exportar
# =========================

csv = resultado.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "Descargar reporte",
    csv,
    "reporte_logistico.csv",
    "text/csv"
)
