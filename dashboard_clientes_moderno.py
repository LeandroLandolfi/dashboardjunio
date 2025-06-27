
import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import plotly.express as px
import os

st.set_page_config(layout="wide", page_title="Dashboard de Clientes", page_icon="📊")

st.markdown("<h1 style='text-align: center;'>📊 Dashboard de Clientes y Ventas</h1>", unsafe_allow_html=True)
st.write("---")

# Buscar archivo de datos
archivo = None
for nombre in ["clientes.xlsx", "clientes.csv"]:
    if os.path.exists(nombre):
        archivo = nombre
        break

if not archivo:
    st.error("❌ No se encontró el archivo 'clientes.xlsx' o 'clientes.csv' en esta carpeta.")
    st.stop()

# Leer datos
df = pd.read_excel(archivo) if archivo.endswith(".xlsx") else pd.read_csv(archivo)
df["Direccion completa"] = df["Cód. Postal de entrega"].astype(str) + ", " + df["Localidad"] + ", " + df["Provincia"] + ", Argentina"

# Geolocalizar si es necesario
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
st.sidebar.header("🎛️ Filtros")
provincias = st.sidebar.multiselect("Provincia", sorted(df["Provincia"].dropna().unique()))
grupos = st.sidebar.multiselect("Grupo económico", sorted(df["Grupo económico"].dropna().unique()))
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

# KPIs
col1, col2, col3 = st.columns(3)
col1.metric("🧍‍♂️ Total clientes", f"{len(df_filtrado):,}")
col2.metric("💰 Total ventas (USD)", f"${df_filtrado['Ventas Netas (USD)'].sum():,.0f}")
col3.metric("📦 Promedio por cliente", f"${df_filtrado['Ventas Netas (USD)'].mean():,.0f}")

st.write("---")

# Mapa
st.subheader("🗺️ Mapa de clientes")

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

st.write("---")

# Gráficos
st.subheader("📈 Análisis de ventas")

col4, col5 = st.columns(2)

with col4:
    ventas_por_prov = df_filtrado.groupby("Provincia")["Ventas Netas (USD)"].sum().reset_index()
    fig1 = px.bar(ventas_por_prov, x="Ventas Netas (USD)", y="Provincia", orientation="h",
                  title="Ventas por provincia", height=400)
    st.plotly_chart(fig1, use_container_width=True)

with col5:
    top_clientes = df_filtrado.sort_values(by="Ventas Netas (USD)", ascending=False).head(10)
    fig2 = px.bar(top_clientes, x="Ventas Netas (USD)", y="Cliente", orientation="h",
                  title="Top 10 clientes", height=400)
    st.plotly_chart(fig2, use_container_width=True)

# Tabla final
st.subheader("📋 Detalle de clientes")
st.dataframe(df_filtrado[["Cliente", "Provincia", "Localidad", "Ventas Netas (USD)", "Grupo económico"]], use_container_width=True)
