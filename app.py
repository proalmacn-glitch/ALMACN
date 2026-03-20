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
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label { color: yellow !important; font-size: 16px !important; }
    .stTextInput>div>div>input { text-align: center; background-color: #111; color: cyan !important; font-size: 20px; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: cyan !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    .step-box { border: 1px solid #444; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: #0a0a0a; }
    .yako-adjust { border: 2px solid red; padding: 15px; border-radius: 10px; margin-top: 20px; background-color: #220000; text-align: center; }
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
        if codigos:
            return codigos[0].data.decode("utf-8").upper()
    except:
        return None
    return None

def ir(acc, cat):
    st.session_state.accion = acc
    st.session_state.categoria = cat
    st.session_state.page = 'form'
    st.session_state.scanned_id = ""
    st.rerun()

# ================= VISTAS / PÁGINAS =================

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
                st.session_state.user = data.get('nombre_personal', u_in).split()[0]
                st.session_state.user_status = "YAKO" if u_in == "YAKO" else data.get('estado', 'PENDIENTE')
                st.session_state.page = 'menu'; st.rerun()
            else: st.error("Acceso Denegado / access 거부됨")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USUARIO{random.randint(100, 999)}", f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre_personal": u})
            st.success(f"TOMA FOTO:\nUser: {u}\nPass: {p}")
    
    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("SALIDA MATERIALES"): ir("SALIDA", "materiales")
    if c2.button("SALIDA HOLDERS"): ir("SALIDA", "holders")
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
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
    
    with st.expander("📷 ESCANEAR QR / QR 스캔", expanded=True):
        cam_scan = st.camera_input("Pon el código frente a la cámara", key="cam_qr")
        if cam_scan:
            codigo = decodificar_qr(cam_scan)
            if codigo:
                st.session_state.scanned_id = codigo
                st.success(f"DETECTADO: {codigo}")

    cod = st.text_input("ID / CÓDIGO / 코드", value=st.session_state.scanned_id).upper().strip()
    cant = st.number_input("CANTIDAD", min_value=1, step=1)
    conf_cant = st.number_input("CONFIRMAR", min_value=0, step=1)
    
    if acc == "ENTRADA":
        ubi = st.text_input("UBICACIÓN").upper().strip()
        quien = "ALMACEN"
    else:
        ubi, quien = "SALIDA", st.text_input("QUIEN RETIRA").upper().strip()

    foto_ev = st.camera_input("FOTO EVIDENCIA", key="foto_ev")
    
    if st.button("REGISTRAR"):
        if not cod: st.error("Falta ID"); return
        if cant != conf_cant: st.error("Cantidades no coinciden"); return
        
        url_f = "NO FOTO"
        if foto_ev:
            try:
                bucket = storage.bucket()
                blob = bucket.blob(f"evidencias/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cod}.jpg")
                blob.upload_from_file(foto_ev, content_type='image/jpeg')
                blob.make_public(); url_f = blob.public_url
            except: url_f = "ERROR"

        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": cod,
            "cantidad": cant if acc == "ENTRADA" else -cant, "ubicacion": ubi,
            "registrado_por": st.session_state.user, "solicitante": quien, "foto_url": url_f
        })
        st.success(f"✅ REGISTRADO: {cod}")
        st.session_state.scanned_id = ""
        if st.button("SIGUIENTE"): st.rerun()

    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO", key="bus_in").upper().strip()
    if c:
        stock = 0; u_fecha = ""; u_ubi = "---"; f_url = None; col_found = None
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
            if f_url:
                try: st.image(f_url)
                except: st.warning("Imagen no disponible")
        else: st.warning("No encontrado")
    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

def admin():
    st.title("PANEL CONTROL / 제어판")
    t1, t2, t3, t4 = st.tabs(["BORRAR", "EXCEL", "CARGA ASISTIDA", "USUARIOS"])
    
    with t1:
        col_db = st.selectbox("Categoría", ["materiales", "holders"])
        c_del = st.text_input("ID a Borrar").upper()
        if st.button("ELIMINAR"):
            docs = db.collection(col_db).where("item", "==", c_del).stream()
            for d in docs: db.collection(col_db).document(d.id).delete()
            st.success("OK")

    with t2:
        ce_s = st.selectbox("Descargar", ["materiales", "holders"])
        if st.button("DESCARGAR CSV"):
            data_e = [d.to_dict() for d in db.collection(ce_s).stream()]
            if data_e:
                df = pd.DataFrame(data_e)
                st.download_button("Descargar", df.to_csv(index=False).encode('utf-8-sig'), f"{ce_s}.csv")

    with t3:
        st.subheader("Paso a Paso / 단계별 업로드")
        
        # PASO 1: ID
        st.markdown('<div class="step-box">', unsafe_allow_html=True)
        id_masivo = st.text_input("1. ID / NOMBRE COMPLETO (Obligatorio)").upper().strip()
        st.markdown('</div>', unsafe_allow_html=True)

        # PASO 2: CANTIDAD (Solo si hay ID)
        cant_masivo = 0
        if id_masivo:
            st.markdown('<div class="step-box">', unsafe_allow_html=True)
            cant_masivo = st.number_input("2. CANTIDAD (Solo números)", min_value=0, step=1)
            st.markdown('</div>', unsafe_allow_html=True)

        # PASO 3: UBICACION (Solo si hay Cantidad > 0)
        ubi_masivo = ""
        if id_masivo and cant_masivo > 0:
            st.markdown('<div class="step-box">', unsafe_allow_html=True)
            ubi_masivo = st.text_input("3. UBICACIÓN REAL").upper().strip()
            st.markdown('</div>', unsafe_allow_html=True)

        # PASO 4: FOTO (Opcional, solo si hay Ubicación)
        url_masivo = "NO FOTO"
        if id_masivo and cant_masivo > 0 and ubi_masivo:
            st.markdown('<div class="step-box">', unsafe_allow_html=True)
            url_masivo = st.text_input("4. URL DE FOTO (Opcional)").strip()
            if not url_masivo: url_masivo = "NO FOTO"
            st.markdown('</div>', unsafe_allow_html=True)
            
            # BOTON FINAL
            if st.button("✅ SUBIR MATERIAL"):
                db.collection("materiales").add({
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "item": id_masivo, "cantidad": cant_masivo,
                    "ubicacion": ubi_masivo, "registrado_por": "YAKO", "foto_url": url_masivo
                })
                st.success(f"Cargado: {id_masivo}")
                st.rerun()
        else:
            st.info("Completa los pasos anteriores para habilitar la carga.")

    with t4:
        u_docs = db.collection("USUARIOS").stream()
        for u in u_docs:
            if u.id != "YAKO":
                c_u, c_b = st.columns([3, 1])
                c_u.write(f"ID: {u.id} | {u.to_dict().get('estado')}")
                if c_b.button("ACTIVAR", key=u.id):
                    db.collection("USUARIOS").document(u.id).update({"estado": "ACTIVO"}); st.rerun()

    if st.button("VOLVER AL MENÚ"): st.session_state.page = 'menu'; st.rerun()

# --- RUTAS ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
