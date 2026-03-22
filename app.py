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

# --- UTILIDADES TÉCNICAS ---
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

def ir(acc, cat, page='form'):
    st.session_state.accion = acc
    st.session_state.categoria = cat
    st.session_state.page = page
    st.session_state.scanned_id = ""
    st.rerun()

# --- ESTILOS VISUALES PERSONALIZADOS ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; font-weight: bold; }
    .stButton>button { 
        background-color: white; color: black; border-radius: 2px; 
        width: 100%; font-weight: bold; border: 2px solid red; height: 45px;
    }
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label, div[data-testid="stSelectbox"] label { 
        color: yellow !important; font-weight: bold; 
    }
    .stTextInput>div>div>input { background-color: #262730; color: cyan !important; font-weight: bold; }
    
    /* Métricas de Stock */
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: #00cccc !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    
    .media-container { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 20px; }
    .photo-right { flex: 1; max-width: 400px; border-radius: 15px; border: 3px solid red; }
    .qr-left { background-color: #1a1a1a; padding: 15px; border-radius: 15px; border: 1px solid #333; text-align: center; }
    .center-container { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

# ================= VISTAS / funciones =================

def login():
    # Estructura Imagen 1
    st.markdown("<h1>LOGIN / 로그인</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:red;'>ALMACÉN / 창고 🔗</h3>", unsafe_allow_html=True)
    
    u_in = st.text_input("Usuario / 사용자").upper().strip()
    p_in = st.text_input("Clave / 비밀번호", type="password").strip()
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(u_in).get()
            if doc.exists and str(doc.to_dict().get('clave')) == p_in:
                st.session_state.user = u_in
                st.session_state.page = 'menu'; st.rerun()
            else: st.error("Error de credenciales")
    with c2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USER{random.randint(10,99)}", f"{random.randint(100,999)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "ACTIVO"})
            st.success(f"User: {u} | Pass: {p}")
    
    st.markdown("<br><hr>", unsafe_allow_html=True)
    st.markdown("<h2>SALIDA RÁPIDA / 빠른 출고</h2>", unsafe_allow_html=True)
    
    cr1, cr2 = st.columns(2)
    with cr1:
        if st.button("SALIDA MATERIALES / 자재 출고"): ir("SALIDA", "materiales")
    with cr2:
        if st.button("SALIDA HOLDERS / 홀더 출고"): ir("SALIDA", "holders")
    
    if st.button("🔍 BUSCAR MATERIAL / 재고 검색"): st.session_state.page = 'buscar'; st.rerun()

    st.markdown('<div class="center-container">', unsafe_allow_html=True)
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWUmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif", width=350)
    st.markdown('</div>', unsafe_allow_html=True)

def menu():
    # Estructura Imagen 2
    st.markdown("<h1>ALMACÉN / 창고</h1>", unsafe_allow_html=True)
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
    
    col_mat, col_hol = st.columns(2)
    
    with col_mat:
        st.markdown("<h3 style='color:red;'>MATERIALES / 자재</h3>", unsafe_allow_html=True)
        if st.button("ENTRADA MAT / 자재 입고"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT / 자재 출고"): ir("SALIDA", "materiales")
        
    with col_hol:
        st.markdown("<h3 style='color:red;'>HOLDERS / 홀더</h3>", unsafe_allow_html=True)
        if st.button("ENTRADA HOL / 홀더 입고"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL / 홀더 출고"): ir("SALIDA", "holders")
    
    st.markdown("<br><hr>", unsafe_allow_html=True)
    
    # Botones inferiores alineados a la izquierda
    c_btn, _ = st.columns([0.4, 0.6])
    with c_btn:
        if st.button("BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
        if st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
        if st.button("SALIR / 로그아웃"): 
            st.session_state.user = None
            st.session_state.page = 'login'
            st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    busqueda = st.text_input("ESCRIBE NOMBRE O ID / ID o 이름 입력").upper().strip()
    
    if busqueda:
        coincidencias = []
        for col in ["materiales", "holders"]:
            docs = db.collection(col).stream()
            for d in docs:
                data = d.to_dict()
                nom = str(data.get('nombre', '')).upper()
                idx = str(data.get('item', '')).upper()
                if busqueda in nom or busqueda in idx:
                    data['cat_db'] = col
                    data['label'] = f"{nom} | {idx}"
                    coincidencias.append(data)
        
        if coincidencias:
            opciones = [c['label'] for c in coincidencias]
            seleccion = st.selectbox("RESULTADOS / 검색 결과:", opciones)
            item = next(c for c in coincidencias if c['label'] == seleccion)
            
            id_f, col_f = item.get('item'), item['cat_db']
            st.markdown(f"<h2>{item.get('nombre')}</h2>", unsafe_allow_html=True)
            
            docs_s = db.collection(col_f).where("item", "==", id_f).stream()
            tot = sum([d.to_dict().get('cantidad', 0) for d in docs_s])
            
            if tot <= 5:
                st.warning(f"⚠️ STOCK BAJO: Quedan {tot} unidades")
            
            c1, c2 = st.columns(2)
            c1.metric("STOCK ACTUAL / 재고", max(0, tot))
            c2.metric("UBICACIÓN / 위치", item.get('ubicacion', '---'))
            
            st.divider()
            st.markdown('<div class="media-container">', unsafe_allow_html=True)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}&bgcolor=000000&color=ffffff"
            st.markdown(f'<div class="qr-left"><img src="{qr_url}" width="150"><br><small>QR {id_f}</small></div>', unsafe_allow_html=True)
            
            foto_url = obtener_url_final(item.get('foto_url', ''))
            if foto_url:
                st.markdown(f'<div class="photo-right"><img src="{foto_url}" style="width:100%; border-radius:15px;"></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu'; st.rerun()

def formulario():
    cat, acc = st.session_state.get('categoria'), st.session_state.get('accion')
    st.header(f"{cat.upper()} - {acc}")
    
    with st.expander("📷 CÁMARA QR / QR 카메라"):
        cam = st.camera_input("SCAN")
        if cam:
            res = decodificar_qr(cam)
            if res: st.session_state.scanned_id = res
            
    cod = st.text_input("ID / 코드", value=st.session_state.scanned_id).upper().strip()
    cant = st.number_input("CANTIDAD / 수량", min_value=1)
    ubi = st.text_input("UBICACIÓN / 위치").upper() if acc == "ENTRADA" else "SALIDA"
    
    if st.button("REGISTRAR / 등록"):
        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": cod,
            "cantidad": cant if acc == "ENTRADA" else -cant, "ubicacion": ubi, 
            "registrado_por": st.session_state.user
        })
        st.success("✅ REGISTRADO / 등록 완료"); st.balloons()
    
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu'; st.rerun()

def admin():
    st.title("PANEL CONTROL / 제어판")
    arch = st.file_uploader("Subir Excel / 엑셀 업로드", type=['xlsx'])
    dest = st.selectbox("Destino / 대상", ["materiales", "holders"])
    
    if arch and st.button("🚀 CARGAR / 로드"):
        df = pd.read_excel(arch)
        df.columns = [str(c).strip().upper() for c in df.columns]
        for _, f in df.iterrows():
            db.collection(dest).add({
                "nombre": str(f.get('NOMBRE','')).upper(), "item": str(f.get('ID','')).upper(),
                "cantidad": int(f.get('CANTIDAD',0)), "ubicacion": str(f.get('UBICACION','ALM')).upper(),
                "foto_url": str(f.get('FOTO','')), "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
        st.success("✅ CARGA EXITOSA")
        
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu'; st.rerun()

# --- NAVEGACIÓN PRINCIPAL ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'admin': admin()
