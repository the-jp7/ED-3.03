import os
import json
from io import BytesIO

import requests
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# ==========================================
# CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Clima en ciudades del mundo", page_icon="🌦️", layout="wide")

TOKEN_FILE = "token.txt"
JSON_CACHE = "respuesta.json"

AZUL = "#1C4C9A"
GRIS = "#B9C3D1"

CIUDADES = [
    "London,UK", "Paris,FR", "Madrid,ES", "Rome,IT", "Berlin,DE",
    "Tokyo,JP", "New York,US", "Mexico City,MX", "Queretaro,MX", "Sydney,AU",
    "Toronto,CA", "Beijing,CN", "Cairo,EG", "Lima,PE", "Bogota,CO",
]

plt.rcParams["font.sans-serif"] = "Arial"
plt.rcParams["axes.edgecolor"] = GRIS


# ==========================================
# FASE 3: CONSUMO Y VALIDACIÓN DE LA API
# ==========================================
def leer_token() -> str:
    """Lee el token desde un archivo externo al código."""
    if not os.path.exists(TOKEN_FILE):
        st.error(f"No se encontró el archivo '{TOKEN_FILE}'. Crea el archivo con tu API key.")
        st.stop()

    with open(TOKEN_FILE, "r") as f:
        api_key = f.read().strip()

    if not api_key:
        st.error("El token está vacío o incompleto.")
        st.stop()

    return api_key


@st.cache_data(show_spinner="Cargando datos del clima...")
def obtener_datos(api_key: str) -> dict:
    """Devuelve los datos desde la caché local o consulta la API la primera vez."""
    if os.path.exists(JSON_CACHE):
        with open(JSON_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)

    list_data = []
    for city in CIUDADES:
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?q={city}&units=metric&appid={api_key}&lang=es"
        )
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            list_data.append(resp.json())

    if not list_data:
        raise ValueError("No se pudo obtener datos de ninguna ciudad. Revisa tu token.")

    data = {"cnt": len(list_data), "list": list_data}
    with open(JSON_CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return data


# ==========================================
# LIMPIEZA DOCUMENTADA
# ==========================================
@st.cache_data
def construir_dataframe(data: dict) -> pd.DataFrame:
    parsed = []
    for item in data.get("list", []):
        parsed.append({
            "ciudad": item.get("name"),
            "pais": item.get("sys", {}).get("country"),
            "temp": item.get("main", {}).get("temp"),
            "humedad": item.get("main", {}).get("humidity"),
            "presion": item.get("main", {}).get("pressure"),
            "viento": item.get("wind", {}).get("speed"),
        })
    return pd.DataFrame(parsed)


# ==========================================
# UTILIDADES DE GRÁFICAS
# ==========================================
def mostrar_figura(fig, nombre_archivo: str):
    """Muestra la figura en la app y ofrece su descarga en PNG."""
    st.pyplot(fig)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
    st.download_button(
        "⬇️ Descargar PNG",
        data=buf.getvalue(),
        file_name=nombre_archivo,
        mime="image/png",
        key=nombre_archivo,
    )
    plt.close(fig)


# ==========================================
# INTERFAZ
# ==========================================
st.title("🌦️ Clima en ciudades del mundo")
st.caption("Datos de OpenWeatherMap · Fases 3 y 4: consumo de API, limpieza y visualización")

api_key = leer_token()

# Barra lateral
with st.sidebar:
    st.header("Controles")
    if st.button("🔄 Actualizar datos desde la API"):
        if os.path.exists(JSON_CACHE):
            os.remove(JSON_CACHE)
        st.cache_data.clear()
        st.rerun()
    bins = st.slider("Barras del histograma", min_value=5, max_value=25, value=10)

# Carga de datos
try:
    data = obtener_datos(api_key)
except requests.exceptions.RequestException as e:
    st.error(f"Error de conexión: {e}")
    st.stop()
except ValueError as e:
    st.error(str(e))
    st.stop()

df = construir_dataframe(data)

# Informe de limpieza
len_inicial = len(df)
df_clean = df.dropna().copy()
len_final = len(df_clean)

with st.expander("📋 Informe de limpieza de datos", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**1. Tipos de dato al cargar**")
        st.dataframe(df.dtypes.astype(str).rename("tipo"))
    with c2:
        st.markdown("**2. Valores faltantes por columna**")
        st.dataframe(df.isnull().sum().rename("faltantes"))
    st.markdown(
        f"**3. Registros iniciales:** {len_inicial} | "
        f"**Registros utilizables:** {len_final} | "
        f"**Perdidos/incompletos:** {len_inicial - len_final}"
    )

if df_clean.empty:
    st.warning("No hay registros utilizables para graficar.")
    st.stop()

# Filtro por país
with st.sidebar:
    paises = sorted(df_clean["pais"].unique())
    seleccion = st.multiselect("Países", paises, default=paises)

df_clean = df_clean[df_clean["pais"].isin(seleccion)].copy()
if df_clean.empty:
    st.info("Selecciona al menos un país en la barra lateral.")
    st.stop()

# Métricas
m1, m2, m3, m4 = st.columns(4)
m1.metric("Ciudades", len(df_clean))
m2.metric("Temp. media", f"{df_clean['temp'].mean():.1f} °C")
m3.metric("Humedad media", f"{df_clean['humedad'].mean():.0f} %")
m4.metric("Viento medio", f"{df_clean['viento'].mean():.1f} m/s")

with st.expander("Ver tabla de datos"):
    st.dataframe(df_clean, use_container_width=True, hide_index=True)

# ==========================================
# FASE 4: LAS 4 GRÁFICAS
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["Distribución", "Comparación", "Relación", "Categorías"])

# 1. Distribución (Histograma)
with tab1:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(df_clean["temp"], bins=bins, color=AZUL, edgecolor="white")
    ax.set_title("Distribución de las temperaturas urbanas", fontsize=11, fontweight="bold", pad=15)
    ax.set_xlabel("Temperatura (°C)")
    ax.set_ylabel("Número de ciudades")
    ax.grid(axis="y", linestyle="--", alpha=0.5, color=GRIS)
    fig.tight_layout()
    mostrar_figura(fig, "grafica_1_distribucion.png")

# 2. Comparación (Barras)
with tab2:
    top_paises = df_clean.groupby("pais")["viento"].mean().nlargest(10).reset_index()
    n = len(top_paises)
    colores = [GRIS] * (n - 1) + [AZUL]  # el valor más alto queda resaltado

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top_paises["pais"][::-1], top_paises["viento"][::-1], color=colores)
    ax.set_title("Países con mayor velocidad promedio de viento", fontsize=11, fontweight="bold", pad=15)
    ax.set_xlabel("Velocidad media del viento (m/s)")
    ax.set_ylabel("País (Código ISO)")
    ax.grid(axis="x", linestyle="--", alpha=0.5, color=GRIS)
    fig.tight_layout()
    mostrar_figura(fig, "grafica_2_comparacion.png")

# 3. Relación (Dispersión)
with tab3:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(df_clean["temp"], df_clean["humedad"], color=AZUL, alpha=0.6)
    ax.set_title("Relación entre temperatura y humedad", fontsize=11, fontweight="bold", pad=15)
    ax.set_xlabel("Temperatura (°C)")
    ax.set_ylabel("Humedad (%)")
    ax.grid(True, linestyle="--", alpha=0.5, color=GRIS)
    fig.tight_layout()
    mostrar_figura(fig, "grafica_3_relacion.png")

# 4. Categorías
with tab4:
    if len(df_clean) < 4:
        st.info("Se necesitan al menos 4 ciudades para dividir el viento en 4 categorías.")
    else:
        # rank(method="first") evita errores de qcut por valores repetidos
        df_clean["rango_viento"] = pd.qcut(
            df_clean["viento"].rank(method="first"),
            q=4,
            labels=["Calma", "Bajo", "Moderado", "Alto"],
        )
        presion_viento = (
            df_clean.groupby("rango_viento", observed=False)["presion"].mean().reset_index()
        )

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(
            presion_viento["rango_viento"].astype(str),
            presion_viento["presion"],
            marker="o", color=AZUL, linewidth=2.5,
        )
        ax.set_title("Presión atmosférica según la categoría de viento", fontsize=11, fontweight="bold", pad=15)
        ax.set_xlabel("Categoría de intensidad de viento")
        ax.set_ylabel("Presión atmosférica promedio (hPa)")
        ax.grid(True, linestyle="--", alpha=0.5, color=GRIS)
        fig.tight_layout()
        mostrar_figura(fig, "grafica_4_evolucion.png")