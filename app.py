import streamlit as st
import math
import re
from streamlit_folium import st_folium
import folium

# --- MOTOR MATEMÁTICO GEODÉSICO (PARÁMETROS OFICIALES VENEZUELA) ---
class Geodesia:
    # Elipsoides
    HAYFORD = {'a': 6378388.0, 'e2': 0.006722670022} # PSAD56
    GRS80   = {'a': 6378137.0, 'e2': 0.006694380023}   # REGVEN / WGS84

    # Parámetros de transformación Molodensky-Badekas (PATVEN)
    # Fuente: Cartografía Nacional / IGVSB
    DX, DY, DZ = -270.933, 115.599, -360.226
    RX, RY, RZ = math.radians(-5.266/3600), math.radians(-1.238/3600), math.radians(2.381/3600)
    DS = -5.109 * 1e-6
    XM, YM, ZM = 2464351.59, -5783466.61, 974809.81

    @staticmethod
    def limpiar_coord(dato, tipo):
        """Convierte entradas GMS o decimales a formato numérico puro."""
        try:
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(dato))
            if len(nums) >= 3:
                dd = float(nums[0]) + float(nums[1])/60 + float(nums[2])/3600
            else:
                dd = float(nums[0])
            # Forzar hemisferio de Venezuela (Norte + / Oeste -)
            return abs(dd) if tipo == 'LAT' else -abs(dd)
        except: return None

    @classmethod
    def transformar(cls, lat, lon, h, inverso=False):
        """Transforma entre La Canoa y REGVEN usando Molodensky-Badekas."""
        orig = cls.HAYFORD if not inverso else cls.GRS80
        l_r, n_r = math.radians(lat), math.radians(lon)
        
        # Geodésicas a Cartesianas
        N = orig['a'] / math.sqrt(1 - orig['e2'] * math.sin(l_r)**2)
        X = (N + h) * math.cos(l_r) * math.cos(n_r)
        Y = (N + h) * math.cos(l_r) * math.sin(n_r)
        Z = (N * (1 - orig['e2']) + h) * math.sin(l_r)

        # Aplicar rotación y traslación
        s = -1 if inverso else 1
        dx_c, dy_c, dz_c = X - cls.XM, Y - cls.YM, Z - cls.ZM
        X_o = X + (s*cls.DX) + (s*(cls.DS*dx_c - cls.RZ*dy_c + cls.RY*dz_c))
        Y_o = Y + (s*cls.DY) + (s*(cls.RZ*dx_c + cls.DS*dy_c - cls.RX*dz_c))
        Z_o = Z + (s*cls.DZ) + (s*(-cls.RY*dx_c + cls.RX*dy_c + cls.DS*dz_c))

        # Cartesianas a Geodésicas (Iterativo)
        dest = cls.GRS80 if not inverso else cls.HAYFORD
        p = math.sqrt(X_o**2 + Y_o**2)
        lon_f = math.degrees(math.atan2(Y_o, X_o))
        lat_f = math.atan2(Z_o, p * (1 - dest['e2']))
        for _ in range(5):
            N_f = dest['a'] / math.sqrt(1 - dest['e2'] * math.sin(lat_f)**2)
            h_f = p / math.cos(lat_f) - N_f
            lat_f = math.atan2(Z_o, p * (1 - dest['e2'] * (N_f / (N_f + h_f))))
        return math.degrees(lat_f), lon_f, h_f

    @classmethod
    def a_utm(cls, lat, lon):
        """Proyección Transversa de Mercator (WGS84)."""
        zone = math.floor((lon + 180) / 6) + 1
        lon0 = (zone - 1) * 6 - 180 + 3
        l_r, n_r, n0_r = math.radians(lat), math.radians(lon), math.radians(lon0)
        a, e2 = cls.GRS80['a'], cls.GRS80['e2']
        k0 = 0.9996
        N = a / math.sqrt(1 - e2 * math.sin(l_r)**2)
        T, A = math.tan(l_r)**2, (n_r - n0_r) * math.cos(l_r)
        M = a * ((1 - e2/4 - 3*e2**2/64) * l_r - (3*e2/8 + 3*e2**2/32) * math.sin(2*l_r))
        E = 500000 + k0 * N * (A + (1-T)*A**3/6)
        Nort = k0 * (M + N * math.tan(l_r) * (A**2/2))
        return E, Nort, zone

# --- INTERFAZ DE USUARIO (STREAMLIT) ---
st.set_page_config(page_title="GeoVZLA Pro", page_icon="📍", layout="wide")

# Inicializar memoria de sesión
if 'mapa_lat' not in st.session_state:
    st.session_state.mapa_lat = None
    st.session_state.mapa_lon = None
    st.session_state.res_text = ""
    st.session_state.res_tipo = "success"

st.title("🇻🇪 GeoVZLA Pro")
st.markdown("#### Calculadora Geodésica de Precisión - Sistema PATVEN")

with st.sidebar:
    st.header("Configuración")
    menu = st.selectbox("Seleccione la Operación:", 
        ["GPS/Google (WGS84) -> La Canoa", 
         "La Canoa (PSAD56) -> GPS/Google", 
         "GPS/Google -> UTM (Metros)", 
         "La Canoa -> UTM (Metros)"])
    st.info("Nota: Los cálculos de UTM se basan en el elipsoide GRS80 (SIRGAS-REGVEN).")

# Entrada de datos
col1, col2, col3 = st.columns(3)
with col1: lat_in = st.text_input("Latitud (N)", "10.4806")
with col2: lon_in = st.text_input("Longitud (W)", "-66.9036")
with col3: alt_in = st.number_input("Altura Elipsoidal (m)", value=0.0)

if st.button("CALCULAR Y UBICAR EN MAPA"):
    lt = Geodesia.limpiar_coord(lat_in, 'LAT')
    ln = Geodesia.limpiar_coord(lon_in, 'LON')
    
    if lt and ln:
        if menu == "GPS/Google (WGS84) -> La Canoa":
            r_lat, r_lon, _ = Geodesia.transformar(lt, ln, alt_in, inverso=True)
            st.session_state.mapa_lat, st.session_state.mapa_lon = lt, ln # Ya es WGS84
            st.session_state.res_text = f"📍 Coordenadas en La Canoa (PSAD56): {r_lat:.8f}°, {r_lon:.8f}°"
            st.session_state.res_tipo = "success"
            
        elif menu == "La Canoa (PSAD56) -> GPS/Google":
            r_lat, r_lon, _ = Geodesia.transformar(lt, ln, alt_in, inverso=False)
            st.session_state.mapa_lat, st.session_state.mapa_lon = r_lat, r_lon # El resultado es WGS84
            st.session_state.res_text = f"📍 Coordenadas REGVEN (WGS84): {r_lat:.8f}°, {r_lon:.8f}°"
            st.session_state.res_tipo = "success"
            
        elif menu == "GPS/Google -> UTM (Metros)":
            e, n, z = Geodesia.a_utm(lt, ln)
            st.session_state.mapa_lat, st.session_state.mapa_lon = lt, ln
            st.session_state.res_text = f"📐 UTM Zona {z}N | Este: {e:,.3f} m | Norte: {n:,.3f} m"
            st.session_state.res_tipo = "info"
            
        elif menu == "La Canoa -> UTM (Metros)":
            m_lat, m_lon, _ = Geodesia.transformar(lt, ln, alt_in, inverso=False)
            e, n, z = Geodesia.a_utm(m_lat, m_lon)
            st.session_state.mapa_lat, st.session_state.mapa_lon = m_lat, m_lon # Punto corregido para mapa
            st.session_state.res_text = f"📐 UTM (SIRGAS) Zona {z}N | Este: {e:,.3f} m | Norte: {n:,.3f} m"
            st.session_state.res_tipo = "info"
    else:
        st.error("Error en formato de coordenadas.")

# Visualización de Resultados y Mapa
if st.session_state.mapa_lat:
    st.divider()
    if st.session_state.res_tipo == "success": st.success(st.session_state.res_text)
    else: st.info(st.session_state.res_text)

    # Mapa Folium
    m = folium.Map(location=[st.session_state.mapa_lat, st.session_state.mapa_lon], zoom_start=17)
    
    # Capa Satelital de Google
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        attr='Google Satellite', name='Satélite', overlay=False, control=True
    ).add_to(m)

    # Marcador Preciso
    folium.Marker(
        [st.session_state.mapa_lat, st.session_state.mapa_lon],
        tooltip="Punto Geodésico",
        icon=folium.Icon(color='red', icon='crosshairs', prefix='fa')
    ).add_to(m)

    st_folium(m, width="100%", height=500, returned_objects=[])

st.caption("GeoVZLA Pro | Implementación de modelos de transformación Molodensky-Badekas para Venezuela.")
