import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage
import pandas as pd
from datetime import datetime
import os
import random
import numpy as np
import cv2
from pyzbar.pyzbar import decode
import requests

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
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label, div[data-testid="stFileUploader"] label { color: yellow !important; font-size: 16px !important; }
    .stTextInput>div>div>input { text-align: center; background-color: #111; color: cyan !important; font-size: 20px; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: cyan !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'user' not in st.session_state: st.session_state.user = None
if 'user_status' not in st.session_state: st.session_state.user_status = None
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

# ================= FUNCIONES TÉCNICAS =================

def decodificar_qr(foto):
    try:
        file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        codigos = decode(img)
        if codigos: return codigos[0].data.decode("utf-8").upper()
    except: return None
    return None

def ir(acc, cat):
    st.session_state.accion = acc; st.session_state.categoria = cat
    st.session_state.page = 'form'; st.session_state.scanned_id = ""; st.rerun()

# ================= PÁGINAS =================

def login():
    st.title("LOGIN / 로그인")
    st.markdown("<h3 style='color: white !important;'>ALMACÉN / 창고</h3>", unsafe_allow_html=True)
    u_in = st.text_input("Usuario / 사용자").upper().strip()
    p_in = st.text_input("Clave / 비밀번호", type="password").strip()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(u_in).get()
            data = doc.to_dict() if doc.exists else None
            if data and str(data.get('clave')) == p_in:
                st.session_state.user = data.get('nombre_personal', u_in).split()[0]
                st.session_state.user_status = "YAKO" if u_in == "YAKO" else data.get('estado', 'PENDIENTE')
                st.session_state.page = 'menu'; st.rerun()
            else: st.error("Acceso Denegado")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USUARIO{random.randint(100, 999)}", f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre_personal": u})
            st.success(f"User: {u}\nPass: {p}")
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")

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
    if st.session_state.user_status == "YAKO" and st.button("PANEL CONTROL"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

def formulario():
    cat = st.session_state.get('categoria', 'materiales')
    acc = st.session_state.get('accion', 'ENTRADA')
    st.header(f"{cat.upper()} - {acc}")
    with st.expander("📷 ESCANEAR QR", expanded=True):
        cam = st.camera_input("QR", key="cam_qr")
        if cam:
            res = decodificar_qr(cam)
            if res: st.session_state.scanned_id = res
    cod = st.text_input("ID / CÓDIGO", value=st.session_state.scanned_id).upper().strip()
    cant = st.number_input("CANTIDAD", min_value=1)
    ubi = st.text_input("UBICACIÓN").upper() if acc == "ENTRADA" else "SALIDA"
    if st.button("REGISTRAR"):
        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": cod,
            "cantidad": cant if acc == "ENTRADA" else -cant, "ubicacion": ubi,
            "registrado_por": st.session_state.user, "foto_url": "NO FOTO"
        })
        st.success("OK"); st.session_state.scanned_id = ""; st.rerun()
    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO", key="bus_in").upper().strip()
    if c:
        stock = 0; u_ubi = "---"; f_url = None; col_found = None; u_fecha = ""
        for col in ["materiales", "holders"]:
            docs = db.collection(col).where("item", "==", c).stream()
            for d in docs:
                col_found = col; dt = d.to_dict(); stock += dt.get('cantidad', 0)
                if dt.get('fecha', '') >= u_fecha and str(dt.get('ubicacion')).upper() != "SALIDA":
                    u_fecha = dt.get('fecha'); u_ubi = dt.get('ubicacion')
                if dt.get('foto_url') not in ["NO FOTO", "ERROR", None]: f_url = dt.get('foto_url')
        if col_found:
            st.subheader(f"ID: {c}")
            c1, c2 = st.columns(2)
            c1.metric("STOCK", stock); c2.metric("UBICACIÓN", u_ubi)
            if f_url: st.image(f_url)
        else: st.warning("No encontrado")
    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

def admin():
    st.title("PANEL CONTROL / 제어판")
    t1, t2, t3 = st.tabs(["BORRAR", "EXCEL", "CARGA EXCEL (AUTO)"])
    
    with t3:
        st.subheader("Carga Automática / 엑셀 업로드")
        st.info("Columnas requeridas: NOMBRE, ID, CANTIDAD, UBICACION, FOTO")
        archivo = st.file_uploader("Subir .xlsx o .csv", type=['xlsx', 'csv'])
        
        if archivo:
            df = pd.read_excel(archivo) if archivo.name.endswith('.xlsx') else pd.read_csv(archivo)
            st.dataframe(df.head())

            if st.button("🚀 INICIAR CARGA"):
                for i, fila in df.iterrows():
                    # Lógica de foto random si está vacío
                    foto = str(fila['FOTO']) if pd.notna(fila['FOTO']) else f"https://picsum.photos/seed/{random.randint(1,1000)}/400/300"
                    
                    db.collection("materiales").add({
                        "nombre": str(fila['NOMBRE']),
                        "item": str(fila['ID']).upper().strip(),
                        "cantidad": int(fila['CANTIDAD']),
                        "ubicacion": str(fila['UBICACION']).upper().strip(),
                        "foto_url": foto,
                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "registrado_por": "AUTO_EXCEL"
                    })
                st.success("¡Carga Completa!")

    if st.button("VOLVER AL MENÚ"): st.session_state.page = 'menu'; st.rerun()

# --- RUTAS ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
