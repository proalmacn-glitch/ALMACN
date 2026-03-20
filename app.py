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

def animacion_aleatoria():
    """Solo Globos y Copos de Nieve aleatoriamente."""
    opcion = random.choice(["globos", "nieve"])
    if opcion == "globos": st.balloons()
    else: st.snow()

# --- ESTILOS VISUALES / 시각적 스타일 ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    .stButton>button { background-color: white; color: black; border-radius: 5px; width: 100%; font-weight: bold; border: 2px solid red; }
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stNumberInput"] label { color: yellow !important; }
    .stTextInput>div>div>input { text-align: center; background-color: #111; color: cyan !important; font-size: 20px; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: #00cccc !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    .center-container { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; width: 100%; }
    .qr-card { background-color: white; padding: 15px; border-radius: 10px; display: inline-block; margin: 20px auto; text-align: center; }
    .user-card { border: 1px solid #444; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: #0e0e0e; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

# ================= VISTAS / 보기 =================

def login():
    st.title("LOGIN / 로그인")
    u_in = st.text_input("USUARIO / 사용자").upper().strip()
    p_in = st.text_input("CLAVE / 비밀번호", type="password").strip()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(u_in).get()
            if doc.exists:
                udata = doc.to_dict()
                if str(udata.get('clave')) == p_in:
                    if udata.get('estado') in ['ACTIVO', 'ADMIN_MASTER'] or u_in == "YAKO":
                        st.session_state.user = u_in
                        st.session_state.page = 'menu'; st.rerun()
                    else: st.warning("CUENTA NO ACTIVADA POR YAKO / 승인 대기 중")
                else: st.error("CLAVE INCORRECTA / 비밀번호 오류")
            else: st.error("USUARIO NO EXISTE / 사용자 없음")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USUARIO{random.randint(100, 999)}", f"PASS{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE"})
            st.success(f"TOMA FOTO / 사진 찍기:\nUser: {u}\nPass: {p}")
    st.divider()
    c_inv1, c_inv2 = st.columns(2)
    if c_inv1.button("SALIDA MAT INVITADO / 자재 출고 (게스트)"): 
        st.session_state.user="INVITADO"; ir("SALIDA", "materiales")
    if c_inv2.button("SALIDA HOL INVITADO / 홀더 출고 (게스트)"): 
        st.session_state.user="INVITADO"; ir("SALIDA", "holders")
    
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    
    # --- GIF RESTAURADO / GIF 복구 ---
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES / 자재")
        if st.button("ENTRADA MAT / 입고"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT / 출고"): ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS / 홀더")
        if st.button("ENTRADA HOL / 입고"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL / 출고"): ir("SALIDA", "holders")
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.session_state.user != "INVITADO" and st.button("PANEL CONTROL / 제어판"): 
        st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR / 로그아웃"): st.session_state.user=None; st.session_state.page='login'; st.rerun()

def formulario():
    cat, acc = st.session_state.get('categoria', 'materiales'), st.session_state.get('accion', 'ENTRADA')
    st.header(f"{cat.upper()} - {acc}")
    with st.expander("📷 CÁMARA / 카메라", expanded=False):
        cam = st.camera_input("QR SCAN")
        if cam:
            res = decodificar_qr(cam)
            if res: st.session_state.scanned_id = res
    cod = st.text_input("ID / CÓDIGO / 코드", value=st.session_state.scanned_id).upper().strip()
    stock_calc = 0
    if cod:
        docs = db.collection(cat).where("item", "==", cod).stream()
        stock_calc = sum([d.to_dict().get('cantidad', 0) for d in docs])
        st.write(f"📊 STOCK EN SISTEMA / 시스템 재고: **{max(0, stock_calc)}**")
    
    col_c1, col_c2 = st.columns(2)
    cant1 = col_c1.number_input("CANTIDAD / 수량", min_value=1, key="cant1")
    cant2 = col_c2.number_input("CONFIRMAR / 확인", min_value=0, key="cant2")
    sol = st.text_input("SOLICITANTE / 신청자").upper().strip() if acc == "SALIDA" else ""
    
    ubi_fija = ""
    if cod:
        d_u = db.collection(cat).where("item", "==", cod).limit(20).stream()
        for d in d_u:
            if d.to_dict().get("ubicacion") != "SALIDA": ubi_fija = d.to_dict().get("ubicacion", ""); break
    ubi = st.text_input("UBICACIÓN / 위치", value=ubi_fija).upper() if acc == "ENTRADA" else "SALIDA"
    
    bloqueado = cant1 != cant2 or (acc == "SALIDA" and (cant1 > stock_calc or not sol))
    if st.button("REGISTRAR / 등록", disabled=bloqueado):
        db.collection(cat).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": cod, 
            "cantidad": cant1 if acc == "ENTRADA" else -cant1, "ubicacion": ubi, 
            "solicitante": sol, "registrado_por": st.session_state.user
        })
        animacion_aleatoria()
        st.success("✅ ¡ÉXITO! / 성공!")
        st.session_state.scanned_id = ""
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    q = st.text_input("ID o NOMBRE / ID 또는 이름").upper().strip()
    if q:
        res = []
        for col in ["materiales", "holders"]:
            docs = db.collection(col).stream()
            for d in docs:
                data = d.to_dict()
                if q in str(data.get('nombre', '')).upper() or q == str(data.get('item', '')).upper():
                    data['cat_db'] = col; res.append(data)
        if res:
            item = res[0]
            id_f, col_f = item.get('item'), item['cat_db']
            st.markdown(f"<h2>{q}</h2>", unsafe_allow_html=True)
            u_real = "---"
            d_u = db.collection(col_f).where("item", "==", id_f).limit(30).stream()
            for d in d_u:
                if d.to_dict().get('ubicacion') != "SALIDA": u_real = d.to_dict().get('ubicacion'); break
            d_s = db.collection(col_f).where("item", "==", id_f).stream()
            tot = sum([d.to_dict().get('cantidad', 0) for d in d_s])
            c1, c2 = st.columns(2); c1.metric("STOCK ACTUAL / 재고", max(0, tot)); c2.metric("UBICACIÓN / 위치", u_real)
            st.divider()
            st.markdown('<div class="center-container">', unsafe_allow_html=True)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}"
            st.markdown(f'<div class="qr-card"><img src="{qr_url}"><br><b style="color:black;">QR {id_f}</b></div>', unsafe_allow_html=True)
            f = convertir_link_drive(item.get('foto_url', ''))
            if f: st.image(f, width=450); st.markdown('</div>', unsafe_allow_html=True)
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user else 'login'; st.rerun()

def admin():
    st.title("PANEL CONTROL / 제어판")
    if st.session_state.user == "YAKO":
        tabs = st.tabs(["BORRAR STOCK / 삭제", "EXCEL REPORTE / 엑셀", "CARGA MASIVA / 로드", "USUARIOS / 사용자", "MI CUENTA / 내 계정"])
    else:
        tabs = st.tabs(["EXCEL REPORTE / 엑셀", "CARGA MASIVA / 로드"])

    if st.session_state.user == "YAKO":
        with tabs[0]:
            st.subheader("BORRADO / 삭제")
            cdb = st.selectbox("CATEGORÍA", ["materiales", "holders"], key="admin_del_cat")
            del_id = st.text_input("ID ESPECÍFICO (VACÍO = TODO 삭제)").upper()
            if st.checkbox("Confirmar Borrado / 확인"):
                if st.button("🔴 EJECUTAR / 실행"):
                    ds = db.collection(cdb).where("item", "==", del_id).stream() if del_id else db.collection(cdb).stream()
                    for d in ds: db.collection(cdb).document(d.id).delete()
                    st.success("BORRADO COMPLETADO / 완료"); st.rerun()
        with tabs[1]: mostrar_tab_excel()
        with tabs[2]: mostrar_tab_carga()
        with tabs[3]:
            st.subheader("GESTIÓN DE ACCESOS / 관리")
            uds = db.collection("USUARIOS").stream()
            for u in uds:
                ud = u.to_dict()
                with st.container():
                    st.markdown(f'<div class="user-card">ID: {u.id} | ESTADO: {ud.get("estado")}</div>', unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    if c1.button("ACTIVAR / 활성화", key=f"a_{u.id}"): 
                        db.collection("USUARIOS").document(u.id).update({"estado": "ACTIVO"}); st.rerun()
                    if c2.button("BORRAR / 삭제", key=f"d_{u.id}"): 
                        db.collection("USUARIOS").document(u.id).delete(); st.rerun()
        with tabs[4]: mostrar_tab_cuenta()
    else:
        with tabs[0]: mostrar_tab_excel()
        with tabs[1]: mostrar_tab_carga()

    if st.button("VOLVER AL MENÚ / 돌아가기"): st.session_state.page = 'menu'; st.rerun()

def mostrar_tab_excel():
    ce = st.selectbox("REPORTE / 보고서", ["materiales", "holders"], key="excel_cat")
    if st.button("📥 GENERAR EXCEL / 엑셀 생성"):
        data = [d.to_dict() for d in db.collection(ce).order_by("fecha").stream()]
        if data:
            df = pd.DataFrame(data).rename(columns={'fecha':'FECHA','item':'ID','cantidad':'MOV','ubicacion':'UBICACIÓN','solicitante':'SOL','registrado_por':'USER'})
            csv = df[['FECHA','ID','MOV','UBICACIÓN','SOL','USER']].to_csv(index=False).encode('utf-8-sig')
            st.download_button("Descargar / 다운로드", csv, f"Reporte_{ce}.csv", "text/csv")

def mostrar_tab_carga():
    dest = st.selectbox("DESTINO / 목적지", ["materiales", "holders"], key="carga_cat")
    arch = st.file_uploader("Subir .xlsx", type=['xlsx'])
    if arch and st.button("🚀 CARGAR / 로드"):
        try:
            df_in = pd.read_excel(arch, engine='openpyxl')
            df_in = df_in.dropna(how='all')
            for _, f in df_in.iterrows():
                db.collection(dest).add({
                    "nombre":str(f['NOMBRE']).upper(),"item":str(f['ID']).upper(),"cantidad":int(f['CANTIDAD']),
                    "ubicacion":str(f['UBICACIÓN']).upper(),"foto_url":str(f.get('FOTO','NO FOTO')),
                    "fecha":datetime.now().strftime("%Y-%m-%d %H:%M"),"registrado_por":st.session_state.user
                })
            st.success("✅ CARGA LISTA / 완료")
        except Exception as e:
            st.error(f"Error al cargar Excel: {e}")

def mostrar_tab_cuenta():
    st.subheader("⚙️ EDITAR MIS CREDENCIALES / 내 계정 편집")
    new_u = st.text_input("NUEVO USUARIO / 새 사용자", value=st.session_state.user).upper().strip()
    new_p = st.text_input("NUEVA CLAVE / 새 비밀번호", type="password")
    if st.button("ACTUALIZAR DATOS / 데이터 업데이트"):
        doc_ref = db.collection("USUARIOS").document(st.session_state.user).get()
        if doc_ref.exists:
            old_data = doc_ref.to_dict()
            db.collection("USUARIOS").document(new_u).set({"clave": new_p, "estado": old_data.get('estado')})
            if new_u != st.session_state.user: db.collection("USUARIOS").document(st.session_state.user).delete()
            st.success("DATOS ACTUALIZADOS / 완료"); st.session_state.user = new_u; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
