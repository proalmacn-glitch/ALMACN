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
def convertir_link_drive(url):
    if not url or url == "NO FOTO": return None
    if 'drive.google.com' in url:
        match = re.search(r'(?:id=|d/)([-\w]{25,})', url)
        if match:
            file_id = match.group(1)
            return f'https://drive.google.com/uc?export=view&id={file_id}'
    return url

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

# --- ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    .stButton>button { background-color: white; color: black; border-radius: 5px; width: 100%; font-weight: bold; border: 2px solid red; }
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: #00cccc !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    .center-container { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; width: 100%; }
    .qr-card { background-color: white; padding: 15px; border-radius: 10px; display: inline-block; margin-bottom: 20px; }
    div[data-testid="stImage"] { display: flex; justify-content: center; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'user_status' not in st.session_state: st.session_state.user_status = None
if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

# ================= VISTAS =================

def login():
    st.title("LOGIN / 로그인")
    u_in = st.text_input("Usuario / 사용자").upper().strip()
    p_in = st.text_input("Clave / 비밀번호", type="password").strip()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(u_in).get()
            data = doc.to_dict() if doc.exists else None
            if data and str(data.get('clave')) == p_in:
                st.session_state.user = u_in
                st.session_state.user_status = "YAKO" if data.get('estado') == 'ADMIN_MASTER' or u_in == "YAKO" else "ACTIVO"
                st.session_state.page = 'menu'; st.rerun()
            else: st.error("Acceso Denegado")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USUARIO{random.randint(100, 999)}", f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre_personal": u})
            st.success(f"User: {u}\nPass: {p}")
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()

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
    if st.button("🔍 BUSCAR"): st.session_state.page = 'buscar'; st.rerun()
    if st.session_state.user_status == "YAKO" and st.button("PANEL CONTROL"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

def formulario():
    cat = st.session_state.categoria
    acc = st.session_state.accion
    st.header(f"{cat.upper()} - {acc}")
    cam = st.camera_input("QR")
    if cam:
        res = decodificar_qr(cam)
        if res: st.session_state.scanned_id = res
    
    cod = st.text_input("ID / CÓDIGO", value=st.session_state.scanned_id).upper().strip()
    cant = st.number_input("CANTIDAD", min_value=1)
    
    # Campo para nombre de usuario manual en salidas o automático en entradas
    if acc == "SALIDA":
        user_manual = st.text_input("NOMBRE DE QUIEN RETIRA / 수령인 성함").upper().strip()
    else:
        user_manual = st.session_state.user

    ubi = st.text_input("UBICACIÓN / 위치").upper() if acc == "ENTRADA" else "SALIDA"
    
    # Obtener nombre e imagen automáticamente si ya existe
    nombre_auto = ""
    foto_auto = "NO FOTO"
    docs = db.collection(cat).where("item", "==", cod).limit(1).stream()
    for d in docs: 
        dt = d.to_dict()
        nombre_auto = dt.get('nombre', '')
        foto_auto = dt.get('foto_url', 'NO FOTO')

    if st.button("REGISTRAR / 등록"):
        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "item": cod,
            "nombre": nombre_auto,
            "cantidad": cant if acc == "ENTRADA" else -cant,
            "ubicacion": ubi,
            "registrado_por": user_manual,
            "foto_url": foto_auto
        })
        st.success("LISTO"); st.session_state.scanned_id = ""; st.rerun()
    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    query = st.text_input("ID o NOMBRE").upper().strip()
    if query:
        resultados = []
        for col in ["materiales", "holders"]:
            docs = db.collection(col).stream()
            for d in docs:
                data = d.to_dict()
                if query in str(data.get('nombre', '')).upper() or query == str(data.get('item', '')).upper():
                    data['categoria_db'] = col
                    resultados.append(data)
        
        if resultados:
            opciones = {f"{r.get('nombre')} [{r.get('item')}]": r for r in resultados}
            seleccion = st.selectbox("SELECCIONA:", list(opciones.keys()))
            item = opciones[seleccion]
            id_f = item.get('item')
            col_f = item['categoria_db']
            
            docs_s = db.collection(col_f).where("item", "==", id_f).stream()
            total = sum([d.to_dict().get('cantidad', 0) for d in docs_s])
            
            st.markdown(f"<h2>{item.get('nombre')}</h2>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.metric("STOCK TOTAL", total)
            c2.metric("UBICACIÓN", item.get('ubicacion'))
            
            st.markdown('<div class="center-container">', unsafe_allow_html=True)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}"
            st.markdown(f'<div class="qr-card"><img src="{qr_url}"><br><b style="color:black;">QR</b></div>', unsafe_allow_html=True)
            foto = convertir_link_drive(item.get('foto_url'))
            if foto: st.image(foto, width=450)
            st.markdown('</div>', unsafe_allow_html=True)
            
    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

def admin():
    st.title("PANEL CONTROL")
    t1, t2, t3 = st.tabs(["BORRAR", "DESCARGAR EXCEL", "USUARIOS"])
    
    with t2:
        st.subheader("REPORTE DE MOVIMIENTOS / 이동 보고서")
        ce_s = st.selectbox("COLECCIÓN / 컬렉션", ["materiales", "holders"])
        if st.button("📥 GENERAR EXCEL / 엑셀 생성"):
            data = [d.to_dict() for d in db.collection(ce_s).order_by("fecha").stream()]
            if data:
                df = pd.DataFrame(data)
                # Renombrar columnas según imagen y bilingüe
                df = df.rename(columns={
                    'fecha': 'HORA Y FECHA / 시간 및 날짜',
                    'nombre': 'NOMBRE / 이름',
                    'item': 'ID',
                    'cantidad': 'CANTIDAD / 수량',
                    'registrado_por': 'USUARIO / 사용자',
                    'foto_url': 'FOTO / 사진'
                })
                # Reordenar columnas exactas
                cols_finales = [
                    'HORA Y FECHA / 시간 및 날짜', 
                    'NOMBRE / 이름', 
                    'ID', 
                    'CANTIDAD / 수량', 
                    'USUARIO / 사용자', 
                    'FOTO / 사진'
                ]
                df = df[cols_finales]
                
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("DESCARGAR EXCEL (CSV)", csv, f"REPORTE_{ce_s.upper()}.csv", "text/csv")
            else:
                st.warning("No hay datos disponibles.")

    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
