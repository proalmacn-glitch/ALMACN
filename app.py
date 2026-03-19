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
    .yako-adjust { border: 2px solid red; padding: 15px; border-radius: 10px; margin-top: 20px; background-color: #220000; }
    /* Estilo para la imagen del producto */
    .img-container { border: 2px solid #333; border-radius: 10px; padding: 5px; background-color: #000; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'user' not in st.session_state: st.session_state.user = None
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
            if not user_input: st.warning("Escribe un usuario")
            else:
                data = None; doc_id = None 
                doc = db.collection("USUARIOS").document(user_input).get()
                if doc.exists: data = doc.to_dict(); doc_id = user_input
                else:
                    query = db.collection("USUARIOS").where("nombre_personal", "==", user_input).stream()
                    for d in query: data = d.to_dict(); doc_id = d.id; break 

                if data:
                    if str(data.get('clave')) == password:
                        if doc_id == "YAKO": st.session_state.user = "YAKO"; st.session_state.page = 'menu'; st.rerun()
                        elif data.get('estado') == "ACTIVO":
                            if data.get('cambio_pendiente', False): st.session_state.temp_user = doc_id; st.session_state.page = 'cambio_clave'; st.rerun()
                            else: st.session_state.user = data.get('nombre_personal', doc_id); st.session_state.page = 'menu'; st.rerun()
                        else: st.warning("Cuenta Pendiente")
                    else: st.error("Clave Incorrecta")
                else: st.error("Usuario no existe")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            animales = ["PERRO", "GATO", "LEON", "TIGRE", "PUMA", "OSO", "TORO", "LOBO", "RATA", "PATO"]
            n = len(list(db.collection("USUARIOS").stream()))
            u = f"USUARIO{n+1}"; p = f"{random.choice(animales)}{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre": u, "nombre_personal": u, "cambio_pendiente": True})
            st.success(f"TOMA FOTO:\nUser: {u}\nPass: {p}")

    st.divider()
    if st.button("🔍 BUSCAR MATERIAL / 재고 검색"): st.session_state.page = 'buscar'; st.rerun()

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
    if st.button("BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.button("SALIR / 로그아웃"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

def ir(acc, cat):
    st.session_state.accion = acc; st.session_state.categoria = cat; st.session_state.page = 'form'; st.rerun()

def formulario():
    cat = st.session_state.categoria.upper(); acc = st.session_state.accion
    st.header(f"{cat} - {acc}")
    cod = st.text_input("ID / CÓDIGO", key="reg_cod").upper().strip()
    cant = st.number_input("CANTIDAD", min_value=1, step=1, key="reg_cant")
    ubi = st.text_input("UBICACIÓN", key="reg_ubi").upper().strip() if acc == "ENTRADA" else "SALIDA"
    st.write("---")
    foto = st.camera_input("FOTO EVIDENCIA", key="reg_foto")
    
    if st.button("REGISTRAR / 등록"):
        url_foto = "NO FOTO"
        if foto:
            bucket = storage.bucket()
            blob = bucket.blob(f"evidencias/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cod}.jpg")
            blob.upload_from_file(foto, content_type='image/jpeg')
            blob.make_public(); url_foto = blob.public_url

        db.collection(st.session_state.categoria).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "item": cod, "cantidad": cant if acc == "ENTRADA" else -cant,
            "ubicacion": ubi, "registrado_por": st.session_state.user, "foto_url": url_foto
        })
        st.success("✅ ÉXITO"); st.rerun()
    
    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

# ================= MÓDULO BUSCAR (PASO 1, 2 Y 3) =================

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO / 코드 (Parcial o Completo)").upper().strip()
    
    final_code = None
    coleccion = None
    
    if c:
        matches = []
        for col in ["materiales", "holders"]:
            docs = db.collection(col).stream()
            for d in docs:
                item = d.to_dict().get('item', '')
                if c in item: matches.append((item, col))
        
        unique_matches = sorted(list(set(matches)))
        
        if not unique_matches: st.warning("No encontrado")
        elif len(unique_matches) > 1:
            opc = [f"{m[0]} ({m[1].upper()})" for m in unique_matches]
            sel = st.selectbox("Resultados / 결과", opc)
            final_code = sel.split(" (")[0]
            coleccion = sel.split(" (")[1].replace(")", "").lower()
        else:
            final_code = unique_matches[0][0]
            coleccion = unique_matches[0][1]

    if final_code:
        # Calcular Stock y Ubicaciones
        stock_total = 0
        ubicaciones = set()
        ultima_foto = None
        
        docs = db.collection(coleccion).where("item", "==", final_code).stream()
        for d in docs:
            dt = d.to_dict()
            stock_total += dt.get('cantidad', 0)
            u = dt.get('ubicacion', '').upper()
            if u and "SALIDA" not in u: ubicaciones.add(u)
            # Guardamos la foto más reciente que no sea "NO FOTO"
            if dt.get('foto_url') and dt.get('foto_url') != "NO FOTO":
                ultima_foto = dt.get('foto_url')

        st.markdown(f"<h2 style='color: white !important;'>RESULTADO: {final_code}</h2>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("STOCK / 재고", stock_total)
        with c2:
            st.metric("UBICACIÓN / 위치", ", ".join(ubicaciones) if ubicaciones else "---")
        
        st.divider()
        
        # PASO 3: MOSTRAR IMAGEN SI EXISTE
        if ultima_foto:
            st.markdown("<h4 style='color: yellow !important;'>FOTO DEL MATERIAL / 자재 사진</h4>", unsafe_allow_html=True)
            st.markdown(f'<div class="img-container"><img src="{ultima_foto}" style="width:100%; border-radius:10px;"></div>', unsafe_allow_html=True)
        else:
            st.info("Sin foto disponible / 사진 없음")

    if st.button("VOLVER / 돌아가기"):
        st.session_state.page = 'login' if not st.session_state.user else 'menu'
        st.rerun()

# --- LÓGICA DE NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
