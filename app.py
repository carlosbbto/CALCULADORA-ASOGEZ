import streamlit as st
import math
import re

# --- LÓGICA GEODÉSICA ---
class Geodesia:
    HAYFORD = {'a': 6378388.0, 'e2': 0.006722670022} 
    GRS80   = {'a': 6378137.0, 'e2': 0.006694380023}   
    DX, DY, DZ = -270.933, 115.599, -360.226
    RX, RY, RZ = math.radians(-5.266/3600), math.radians(-1.238/3600), math.radians(2.381/3600)
    DS = -5.109 * 1e-6
    XM, YM, ZM = 2464351.59, -5783466.61, 974809.81

    @staticmethod
    def limpiar_coord(dato, tipo):
        try:
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(dato))
            if len(nums) >= 3:
                dd = float(nums[0]) + float(nums[1])/60 + float(nums[2])/3600
            else:
                dd = float(nums[0])
            return abs(dd) if tipo == 'LAT' else -abs(dd)
        except: return None

    @classmethod
    def transformar(cls, lat, lon, h, inverso=False):
        orig = cls.HAYFORD if not inverso else cls.GRS80
        l_r, n_r = math.radians(lat), math.radians(lon)
        N = orig['a'] / math.sqrt(1 - orig['e2'] * math.sin(l_r)**2)
        X = (N + h) * math.cos(l_r) * math.cos(n_r)
        Y = (N + h) * math.cos(l_r) * math.sin(n_r)
        Z = (N * (1 - orig['e2']) + h) * math.sin(l_r)
        s = -1 if inverso else 1
        dx_c, dy_c, dz_c = X - cls.XM, Y - cls.YM, Z - cls.ZM
        X_o = X + (s*cls.DX) + (s*(cls.DS*dx_c - cls.RZ*dy_c + cls.RY*dz_c))
        Y_o = Y + (s*cls.DY) + (s*(cls.RZ*dx_c + cls.DS*dy_c - cls.RX*dz_c))
        Z_o = Z + (s*cls.DZ) + (s*(-cls.RY*dx_c + cls.RX*dy_c + cls.DS*dz_c))
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
        zone = math.floor((lon + 180) / 6) + 1
        lon0 = (zone - 1) * 6 - 180 + 3
        l_r, n_r, n0_r = math.radians(lat), math.radians(lon), math.radians(lon0)
        a, e2 = cls.GRS80['a'], cls.GRS80['e2']
        k0 = 0.9996
        N = a / math.sqrt(1 - e2 * math.sin(l_r)**2)
        T, C, A = math.tan(l_r)**2, (e2/(1-e2)) * math.cos(l_r)**2, (n_r - n0_r) * math.cos(l_r)
        M = a * ((1 - e2/4 - 3*e2**2/64) * l_r - (3*e2/8 + 3*e2**2/32) * math.sin(2*l_r))
        E = 500000 + k0 * N * (A + (1-T+C)*A**3/6)
        Nort = k0 * (M + N * math.tan(l_r) * (A**2/2))
        return E, Nort, zone

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Geodesia VZLA", page_icon="📍")
st.title("🇻🇪 GeoVZLA Pro")
st.write("Conversor de precisión oficial (PATVEN)")

with st.expander("📖 Instrucciones de Formato"):
    st.info("Latitud: 10.48 o 10 28 48 N | Longitud: -66.9 o 66 54 00 W")

menu = st.selectbox("¿Qué deseas hacer?", 
    ["Google Maps -> La Canoa (PSAD56)", 
     "La Canoa -> Google Maps (REGVEN)", 
     "Obtener UTM desde Google Maps", 
     "Obtener UTM desde La Canoa"])

c1, c2 = st.columns(2)
with c1: lat_s = st.text_input("Latitud", "10.4806")
with c2: lon_s = st.text_input("Longitud", "-66.9036")
h_s = st.number_input("Altura (m)", value=0.0)

if st.button("CALCULAR AHORA"):
    lt = Geodesia.limpiar_coord(lat_s, 'LAT')
    ln = Geodesia.limpiar_coord(lon_s, 'LON')
    
    if menu == "Google Maps -> La Canoa (PSAD56)":
        res = Geodesia.transformar(lt, ln, h_s, inverso=True)
        st.success(f"📍 La Canoa: {res[0]:.8f}, {res[1]:.8f}")
    elif menu == "La Canoa -> Google Maps (REGVEN)":
        res = Geodesia.transformar(lt, ln, h_s, inverso=False)
        st.success(f"📍 REGVEN/Google: {res[0]:.8f}, {res[1]:.8f}")
    elif menu == "Obtener UTM desde Google Maps":
        e, n, z = Geodesia.a_utm(lt, ln)
        st.success(f"📐 UTM Zona {z}N | E: {e:,.3f} | N: {n:,.3f}")
    else:
        temp = Geodesia.transformar(lt, ln, h_s, inverso=False)
        e, n, z = Geodesia.a_utm(temp[0], temp[1])
        st.success(f"📐 UTM Zona {z}N | E: {e:,.3f} | N: {n:,.3f}")
