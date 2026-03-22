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
        st.error(f"Error Conexión / 연결 오류: {e}")

db = firestore.client()

# --- UTILIDADES TÉCNICAS ---
def convertir_link_drive(url):
    """
    Transforma enlaces de Drive en enlaces de imagen pura.
    Limpia espacios y fuerza el parámetro de descarga.
    """
    if not url or str(url).upper() in ["NO FOTO", "NAN", "0", "NONE"]:
        return None
    
    # Limpiar espacios en blanco que el Excel a veces añade al final
    url_limpia = str(url).strip()
    
    # Extraer el ID único del archivo
    match = re.search(r'(?:id=|d/|file/d/)([-\w]{25,})', url_limpia)
    
    if match:
        file_id = match.group(1)
        # Usamos 'uc?export=download' que es más fuerte para saltar el visor de Google
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

# --- ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    .stButton>button { background-color: white; color: black; border-radius: 5px; width: 100%; font-weight: bold; border: 2px solid red; }
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stMetricValue"] { color: #00cccc !important; text-align: center !important; }
    .center-container { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

# ================= VISTAS =================

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
                    else: st.warning("CUENTA NO ACTIVADA / 승인 대기")
                else: st.error("CLAVE INCORRECTA / 비밀번호 오류")
            else: st.error("USUARIO NO EXISTE / 사용자 없음")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USUARIO{random.randint(100, 999)}", f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE"})
            st.success(f"TOMA FOTO / 사진 찍기:\nUser: {u}\nPass: {p}")
    st.divider()
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
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
    if st.session_state.user != "INVITADO" and st.button("PANEL CONTROL / 제어판"): 
        st.session_state.page = 'admin'; st.rerun()
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
            st.markdown(f"<h2>{item.get('nombre', id_f)}</h2>", unsafe_allow_html=True)
            
            d_u = db.collection(col_f).where("item", "==", id_f).limit(30).stream()
            u_real = "---"
            for d in d_u:
                if d.to_dict().get('ubicacion') != "SALIDA": u_real = d.to_dict().get('ubicacion'); break
            
            d_s = db.collection(col_f).where("item", "==", id_f).stream()
            tot = sum([d.to_dict().get('cantidad', 0) for d in d_s])
            
            c1, c2 = st.columns(2)
            c1.metric("STOCK ACTUAL / 재고", max(0, tot))
            c2.metric("UBICACIÓN / 위치", u_real)
            
            st.divider()
            
            st.markdown('<div class="center-container">', unsafe_allow_html=True)
            
            # 1. QR
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}"
            st.image(qr_url, caption=f"QR {id_f}")
            
            # 2. FOTO (Con el nuevo link de descarga directa)
            foto_final = convertir_link_drive(item.get('foto_url', ''))
            if foto_final:
                try:
                    # use_container_width reemplaza a use_column_width en versiones nuevas
                    st.image(foto_final, width=450)
                except:
                    st.warning("⚠️ No se pudo cargar la foto. Verifica los permisos en Drive.")
            else:
                st.info("Sin foto registrada")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user else 'login'; st.rerun()

def admin():
    st.title("PANEL CONTROL / 제어판")
    tabs = st.tabs(["EXCEL REPORTE / 엑셀", "CARGA MASIVA / 로드"])
    
    with tabs[0]:
        ce = st.selectbox("REPORTE", ["materiales", "holders"])
        if st.button("📥 GENERAR EXCEL BILINGÜE"):
            data = [d.to_dict() for d in db.collection(ce).order_by("fecha").stream()]
            if data:
                df = pd.DataFrame(data).rename(columns={
                    'fecha': 'FECHA / 날짜', 'item': 'ID / 아이디', 'cantidad': 'MOVIMIENTO / 이동',
                    'ubicacion': 'UBICACIÓN / 위치', 'solicitante': 'SOLICITANTE / 신청자', 'registrado_por': 'USUARIO / 사용자'
                })
                csv = df[['FECHA / 날짜', 'ID / 아이디', 'MOVIMIENTO / 이동', 'UBICACIÓN / 위치', 'SOLICITANTE / 신청자', 'USUARIO / 사용자']].to_csv(index=False).encode('utf-8-sig')
                st.download_button("Descargar / 다운로드", csv, f"Reporte_{ce}.csv", "text/csv")

    with tabs[1]:
        dest = st.selectbox("DESTINO", ["materiales", "holders"])
        arch = st.file_uploader("Subir Excel", type=['xlsx'])
        if arch and st.button("🚀 CARGAR"):
            df_in = pd.read_excel(arch, engine='openpyxl')
            df_in.columns = [str(c).strip().upper() for c in df_in.columns]
            for _, f in df_in.iterrows():
                db.collection(dest).add({
                    "nombre": str(f.get('NOMBRE', 'S/N')).upper(),
                    "item": str(f.get('ID', 'S/ID')).upper(),
                    "cantidad": int(f.get('CANTIDAD', 0)),
                    "ubicacion": str(f.get('UBICACIÓN', f.get('UBICACION', 'S/U'))).upper(),
                    "foto_url": str(f.get('FOTO', 'NO FOTO')),
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "registrado_por": st.session_state.user
                })
            st.success("✅ ¡Carga Exitosa!")

    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
