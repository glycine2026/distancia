import streamlit as st
import pandas as pd

st.set_page_config(page_title="Calculadora logística", layout="wide")

# =============================
# Cargar Excel
# =============================

df = pd.read_excel("km_26.xlsx", sheet_name="Hoja1")
tarifas = pd.read_excel("km_26.xlsx", sheet_name="Hoja2")

df.columns = df.columns.str.strip()

# =============================
# Inputs económicos
# =============================

st.sidebar.header("Parámetros")

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

# =============================
# Selección campo
# =============================

st.title("Simulador logístico")

campos = sorted(df["Campo"].dropna().unique())

campo = st.selectbox(
    "Campo",
    campos
)

df_campo = df[df["Campo"] == campo]

# =============================
# Selección destino
# =============================

destinos = sorted(df_campo["Destino"].dropna().unique())

destino = st.selectbox(
    "Destino",
    destinos
)

row = df_campo[df_campo["Destino"] == destino].iloc[0]

km = row["Km"]
zona = row["Zona"]
localidad = row["Localidad"]

# =============================
# Buscar tarifa
# =============================

tarifa = tarifas.iloc[0]["Importe"]

# =============================
# Calcular flete
# =============================

flete = km * tarifa
flete_usd = flete / tipo_cambio

# =============================
# Precio neto
# =============================

precio_neto = precio - flete - paritaria - secada - (comision * precio)

# =============================
# Gasto comercial
# =============================

gasto_comercial = (precio - precio_neto) / precio

# =============================
# Promedios
# =============================

prom_localidad = df[df["Localidad"] == localidad]["Flete promedio"].mean()
prom_zona = df[df["Zona"] == zona]["Flete promedio"].mean()

# =============================
# Resultados
# =============================

col1, col2, col3 = st.columns(3)

col1.metric("Km", round(km,1))
col2.metric("Flete ($)", round(flete,2))
col3.metric("Flete USD", round(flete_usd,2))

st.subheader("Resultado económico")

col4, col5 = st.columns(2)

col4.metric("Precio Neto", round(precio_neto,2))
col5.metric("Gasto Comercial %", round(gasto_comercial*100,2))

# =============================
# Promedios
# =============================

st.subheader("Comparación logística")

c1, c2 = st.columns(2)

c1.metric(
    "Promedio localidad",
    round(prom_localidad,2) if pd.notna(prom_localidad) else "N/A"
)

c2.metric(
    "Promedio zona",
    round(prom_zona,2) if pd.notna(prom_zona) else "N/A"
)

# =============================
# Tabla final tipo Excel
# =============================

st.subheader("Resumen")

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
    "Gasto Comercial":[round(gasto_comercial*100,2)]
})

st.dataframe(resultado, use_container_width=True)

# =============================
# Exportar
# =============================

csv = resultado.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    "Descargar reporte",
    csv,
    "reporte_logistico.csv",
    "text/csv"
)
