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

# --- UTILIDADES / 유틸리티 ---
def convertir_link_drive(url):
    """Convierte links de Drive para visualización directa."""
    if 'drive.google.com' in url:
        match = re.search(r'd/([^/]+)', url)
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
    
    /* Etiquetas Amarillas */
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stNumberInput"] label { 
        color: yellow !important; font-size: 16px !important; 
    }

    /* Métricas Cian Mate (Azul suave) */
    div[data-testid="stMetricValue"] { 
        font-size: 45px !important; color: #00cccc !important; text-align: center !important; 
    }
    div[data-testid="stMetricLabel"] { 
        font-size: 18px !important; color: white !important; text-align: center !important; 
    }
    div[data-testid="stMetric"] { 
        background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; 
    }
    
    /* CENTRADO TOTAL */
    .center-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        width: 100%;
    }
    
    .qr-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        display: inline-block;
        margin-bottom: 20px;
    }

    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
    }

    .user-card { border: 1px solid #444; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: #0e0e0e; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
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
                if data.get('estado') in ['ACTIVO', 'ADMIN_MASTER'] or u_in == "YAKO":
                    st.session_state.user = u_in
                    st.session_state.user_status = "YAKO" if data.get('estado') == 'ADMIN_MASTER' or u_in == "YAKO" else "ACTIVO"
                    st.session_state.page = 'menu'; st.rerun()
                else: st.warning("Cuenta pendiente de activación / 승인 대기 중")
            else: st.error("Acceso Denegado / access 거부됨")
            
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USUARIO{random.randint(100, 999)}", f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre_personal": u})
            st.success(f"TOMA FOTO / 사진 찍기:\nUser: {u}\nPass: {p}")
    
    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("SALIDA MATERIALES / 자재 출고"):
        st.session_state.user="INVITADO"; ir("SALIDA", "materiales")
    if c2.button("SALIDA HOLDERS / 홀더 출고"):
        st.session_state.user="INVITADO"; ir("SALIDA", "holders")
    
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES / 자재")
        if st.button("ENTRADA MAT / 자재 입고"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT / 자재 출고"): ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS / 홀더")
        if st.button("ENTRADA HOL / 홀더 입고"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL / 홀더 출고"): ir("SALIDA", "holders")
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.session_state.user_status == "YAKO" and st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR / 로그아웃"): 
        st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

def formulario():
    cat = st.session_state.get('categoria', 'materiales')
    acc = st.session_state.get('accion', 'ENTRADA')
    st.header(f"{cat.upper()} - {acc}")
    with st.expander("📷 ESCANEAR QR / QR 스캔", expanded=True):
        cam = st.camera_input("QR")
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
        st.success("REGISTRADO EXITOSAMENTE / 등록 완료"); st.session_state.scanned_id = ""; st.rerun()
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

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
        
        item_elegido = None
        if len(resultados) > 1:
            st.warning(f"RESULTADOS / 검색 결과: {len(resultados)}")
            opciones = {f"{r.get('nombre')} [{r.get('item')}]": r for r in resultados}
            seleccion = st.selectbox("SELECCIONA / 선택하세요:", list(opciones.keys()))
            item_elegido = opciones[seleccion]
        elif len(resultados) == 1:
            item_elegido = resultados[0]
            
        if item_elegido:
            id_f = item_elegido.get('item', '---')
            col_f = item_elegido['categoria_db']
            docs_stock = db.collection(col_f).where("item", "==", id_f).stream()
            total_stock = sum([doc.to_dict().get('cantidad', 0) for doc in docs_stock])
            
            st.markdown(f"<h2>{item_elegido.get('nombre', '---')}</h2>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.metric("STOCK TOTAL / 총 재고", total_stock)
            c2.metric("UBICACIÓN / 위치", item_elegido.get('ubicacion', '---'))
            
            st.divider()
            st.markdown('<div class="center-container">', unsafe_allow_html=True)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}"
            st.markdown(f'''
                <div class="qr-card">
                    <img src="{qr_url}"><br>
                    <b style="color: black;">CÓDIGO QR / QR 코드</b>
                </div>
            ''', unsafe_allow_html=True)
            
            foto = item_elegido.get('foto_url', '')
            if foto and foto not in ["NO FOTO", "ERROR"]:
                st.image(convertir_link_drive(foto), width=450, caption=f"REFERENCIA / 참조: {item_elegido.get('nombre')}")
            st.markdown('</div>', unsafe_allow_html=True)
            
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user else 'login'; st.rerun()

def admin():
    if st.session_state.user_status != "YAKO": st.error("ACCESO PROHIBIDO / access 금지됨"); return
    st.title("PANEL CONTROL / 제어판")
    t1, t2, t3, t4 = st.tabs(["BORRAR / 삭제", "EXCEL / 엑셀", "CARGA EXCEL / 엑셀 업로드", "USUARIOS / 사용자"])
    
    with t1:
        col_db = st.selectbox("CATEGORÍA / 카테고리", ["materiales", "holders"], format_func=lambda x: x.upper())
        c_del = st.text_input("ID ESPECÍFICO / 특정 ID").upper()
        if st.checkbox("SÍ, ESTOY SEGURO / 네, 확실합니다"):
            if st.button("🔴 CONFIRMAR ELIMINACIÓN / 삭제 확인"):
                docs = db.collection(col_db).where("item", "==", c_del).stream() if c_del else db.collection(col_db).stream()
                for d in docs: db.collection(col_db).document(d.id).delete()
                st.success("ELIMINADO / 삭제됨"); st.rerun()
                
    with t2:
        ce_s = st.selectbox("COLECCIÓN / 컬렉션", ["materiales", "holders"], key="desc", format_func=lambda x: x.upper())
        if st.button("📥 GENERAR EXCEL / 엑셀 생성"):
            data = [d.to_dict() for d in db.collection(ce_s).stream()]
            if data:
                df = pd.DataFrame(data).groupby('item').agg({'cantidad': 'sum', 'ubicacion': 'last', 'nombre': 'first'}).reset_index()
                st.download_button("Descargar CSV / CSV 다운로드", df.to_csv(index=False).encode('utf-8-sig'), f"STOCK_{ce_s.upper()}.csv", "text/csv")

    with t3:
        dest = st.selectbox("DESTINO / 목적지", ["MATERIALES", "HOLDERS"])
        archivo = st.file_uploader("SUBIR / 업로드 (.xlsx)", type=['xlsx'])
        if archivo and st.button("🚀 INICIAR CARGA / 업로드 시작"):
            df = pd.read_excel(archivo)
            col_dest = dest.lower()
            for _, f in df.iterrows():
                db.collection(col_dest).add({
                    "nombre": str(f['NOMBRE']).upper(), "item": str(f['ID']).upper(),
                    "cantidad": int(f['CANTIDAD']), "ubicacion": str(f['UBICACION']).upper(),
                    "foto_url": str(f['FOTO']), "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "registrado_por": "YAKO_EXCEL"
                })
            st.success("COMPLETADO / 완료")

    with t4:
        u_docs = db.collection("USUARIOS").stream()
        for u in u_docs:
            ud = u.to_dict()
            if ud.get('estado') != "ADMIN_MASTER":
                with st.container():
                    st.markdown(f'<div class="user-card">', unsafe_allow_html=True)
                    st.write(f"**ID:** {u.id} | **Estado:** {ud.get('estado')}")
                    st.text_input(f"Contraseña de / 비밀번호: {u.id}", value=ud.get('clave'), type="password", disabled=True)
                    c1, c2 = st.columns(2)
                    if c1.button("ACTIVAR / 활성화", key=f"act_{u.id}"): db.collection("USUARIOS").document(u.id).update({"estado": "ACTIVO"}); st.rerun()
                    if c2.button("BORRAR / 삭제", key=f"del_{u.id}"): db.collection("USUARIOS").document(u.id).delete(); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): st.session_state.page = 'menu'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
