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
    .img-container { border: 2px solid #333; border-radius: 10px; padding: 5px; background-color: #000; text-align: center; margin-top: 10px; }
    .qr-container { background-color: white; padding: 10px; border-radius: 10px; text-align: center; margin-top: 10px; display: inline-block; }
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
                        nombre_mostrar = data.get('nombre_personal', doc_id)
                        if doc_id == "YAKO": st.session_state.user = "YAKO"; st.session_state.page = 'menu'; st.rerun()
                        elif data.get('estado') == "ACTIVO":
                            if data.get('cambio_pendiente', False): st.session_state.temp_user = doc_id; st.session_state.page = 'cambio_clave'; st.rerun()
                            else: st.session_state.user = nombre_mostrar; st.session_state.page = 'menu'; st.rerun()
                        else: st.warning("Cuenta Pendiente")
                    else: st.error("Clave Incorrecta")
                else: st.error("Usuario no existe")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            animales = ["PERRO", "GATO", "LEON", "TIGRE", "PUMA", "OSO", "TORO", "LOBO", "RATA", "PATO"]
            u = f"USUARIO{random.randint(100, 999)}"
            p = f"{random.choice(animales)}{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre": u, "nombre_personal": u, "cambio_pendiente": True})
            st.success(f"User: {u}\nPass: {p}")
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("SALIDA MATERIALES"): st.session_state.user = "INVITADO"; st.session_state.es_invitado = True; ir("SALIDA", "materiales")
    with c2:
        if st.button("SALIDA HOLDERS"): st.session_state.user = "INVITADO"; st.session_state.es_invitado = True; ir("SALIDA", "holders")
    if st.button("🔍 BUSCAR MATERIAL / 재고 검색"): st.session_state.page = 'buscar'; st.rerun()

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA: {st.session_state.user}")
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
    if st.session_state.user == "YAKO":
        if st.button("PANEL CONTROL"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR / 로그아웃"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

def ir(acc, cat):
    st.session_state.accion = acc; st.session_state.categoria = cat; st.session_state.page = 'form'; st.rerun()

def formulario():
    cat = st.session_state.categoria.upper(); acc = st.session_state.accion
    st.header(f"{cat} - {acc}")
    cod = st.text_input("ID / CÓDIGO", key="reg_cod").upper().strip()
    cant = st.number_input("CANTIDAD", min_value=1, step=1, key="reg_cant")
    conf = st.number_input("CONFIRMAR CANTIDAD", min_value=1, step=1, key="reg_conf")
    
    if acc == "ENTRADA":
        ubi = st.text_input("UBICACIÓN", key="reg_ubi").upper().strip()
        dest = "ALMACEN"
    else:
        ubi = "SALIDA"; dest = st.text_input("QUIEN RETIRA", key="reg_dest").upper().strip()

    foto = st.camera_input("FOTO EVIDENCIA")
    
    if st.button("REGISTRAR / 등록"):
        if not cod: st.error("Falta Código"); return
        if cant != conf: st.error("Cantidades no coinciden"); return
        
        url_foto = "NO FOTO"
        if foto:
            try:
                bucket = storage.bucket()
                blob = bucket.blob(f"evidencias/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cod}.jpg")
                blob.upload_from_file(foto, content_type='image/jpeg')
                blob.make_public(); url_foto = blob.public_url
            except Exception as e: url_foto = "ERROR_SUBIDA"

        db.collection(st.session_state.categoria).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "item": cod, "cantidad": cant if acc == "ENTRADA" else -cant,
            "ubicacion": ubi, "registrado_por": st.session_state.user, "solicitante": dest, "foto_url": url_foto
        })
        
        # --- GENERACIÓN DE QR AUTOMÁTICO AL REGISTRAR ---
        st.success("✅ REGISTRO EXITOSO / 성공")
        st.markdown(f"### QR GENERADO PARA: {cod}")
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={cod}"
        st.markdown(f'<div class="qr-container"><img src="{qr_url}"><br><b style="color:black;">{cod}</b></div>', unsafe_allow_html=True)
        st.info("Puedes tomar captura al QR para identificar tu material.")
        st.button("LISTO / SIGUIENTE", on_click=lambda: st.rerun())
    
    if st.button("VOLVER"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO (Parcial o Completo)").upper().strip()
    if c:
        stock = 0; ubi_list = set(); foto_mostrar = None; coleccion = None
        matches = []
        for col in ["materiales", "holders"]:
            docs = db.collection(col).stream()
            for d in docs:
                dt = d.to_dict()
                if c in dt.get('item', ''): matches.append((dt.get('item'), col))
        unique_matches = sorted(list(set(matches)))
        if unique_matches:
            if len(unique_matches) > 1:
                sel = st.selectbox("Selecciona:", [f"{m[0]} ({m[1].upper()})" for m in unique_matches])
                final_code = sel.split(" (")[0]; coleccion = sel.split(" (")[1].replace(")", "").lower()
            else:
                final_code = unique_matches[0][0]; coleccion = unique_matches[0][1]

            res_docs = db.collection(coleccion).where("item", "==", final_code).stream()
            for dr in res_docs:
                dt_r = dr.to_dict(); stock += dt_r.get('cantidad', 0)
                l = str(dt_r.get('ubicacion', dt_r.get('ubi', ''))).upper()
                if "SALIDA" not in l and l != "": ubi_list.add(l)
                if dt_r.get('foto_url') and dt_r.get('foto_url') not in ["NO FOTO", "ERROR"]: foto_mostrar = dt_r.get('foto_url')

            st.subheader(f"RESULTADO: {final_code}")
            c1, c2 = st.columns(2)
            c1.metric("STOCK", stock); c2.metric("UBICACIÓN", ", ".join(ubi_list) if ubi_list else "---")
            if foto_mostrar:
                try: st.image(foto_mostrar, caption=f"ID: {final_code}")
                except: st.info("Imagen no disponible")
            
            # MOSTRAR QR TAMBIÉN EN LA BÚSQUEDA
            st.markdown("---")
            st.markdown("#### QR DE IDENTIFICACIÓN")
            qr_url_busq = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={final_code}"
            st.markdown(f'<div class="qr-container"><img src="{qr_url_busq}"><br><b style="color:black;">{final_code}</b></div>', unsafe_allow_html=True)

    if st.button("VOLVER"): st.session_state.page = 'login' if st.session_state.user in [None, "INVITADO"] else 'menu'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
