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
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label { color: yellow !important; }
    .stTextInput>div>div>input { text-align: center; background-color: #111; color: cyan !important; font-size: 20px; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: #00cccc !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    .center-container { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

# --- VISTAS ---
def login():
    st.title("LOGIN / 로그인")
    u_in = st.text_input("USUARIO / 사용자").upper().strip()
    p_in = st.text_input("CLAVE / 비밀번호", type="password").strip()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(u_in).get()
            if doc.exists and str(doc.to_dict().get('clave')) == p_in:
                st.session_state.user = u_in
                st.session_state.page = 'menu'; st.rerun()
            else: st.error("Error de credenciales")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USER{random.randint(10,99)}", f"{random.randint(100,999)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "ACTIVO"})
            st.success(f"User: {u} | Pass: {p}")
    st.divider()
    st.markdown('<div class="center-container">', unsafe_allow_html=True)
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")
    st.markdown('</div>', unsafe_allow_html=True)

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA: {st.session_state.user}")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("ENTRADA MAT"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT"): ir("SALIDA", "materiales")
    with c2:
        if st.button("ENTRADA HOL"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL"): ir("SALIDA", "holders")
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.button("⚙️ PANEL CONTROL"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR"): st.session_state.user=None; st.session_state.page='login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    q = st.text_input("ID o NOMBRE").upper().strip()
    if q:
        res = []
        for col in ["materiales", "holders"]:
            docs = db.collection(col).stream()
            for d in docs:
                data = d.to_dict()
                if q in str(data.get('nombre', '')).upper() or q == str(data.get('item', '')).upper():
                    data['cat_db'] = col; res.append(data)
        if res:
            item = res[0]
            id_f, col_f = item.get('item'), item['cat_db']
            st.markdown(f"<h2>{item.get('nombre', q)}</h2>", unsafe_allow_html=True)
            d_s = db.collection(col_f).where("item", "==", id_f).stream()
            tot = sum([d.to_dict().get('cantidad', 0) for d in d_s])
            c1, c2 = st.columns(2)
            c1.metric("STOCK ACTUAL", max(0, tot))
            c2.metric("UBICACIÓN", item.get('ubicacion', '---'))
            st.divider()
            st.markdown('<div class="center-container">', unsafe_allow_html=True)
            st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}", width=150)
            url_img = obtener_url_final(item.get('foto_url', ''))
            if url_img:
                st.markdown(f'<div style="margin-top:20px;"><img src="{url_img}" style="width:100%; max-width:400px; border-radius:15px; border:3px solid red;"></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

def formulario():
    cat, acc = st.session_state.get('categoria'), st.session_state.get('accion')
    st.header(f"{cat.upper()} - {acc}")
    with st.expander("📷 CÁMARA QR"):
        cam = st.camera_input("SCAN")
        if cam:
            res = decodificar_qr(cam)
            if res: st.session_state.scanned_id = res
    cod = st.text_input("ID / 코드", value=st.session_state.scanned_id).upper().strip()
    cant = st.number_input("CANTIDAD", min_value=1)
    if st.button("REGISTRAR"):
        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": cod,
            "cantidad": cant if acc == "ENTRADA" else -cant, "ubicacion": "ALM", "registrado_por": st.session_state.user
        })
        st.success("REGISTRADO"); st.balloons()
    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

def admin():
    st.title("PANEL CONTROL")
    arch = st.file_uploader("Subir Excel (.xlsx)", type=['xlsx'])
    dest = st.selectbox("Destino", ["materiales", "holders"])
    if arch and st.button("🚀 CARGAR DATOS"):
        df = pd.read_excel(arch)
        df.columns = [str(c).strip().upper() for c in df.columns]
        for _, f in df.iterrows():
            db.collection(dest).add({
                "nombre": str(f.get('NOMBRE','')).upper(), "item": str(f.get('ID','')).upper(),
                "cantidad": int(f.get('CANTIDAD',0)), "ubicacion": str(f.get('UBICACION','ALM')).upper(),
                "foto_url": str(f.get('FOTO','')), "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        st.success("CARGA EXITOSA")
    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'admin': admin()
