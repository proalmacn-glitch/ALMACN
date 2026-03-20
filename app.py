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
    .warning-box { border: 2px solid orange; padding: 15px; border-radius: 10px; background-color: #2b1d00; color: white; text-align: center; margin-bottom: 20px; }
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

# ================= VISTAS =================

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
                if data.get('estado') == 'ACTIVO' or u_in == "YAKO":
                    st.session_state.user = data.get('nombre_personal', u_in).split()[0]
                    st.session_state.user_status = "YAKO" if u_in == "YAKO" else "ACTIVO"
                    st.session_state.page = 'menu'; st.rerun()
                else: st.warning("Cuenta pendiente de activación / 승인 대기 중")
            else: st.error("Acceso Denegado")
            
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USUARIO{random.randint(100, 999)}", f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre_personal": u})
            st.success(f"TOMA FOTO / 사진 찍기:\nUser: {u}\nPass: {p}")
    
    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("SALIDA MATERIALES / 자재 출고"):
        st.session_state.user="INVITADO"; st.session_state.user_status="INVITADO"; ir("SALIDA", "materiales")
    if c2.button("SALIDA HOLDERS / 홀더 출고"):
        st.session_state.user="INVITADO"; st.session_state.user_status="INVITADO"; ir("SALIDA", "holders")
    
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES")
        if st.button("ENTRADA MAT"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT"): ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS")
        if st.button("ENTRADA HOL"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL"): ir("SALIDA", "holders")
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.session_state.user_status == "YAKO" and st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR / 로그아웃"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

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
    if st.button("REGISTRAR / 등록"):
        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": cod,
            "cantidad": cant if acc == "ENTRADA" else -cant, "ubicacion": ubi,
            "registrado_por": st.session_state.user, "foto_url": "NO FOTO"
        })
        st.success("REGISTRADO EXITOSAMENTE"); st.session_state.scanned_id = ""; st.rerun()
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

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
            if f_url:
                try: st.image(f_url)
                except: st.warning("Imagen no disponible")
        else: st.warning("No encontrado")
    if st.button("VOLVER"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def admin():
    if st.session_state.user_status != "YAKO": st.error("ACCESO RESTRINGIDO"); return
    st.title("PANEL CONTROL / 제어판")
    t1, t2, t3, t4 = st.tabs(["BORRAR/삭제", "EXCEL/엑셀", "CARGA EXCEL", "USUARIOS/사용자"])
    
    with t1:
        st.subheader("Eliminar Material o Categoría")
        col_db = st.selectbox("Categoría a limpiar", ["materiales", "holders"])
        c_del = st.text_input("ID Específico (Vació para borrar TODO EL STOCK)").upper()
        
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.warning("⚠️ ESTA ACCIÓN NO SE PUEDE DESHACER")
        # VENTANA DE CONFIRMACIÓN
        seguro = st.checkbox(f"SÍ, ESTOY SEGURO QUE QUIERO ELIMINAR {'EL ITEM ' + c_del if c_del else 'TODO EL STOCK DE ' + col_db.upper()}")
        if seguro:
            if st.button("🔴 CONFIRMAR ELIMINACIÓN DEFINITIVA"):
                if c_del:
                    docs = db.collection(col_db).where("item", "==", c_del).stream()
                    for d in docs: db.collection(col_db).document(d.id).delete()
                    st.success(f"ID {c_del} eliminado.")
                else:
                    docs = db.collection(col_db).stream()
                    for d in docs: db.collection(col_db).document(d.id).delete()
                    st.success(f"Stock de {col_db} vaciado.")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with t2:
        st.subheader("Descargar Stock Actual")
        ce_s = st.selectbox("Colección a descargar", ["materiales", "holders"], key="desc")
        if st.button("📥 GENERAR REPORTE EXCEL"):
            data = [d.to_dict() for d in db.collection(ce_s).stream()]
            if data:
                df_out = pd.DataFrame(data)
                df_resumen = df_out.groupby('item').agg({'cantidad': 'sum', 'ubicacion': 'last'}).reset_index()
                csv = df_resumen.to_csv(index=False).encode('utf-8-sig')
                st.download_button("Descargar CSV", csv, f"stock_{ce_s}.csv", "text/csv")
            else: st.info("Sin datos.")

    with t3:
        st.subheader("Carga Automática desde Excel")
        st.info("Columnas: NOMBRE, ID, CANTIDAD, UBICACION, FOTO")
        archivo = st.file_uploader("Subir .xlsx", type=['xlsx'])
        if archivo:
            df = pd.read_excel(archivo)
            if st.button("🚀 INICIAR CARGA MASIVA"):
                for _, f in df.iterrows():
                    foto = str(f['FOTO']) if pd.notna(f['FOTO']) and str(f['FOTO']).strip() != "" else f"https://picsum.photos/seed/{random.randint(1,999)}/400/300"
                    db.collection("materiales").add({
                        "nombre": str(f['NOMBRE']), "item": str(f['ID']).upper(),
                        "cantidad": int(f['CANTIDAD']), "ubicacion": str(f['UBICACION']).upper(),
                        "foto_url": foto, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "registrado_por": "YAKO"
                    })
                st.success("Carga completada con éxito.")

    with t4:
        st.subheader("Gestión de Usuarios")
        u_docs = db.collection("USUARIOS").stream()
        for u in u_docs:
            ud = u.to_dict()
            if u.id != "YAKO":
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"**ID:** {u.id} | **Estado:** {ud.get('estado')}")
                if c2.button("ACTIVAR", key=f"act_{u.id}"):
                    db.collection("USUARIOS").document(u.id).update({"estado": "ACTIVO"}); st.rerun()
                if c3.button("BORRAR", key=f"del_{u.id}"):
                    db.collection("USUARIOS").document(u.id).delete(); st.rerun()
        
        st.divider()
        st.subheader("Cambiar Clave (YAKO)")
        new_p = st.text_input("Nueva Clave Admin", type="password")
        if st.button("ACTUALIZAR CLAVE"):
            db.collection("USUARIOS").document("YAKO").update({"clave": new_p})
            st.success("Clave de administrador actualizada.")

    if st.button("VOLVER AL MENÚ"): st.session_state.page = 'menu'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
