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

# --- CONFIGURACIÓN DE PÁGINA / 페이지 설정 ---
st.set_page_config(page_title="YAKO PRO WEB", page_icon="📦", layout="centered")

# --- CONEXIÓN FIREBASE / 파이어베이스 연결 ---
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

# --- ESTILOS VISUALES / 시각적 스타일 ---
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
    .qr-container { background-color: white; padding: 10px; border-radius: 10px; display: inline-block; margin-top: 15px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN / 세션 변수 ---
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

# ================= VISTAS / 보기 =================

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
    if st.button("SALIR / 로그아웃"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

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
        st.success("REGISTRADO EXITOSAMENTE / 등록 완료"); st.session_state.scanned_id = ""; st.rerun()
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    query = st.text_input("ID o NOMBRE / ID 또는 이름", key="bus_in").upper().strip()
    
    if query:
        stock = 0; u_ubi = "---"; f_url = None; col_found = None; u_fecha = ""; final_id = ""; final_nombre = ""
        
        for col in ["materiales", "holders"]:
            # Búsqueda simultánea por ID y por NOMBRE
            docs_id = db.collection(col).where("item", "==", query).stream()
            docs_nom = db.collection(col).where("nombre", "==", query).stream()
            todos_los_docs = list(docs_id) + list(docs_nom)
            
            for d in todos_los_docs:
                col_found = col; dt = d.to_dict(); stock += dt.get('cantidad', 0)
                final_id = dt.get('item', query)
                final_nombre = dt.get('nombre', 'SIN NOMBRE')
                
                if dt.get('fecha', '') >= u_fecha and str(dt.get('ubicacion')).upper() != "SALIDA":
                    u_fecha = dt.get('fecha'); u_ubi = dt.get('ubicacion')
                if dt.get('foto_url') not in ["NO FOTO", "ERROR", None]: f_url = dt.get('foto_url')
        
        if col_found:
            st.markdown(f"### {final_nombre}")
            st.write(f"**ID:** {final_id}")
            
            c1, c2 = st.columns(2)
            c1.metric("STOCK TOTAL / 총 재고", stock)
            c2.metric("UBICACIÓN / 위치", u_ubi)
            
            # QR CENTRADO
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={final_id}"
            st.markdown(f'''
                <div style="text-align: center; margin-top: 15px;">
                    <div class="qr-container">
                        <img src="{qr_url}" /><br>
                        <b style="color: black;">CÓDIGO QR / QR 코드</b><br>
                        <span style="color: black;">{final_id}</span>
                    </div>
                </div>
            ''', unsafe_allow_html=True)

            if f_url:
                try:
                    st.markdown('<div style="text-align: center; margin-top: 20px;">', unsafe_allow_html=True)
                    st.image(f_url, caption=f"REFERENCIA / 참조: {final_id}")
                    st.markdown('</div>', unsafe_allow_html=True)
                except:
                    st.warning("Imagen no disponible / 사진을 표시할 수 없습니다")
        else: st.warning("No encontrado / 찾을 수 없음")
        
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def admin():
    if st.session_state.user_status != "YAKO": 
        st.error("ACCESO PROHIBIDO / access 금지됨"); st.session_state.page = 'login'; st.rerun()
        
    st.title("PANEL CONTROL / 제어판")
    t1, t2, t3, t4 = st.tabs(["BORRAR / 삭제", "EXCEL / 엑셀", "CARGA EXCEL / 엑셀 업로드", "USUARIOS / 사용자"])
    
    with t1:
        st.subheader("ELIMINAR / 삭제")
        col_db = st.selectbox("CATEGORÍA / 카테고리", ["materiales", "holders"], format_func=lambda x: x.upper())
        c_del = st.text_input("ID ESPECÍFICO / 특정 ID").upper()
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.warning("⚠️ ESTA ACCIÓN NO SE PUEDE DESHACER")
        seguro = st.checkbox("SÍ, ESTOY SEGURO / 네, 확실합니다")
        if seguro:
            if st.button("🔴 CONFIRMAR ELIMINACIÓN / 삭제 확인"):
                if c_del:
                    docs = db.collection(col_db).where("item", "==", c_del).stream()
                    for d in docs: db.collection(col_db).document(d.id).delete()
                    st.success(f"ID {c_del} ELIMINADO / 삭제됨")
                else:
                    docs = db.collection(col_db).stream()
                    for d in docs: db.collection(col_db).document(d.id).delete()
                    st.success(f"STOCK VACIADO / 재고 삭제 완료")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with t2:
        st.subheader("DESCARGAR / 다운로드")
        ce_s = st.selectbox("COLECCIÓN / 컬렉션", ["materiales", "holders"], key="desc", format_func=lambda x: x.upper())
        if st.button("📥 GENERAR EXCEL / 엑셀 생성"):
            data = [d.to_dict() for d in db.collection(ce_s).stream()]
            if data:
                df_out = pd.DataFrame(data)
                df_resumen = df_out.groupby('item').agg({'cantidad': 'sum', 'ubicacion': 'last'}).reset_index()
                csv = df_resumen.to_csv(index=False).encode('utf-8-sig')
                st.download_button("Descargar CSV / CSV 다운로드", csv, f"STOCK_{ce_s.upper()}.csv", "text/csv")
            else: st.info("SIN DATOS / 데이터 없음")

    with t3:
        st.subheader("CARGA EXCEL / 엑셀 업로드")
        destino_excel = st.selectbox("DESTINO / 목적지", ["MATERIALES", "HOLDERS"])
        st.info("COLUMNAS / 열: NOMBRE, ID, CANTIDAD, UBICACION, FOTO")
        archivo = st.file_uploader("SUBIR / 업로드 (.xlsx)", type=['xlsx'])
        if archivo:
            df = pd.read_excel(archivo)
            if st.button("🚀 INICIAR CARGA / 업로드 시작"):
                coleccion_destino = "materiales" if destino_excel == "MATERIALES" else "holders"
                for _, f in df.iterrows():
                    foto = str(f['FOTO']) if pd.notna(f['FOTO']) and str(f['FOTO']).strip() != "" else f"https://picsum.photos/seed/{random.randint(1,999)}/400/300"
                    db.collection(coleccion_destino).add({
                        "nombre": str(f['NOMBRE']).upper().strip(), "item": str(f['ID']).upper().strip(),
                        "cantidad": int(f['CANTIDAD']), "ubicacion": str(f['UBICACION']).upper().strip(),
                        "foto_url": foto, "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "registrado_por": "YAKO_EXCEL"
                    })
                st.success("CARGA COMPLETADA / 업로드 완료")

    with t4:
        st.subheader("USUARIOS / 사용자")
        u_docs = db.collection("USUARIOS").stream()
        for u in u_docs:
            ud = u.to_dict()
            if ud.get('estado') != "ADMIN_MASTER":
                with st.container():
                    st.markdown(f'<div class="user-card">', unsafe_allow_html=True)
                    col_u1, col_u2 = st.columns([2, 1])
                    with col_u1:
                        st.write(f"**ID:** {u.id} | **Estado:** {ud.get('estado')}")
                        st.text_input(f"Contraseña de / 비밀번호: {u.id}", value=ud.get('clave'), type="password", key=f"pw_{u.id}", disabled=True)
                    with col_u2:
                        if st.button("ACTIVAR / 활성화", key=f"act_{u.id}"):
                            db.collection("USUARIOS").document(u.id).update({"estado": "ACTIVO"}); st.rerun()
                        if st.button("BORRAR / 삭제", key=f"del_{u.id}"):
                            db.collection("USUARIOS").document(u.id).delete(); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        st.subheader("⚙️ PERFIL MAESTRO / 마스터 프로필")
        admin_actual = db.collection("USUARIOS").where("estado", "==", "ADMIN_MASTER").get()
        current_id = admin_actual[0].id if admin_actual else "YAKO"
        current_pw = admin_actual[0].to_dict().get('clave') if admin_actual else "1234"

        new_admin_id = st.text_input("NOMBRE / 이름", value=current_id).upper().strip()
        new_admin_pw = st.text_input("CLAVE / 비밀번호", value=current_pw, type="password")
        
        if st.button("💾 GUARDAR / 저장"):
            if new_admin_id != current_id:
                db.collection("USUARIOS").document(current_id).delete()
            db.collection("USUARIOS").document(new_admin_id).set({
                "clave": new_admin_pw, "estado": "ADMIN_MASTER", "nombre_personal": new_admin_id
            })
            st.success("ACTUALIZADO / 업데이트됨")
            st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

    if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): st.session_state.page = 'menu'; st.rerun()

# --- NAVEGACIÓN / 탐색 ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
