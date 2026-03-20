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
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stNumberInput"] label { color: yellow !important; }
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: #00cccc !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    .center-container { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; width: 100%; }
    .qr-card { background-color: white; padding: 15px; border-radius: 10px; display: inline-block; margin-bottom: 20px; }
    div[data-testid="stImage"] { display: flex; justify-content: center; }
    .user-card { border: 1px solid #444; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: #0e0e0e; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'user_status' not in st.session_state: st.session_state.user_status = None
if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

# ================= VISTAS / 보기 =================

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
                st.session_state.user = u_in
                st.session_state.user_status = "YAKO" if data.get('estado') == 'ADMIN_MASTER' or u_in == "YAKO" else "ACTIVO"
                st.session_state.page = 'menu'; st.rerun()
            else: st.error("Acceso Denegado / 거부됨")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USUARIO{random.randint(100, 999)}", f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre_personal": u})
            st.success(f"User: {u}\nPass: {p}")
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES / 자재")
        if st.button("ENTRADA MAT"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT"): ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS / 홀더")
        if st.button("ENTRADA HOL"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL"): ir("SALIDA", "holders")
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.session_state.user_status == "YAKO" and st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR / 로그아웃"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

def formulario():
    cat = st.session_state.categoria
    acc = st.session_state.accion
    st.header(f"{cat.upper()} - {acc}")
    cam = st.camera_input("QR")
    if cam:
        res = decodificar_qr(cam)
        if res: st.session_state.scanned_id = res
    cod = st.text_input("ID / CÓDIGO / 코드", value=st.session_state.scanned_id).upper().strip()
    cant = st.number_input("CANTIDAD / 수량", min_value=1)
    ubi = st.text_input("UBICACIÓN / 위치").upper() if acc == "ENTRADA" else "SALIDA"
    
    # Buscar nombre automático
    nombre_auto = "NUEVO MATERIAL"
    docs = db.collection(cat).where("item", "==", cod).limit(1).stream()
    for d in docs: nombre_auto = d.to_dict().get('nombre', 'NUEVO MATERIAL')

    if st.button("REGISTRAR / 등록"):
        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "item": cod,
            "nombre": nombre_auto,
            "cantidad": cant if acc == "ENTRADA" else -cant,
            "ubicacion": ubi,
            "registrado_por": st.session_state.user
        })
        st.success("REGISTRADO / 완료"); st.session_state.scanned_id = ""; st.rerun()
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu'; st.rerun()

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
            opciones = {f"{r.get('nombre')} [{r.get('item')}]": r for r in resultados}
            seleccion = st.selectbox("SELECCIONA / 선택:", list(opciones.keys()))
            item = opciones[seleccion]
            id_f = item.get('item')
            col_f = item['categoria_db']
            
            docs_s = db.collection(col_f).where("item", "==", id_f).stream()
            total = sum([d.to_dict().get('cantidad', 0) for d in docs_s])
            
            st.markdown(f"<h2>{item.get('nombre')}</h2>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.metric("STOCK TOTAL / 총 재고", total)
            c2.metric("UBICACIÓN / 위치", item.get('ubicacion', '---'))
            
            st.divider()
            st.markdown('<div class="center-container">', unsafe_allow_html=True)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}"
            st.markdown(f'<div class="qr-card"><img src="{qr_url}"><br><b style="color:black;">QR {id_f}</b></div>', unsafe_allow_html=True)
            foto = convertir_link_drive(item.get('foto_url', ''))
            if foto: st.image(foto, width=450, caption=f"REFERENCIA: {item.get('nombre')}")
            st.markdown('</div>', unsafe_allow_html=True)
            
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user else 'login'; st.rerun()

def admin():
    if st.session_state.user_status != "YAKO": st.error("ACCESO PROHIBIDO"); return
    st.title("PANEL CONTROL / 제어판")
    t1, t2, t3, t4 = st.tabs(["BORRAR / 삭제", "EXCEL DETALLADO", "CARGA MASIVA", "USUARIOS / 사용자"])
    
    with t1:
        col_db = st.selectbox("CATEGORÍA", ["materiales", "holders"])
        c_del = st.text_input("ID ESPECÍFICO A BORRAR").upper()
        if st.checkbox("Confirmar borrado"):
            if st.button("🔴 EJECUTAR BORRADO"):
                docs = db.collection(col_db).where("item", "==", c_del).stream() if c_del else db.collection(col_db).stream()
                for d in docs: db.collection(col_db).document(d.id).delete()
                st.success("Borrado con éxito"); st.rerun()
                
    with t2:
        ce_s = st.selectbox("COLECCIÓN PARA REPORTE", ["materiales", "holders"])
        if st.button("📥 GENERAR REPORTE EXCEL"):
            data = [d.to_dict() for d in db.collection(ce_s).order_by("fecha").stream()]
            if data:
                df = pd.DataFrame(data).rename(columns={
                    'fecha': 'FECHA Y HORA', 'item': 'ID', 'nombre': 'NOMBRE',
                    'cantidad': 'MOVIMIENTO', 'ubicacion': 'UBICACIÓN', 'registrado_por': 'USUARIO'
                })
                csv = df[['FECHA Y HORA', 'ID', 'NOMBRE', 'MOVIMIENTO', 'UBICACIÓN', 'USUARIO']].to_csv(index=False).encode('utf-8-sig')
                st.download_button("Descargar Excel (.csv)", csv, f"Reporte_{ce_s}.csv", "text/csv")

    with t3:
        dest = st.selectbox("DESTINO CARGA", ["materiales", "holders"])
        archivo = st.file_uploader("Subir Excel (.xlsx)", type=['xlsx'])
        if archivo and st.button("🚀 INICIAR CARGA"):
            df_in = pd.read_excel(archivo)
            for _, f in df_in.iterrows():
                db.collection(dest).add({
                    "nombre": str(f['NOMBRE']).upper(), "item": str(f['ID']).upper(),
                    "cantidad": int(f['CANTIDAD']), "ubicacion": str(f['UBICACIÓN']).upper(),
                    "foto_url": str(f.get('FOTO', 'NO FOTO')), "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "registrado_por": st.session_state.user
                })
            st.success("Carga masiva completada"); st.rerun()

    with t4:
        u_docs = db.collection("USUARIOS").stream()
        for u in u_docs:
            ud = u.to_dict()
            if ud.get('estado') != "ADMIN_MASTER":
                with st.container():
                    st.markdown(f'<div class="user-card">', unsafe_allow_html=True)
                    st.write(f"**ID:** {u.id} | **Estado:** {ud.get('estado')}")
                    c1, c2 = st.columns(2)
                    if c1.button("ACTIVAR", key=f"act_{u.id}"): db.collection("USUARIOS").document(u.id).update({"estado": "ACTIVO"}); st.rerun()
                    if c2.button("BORRAR", key=f"del_{u.id}"): db.collection("USUARIOS").document(u.id).delete(); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): st.session_state.page = 'menu'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
