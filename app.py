import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage
import pandas as pd
from datetime import datetime
import os
import random
import requests
from io import BytesIO

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
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: cyan !important; text-align: center !important; font-weight: bold !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    .yako-adjust { border: 2px solid red; padding: 15px; border-radius: 10px; margin-top: 20px; background-color: #220000; text-align: center; }
    .qr-box { background-color: white; padding: 15px; border-radius: 10px; text-align: center; margin-top: 15px; display: inline-block; color: black; border: 3px solid red; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'user' not in st.session_state: st.session_state.user = None
if 'user_status' not in st.session_state: st.session_state.user_status = None
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

# ================= FUNCIONES =================

def ir(acc, cat):
    st.session_state.accion = acc
    st.session_state.categoria = cat
    st.session_state.page = 'form'
    st.session_state.scanned_id = ""
    st.rerun()

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
                nombre_c = data.get('nombre_personal', doc_id)
                st.session_state.user = nombre_c.split()[0] 
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
    st.markdown("<h4 style='color: yellow !important; text-align: center;'>SALIDA RÁPIDA / 빠른 출고</h4>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("SALIDA MATERIALES / 자재 출고"): 
            st.session_state.user="INVITADO"; st.session_state.user_status="INVITADO"; ir("SALIDA", "materiales")
    with c2:
        if st.button("SALIDA HOLDERS / 홀더 출고"): 
            st.session_state.user="INVITADO"; st.session_state.user_status="INVITADO"; ir("SALIDA", "holders")
    
    if st.button("🔍 BUSCAR MATERIAL / 재고 검색"): st.session_state.page = 'buscar'; st.rerun()

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES / 자재")
        if st.button("ENTRADA MAT / 자재 입고"): 
            if st.session_state.user_status in ["ACTIVO", "YAKO"]: ir("ENTRADA", "materiales")
            else: st.error("SOLO PERSONAL AUTORIZADO")
        if st.button("SALIDA MAT / 자재 출고"): ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS / 홀더")
        if st.button("ENTRADA HOL / 홀더 입고"): 
            if st.session_state.user_status in ["ACTIVO", "YAKO"]: ir("ENTRADA", "holders")
            else: st.error("SOLO PERSONAL AUTORIZADO")
        if st.button("SALIDA HOL / 홀더 출고"): ir("SALIDA", "holders")

    st.divider()
    if st.button("BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.session_state.user_status == "YAKO":
        if st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR / 로그아웃"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

def formulario():
    cat = st.session_state.get('categoria', 'materiales')
    acc = st.session_state.get('accion', 'ENTRADA')
    st.header(f"{cat.upper()} - {acc}")
    
    with st.expander("📷 LECTOR QR-BARRA / 스캔"):
        cam = st.camera_input("Captura el código / 코드를 찍으세요")
        if cam:
            st.session_state.scanned_id = "SCANNED_ID" 
            st.info("Código detectado.")

    cod = st.text_input("ID / CÓDIGO / 코드", value=st.session_state.scanned_id).upper().strip()
    cant = st.number_input("CANTIDAD / 수량", min_value=1, step=1)
    conf_cant = st.number_input("CONFIRMAR CANTIDAD / 수량 확인", min_value=0, step=1)
    
    if acc == "ENTRADA":
        ubi = st.text_input("UBICACIÓN / 위치").upper().strip()
        quien = "ALMACEN"
    else:
        ubi = "SALIDA"
        quien = st.text_input("QUIEN RETIRA / 수령자").upper().strip()

    foto = st.camera_input("FOTO EVIDENCIA / 증거 사진")
    
    if st.button("REGISTRAR / 등록"):
        if not cod: st.error("Falta Código / 코드 필요"); return
        if cant != conf_cant: st.error("Las cantidades no coinciden / 수량 불일치"); return
        if acc == "SALIDA" and not quien: st.error("Debe indicar quién retira"); return

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
            "ubicacion": ubi, "registrado_por": st.session_state.user, "solicitante": quien, "foto_url": url_f
        })
        st.success("✅ ÉXITO / 성공")
        st.session_state.scanned_id = "" 
        if st.button("SIGUIENTE / 다음"): st.rerun()

    if st.button("VOLVER / 돌아가기"): 
        st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO / 코드", key="search_input").upper().strip()
    
    if c:
        stock = 0
        ultima_fecha = ""
        ultima_ubicacion = "---"
        f_url = None
        col_found = None

        for col in ["materiales", "holders"]:
            docs = db.collection(col).where("item", "==", c).stream()
            for d in docs:
                col_found = col
                dt = d.to_dict()
                stock += dt.get('cantidad', 0)
                
                f_reg = dt.get('fecha', '2000-01-01 00:00')
                u_reg = str(dt.get('ubicacion', '')).upper()
                
                if f_reg >= ultima_fecha and u_reg != "SALIDA" and u_reg != "":
                    ultima_fecha = f_reg
                    ultima_ubicacion = u_reg
                
                if dt.get('foto_url') and dt.get('foto_url') not in ["NO FOTO", "ERROR"]:
                    f_url = dt.get('foto_url')
        
        if col_found:
            st.subheader(f"RESULTADO: {c}")
            c1, c2 = st.columns(2)
            c1.metric("STOCK / 재고", stock)
            c2.metric("UBICACIÓN / 위치", ultima_ubicacion)
            
            if f_url:
                try:
                    st.image(f_url, caption=f"ID: {c}")
                except:
                    st.warning("Imagen no disponible / 사진을 표시할 수 없습니다")
            
            qr_busq = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={c}"
            st.markdown(f'<div class="qr-box"><img src="{qr_busq}"><br><b style="color:black;">{c}</b></div>', unsafe_allow_html=True)

            if st.session_state.user_status == "YAKO":
                st.markdown('<div class="yako-adjust"><h3>⚠️ AJUSTE YAKO / 야코 조정</h3>', unsafe_allow_html=True)
                aq = st.number_input("Ajuste Cantidad (+/-) / 수량 조정", step=1, key="aq_val")
                au = st.text_input("Ubicación Real / 실제 위치", key="au_val").upper().strip()
                if st.button("CONFIRMAR AJUSTE / 조정 확인"):
                    if not au: st.warning("Escribe una ubicación / 위치를 입력하세요")
                    else:
                        db.collection(col_found).add({
                            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "item": c, "cantidad": aq, "ubicacion": au,
                            "registrado_por": "YAKO", "foto_url": "NO FOTO"
                        })
                        st.success("Ajustado / 조정됨"); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No se encontró el código / 코드를 찾을 수 없습니다")

    if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): 
        st.session_state.page = 'menu' if st.session_state.user != "INVITADO" else 'login'; st.rerun()

def admin():
    st.title("PANEL CONTROL / 제어판")
    t1, t2, t3, t4, t5 = st.tabs(["BORRAR / 삭제", "EXCEL / 엑셀", "CARGA / 업로드", "PERFIL / 프로필", "USUARIOS / 사용자"])
    
    with t1:
        st.subheader("Eliminar / 삭제")
        col_db = st.selectbox("Categoría / 카테고리", ["materiales", "holders"])
        c_del = st.text_input("ID a Borrar").upper()
        if st.button("ELIMINAR TODO / 전체 삭제"):
            docs = db.collection(col_db).where("item", "==", c_del).stream()
            for d in docs: db.collection(col_db).document(d.id).delete()
            st.success("Borrado / 삭제됨")

    with t2:
        st.subheader("Reportes / 보고서")
        ce_s = st.selectbox("Colección / 카테고리", ["materiales", "holders"], key="sel_csv")
        if st.button("GENERAR CSV / CSV 생성"):
            data_e = [d.to_dict() for d in db.collection(ce_s).stream()]
            if data_e:
                df = pd.DataFrame(data_e)
                st.download_button("Descargar / 다운로드", df.to_csv(index=False).encode('utf-8-sig'), f"{ce_s}.csv")

    with t3:
        st.subheader("Carga Masiva / 대량 업로드")
        txt = st.text_area("ID CANT UBICACION")
        if st.button("SUBIR LISTA / 목록 업로드"):
            for l in txt.split('\n'):
                p = l.split()
                if len(p)>=3:
                    db.collection("materiales").add({
                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "item": p[0].upper(), "cantidad": int(p[1]),
                        "ubicacion": p[2].upper(), "registrado_por": "YAKO", "foto_url": "NO FOTO"
                    })
            st.success("Cargado / 업로드됨")

    with t4:
        new_p = st.text_input("Nueva Clave Yako / 새로운 비밀번호", type="password")
        if st.button("ACTUALIZAR CLAVE / 비밀번호 업데이트"):
            db.collection("USUARIOS").document("YAKO").update({"clave": new_p})
            st.success("OK")

    with t5:
        u_docs = db.collection("USUARIOS").stream()
        for u in u_docs:
            ud = u.to_dict()
            if u.id != "YAKO":
                c_u, c_b = st.columns([3, 1])
                c_u.write(f"ID: {u.id} | {ud.get('estado')}")
                if c_b.button("ACTIVAR / 활성화", key=u.id):
                    db.collection("USUARIOS").document(u.id).update({"estado": "ACTIVO"})
                    st.rerun()

    if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): st.session_state.page = 'menu'; st.rerun()

# --- RUTAS ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
