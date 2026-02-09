import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
from datetime import datetime
import os
import random

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="YAKO PRO WEB", page_icon="📦", layout="centered")

# --- CONEXIÓN FIREBASE ---
if not firebase_admin._apps:
    try:
        cred_path = "Key.json"
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        else:
            if "textkey" in st.secrets:
                cred = credentials.Certificate(dict(st.secrets["textkey"]))
                firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Error Conexión / 연결 오류: {e}")

db = firestore.client()

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    
    /* Botones */
    .stButton>button { 
        background-color: white; 
        color: black; 
        border-radius: 5px; 
        width: 100%; 
        font-weight: bold; 
        border: 2px solid red; 
    }
    .stButton>button:hover { background-color: red; color: white; }
    
    /* Inputs */
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stTextArea"] label { 
        color: yellow !important; 
        font-size: 16px !important;
    }
    .stTextInput>div>div>input { text-align: center; }
    .stNumberInput>div>div>input { text-align: center; }
    
    /* DATOS GIGANTES */
    div[data-testid="stMetricValue"] {
        font-size: 55px !important;
        color: cyan !important;
        text-align: center !important;
        font-weight: bold !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 20px !important;
        color: white !important;
        text-align: center !important;
        justify-content: center !important;
    }
    div[data-testid="stMetric"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        background-color: #111;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #333;
    }
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
                    st.session_state.user = "YAKO"
                    st.session_state.page = 'menu'
                    st.rerun()
                elif data.get('estado') == "ACTIVO":
                    if data.get('cambio_pendiente', False):
                        st.session_state.temp_user = user
                        st.session_state.page = 'cambio_clave'
                        st.rerun()
                    else:
                        st.session_state.user = data.get('nombre_personal', user)
                        st.session_state.page = 'menu'
                        st.rerun()
                else: st.warning("Cuenta Pendiente / 계정 대기 중")
            else: st.error("Clave Incorrecta / 비밀번호 오류")
        else: st.error("Usuario no existe / 사용자 없음")

    if col2.button("REGISTRARSE / 등록"):
        animales = ["LEON", "TIGRE", "AGUILA", "LOBO", "OSO", "TORO", "GATO", "PERRO", "PUMA", "ZORRO", "HALCON", "DRAGON", "COBRA", "PANTERA", "TIBURON", "BUFALO", "RINOCERONTE", "ELEFANTE", "JAGUAR", "FENIX"]
        n = len(list(db.collection("USUARIOS").stream()))
        u = f"USUARIO{n+1}"
        an = random.choice(animales)
        num = random.randint(10, 99)
        p = f"{an}{num}"
        
        db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre": u, "cambio_pendiente": True})
        st.success(f"TOMA FOTO / 사진 찍기:\n\nUsuario: {u}\nClave: {p}")

    # SALIDA RÁPIDA
    st.divider()
    st.markdown("<h4 style='color: yellow !important;'>SALIDA RÁPIDA (SIN LOGIN) / 빠른 출고</h4>", unsafe_allow_html=True)
    c_out1, c_out2 = st.columns(2)
    with c_out1:
        if st.button("SALIDA MATERIALES / 자재 출고"):
            st.session_state.user = "INVITADO / 손님"
            st.session_state.es_invitado = True
            ir("SALIDA", "materiales")
    with c_out2:
        if st.button("SALIDA HOLDERS / 홀더 출고"):
            st.session_state.user = "INVITADO / 손님"
            st.session_state.es_invitado = True
            ir("SALIDA", "holders")

def cambio_clave():
    st.title("PRIMER INICIO / 첫 로그인")
    nn = st.text_input("Nuevo Nombre / 새 이름").upper()
    nc = st.text_input("Nueva Clave / 새 비밀번호", type="password")
    nc2 = st.text_input("Confirmar Clave / 비밀번호 확인", type="password")
    
    if st.button("GUARDAR / 저장"):
        if nc == nc2 and nn and nc:
            db.collection("USUARIOS").document(st.session_state.temp_user).update({"nombre_personal": nn, "clave": nc, "cambio_pendiente": False})
            st.session_state.user = nn
            st.session_state.es_invitado = False
            st.session_state.page = 'menu'
            st.rerun()
        else: st.error("Error: Claves no coinciden / 오류: 비밀번호 불일치")

def menu():
    st.title("MENÚ / 메뉴")
    st.info(f"USUARIO / 사용자: {st.session_state.user}")
    
    if st.session_state.user == "YAKO":
        pend = len(list(db.collection("USUARIOS").where("estado", "==", "PENDIENTE").stream()))
        if pend > 0: st.error(f"⚠ {pend} USUARIOS PENDIENTES / 대기 중인 사용자")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES / 자재")
        if st.button("ENTRADA MAT / 자재 입고"): 
            st.session_state.es_invitado = False
            ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT / 자재 출고"): 
            st.session_state.es_invitado = False
            ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS / 홀더")
        if st.button("ENTRADA HOL / 홀더 입고"): 
            st.session_state.es_invitado = False
            ir("ENTRADA", "holders")
        if st.button("SALIDA HOL / 홀더 출고"): 
            st.session_state.es_invitado = False
            ir("SALIDA", "holders")
        
    st.divider()
    if st.button("BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.session_state.user:
        if st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
    if st.button("SALIR / 로그아웃"): 
        st.session_state.user = None
        st.session_state.page = 'login'
        st.rerun()

def ir(acc, cat):
    st.session_state.accion = acc
    st.session_state.categoria = cat
    st.session_state.page = 'form'
    st.rerun()

def formulario():
    cat = st.session_state.categoria.upper()
    acc = st.session_state.accion
    
    tipo_txt = "ENTRADA / 입고" if acc == "ENTRADA" else "SALIDA / 출고"
    st.header(f"{cat} - {tipo_txt}")
    
    if st.session_state.get('es_invitado', False):
        st.warning("MODO INVITADO: Solo Salidas / 게스트 모드")

    cod = st.text_input("ID / CÓDIGO / 코드").upper().strip()
    
    # Value=None para que salga limpio
    cant = st.number_input("CANTIDAD / 수량", min_value=1, step=1, value=None, placeholder="Escribe aquí / 여기에 쓰기")
    
    if acc == "ENTRADA":
        conf = st.number_input("CONFIRMAR CANTIDAD / 수량 확인", min_value=1, step=1, value=None)
        ubi = st.text_input("UBICACIÓN / 위치").upper().strip()
        dest = "ALMACEN"
    else:
        ubi = "SALIDA / 출고"
        dest = st.text_input("QUIEN RETIRA / 수령자 (Manual)").upper().strip()
        
    if st.button("REGISTRAR / 등록"):
        if not cod: st.error("Falta Código / 코드 필요"); return
        if cant is None: st.error("Falta Cantidad / 수량 필요"); return
        
        if acc == "ENTRADA":
            if conf is None: st.error("Falta Confirmar Cantidad / 수량 확인 필요"); return
            if cant != conf: st.error("No coinciden / 불일치"); return
            if not ubi: st.error("Falta Ubicación / 위치 필요"); return
            val = cant
        else:
            tot = 0
            for d in db.collection(st.session_state.categoria).where("item", "==", cod).stream(): tot += d.to_dict().get('cantidad', 0)
            if cant > tot: st.error(f"Stock insuficiente / 재고 부족 (Max: {tot})"); return
            if not dest: st.error("Falta Quien Retira / 수령자 필요"); return
            val = -cant
            
        db.collection(st.session_state.categoria).add({
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), 
            "item": cod, 
            "cantidad": val, 
            "ubicacion": ubi, 
            "registrado_por": st.session_state.user, 
            "solicitante": dest
        })
        st.success("EXITO / 성공")
        
    if st.button("VOLVER / 돌아가기"): 
        if st.session_state.get('es_invitado', False):
            st.session_state.user = None
            st.session_state.page = 'login'
        else:
            st.session_state.page = 'menu'
        st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO / 코드").upper()
    
    stock_val = 0
    ubi_val = "---"
    
    if c:
        t = 0; u = set()
        for col in ["materiales", "holders"]:
            for d in db.collection(col).where("item", "==", c).stream():
                dt = d.to_dict()
                t += dt.get('cantidad', 0)
                
                # --- FILTRO IMPORTANTE: NO MOSTRAR "SALIDA" ---
                loc = dt.get('ubicacion', '').upper()
                if "SALIDA" not in loc and loc != "":
                    u.add(dt.get('ubicacion', ''))
        
        stock_val = t
        ubi_val = ", ".join(u) if u else "---"

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("STOCK / 재고", stock_val)
    with col2:
        st.metric("UBICACIÓN / 위치", ubi_val)
    st.divider()

    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu'; st.rerun()

def admin():
    st.title("PANEL ADMIN / 관리자")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["BORRAR/삭제", "EXCEL/엑셀", "STOCK/재고", "PERFIL/프로필", "USUARIOS/사용자"])
    
    with tab1: # BORRAR
        col = st.selectbox("Categoría / 카테고리", ["materiales", "holders"])
        c = st.text_input("Código a Borrar / 삭제할 코드").upper()
        if st.button("BORRAR DEFINITIVAMENTE / 영구 삭제"):
            docs = db.collection(col).where("item", "==", c).stream()
            count = 0
            for d in docs: db.collection(col).document(d.id).delete(); count+=1
            if count > 0: st.success("Borrado / 삭제됨")
            else: st.warning("No encontrado / 찾을 수 없음")

    with tab2: # EXCEL
        col_ex = st.selectbox("Descargar / 다운로드", ["materiales", "holders"])
        if st.button("GENERAR EXCEL / 엑셀 생성"):
            data = []
            for d in db.collection(col_ex).stream():
                dt = d.to_dict()
                qty = dt.get('cantidad', 0)
                tipo = "ENTRADA / 입고" if qty >= 0 else "SALIDA / 출고"
                data.append({
                    "FECHA Y HORA / 날짜 및 시간": str(dt.get('fecha', '')).upper(),
                    "REGISTRADO POR / 등록자": str(dt.get('registrado_por', '')).upper(),
                    "ITEM / 항목": str(dt.get('item', '')).upper(),
                    "CANTIDAD / 수량": qty,
                    "TIPO / 유형": tipo,
                    "UBICACIÓN / 위치": str(dt.get('ubicacion', '')).upper(),
                    "SOLICITANTE / 요청자": str(dt.get('solicitante', '---')).upper()
                })
            
            if data:
                df = pd.DataFrame(data)
                cols = ["FECHA Y HORA / 날짜 및 시간", "REGISTRADO POR / 등록자", "ITEM / 항목", "CANTIDAD / 수량", "TIPO / 유형", "UBICACIÓN / 위치", "SOLICITANTE / 요청자"]
                df = df[cols]
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("DESCARGAR CSV / 다운로드", csv, f"Reporte_{col_ex}.csv", "text/csv")
            else: st.warning("Vacío / 비어 있음")

    with tab3: # STOCK MASIVO
        st.subheader("CARGA MASIVA / 대량 등록")
        cat_st = st.selectbox("Categoría / 카테고리", ["materiales", "holders"], key="masiva_sel")
        st.caption("Formato: ID (espacio) CANTIDAD (espacio) UBICACION / 형식: ID (공백) 수량 (공백) 위치")
        txt = st.text_area("Pegar Lista / 목록 붙여넣기")
        if st.button("CARGAR LISTA / 목록 업로드"):
            for l in txt.split('\n'):
                p = l.replace('\t', ' ').split()
                if len(p)>=3:
                    db.collection(cat_st).add({
                        "fecha": datetime.now().strftime("%Y-%m-%d"), 
                        "item": p[0].upper(), 
                        "cantidad": int(p[1]), 
                        "ubicacion": p[2].upper(), 
                        "registrado_por": st.session_state.user, 
                        "tipo": "MASIVA", 
                        "solicitante": "CARGA"
                    })
            st.success("Cargado / 완료")

    with tab4: # PERFIL YAKO
        if st.session_state.user == "YAKO":
            nn = st.text_input("Nuevo Nombre / 새 이름").upper()
            nc = st.text_input("Nueva Clave / 새 비밀번호", type="password")
            nc2 = st.text_input("Confirmar Clave / 비밀번호 확인", type="password")
            if st.button("ACTUALIZAR / 업데이트"):
                if nc==nc2 and nn: db.collection("USUARIOS").document("YAKO").update({"nombre": nn, "clave": nc}); st.success("OK")
                else: st.error("No coinciden / 불일치")
        else: st.warning("Solo YAKO / 야코 전용")

    with tab5: # USUARIOS
        if st.session_state.user == "YAKO":
            us = [u.id for u in db.collection("USUARIOS").stream() if u.id != "YAKO"]
            if us:
                sel = st.selectbox("Usuario / 사용자", us)
                c1, c2 = st.columns(2)
                if c1.button("ACTIVAR / 활성화"): db.collection("USUARIOS").document(sel).update({"estado": "ACTIVO"}); st.success("Activado / 활성화됨")
                if c2.button("BORRAR / 삭제"): db.collection("USUARIOS").document(sel).delete(); st.success("Borrado / 삭제됨")
            else: st.info("No hay usuarios / 사용자 없음")

    if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): st.session_state.page = 'menu'; st.rerun()

# RUTEADOR
if st.session_state.page == 'login': login()
elif st.session_state.page == 'registro': registro()
elif st.session_state.page == 'cambio_clave': cambio_clave()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
