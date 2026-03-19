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

# --- ESTILOS VISUALES (RESTAURADOS) ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    .stButton>button { background-color: white; color: black; border-radius: 5px; width: 100%; font-weight: bold; border: 2px solid red; }
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stCameraInput"] label, div[data-testid="stTextArea"] label { color: yellow !important; font-size: 16px !important; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { text-align: center; }
    div[data-testid="stMetricValue"] { font-size: 55px !important; color: cyan !important; text-align: center !important; font-weight: bold !important; }
    div[data-testid="stMetricLabel"] { font-size: 20px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    .yako-adjust { border: 2px solid red; padding: 15px; border-radius: 10px; margin-top: 20px; background-color: #220000; text-align: center; }
    .qr-box { background-color: white; padding: 15px; border-radius: 10px; text-align: center; margin-top: 15px; display: inline-block; color: black; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'user' not in st.session_state: st.session_state.user = None
if 'user_status' not in st.session_state: st.session_state.user_status = None
if 'page' not in st.session_state: st.session_state.page = 'login'

# ================= FUNCIONES DE NAVEGACIÓN =================

def login():
    st.title("LOGIN / 로그인")
    st.markdown("<h3 style='color: white !important;'>ALMACÉN / 창고</h3>", unsafe_allow_html=True)
    user_input = st.text_input("Usuario / 사용자").upper().strip()
    password = st.text_input("Clave / 비밀번호", type="password").strip()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ENTRAR / 입장"):
            if not user_input: st.warning("Escribe un usuario")
            else:
                data = None; doc_id = None 
                doc = db.collection("USUARIOS").document(user_input).get()
                if doc.exists: data = doc.to_dict(); doc_id = user_input
                else:
                    query = db.collection("USUARIOS").where("nombre_personal", "==", user_input).stream()
                    for d in query: data = d.to_dict(); doc_id = d.id; break 
                
                if data and str(data.get('clave')) == password:
                    st.session_state.user = data.get('nombre_personal', doc_id)
                    st.session_state.user_status = data.get('estado', 'PENDIENTE')
                    if doc_id == "YAKO": st.session_state.user_status = "YAKO"
                    st.session_state.page = 'menu'; st.rerun()
                else: st.error("Credenciales Incorrectas / 잘못된 자격 증명")

    with col2:
        if st.button("REGISTRARSE / 등록"):
            u = f"USUARIO{random.randint(100, 999)}"
            p = f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre_personal": u})
            st.success(f"SOLICITUD ENVIADA A YAKO:\nUser: {u}\nPass: {p}")

    st.divider()
    st.markdown("<h4 style='color: yellow !important; text-align: center;'>OPCIONES RÁPIDAS</h4>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("SALIDA MATERIALES"): 
            st.session_state.user="INVITADO"; st.session_state.user_status="INVITADO"; ir("SALIDA", "materiales")
    with c2:
        if st.button("SALIDA HOLDERS"): 
            st.session_state.user="INVITADO"; st.session_state.user_status="INVITADO"; ir("SALIDA", "holders")
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"SESIÓN: {st.session_state.user} | ROL: {st.session_state.user_status}")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES / 자재")
        # --- SEGURIDAD DE ENTRADA ---
        if st.button("ENTRADA MAT"): 
            if st.session_state.user_status in ["ACTIVO", "YAKO"]: ir("ENTRADA", "materiales")
            else: st.error("ACCESO DENEGADO (SOLO ACTIVO)")
        if st.button("SALIDA MAT"): ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS / 홀더")
        if st.button("ENTRADA HOL"): 
            if st.session_state.user_status in ["ACTIVO", "YAKO"]: ir("ENTRADA", "holders")
            else: st.error("ACCESO DENEGADO (SOLO ACTIVO)")
        if st.button("SALIDA HOL"): ir("SALIDA", "holders")

    st.divider()
    if st.button("BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.session_state.user_status == "YAKO":
        if st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR / 로그아웃"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

def ir(acc, cat):
    st.session_state.accion = acc; st.session_state.categoria = cat; st.session_state.page = 'form'; st.rerun()

def formulario():
    cat = st.session_state.categoria; acc = st.session_state.accion
    st.header(f"{cat.upper()} - {acc}")
    cod = st.text_input("ID / CÓDIGO").upper().strip()
    cant = st.number_input("CANTIDAD", min_value=1, step=1)
    
    if acc == "ENTRADA":
        ubi = st.text_input("UBICACIÓN / 위치").upper().strip()
        dest = "ALMACEN"
    else:
        ubi = "SALIDA"
        dest = st.text_input("QUIEN RETIRA / 수령자").upper().strip()

    foto = st.camera_input("FOTO EVIDENCIA / 증거 사진")
    
    if st.button("CONFIRMAR REGISTRO"):
        if not cod: st.error("Falta ID"); return
        
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
            "ubicacion": ubi, "registrado_por": st.session_state.user, "solicitante": dest, "foto_url": url_foto
        })
        
        st.success("✅ REGISTRO EXITOSO")
        # --- GENERACIÓN DE QR ---
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={cod}"
        st.markdown(f'<div class="qr-box"><img src="{qr_url}"><br><b>{cod}</b></div>', unsafe_allow_html=True)
        if st.button("NUEVO REGISTRO"): st.rerun()

    if st.button("VOLVER"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO").upper().strip()
    if c:
        stock = 0; ubis = set(); last_foto = None; found_col = None
        for col in ["materiales", "holders"]:
            docs = db.collection(col).where("item", "==", c).stream()
            for d in docs:
                found_col = col
                dt = d.to_dict(); stock += dt.get('cantidad', 0)
                u = str(dt.get('ubicacion', dt.get('ubi', ''))).upper()
                if u and "SALIDA" not in u and u != "NONE": ubis.add(u)
                if dt.get('foto_url') and dt.get('foto_url') not in ["NO FOTO", "ERROR"]: last_foto = dt.get('foto_url')
        
        if found_col:
            st.subheader(f"ID: {c}")
            c1, c2 = st.columns(2)
            c1.metric("STOCK TOTAL", stock)
            c2.metric("UBICACIONES", ", ".join(ubis) if ubis else "---")
            if last_foto: st.image(last_foto, caption="Última Evidencia")
            
            # --- PANEL AJUSTE YAKO ---
            if st.session_state.user_status == "YAKO":
                st.markdown('<div class="yako-adjust"><h3>⚠️ AJUSTE MANUAL</h3>', unsafe_allow_html=True)
                adj_cant = st.number_input("Cantidad (+/-)", step=1)
                adj_ubi = st.text_input("Nueva Ubicación Real").upper()
                if st.button("APLICAR AJUSTE"):
                    db.collection(found_col).add({
                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "item": c, "cantidad": adj_cant, "ubicacion": adj_ubi if adj_ubi else "AJUSTE",
                        "registrado_por": "YAKO", "solicitante": "AJUSTE", "foto_url": "NO FOTO"
                    })
                    st.success("Ajuste realizado"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else: st.warning("No se encontró el material")

    if st.button("VOLVER"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def admin():
    st.title("PANEL DE CONTROL / 제어판")
    tab1, tab2, tab3 = st.tabs(["USUARIOS", "EXCEL/CSV", "CARGA MASIVA"])
    
    with tab1:
        st.subheader("Gestión de Usuarios")
        users = db.collection("USUARIOS").stream()
        for u in users:
            ud = u.to_dict()
            col_a, col_b = st.columns([3, 1])
            col_a.write(f"User: {u.id} | Nombre: {ud.get('nombre_personal')} | Status: {ud.get('estado')}")
            if col_b.button("ACTIVAR", key=u.id):
                db.collection("USUARIOS").document(u.id).update({"estado": "ACTIVO"})
                st.rerun()
    
    with tab2:
        cat_sel = st.selectbox("Categoría a exportar", ["materiales", "holders"])
        if st.button("GENERAR REPORTE"):
            items = [d.to_dict() for d in db.collection(cat_sel).stream()]
            if items:
                df = pd.DataFrame(items)
                st.download_button("Descargar CSV", df.to_csv(index=False).encode('utf-8-sig'), f"reporte_{cat_sel}.csv", "text/csv")
    
    with tab3:
        st.write("Formato: ID CANTIDAD UBICACION")
        txt = st.text_area("Pega la lista aquí")
        if st.button("PROCESAR CARGA"):
            for line in txt.split('\n'):
                parts = line.split()
                if len(parts) >= 3:
                    db.collection("materiales").add({
                        "fecha": datetime.now().strftime("%Y-%m-%d"),
                        "item": parts[0].upper(), "cantidad": int(parts[1]),
                        "ubicacion": parts[2].upper(), "registrado_por": "YAKO", "foto_url": "NO FOTO"
                    })
            st.success("Carga masiva finalizada")

    if st.button("VOLVER AL MENÚ"): st.session_state.page = 'menu'; st.rerun()

# --- LÓGICA DE RUTAS ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
