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

# --- CONFIGURACIÓN DE PÁGINA / 페이지 설정 ---
st.set_page_config(page_title="YAKO PRO WEB", page_icon="📦", layout="centered")

# --- CONEXIÓN FIREBASE / 파이어베이스 연결 ---
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
        st.error(f"Error Conexión / 연결 오류: {e}")

db = firestore.client()

# --- UTILIDADES TÉCNICAS / 기술 유틸리티 ---
def convertir_link_drive(url):
    """
    CORRECCIÓN CRÍTICA: Extrae el ID y genera el link de descarga directa 
    que evita el visor de Google Drive.
    """
    if not url or str(url).upper() in ["NO FOTO", "NAN", "NONE", "0"]: 
        return None
    
    # Limpieza profunda de espacios y caracteres invisibles
    url_limpia = str(url).strip()
    
    # Buscar ID de Drive (formato estándar de 25+ caracteres)
    match = re.search(r'(?:id=|d/|file/d/)([-\w]{25,})', url_limpia)
    
    if match:
        file_id = match.group(1)
        # Formato uc?export=download es el más estable para Streamlit
        return f'https://drive.google.com/uc?export=download&id={file_id}'
    
    return url_limpia if "http" in url_limpia else None

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

def animacion_aleatoria():
    opcion = random.choice(["globos", "nieve"])
    if opcion == "globos": st.balloons()
    else: st.snow()

# --- ESTILOS VISUALES / 시각적 스타일 ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    .stButton>button { background-color: white; color: black; border-radius: 5px; width: 100%; font-weight: bold; border: 2px solid red; }
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stNumberInput"] label { color: yellow !important; }
    .stTextInput>div>div>input { text-align: center; background-color: #111; color: cyan !important; font-size: 20px; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: #00cccc !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    .center-container { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; width: 100%; }
    .qr-card { background-color: white; padding: 15px; border-radius: 10px; display: inline-block; margin: 20px auto; text-align: center; }
    /* Centrado forzado de imágenes */
    div[data-testid="stImage"] { display: flex; justify-content: center; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

# ================= VISTAS / 보기 =================

def login():
    st.title("LOGIN / 로그인")
    u_in = st.text_input("USUARIO / 사용자").upper().strip()
    p_in = st.text_input("CLAVE / 비밀번호", type="password").strip()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(u_in).get()
            if doc.exists:
                udata = doc.to_dict()
                if str(udata.get('clave')) == p_in:
                    if udata.get('estado') in ['ACTIVO', 'ADMIN_MASTER'] or u_in == "YAKO":
                        st.session_state.user = u_in
                        st.session_state.page = 'menu'; st.rerun()
                    else: st.warning("CUENTA NO ACTIVADA POR YAKO / 승인 대기 중")
                else: st.error("CLAVE INCORRECTA / 비밀번호 오류")
            else: st.error("USUARIO NO EXISTE / 사용자 없음")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USUARIO{random.randint(100, 999)}", f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE"})
            st.success(f"TOMA FOTO / 사진 찍기:\nUser: {u}\nPass: {p}")
    st.divider()
    st.markdown('<div class="center-container">', unsafe_allow_html=True)
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")
    st.markdown('</div>', unsafe_allow_html=True)

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES / 자재")
        if st.button("ENTRADA MAT / 입고"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT / 出고"): ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS / 홀더")
        if st.button("ENTRADA HOL / 입고"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL / 出고"): ir("SALIDA", "holders")
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.session_state.user == "YAKO" and st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR / 로그아웃"): st.session_state.user=None; st.session_state.page='login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    q = st.text_input("ID o NOMBRE / ID 또는 이름").upper().strip()
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
            st.markdown(f"<h2>{q}</h2>", unsafe_allow_html=True)
            u_real = "---"
            d_u = db.collection(col_f).where("item", "==", id_f).limit(30).stream()
            for d in d_u:
                if d.to_dict().get('ubicacion') != "SALIDA": u_real = d.to_dict().get('ubicacion'); break
            d_s = db.collection(col_f).where("item", "==", id_f).stream()
            tot = sum([d.to_dict().get('cantidad', 0) for d in d_s])
            c1, c2 = st.columns(2); c1.metric("STOCK ACTUAL / 재고", max(0, tot)); c2.metric("UBICACIÓN / 위치", u_real)
            st.divider()
            
            st.markdown('<div class="center-container">', unsafe_allow_html=True)
            # 1. QR
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}"
            st.image(qr_url, caption=f"QR {id_f}")
            
            # 2. FOTO DE DRIVE
            foto_final = convertir_link_drive(item.get('foto_url', ''))
            
            if foto_final:
                try:
                    # Cargamos con un ancho fijo para centrado y forzamos descarga
                    st.image(foto_final, width=450)
                except Exception:
                    st.error("Error al cargar imagen. Revisa permisos de Drive.")
            else:
                st.info("No hay foto disponible / 사용 가능한 사진이 없습니다.")
            st.markdown('</div>', unsafe_allow_html=True)
            
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user else 'login'; st.rerun()

# [El resto de las funciones admin, formulario, mostrar_tab_excel permanecen iguales como estaban]
# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': # [Lógica de admin como la tenías]
    pass
