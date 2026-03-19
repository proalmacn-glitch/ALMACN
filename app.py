import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage
import pandas as pd
from datetime import datetime
import os
import random

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="YAKO PRO WEB", page_icon="📦", layout="centered")

# --- CONEXIÓN FIREBASE ---
if not firebase_admin._apps:
    try:
        bucket_name = 'almacnn.firebasestorage.app'
        cred_path = "Key.json"
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
        else:
            if "textkey" in st.secrets:
                cred = credentials.Certificate(dict(st.secrets["textkey"]))
                firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
    except Exception as e:
        st.error(f"Error Conexión / 연결 오류: {e}")

db = firestore.client()

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    .stButton>button { background-color: white; color: black; border-radius: 5px; width: 100%; font-weight: bold; border: 2px solid red; }
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stCameraInput"] label, div[data-testid="stTextArea"] label { color: yellow !important; font-size: 16px !important; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { text-align: center; }
    div[data-testid="stMetricValue"] { font-size: 55px !important; color: cyan !important; text-align: center !important; font-weight: bold !important; }
    div[data-testid="stMetricLabel"] { font-size: 20px !important; color: white !important; text-align: center !important; justify-content: center !important; }
    div[data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    .qr-box { background-color: white; padding: 10px; border-radius: 10px; text-align: center; margin-top: 10px; display: inline-block; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'user' not in st.session_state: st.session_state.user = None
if 'user_status' not in st.session_state: st.session_state.user_status = None
if 'page' not in st.session_state: st.session_state.page = 'login'

# ================= FUNCIONES =================

def login():
    st.title("LOGIN / 로그인")
    st.markdown("<h3 style='color: white !important;'>ALMACÉN / 창고</h3>", unsafe_allow_html=True)
    user_input = st.text_input("Usuario / 사용자").upper().strip()
    password = st.text_input("Clave / 비밀번호", type="password").strip()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(user_input).get()
            data = None
            if doc.exists: data = doc.to_dict()
            else:
                query = db.collection("USUARIOS").where("nombre_personal", "==", user_input).stream()
                for d in query: data = d.to_dict(); break 
            
            if data and str(data.get('clave')) == password:
                st.session_state.user = data.get('nombre_personal', user_input)
                st.session_state.user_status = data.get('estado')
                st.session_state.page = 'menu'; st.rerun()
            else: st.error("Acceso Denegado / access 거부됨")

    with col2:
        if st.button("REGISTRARSE / 등록"):
            u = f"USUARIO{random.randint(100, 999)}"
            p = f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre_personal": u})
            st.success(f"PENDIENTE DE APROBACIÓN POR YACO:\nUser: {u}\nPass: {p}")

    st.divider()
    if st.button("SALIDA RÁPIDA / 빠른 출고"): st.session_state.user="INVITADO"; st.session_state.user_status="INVITADO"; ir("SALIDA", "materiales")
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA: {st.session_state.user} ({st.session_state.user_status})")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES")
        # SEGURIDAD: Solo ACTIVO o YAKO pueden dar entrada
        if st.button("ENTRADA MAT"): 
            if st.session_state.user_status in ["ACTIVO", "YAKO"]: ir("ENTRADA", "materiales")
            else: st.error("SOLO PERSONAL AUTORIZADO / 승인된 인원만 가능")
        if st.button("SALIDA MAT"): ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS")
        if st.button("ENTRADA HOL"): 
            if st.session_state.user_status in ["ACTIVO", "YAKO"]: ir("ENTRADA", "holders")
            else: st.error("SOLO PERSONAL AUTORIZADO / 승인된 인원만 가능")
        if st.button("SALIDA HOL"): ir("SALIDA", "holders")

    st.divider()
    if st.button("BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.button("SALIR / 로그아웃"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

def ir(acc, cat):
    st.session_state.accion = acc; st.session_state.categoria = cat; st.session_state.page = 'form'; st.rerun()

def formulario():
    cat = st.session_state.categoria; acc = st.session_state.accion
    st.header(f"{cat.upper()} - {acc}")
    cod = st.text_input("ID / CÓDIGO").upper().strip()
    cant = st.number_input("CANTIDAD", min_value=1, step=1)
    ubi = st.text_input("UBICACIÓN").upper().strip() if acc == "ENTRADA" else "SALIDA"
    foto = st.camera_input("FOTO EVIDENCIA")
    
    if st.button("REGISTRAR"):
        url_foto = "NO FOTO"
        if foto:
            try:
                bucket = storage.bucket()
                blob = bucket.blob(f"evidencias/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cod}.jpg")
                blob.upload_from_file(foto, content_type='image/jpeg')
                blob.make_public(); url_foto = blob.public_url
            except: url_foto = "ERROR_SUBIDA"

        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "item": cod, "cantidad": cant if acc == "ENTRADA" else -cant,
            "ubicacion": ubi, "registrado_por": st.session_state.user, "foto_url": url_foto
        })
        
        st.success("✅ REGISTRADO")
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={cod}"
        st.markdown(f'<div class="qr-box"><img src="{qr_url}"><br><b style="color:black;">{cod}</b></div>', unsafe_allow_html=True)
        if st.button("SIGUIENTE"): st.rerun()

    if st.button("VOLVER"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO").upper().strip()
    if c:
        stock = 0; ubis = set(); foto_v = None
        for col in ["materiales", "holders"]:
            docs = db.collection(col).where("item", "==", c).stream()
            for d in docs:
                dt = d.to_dict(); stock += dt.get('cantidad', 0)
                u = str(dt.get('ubicacion', dt.get('ubi', ''))).upper()
                if u and "SALIDA" not in u: ubis.add(u)
                if dt.get('foto_url') and dt.get('foto_url') not in ["NO FOTO", "ERROR"]: foto_v = dt.get('foto_url')
        
        st.subheader(f"RESULTADO: {c}")
        c1, c2 = st.columns(2)
        c1.metric("STOCK", stock); c2.metric("UBICACIÓN", ", ".join(ubis) if ubis else "---")
        if foto_v: st.image(foto_v, caption=f"ID: {c}")
    if st.button("VOLVER"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
