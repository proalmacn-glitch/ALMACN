import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os
import random
import numpy as np
import cv2
from pyzbar.pyzbar import decode
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="YAKO PRO WEB", page_icon="📦", layout="centered")

# --- CONEXIÓN FIREBASE ---
if not firebase_admin._apps:
    try:
        bucket_name = 'almacnn.firebasestorage.app'
        if "textkey" in st.secrets:
            cred = credentials.Certificate(dict(st.secrets["textkey"]))
            firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
        elif os.path.exists("Key.json"):
            cred = credentials.Certificate("Key.json")
            firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
    except Exception as e:
        st.error(f"Error Conexión: {e}")

db = firestore.client()

# --- UTILIDADES ---
def obtener_url_final(url):
    if not url or str(url).upper() in ["NO FOTO", "NAN", "NONE", "0"]:
        return None
    url_limpia = str(url).strip()
    if "drive.google.com" in url_limpia:
        match = re.search(r'(?:id=|d/|file/d/)([-\w]{25,})', url_limpia)
        if match:
            return f'https://drive.google.com/uc?export=download&id={match.group(1)}'
    return url_limpia

def decodificar_qr(foto):
    try:
        file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        codigos = decode(img)
        if codigos: return codigos[0].data.decode("utf-8").upper()
    except: return None
    return None

def ir(acc, cat):
    st.session_state.accion = acc
    st.session_state.categoria = cat
    st.session_state.page = 'form'
    st.session_state.scanned_id = ""
    st.rerun()

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    .stButton>button { background-color: white; color: black; border-radius: 5px; width: 100%; font-weight: bold; border: 2px solid red; }
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stNumberInput"] label { color: yellow !important; }
    .stTextInput>div>div>input { text-align: center; background-color: #111; color: cyan !important; font-size: 20px; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 40px !important; color: #00cccc !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 16px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    
    .media-container { display: flex; flex-direction: row; flex-wrap: wrap; justify-content: center; align-items: center; gap: 20px; width: 100%; margin-top: 15px; }
    .photo-right { flex: 1; max-width: 350px; min-width: 250px; border-radius: 15px; border: 3px solid red; box-shadow: 0px 4px 15px rgba(255, 0, 0, 0.5); }
    .qr-left { background-color: #1a1a1a; padding: 15px; border-radius: 15px; border: 1px solid #333; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .center-container { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None

# ================= VISTAS =================

def login():
    st.title("LOGIN / 로그인")
    u_in = st.text_input("USUARIO / 사용자").upper().strip()
    p_in = st.text_input("CLAVE / 비밀번호", type="password").strip()
    
    c_log1, c_log2 = st.columns(2)
    with c_log1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(u_in).get()
            if doc.exists and str(doc.to_dict().get('clave')) == p_in:
                st.session_state.user = u_in
                st.session_state.page = 'menu'; st.rerun()
            else: st.error("Error de credenciales")
    with c_log2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USER{random.randint(10,99)}", f"{random.randint(100,999)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "ACTIVO"})
            st.success(f"User: {u} | Pass: {p}")

    st.divider()
    
    # --- PARTE PRINCIPAL (MONTACARGAS + SALIDA RÁPIDA + BUSCADOR) ---
    st.markdown('<div class="center-container">', unsafe_allow_html=True)
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif", width=300)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### SALIDA RÁPIDA / 빠른 출고")
    c_r1, c_r2 = st.columns(2)
    with c_r1:
        if st.button("SALIDA MATERIALES / 자재 출고"): ir("SALIDA", "materiales")
    with c_r2:
        if st.button("SALIDA HOLDERS / 홀더 출고"): ir("SALIDA", "holders")
    
    # BUSCADOR INTEGRADO EN EL INICIO
    st.markdown("---")
    st.subheader("🔍 BUSCAR MATERIAL / 재고 검색")
    busqueda_login = st.text_input("NOMBRE O ID / ID o 이름", key="bus_login").upper().strip()
    
    if busqueda_login:
        mostrar_resultados(busqueda_login)

def mostrar_resultados(busqueda):
    coincidencias = []
    for col in ["materiales", "holders"]:
        docs = db.collection(col).stream()
        for d in docs:
            data = d.to_dict()
            nom, idx = str(data.get('nombre','')).upper(), str(data.get('item','')).upper()
            if busqueda in nom or busqueda in idx:
                data['cat_db'] = col; data['label'] = f"{nom} | {idx}"; coincidencias.append(data)
    
    if coincidencias:
        item = st.selectbox("RESULTADOS:", [c['label'] for c in coincidencias])
        res = next(i for i in coincidencias if i['label'] == item)
        id_f, col_f = res.get('item'), res['cat_db']
        
        # Alerta stock bajo
        d_stock = db.collection(col_f).where("item", "==", id_f).stream()
        tot = sum([d.to_dict().get('cantidad', 0) for d in d_stock])
        if tot <= 5: st.warning(f"⚠️ STOCK BAJO: {tot} unidades")

        c1, c2 = st.columns(2)
        c1.metric("STOCK", tot); c2.metric("UBICACIÓN", res.get('ubicacion','---'))
        
        st.markdown('<div class="media-container">', unsafe_allow_html=True)
        # QR izquierda
        qr = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}&bgcolor=000000&color=ffffff"
        st.markdown(f'<div class="qr-left"><img src="{qr}" width="130"><br><small>QR {id_f}</small></div>', unsafe_allow_html=True)
        # Imagen derecha
        foto = obtener_url_final(res.get('foto_url', ''))
        if foto: st.markdown(f'<img src="{foto}" class="photo-right">', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("No hay resultados")

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"SESIÓN: {st.session_state.user}")
    st.subheader("MATERIALES")
    c1, c2 = st.columns(2)
    with c1: st.button("ENTRADA MAT", on_click=ir, args=("ENTRADA", "materiales"))
    with c2: st.button("SALIDA MAT", on_click=ir, args=("SALIDA", "materiales"))
    
    st.subheader("HOLDERS")
    c3, c4 = st.columns(2)
    with c3: st.button("ENTRADA HOL", on_click=ir, args=("ENTRADA", "holders"))
    with c4: st.button("SALIDA HOL", on_click=ir, args=("SALIDA", "holders"))
    
    st.divider()
    if st.button("⚙️ PANEL CONTROL"): st.session_state.page = 'admin'; st.rerun()
    if st.button("LOGOUT"): st.session_state.user=None; st.session_state.page='login'; st.rerun()

def formulario():
    cat, acc = st.session_state.get('categoria'), st.session_state.get('accion')
    st.header(f"{acc} - {cat.upper()}")
    cod = st.text_input("ID / 코드").upper().strip()
    cant = st.number_input("CANTIDAD", min_value=1)
    if st.button("REGISTRAR"):
        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": cod,
            "cantidad": cant if acc == "ENTRADA" else -cant, "ubicacion": "ALM",
            "registrado_por": st.session_state.user if st.session_state.user else "PUBLICO"
        })
        st.success("REGISTRADO"); st.balloons()
    if st.button("VOLVER"): 
        st.session_state.page = 'menu' if st.session_state.user else 'login'; st.rerun()

def admin():
    st.title("PANEL CONTROL")
    arch = st.file_uploader("Subir Excel", type=['xlsx'])
    if arch and st.button("🚀 CARGAR"):
        df = pd.read_excel(arch)
        for _, f in df.iterrows():
            db.collection("materiales").add({
                "nombre": str(f.get('NOMBRE','')).upper(), "item": str(f.get('ID','')).upper(),
                "cantidad": int(f.get('CANTIDAD',0)), "ubicacion": str(f.get('UBICACION','ALM')).upper(),
                "foto_url": str(f.get('FOTO','')), "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        st.success("CARGA EXITOSA")
    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'admin': admin()
