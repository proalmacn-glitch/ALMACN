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
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label, div[data-testid="stFileUploader"] label, div[data-testid="stSelectbox"] label { color: yellow !important; font-size: 16px !important; }
    .stTextInput>div>div>input { text-align: center; background-color: #111; color: cyan !important; font-size: 20px; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: cyan !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    .warning-box { border: 2px solid orange; padding: 15px; border-radius: 10px; background-color: #2b1d00; color: white; text-align: center; margin-bottom: 20px; }
    .user-card { border: 1px solid #444; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: #0e0e0e; }
    .qr-container { background-color: white; padding: 10px; border-radius: 10px; display: inline-block; margin-top: 15px; text-align: center; }
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
                if data.get('estado') in ['ACTIVO', 'ADMIN_MASTER'] or u_in == "YAKO":
                    st.session_state.user = data.get('nombre_personal', u_in).split()[0]
                    st.session_state.user_status = "YAKO" if data.get('estado') == 'ADMIN_MASTER' or u_in == "YAKO" else "ACTIVO"
                    st.session_state.page = 'menu'; st.rerun()
                else: st.warning("Cuenta pendiente / 승인 대기 중")
            else: st.error("Acceso Denegado / access 거부됨")
            
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
    
    col_mat, col_hol = st.columns(2)
    with col_mat:
        st.markdown("<h3 style='color:red !important;'>MATERIALES / 자재</h3>", unsafe_allow_html=True)
        if st.button("ENTRADA MAT / 자재 입고"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT / 자재 출고"): ir("SALIDA", "materiales")
    with col_hol:
        st.markdown("<h3 style='color:red !important;'>HOLDERS / 홀더</h3>", unsafe_allow_html=True)
        if st.button("ENTRADA HOL / 홀더 입고"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL / 홀더 출고"): ir("SALIDA", "holders")
    
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    
    if st.session_state.user_status == "YAKO":
        if st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
            
    if st.button("SALIR / 로그아웃"): 
        st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

def formulario():
    cat = st.session_state.get('categoria', 'materiales')
    acc = st.session_state.get('accion', 'ENTRADA')
    st.header(f"{cat.upper()} - {acc}")
    
    with st.expander("📷 ESCANEAR QR / QR 스캔", expanded=True):
        cam = st.camera_input("QR", key="cam_qr")
        if cam:
            res = decodificar_qr(cam)
            if res: st.session_state.scanned_id = res

    cod = st.text_input("ID / CÓDIGO / 코드", value=st.session_state.scanned_id).upper().strip()
    cant = st.number_input("CANTIDAD / 수량", min_value=1)
    ubi = st.text_input("UBICACIÓN / 위치").upper() if acc == "ENTRADA" else "SALIDA"
    
    if st.button("REGISTRAR / 등록"):
        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": cod,
            "cantidad": cant if acc == "ENTRADA" else -cant, "ubicacion": ubi,
            "registrado_por": st.session_state.user, "foto_url": "NO FOTO"
        })
        st.success("✅ REGISTRADO / 등록 완료"); st.session_state.scanned_id = ""; st.rerun()
    
    if st.button("VOLVER / 돌아가기"): 
        st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    query = st.text_input("ID o NOMBRE / ID o 이름", key="bus_in").upper().strip()
    
    if query:
        stock = 0; u_ubi = "---"; f_url = None; col_found = None; u_fecha = ""; final_id = ""; final_nom = ""
        for col in ["materiales", "holders"]:
            docs_id = db.collection(col).where("item", "==", query).stream()
            docs_nom = db.collection(col).where("nombre", "==", query).stream()
            todos = list(docs_id) + list(docs_nom)
            for d in todos:
                col_found = col; dt = d.to_dict(); stock += dt.get('cantidad', 0)
                final_id = dt.get('item', query); final_nom = dt.get('nombre', 'SIN NOMBRE')
                if dt.get('fecha', '') >= u_fecha and str(dt.get('ubicacion')).upper() != "SALIDA":
                    u_fecha = dt.get('fecha'); u_ubi = dt.get('ubicacion')
                if dt.get('foto_url') not in ["NO FOTO", "ERROR", None]: f_url = dt.get('foto_url')
        
        if col_found:
            st.subheader(f"ID: {final_id} | {final_nom}")
            c1, c2 = st.columns(2)
            c1.metric("STOCK / 재고", stock); c2.metric("UBICACIÓN / 위치", u_ubi)
            
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={final_id}"
            st.markdown(f'<div style="text-align:center;"><div class="qr-container"><img src="{qr_url}"/><br><b>QR CODE</b></div></div>', unsafe_allow_html=True)
            if f_url:
                try: st.image(f_url)
                except: st.warning("Imagen no disponible")
        else: st.warning("No encontrado / 찾을 수 없음")
        
    if st.button("VOLVER / 돌아가기"): 
        st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def admin():
    if st.session_state.user_status != "YAKO": st.error("ACCESO PROHIBIDO"); st.rerun()
    st.title("PANEL CONTROL / 제어판")
    t1, t2, t3, t4 = st.tabs(["BORRAR / 삭제", "EXCEL / 엑셀", "CARGA / 업로드", "USUARIOS / 사용자"])
    
    with t1:
        st.subheader("Eliminar / 삭제")
        col_db = st.selectbox("Categoría / 카테고리", ["materiales", "holders"], format_func=lambda x: x.upper())
        c_del = st.text_input("ID ESPECÍFICO (Vacío = TODO / 비워두면 전체 삭제)").upper()
        st.markdown('<div class="warning-box">⚠️ ACCIÓN IRREVERSIBLE / 되돌릴 수 없음</div>', unsafe_allow_html=True)
        if st.checkbox("SÍ, ESTOY SEGURO / 예, 확신합니다"):
            if st.button("🔴 CONFIRMAR ELIMINACIÓN / 삭제 확인"):
                docs = db.collection(col_db).stream() if not c_del else db.collection(col_db).where("item", "==", c_del).stream()
                for d in docs: db.collection(col_db).document(d.id).delete()
                st.success("ELIMINADO / 삭제됨"); st.rerun()

    with t2:
        st.subheader("Reportes / 보고서")
        ce_s = st.selectbox("Colección / 컬렉션", ["materiales", "holders"], key="desc", format_func=lambda x: x.upper())
        if st.button("📥 DESCARGAR STOCK / 재고 다운로드"):
            data = [d.to_dict() for d in db.collection(ce_s).stream()]
            if data:
                df = pd.DataFrame(data).groupby('item').agg({'cantidad':'sum', 'ubicacion':'last'}).reset_index()
                st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8-sig'), f"STOCK_{ce_s.upper()}.csv")

    with t3:
        st.subheader("Carga Excel / 엑셀 업로드")
        dest = st.selectbox("Destino / 목적지", ["MATERIALES / 자재", "HOLDERS / 홀더"])
        archivo = st.file_uploader("Subir / 업로드", type=['xlsx'])
        if archivo and st.button("🚀 INICIAR CARGA / 업로드 시작"):
            df = pd.read_excel(archivo)
            col_dest = "materiales" if "MATERIALES" in dest else "holders"
            for _, f in df.iterrows():
                foto = str(f['FOTO']) if pd.notna(f['FOTO']) else f"https://picsum.photos/seed/{random.randint(1,999)}/400/300"
                db.collection(col_dest).add({
                    "nombre": str(f['NOMBRE']).upper(), "item": str(f['ID']).upper(),
                    "cantidad": int(f['CANTIDAD']), "ubicacion": str(f['UBICACION']).upper(),
                    "foto_url": foto, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "registrado_por": "YAKO"
                })
            st.success("CARGA COMPLETADA / 업로드 완료")

    with t4:
        st.subheader("Usuarios / 사용자 관리")
        u_docs = db.collection("USUARIOS").stream()
        for u in u_docs:
            ud = u.to_dict()
            if ud.get('estado') != "ADMIN_MASTER":
                with st.container():
                    st.markdown(f'<div class="user-card"><b>ID:</b> {u.id} | <b>Estado:</b> {ud.get("estado")}</div>', unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    if c1.button("ACTIVAR / 활성화", key=f"act_{u.id}"):
                        db.collection("USUARIOS").document(u.id).update({"estado": "ACTIVO"}); st.rerun()
                    if c2.button("BORRAR / 삭제", key=f"del_{u.id}"):
                        db.collection("USUARIOS").document(u.id).delete(); st.rerun()
        
        st.divider()
        st.subheader("Configuración Admin / 관리자 설정")
        new_id = st.text_input("Nuevo Nombre / 새 이름").upper().strip()
        new_pw = st.text_input("Nueva Clave / 새 비밀번호", type="password")
        if st.button("💾 GUARDAR CAMBIOS / 변경 사항 저장"):
            # Lógica para actualizar perfil admin master
            admin_ref = db.collection("USUARIOS").where("estado", "==", "ADMIN_MASTER").get()
            old_id = admin_ref[0].id if admin_ref else "YAKO"
            if new_id and new_id != old_id: db.collection("USUARIOS").document(old_id).delete()
            db.collection("USUARIOS").document(new_id if new_id else old_id).set({
                "clave": new_pw, "estado": "ADMIN_MASTER", "nombre_personal": new_id if new_id else old_id
            })
            st.success("ACTUALIZADO / 업데이트됨")

    if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): st.session_state.page = 'menu'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
