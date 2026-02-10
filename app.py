import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage
import pandas as pd
from datetime import datetime
import os
import random

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="YAKO PRO WEB", page_icon="📦", layout="centered")

# --- CONEXIÓN FIREBASE + FOTOS (STORAGE) ---
if not firebase_admin._apps:
    try:
        # TU BUCKET PARA LAS FOTOS
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
        st.error(f"Error Conexión: {e}")

db = firestore.client()

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    .stButton>button { background-color: white; color: black; border-radius: 5px; width: 100%; font-weight: bold; border: 2px solid red; }
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stCameraInput"] label { color: yellow !important; font-size: 16px !important; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { text-align: center; }
    /* NÚMEROS GIGANTES */
    div[data-testid="stMetricValue"] { font-size: 55px !important; color: cyan !important; text-align: center !important; font-weight: bold !important; }
    div[data-testid="stMetricLabel"] { font-size: 20px !important; color: white !important; text-align: center !important; justify-content: center !important; }
    div[data-testid="stMetric"] { display: flex; flex-direction: column; align-items: center; background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = 'login'

# ================= FUNCIONES =================

def login():
    st.title("LOGIN / 로그인")
    st.markdown("<h3 style='color: white !important;'>ALMACÉN / 창고</h3>", unsafe_allow_html=True)
    
    user = st.text_input("Usuario / 사용자").upper().strip()
    password = st.text_input("Clave / 비밀번호", type="password").strip()
    
    col1, col2 = st.columns(2)
    if col1.button("ENTRAR / 입장"):
        doc = db.collection("USUARIOS").document(user).get()
        if doc.exists:
            data = doc.to_dict()
            if str(data.get('clave')) == password:
                if user == "YAKO":
                    st.session_state.user = "YAKO"; st.session_state.page = 'menu'; st.rerun()
                elif data.get('estado') == "ACTIVO":
                    if data.get('cambio_pendiente', False):
                        st.session_state.temp_user = user; st.session_state.page = 'cambio_clave'; st.rerun()
                    else:
                        st.session_state.user = data.get('nombre_personal', user); st.session_state.page = 'menu'; st.rerun()
                else: st.warning("Cuenta Pendiente")
            else: st.error("Clave Incorrecta")
        else: st.error("Usuario no existe")

    if col2.button("REGISTRARSE / 등록"):
        animales = ["LEON", "TIGRE", "AGUILA", "LOBO", "OSO", "TORO", "GATO", "PERRO", "PUMA", "ZORRO", "HALCON", "DRAGON", "COBRA", "PANTERA", "TIBURON", "BUFALO", "RINOCERONTE", "ELEFANTE", "JAGUAR", "FENIX"]
        n = len(list(db.collection("USUARIOS").stream()))
        u = f"USUARIO{n+1}"
        an = random.choice(animales)
        num = random.randint(10, 99)
        p = f"{an}{num}"
        db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre": u, "cambio_pendiente": True})
        st.success(f"TOMA FOTO:\nUser: {u}\nPass: {p}")

    st.divider()

    # --- SALIDA RÁPIDA ---
    st.markdown("<h4 style='color: yellow !important;'>SALIDA RÁPIDA (SIN LOGIN) / 빠른 출고</h4>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("SALIDA MATERIALES / 자재 출고"): 
            st.session_state.user = "INVITADO / 손님"; st.session_state.es_invitado = True; ir("SALIDA", "materiales")
    with c2:
        if st.button("SALIDA HOLDERS / 홀더 출고"): 
            st.session_state.user = "INVITADO / 손님"; st.session_state.es_invitado = True; ir("SALIDA", "holders")

    st.write("") # Espacio
    st.write("") # Espacio

    # --- BOTÓN BUSCAR (AHORA ESTÁ AL FINAL, DONDE PEDISTE) ---
    if st.button("🔍 BUSCAR MATERIAL / 재고 검색 (Acceso Libre)"):
        st.session_state.page = 'buscar'
        st.rerun()

def cambio_clave():
    st.title("PRIMER INICIO")
    nn = st.text_input("Nuevo Nombre").upper()
    nc = st.text_input("Nueva Clave", type="password")
    nc2 = st.text_input("Confirmar Clave", type="password")
    if st.button("GUARDAR"):
        if nc == nc2 and nn and nc:
            db.collection("USUARIOS").document(st.session_state.temp_user).update({"nombre_personal": nn, "clave": nc, "cambio_pendiente": False})
            st.session_state.user = nn; st.session_state.es_invitado = False; st.session_state.page = 'menu'; st.rerun()
        else: st.error("Error Claves")

def menu():
    st.title("MENÚ / 메뉴")
    st.info(f"USUARIO: {st.session_state.user}")
    
    if st.session_state.user == "YAKO":
        pend = len(list(db.collection("USUARIOS").where("estado", "==", "PENDIENTE").stream()))
        if pend > 0: st.error(f"⚠ {pend} USUARIOS PENDIENTES")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES")
        if st.button("ENTRADA MAT"): st.session_state.es_invitado = False; ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT"): st.session_state.es_invitado = False; ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS")
        if st.button("ENTRADA HOL"): st.session_state.es_invitado = False; ir("ENTRADA", "holders")
        if st.button("SALIDA HOL"): st.session_state.es_invitado = False; ir("SALIDA", "holders")
        
    st.divider()
    if st.button("BUSCAR"): st.session_state.page = 'buscar'; st.rerun()
    if st.session_state.user:
        if st.button("ADMIN PANEL"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

def ir(acc, cat):
    st.session_state.accion = acc; st.session_state.categoria = cat; st.session_state.page = 'form'; st.rerun()

def formulario():
    cat = st.session_state.categoria.upper(); acc = st.session_state.accion
    st.header(f"{cat} - {acc}")
    if st.session_state.get('es_invitado', False): st.warning("MODO INVITADO")

    cod = st.text_input("ID / CÓDIGO").upper().strip()
    
    # --- CAMPO CANTIDAD ---
    cant = st.number_input("CANTIDAD / 수량", min_value=1, step=1, value=None, placeholder="Escribe cantidad")
    
    # --- CAMPO CONFIRMACIÓN (OBLIGATORIO) ---
    st.caption("Por seguridad, confirma la cantidad:")
    conf = st.number_input("CONFIRMAR CANTIDAD / 수량 확인", min_value=1, step=1, value=None, placeholder="Repite el número")

    if acc == "ENTRADA": ubi = st.text_input("UBICACIÓN").upper().strip(); dest = "ALMACEN"
    else: ubi = "SALIDA / 출고"; dest = st.text_input("QUIEN RETIRA").upper().strip()
    
    # --- FOTO DE EVIDENCIA (CÁMARA) ---
    st.write("---")
    foto = st.camera_input("FOTO EVIDENCIA / 증거 사진")
    st.write("---")
        
    if st.button("REGISTRAR"):
        if not cod: st.error("Falta Código"); return
        if cant is None or conf is None: st.error("Faltan Cantidades"); return
        
        # VALIDACIÓN: SI NO COINCIDEN, NO DEJA PASAR
        if cant != conf: st.error(f"❌ ERROR: Las cantidades no coinciden ({cant} vs {conf})"); return

        if acc == "ENTRADA":
            if not ubi: st.error("Falta Ubicación"); return
            val = cant
        else:
            tot = 0
            for d in db.collection(st.session_state.categoria).where("item", "==", cod).stream(): tot += d.to_dict().get('cantidad', 0)
            if cant > tot: st.error(f"Stock insuficiente (Max: {tot})"); return
            if not dest: st.error("Falta Quien Retira"); return
            val = -cant
            
        # SUBIR FOTO A FIREBASE Y OBTENER LINK
        url_foto = "NO FOTO"
        if foto:
            try:
                bucket = storage.bucket()
                nombre_archivo = f"evidencias/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cod}.jpg"
                blob = bucket.blob(nombre_archivo)
                blob.upload_from_file(foto, content_type='image/jpeg')
                blob.make_public() 
                url_foto = blob.public_url # ESTE LINK VA AL EXCEL
            except Exception as e:
                st.error(f"Error subiendo foto: {e}")
                url_foto = "ERROR FOTO"

        db.collection(st.session_state.categoria).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": cod, "cantidad": val, "ubicacion": ubi, 
            "registrado_por": st.session_state.user, "solicitante": dest, "foto_url": url_foto
        })
        st.success("EXITO / 성공")
        
    if st.button("VOLVER"): 
        if st.session_state.get('es_invitado', False): st.session_state.user = None; st.session_state.page = 'login'
        else: st.session_state.page = 'menu'
        st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO").upper()
    s = 0; u_list = set()
    
    if c:
        for col in ["materiales", "holders"]:
            for d in db.collection(col).where("item", "==", c).stream():
                dt = d.to_dict(); s += dt.get('cantidad', 0)
                l = dt.get('ubicacion', '').upper()
                if "SALIDA" not in l and l != "": u_list.add(l)
        
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("STOCK", s)
    c2.metric("UBICACIÓN", ", ".join(u_list) if u_list else "---")
    st.divider()

    if st.button("VOLVER"):
        if st.session_state.user is None: st.session_state.page = 'login'
        else: st.session_state.page = 'menu'
        st.rerun()

def admin():
    st.title("ADMIN")
    t1, t2, t3, t4, t5 = st.tabs(["BORRAR", "EXCEL", "STOCK", "PERFIL", "USUARIOS"])
    
    with t1:
        col = st.selectbox("Cat", ["materiales", "holders"])
        c = st.text_input("Código").upper()
        if st.button("BORRAR"):
            for d in db.collection(col).where("item", "==", c).stream(): db.collection(col).document(d.id).delete()
            st.success("Borrado")

    with t2:
        ce = st.selectbox("Descargar", ["materiales", "holders"])
        if st.button("GENERAR EXCEL"):
            data = []
            for d in db.collection(ce).stream():
                dt = d.to_dict(); q = dt.get('cantidad', 0)
                data.append({
                    "FECHA": dt.get('fecha', ''), "REGISTRADO": dt.get('registrado_por', ''), "ITEM": dt.get('item', ''),
                    "CANT": q, "TIPO": "ENTRADA" if q>=0 else "SALIDA", "UBI": dt.get('ubicacion', ''), 
                    "SOLICITA": dt.get('solicitante', ''), "FOTO (LINK)": dt.get('foto_url', 'NO')
                })
            if data:
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("DESCARGAR CSV", csv, "reporte.csv", "text/csv")

    with t3:
        st.subheader("CARGA MASIVA")
        cat_st = st.selectbox("Cat", ["materiales", "holders"], key="mas")
        txt = st.text_area("ID CANT UBI")
        if st.button("CARGAR"):
            for l in txt.split('\n'):
                p = l.replace('\t', ' ').split()
                if len(p)>=3: db.collection(cat_st).add({"fecha": datetime.now().strftime("%Y-%m-%d"), "item": p[0].upper(), "cantidad": int(p[1]), "ubicacion": p[2].upper(), "registrado_por": st.session_state.user, "tipo": "MASIVA"})
            st.success("Cargado")

    with t4:
        if st.session_state.user == "YAKO":
            n = st.text_input("Nombre"); p = st.text_input("Clave", type="password"); p2 = st.text_input("Conf", type="password")
            if st.button("Update"):
                if p==p2: db.collection("USUARIOS").document("YAKO").update({"nombre": n, "clave": p}); st.success("OK")

    with t5:
        # ACTUALIZACIÓN: Ver nombre real en Panel Yako
        if st.session_state.user == "YAKO":
            us = []; u_ids = []
            for u in db.collection("USUARIOS").stream():
                if u.id != "YAKO":
                    d = u.to_dict()
                    nombre = d.get('nombre_personal', 'SIN NOMBRE')
                    estado = d.get('estado', '')
                    us.append(f"{u.id} - {nombre} ({estado})")
                    u_ids.append(u.id)
            if us:
                s = st.selectbox("Usuario", us)
                sid = u_ids[us.index(s)]
                c1, c2 = st.columns(2)
                if c1.button("ACTIVAR"): db.collection("USUARIOS").document(sid).update({"estado": "ACTIVO"}); st.success("OK"); st.rerun()
                if c2.button("BORRAR"): db.collection("USUARIOS").document(sid).delete(); st.success("X"); st.rerun()

    if st.button("VOLVER"): st.session_state.page = 'menu'; st.rerun()

if st.session_state.page == 'login': login()
elif st.session_state.page == 'registro': registro()
elif st.session_state.page == 'cambio_clave': cambio_clave()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
