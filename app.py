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

# --- ESTILOS VISUALES / 시각적 스타일 ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    .stButton>button { background-color: white; color: black; border-radius: 5px; width: 100%; font-weight: bold; border: 2px solid red; }
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stNumberInput"] label { 
        color: yellow !important; font-size: 16px !important; 
    }
    .stTextInput>div>div>input { 
        text-align: center; background-color: #111; color: cyan !important; font-size: 20px; font-weight: bold; 
    }
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: #00cccc !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    .center-container { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; width: 100%; margin: auto; }
    .qr-card { background-color: white; padding: 15px; border-radius: 10px; display: inline-block; margin: 20px auto; text-align: center; }
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
            if doc.exists and str(doc.to_dict().get('clave')) == p_in:
                st.session_state.user = u_in
                st.session_state.page = 'menu'; st.rerun()
            else: st.error("DATOS INCORRECTOS / 잘못된 정보")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USUARIO{random.randint(100, 999)}", f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre_personal": u})
            st.success(f"User: {u}\nPass: {p}")
    st.divider()
    c_inv1, c_inv2 = st.columns(2)
    if c_inv1.button("SALIDA MAT INVITADO / 자재 출고 (게스트)"):
        st.session_state.user = "INVITADO"; ir("SALIDA", "materiales")
    if c_inv2.button("SALIDA HOL INVITADO / 홀더 출고 (게스트)"):
        st.session_state.user = "INVITADO"; ir("SALIDA", "holders")
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"SESIÓN / 세션: {st.session_state.user}")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES / 자재")
        if st.button("ENTRADA MAT / 입고"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT / 출고"): ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS / 홀더")
        if st.button("ENTRADA HOL / 입고"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL / 출고"): ir("SALIDA", "holders")
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.button("SALIR / 로그아웃"): st.session_state.user=None; st.session_state.page='login'; st.rerun()

def formulario():
    cat, acc = st.session_state.get('categoria', 'materiales'), st.session_state.get('accion', 'ENTRADA')
    st.header(f"{cat.upper()} - {acc}")
    with st.expander("📷 USAR CÁMARA / 카메라 사용", expanded=False):
        cam = st.camera_input("QR SCAN")
        if cam:
            res = decodificar_qr(cam)
            if res: st.session_state.scanned_id = res
    cod = st.text_input("ID / CÓDIGO / 코드", value=st.session_state.scanned_id).upper().strip()
    stock_calc = 0
    if cod:
        docs = db.collection(cat).where("item", "==", cod).stream()
        stock_calc = sum([d.to_dict().get('cantidad', 0) for d in docs])
        st.write(f"📊 STOCK EN SISTEMA / 시스템 재고: **{stock_calc}**")
    col_c1, col_c2 = st.columns(2)
    cant1 = col_c1.number_input("CANTIDAD / 수량", min_value=1, key="cant1")
    cant2 = col_c2.number_input("CONFIRMAR CANTIDAD / 수량 확인", min_value=0, key="cant2")
    solicitante = st.text_input("NOMBRE SOLICITANTE / 신청자 이름").upper().strip() if acc == "SALIDA" else ""
    ubi_fija = ""
    if cod:
        doc_ubi = db.collection(cat).where("item", "==", cod).limit(10).stream()
        for d in doc_ubi:
            u_temp = d.to_dict().get("ubicacion", "")
            if u_temp != "SALIDA": ubi_fija = u_temp; break
    ubi = st.text_input("UBICACIÓN / 위치", value=ubi_fija).upper() if acc == "ENTRADA" else "SALIDA"
    bloqueado = cant1 != cant2 or (acc == "SALIDA" and (cant1 > stock_calc or not solicitante))
    if st.button("REGISTRAR ACCIÓN / 작업 등록", disabled=bloqueado):
        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": cod,
            "cantidad": cant1 if acc == "ENTRADA" else -cant1,
            "ubicacion": ubi, "solicitante": solicitante, "registrado_por": st.session_state.user
        })
        st.success("✅ ¡ACCIÓN EFECTUADA CON ÉXITO! / 작업이 완료되었습니다!")
        st.balloons(); st.session_state.scanned_id = ""
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    query = st.text_input("ID o NOMBRE / ID 또는 이름").upper().strip()
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
            if len(resultados) > 1:
                st.warning("⚠️ HAY MÁS DE 1 COINCIDENCIA / 1개 이상의 결과가 있습니다")
                opciones = {f"{r.get('nombre')} [{r.get('item')}]": r for r in resultados}
                seleccion = st.selectbox("ELEGIR MATERIAL / 자재 선택:", list(opciones.keys()))
                item = opciones[seleccion]
            else: item = resultados[0]
            id_f, col_f = item.get('item'), item['categoria_db']
            st.markdown(f"<h2>{query}</h2>", unsafe_allow_html=True)
            ubi_real = "---"
            # Consulta simplificada para evitar el error de índice
            docs_ubi = db.collection(col_f).where("item", "==", id_f).limit(20).stream()
            for d in docs_ubi:
                u_temp = d.to_dict().get('ubicacion', '---')
                if u_temp != "SALIDA": ubi_real = u_temp; break
            docs_stock = db.collection(col_f).where("item", "==", id_f).stream()
            total_neto = sum([d.to_dict().get('cantidad', 0) for d in docs_stock])
            c1, c2 = st.columns(2)
            c1.metric("SUMA ACTUAL / 현재 총계", total_neto)
            c2.metric("UBICACIÓN / 위치", ubi_real)
            st.divider()
            st.markdown('<div class="center-container">', unsafe_allow_html=True)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}"
            st.markdown(f'<div class="qr-card"><img src="{qr_url}"><br><b style="color:black;">QR {id_f}</b></div>', unsafe_allow_html=True)
            foto = convertir_link_drive(item.get('foto_url', ''))
            if foto: st.image(foto, width=450, caption=f"REF: {item.get('nombre')}")
            st.markdown('</div>', unsafe_allow_html=True)
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user else 'login'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
    
