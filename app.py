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

# ================= FUNCIONES =================

def login():
    st.title("LOGIN / 로그인")
    st.markdown("<h3 style='color: white !important;'>ALMACÉN / 창고</h3>", unsafe_allow_html=True)
    user_input = st.text_input("Usuario / 사용자").upper().strip()
    password = st.text_input("Clave / 비밀번호", type="password").strip()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(user_input).get()
            data = None; doc_id = None
            if doc.exists: data = doc.to_dict(); doc_id = user_input
            else:
                query = db.collection("USUARIOS").where("nombre_personal", "==", user_input).stream()
                for d in query: data = d.to_dict(); doc_id = d.id; break 
            
            if data and str(data.get('clave')) == password:
                st.session_state.user = data.get('nombre_personal', doc_id)
                st.session_state.user_status = data.get('estado', 'PENDIENTE')
                if doc_id == "YAKO": st.session_state.user_status = "YAKO"
                st.session_state.page = 'menu'; st.rerun()
            else: st.error("Acceso Denegado / access 거부됨")

    with col2:
        if st.button("REGISTRARSE / 등록"):
            u = f"USUARIO{random.randint(100, 999)}"
            p = f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre_personal": u})
            st.success(f"TOMA FOTO / 사진 찍기:\nUser: {u}\nPass: {p}")

    st.divider()
    st.markdown("<h4 style='color: yellow !important;'>SALIDA RÁPIDA (SIN LOGIN) / 빠른 출고</h4>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("SALIDA MATERIALES / 자재 출고"): 
            st.session_state.user="INVITADO"; st.session_state.user_status="INVITADO"; ir("SALIDA", "materiales")
    with c2:
        if st.button("SALIDA HOLDERS / 홀더 출고"): 
            st.session_state.user="INVITADO"; st.session_state.user_status="INVITADO"; ir("SALIDA", "holders")
    
    if st.button("🔍 BUSCAR MATERIAL / 재고 검색"): st.session_state.page = 'buscar'; st.rerun()
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA / 안녕하세요: {st.session_state.user} ({st.session_state.user_status})")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES / 자재")
        if st.button("ENTRADA MAT / 자재 입고"): 
            if st.session_state.user_status in ["ACTIVO", "YAKO"]: ir("ENTRADA", "materiales")
            else: st.error("SOLO PERSONAL AUTORIZADO / 승인된 인원만 가능")
        if st.button("SALIDA MAT / 자재 출고"): ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS / 홀더")
        if st.button("ENTRADA HOL / 홀더 입고"): 
            if st.session_state.user_status in ["ACTIVO", "YAKO"]: ir("ENTRADA", "holders")
            else: st.error("SOLO PERSONAL AUTORIZADO / 승인된 인원만 가능")
        if st.button("SALIDA HOL / 홀더 출고"): ir("SALIDA", "holders")

    st.divider()
    col_bt, col_gf = st.columns([1.5, 1])
    with col_bt:
        if st.button("BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
        if st.session_state.user_status == "YAKO":
            if st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
        if st.button("SALIR / 로그아웃"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()
    with col_gf:
        st.image("https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExZHV3YjNoYXFxYXA4MDl5Z3NyYWpkM2w5MDR0dnE3YWJjMGVuaTNpcSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/jTYy5WWGYTBp610Ddd/giphy.gif", use_column_width=True)

def ir(acc, cat):
    st.session_state.accion = acc; st.session_state.categoria = cat; st.session_state.page = 'form'; st.rerun()

def formulario():
    cat = st.session_state.categoria; acc = st.session_state.accion
    st.header(f"{cat.upper()} - {acc}")
    cod = st.text_input("ID / CÓDIGO / 코드").upper().strip()
    cant = st.number_input("CANTIDAD / 수량", min_value=1, step=1)
    ubi = st.text_input("UBICACIÓN / 위치").upper().strip() if acc == "ENTRADA" else "SALIDA"
    foto = st.camera_input("FOTO EVIDENCIA / 증거 사진")
    
    if st.button("REGISTRAR / 등록"):
        url_f = "NO FOTO"
        if foto:
            try:
                bucket = storage.bucket()
                blob = bucket.blob(f"evidencias/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cod}.jpg")
                blob.upload_from_file(foto, content_type='image/jpeg')
                blob.make_public(); url_f = blob.public_url
            except: url_f = "ERROR_SUBIDA"

        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "item": cod, "cantidad": cant if acc == "ENTRADA" else -cant,
            "ubicacion": ubi, "registrado_por": st.session_state.user, "foto_url": url_f
        })
        st.success("✅ ÉXITO / 성공")
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={cod}"
        st.markdown(f'<div class="qr-box"><img src="{qr_url}"><br><b style="color:black;">{cod}</b></div>', unsafe_allow_html=True)
        if st.button("SIGUIENTE / 다음"): st.rerun()

    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO / 코드").upper().strip()
    if c:
        stock = 0; u_list = set(); f_url = None; col_found = None
        for col in ["materiales", "holders"]:
            docs = db.collection(col).where("item", "==", c).stream()
            for d in docs:
                col_found = col
                dt = d.to_dict(); stock += dt.get('cantidad', 0)
                l = str(dt.get('ubicacion', dt.get('ubi', ''))).upper()
                if l and "SALIDA" not in l and l != "NONE": u_list.add(l)
                if dt.get('foto_url') and dt.get('foto_url') not in ["NO FOTO", "ERROR"]: f_url = dt.get('foto_url')
        
        if col_found:
            st.subheader(f"RESULTADO: {c}")
            c1, c2 = st.columns(2)
            c1.metric("STOCK / 재고", stock)
            c2.metric("UBICACIÓN / 위치", ", ".join(u_list) if u_list else "---")
            if f_url: st.image(f_url, caption=f"ID: {c}")
            
            if st.session_state.user_status == "YAKO":
                st.markdown('<div class="yako-adjust"><h3>⚠️ AJUSTE YAKO</h3>', unsafe_allow_html=True)
                aq = st.number_input("Ajuste Cantidad (+/-)", step=1)
                au = st.text_input("Ubicación Real").upper()
                if st.button("CONFIRMAR AJUSTE"):
                    db.collection(col_found).add({"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": c, "cantidad": aq, "ubicacion": au if au else "AJUSTE", "registrado_por": "YAKO", "foto_url": "NO FOTO", "tipo": "AJUSTE"})
                    st.success("Ajustado"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

# ================= PANEL ADMIN RESTAURADO =================

def admin():
    st.title("PANEL ADMIN / 관리자")
    # Pestañas restauradas tal como estaban
    t1, t2, t3 = st.tabs(["USUARIOS / 사용자", "EXCEL / EXPORTAR", "STOCK / CARGA"])
    
    with t1:
        st.subheader("Control de Usuarios")
        u_docs = db.collection("USUARIOS").stream()
        for u in u_docs:
            ud = u.to_dict()
            if u.id != "YAKO":
                col_u, col_b = st.columns([3, 1])
                col_u.write(f"**ID:** {u.id} | **Nombre:** {ud.get('nombre_personal')} | **Status:** {ud.get('estado')}")
                if col_b.button("ACTIVAR / 활성화", key=u.id):
                    db.collection("USUARIOS").document(u.id).update({"estado": "ACTIVO"})
                    st.success(f"Usuario {u.id} activado"); st.rerun()

    with t2:
        st.subheader("Generar Reportes")
        ce_s = st.selectbox("Selecciona Categoría", ["materiales", "holders"])
        if st.button("GENERAR EXCEL (CSV)"):
            data_e = [d.to_dict() for d in db.collection(ce_s).stream()]
            if data_e:
                df = pd.DataFrame(data_e)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("Descargar Archivo", csv, f"{ce_s}_reporte.csv", "text/csv")
            else: st.warning("No hay datos")

    with t3:
        st.subheader("Carga Masiva de Stock")
        st.write("Formato: **CODIGO CANTIDAD UBICACION** (separados por espacio)")
        lista = st.text_area("Pega tu lista aquí")
        if st.button("SUBIR A FIREBASE"):
            count = 0
            for l in lista.split('\n'):
                p = l.split()
                if len(p) >= 3:
                    db.collection("materiales").add({
                        "fecha": datetime.now().strftime("%Y-%m-%d"),
                        "item": p[0].upper(), "cantidad": int(p[1]),
                        "ubicacion": p[2].upper(), "registrado_por": "YAKO", "foto_url": "NO FOTO"
                    })
                    count += 1
            st.success(f"Se cargaron {count} registros correctamente.")

    if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): st.session_state.page = 'menu'; st.rerun()

# --- RUTAS ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
