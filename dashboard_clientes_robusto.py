
import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import plotly.express as px
import os

st.set_page_config(layout="wide")
st.title("📊 Dashboard de Clientes y Ventas")

# Buscar archivo
archivo = None
for nombre in ["clientes.xlsx", "clientes.csv"]:
    if os.path.exists(nombre):
        archivo = nombre
        break

if not archivo:
    st.error("❌ No se encontró el archivo 'clientes.xlsx' o 'clientes.csv' en esta carpeta.")
    st.stop()

# Leer archivo
if archivo.endswith(".xlsx"):
    df = pd.read_excel(archivo)
else:
    df = pd.read_csv(archivo)

# Dirección para geolocalización
df["Direccion completa"] = df["Cód. Postal de entrega"].astype(str) + ", " + df["Localidad"] + ", " + df["Provincia"] + ", Argentina"

# Verificar y generar coordenadas si faltan
if "Latitud" not in df.columns or "Longitud" not in df.columns:
    with st.spinner("🌍 Geolocalizando direcciones..."):
        geolocator = Nominatim(user_agent="dashboard_clientes")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        coords = df["Direccion completa"].apply(lambda x: geocode(x) if pd.notnull(x) else None)
        df["Latitud"] = coords.apply(lambda loc: loc.latitude if loc else None)
        df["Longitud"] = coords.apply(lambda loc: loc.longitude if loc else None)
        df.to_excel("clientes_geolocalizados.xlsx", index=False)
        st.success("✅ Coordenadas generadas y guardadas en 'clientes_geolocalizados.xlsx'")

# Sidebar filtros
st.sidebar.header("Filtros")
provincias = st.sidebar.multiselect("Provincia", options=sorted(df["Provincia"].dropna().unique()))
grupos = st.sidebar.multiselect("Grupo económico", options=sorted(df["Grupo económico"].dropna().unique()))
ventas_min, ventas_max = int(df["Ventas Netas (USD)"].min()), int(df["Ventas Netas (USD)"].max())
rango_ventas = st.sidebar.slider("Rango de ventas (USD)", ventas_min, ventas_max, (ventas_min, ventas_max))

# Aplicar filtros
df_filtrado = df.copy()
if provincias:
    df_filtrado = df_filtrado[df_filtrado["Provincia"].isin(provincias)]
if grupos:
    df_filtrado = df_filtrado[df_filtrado["Grupo económico"].isin(grupos)]
df_filtrado = df_filtrado[
    (df_filtrado["Ventas Netas (USD)"] >= rango_ventas[0]) &
    (df_filtrado["Ventas Netas (USD)"] <= rango_ventas[1])
]

st.markdown(f"Clientes encontrados: **{len(df_filtrado)}**")

# Mapa
st.subheader("🌎 Mapa de clientes")

mapa = folium.Map(location=[-38.5, -63.6], zoom_start=5)
cluster = MarkerCluster().add_to(mapa)

def color_por_ventas(usd):
    if usd > 500_000:
        return "red"
    elif usd > 200_000:
        return "orange"
    return "green"

for _, row in df_filtrado.dropna(subset=["Latitud", "Longitud"]).iterrows():
    color = color_por_ventas(row["Ventas Netas (USD)"])
    popup = f"{row['Cliente']}<br>Ventas USD: ${row['Ventas Netas (USD)']:,}"
    folium.CircleMarker(
        location=[row["Latitud"], row["Longitud"]],
        radius=6,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8,
        popup=popup,
        tooltip=row["Cliente"]
    ).add_to(cluster)

folium_static(mapa, width=1000, height=500)

# Gráficos
col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 Ventas por provincia")
    ventas_por_prov = df_filtrado.groupby("Provincia")["Ventas Netas (USD)"].sum().reset_index()
    fig1 = px.bar(ventas_por_prov, x="Ventas Netas (USD)", y="Provincia", orientation="h", title="Ventas por provincia")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("🏆 Top 10 clientes")
    top_clientes = df_filtrado.sort_values(by="Ventas Netas (USD)", ascending=False).head(10)
    fig2 = px.bar(top_clientes, x="Ventas Netas (USD)", y="Cliente", orientation="h", title="Top 10 clientes")
    st.plotly_chart(fig2, use_container_width=True)

# Tabla
st.subheader("📋 Detalle de clientes")
st.dataframe(df_filtrado[["Cliente", "Provincia", "Localidad", "Ventas Netas (USD)", "Grupo económico"]])
