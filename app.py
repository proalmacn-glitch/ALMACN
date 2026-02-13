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
    /* Estilo para el panel de ajuste de Yako */
    .yako-adjust { border: 2px solid red; padding: 15px; border-radius: 10px; margin-top: 20px; background-color: #220000; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = 'login'

# ================= FUNCIONES =================

def login():
    st.title("LOGIN / 로그인")
    st.markdown("<h3 style='color: white !important;'>ALMACÉN / 창고</h3>", unsafe_allow_html=True)
    
    # --- LOGIN NORMAL (SIN CENTRADO FORZADO) ---
    user_input = st.text_input("Usuario / 사용자").upper().strip()
    password = st.text_input("Clave / 비밀번호", type="password").strip()
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ENTRAR / 입장"):
            data = None; doc_id = None 
            doc = db.collection("USUARIOS").document(user_input).get()
            if doc.exists:
                data = doc.to_dict(); doc_id = user_input
            else:
                query = db.collection("USUARIOS").where("nombre_personal", "==", user_input).stream()
                for d in query: data = d.to_dict(); doc_id = d.id; break 

            if data:
                if str(data.get('clave')) == password:
                    nombre_mostrar = data.get('nombre_personal', doc_id)
                    if doc_id == "YAKO":
                        st.session_state.user = "YAKO"; st.session_state.page = 'menu'; st.rerun()
                    elif data.get('estado') == "ACTIVO":
                        if data.get('cambio_pendiente', False):
                            st.session_state.temp_user = doc_id; st.session_state.page = 'cambio_clave'; st.rerun()
                        else:
                            st.session_state.user = nombre_mostrar; st.session_state.page = 'menu'; st.rerun()
                    else: st.warning("Cuenta Pendiente / 계정 대기 중")
                else: st.error("Clave Incorrecta / 비밀번호 오류")
            else: st.error("Usuario no existe / 사용자 없음")

    with col2:
        if st.button("REGISTRARSE / 등록"):
            animales = ["PERRO", "GATO", "LEON", "TIGRE", "PUMA", "OSO", "TORO", "LOBO", "RATA", "PATO"]
            n = len(list(db.collection("USUARIOS").stream()))
            u = f"USUARIO{n+1}"
            p = f"{random.choice(animales)}{random.randint(10, 99)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "PENDIENTE", "nombre": u, "nombre_personal": u, "cambio_pendiente": True})
            st.success(f"TOMA FOTO / 사진 찍기:\n\nUser: {u}\nPass: {p}")

    st.divider()
    st.markdown("<h4 style='color: yellow !important;'>SALIDA RÁPIDA (SIN LOGIN) / 빠른 출고</h4>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("SALIDA MATERIALES / 자재 출고"): st.session_state.user = "INVITADO / 손님"; st.session_state.es_invitado = True; ir("SALIDA", "materiales")
    with c2:
        if st.button("SALIDA HOLDERS / 홀더 출고"): st.session_state.user = "INVITADO / 손님"; st.session_state.es_invitado = True; ir("SALIDA", "holders")
    
    st.write("") 
    if st.button("🔍 BUSCAR MATERIAL / 재고 검색"): st.session_state.page = 'buscar'; st.rerun()

    st.write("")
    st.write("")
    c_img1, c_img2, c_img3 = st.columns([1, 2, 1]) 
    with c_img2:
        st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")

def cambio_clave():
    st.title("PRIMER INICIO / 첫 로그인")
    nn = st.text_input("Nuevo Nombre / 새 이름").upper().strip()
    nc = st.text_input("Nueva Clave / 새 비밀번호", type="password")
    nc2 = st.text_input("Confirmar Clave / 비밀번호 확인", type="password")
    if st.button("GUARDAR / 저장"):
        if nc == nc2 and nn and nc:
            db.collection("USUARIOS").document(st.session_state.temp_user).update({"nombre_personal": nn, "clave": nc, "cambio_pendiente": False})
            st.session_state.user = nn; st.session_state.es_invitado = False; st.session_state.page = 'menu'; st.rerun()
        else: st.error("Error: Claves no coinciden / 오류: 비밀번호 불일치")

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
    
    if st.session_state.user == "YAKO":
        pend = len(list(db.collection("USUARIOS").where("estado", "==", "PENDIENTE").stream()))
        if pend > 0: st.error(f"⚠ {pend} USUARIOS PENDIENTES / 대기 중인 사용자")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("MATERIALES / 자재")
        if st.button("ENTRADA MAT / 자재 입고"): st.session_state.es_invitado = False; ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT / 자재 출고"): st.session_state.es_invitado = False; ir("SALIDA", "materiales")
    with c2:
        st.subheader("HOLDERS / 홀더")
        if st.button("ENTRADA HOL / 홀더 입고"): st.session_state.es_invitado = False; ir("ENTRADA", "holders")
        if st.button("SALIDA HOL / 홀더 출고"): st.session_state.es_invitado = False; ir("SALIDA", "holders")
        
    st.divider()

    col_botones, col_gif = st.columns([1.5, 1])

    with col_botones:
        if st.button("BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
        if st.session_state.user:
            if st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
        if st.button("SALIR / 로그아웃"): st.session_state.user = None; st.session_state.page = 'login'; st.rerun()
    
    with col_gif:
        st.image("https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExZHV3YjNoYXFxYXA4MDl5Z3NyYWpkM2w5MDR0dnE3YWJjMGVuaTNpcSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/jTYy5WWGYTBp610Ddd/giphy.gif", use_column_width=True)

def ir(acc, cat):
    st.session_state.accion = acc; st.session_state.categoria = cat; st.session_state.page = 'form'; st.rerun()

def formulario():
    cat = st.session_state.categoria.upper(); acc = st.session_state.accion
    tipo_txt = "ENTRADA / 입고" if acc == "ENTRADA" else "SALIDA / 출고"
    st.header(f"{cat} - {tipo_txt}")
    if st.session_state.get('es_invitado', False): st.warning("MODO INVITADO: Solo Salidas / 게스트 모드")

    cod = st.text_input("ID / CÓDIGO / 코드").upper().strip()
    cant = st.number_input("CANTIDAD / 수량", min_value=1, step=1, value=None, placeholder="Escribe aquí / 여기에 쓰기")
    st.caption("Por seguridad, confirma la cantidad / 보안을 위해 수량을 확인하세요:")
    conf = st.number_input("CONFIRMAR CANTIDAD / 수량 확인", min_value=1, step=1, value=None, placeholder="Repite el número / 숫자 반복")

    sub_categoria = None

    if acc == "ENTRADA":
        ubi = st.text_input("UBICACIÓN / 위치").upper().strip()
        
        st.write("---")
        opciones_cat = ["ROBOT", "GUN", "JIG", "ATD", "STUD ARC", "STUD RESISTENCE", "CO2", "SEALER", "H.W", "OTRO"]
        sub_categoria = st.selectbox("CATEGORÍA (OPCIONAL) / 카테고리 (선택)", opciones_cat, index=None, placeholder="Seleccionar / 선택")
        st.write("---")
        
        dest = "ALMACEN"
    else:
        ubi = "SALIDA / 출고"
        dest = st.text_input("QUIEN RETIRA / 수령자 (Manual)").upper().strip()
    
    st.write("---")
    foto = st.camera_input("FOTO EVIDENCIA / 증거 사진")
    st.write("---")
        
    if st.button("REGISTRAR / 등록"):
        if not cod: st.error("Falta Código / 코드 필요"); return
        if cant is None or conf is None: st.error("Faltan Cantidades / 수량 필요"); return
        if cant != conf: st.error(f"❌ ERROR: Las cantidades no coinciden / 수량 불일치 ({cant} vs {conf})"); return

        if acc == "ENTRADA":
            if not ubi: st.error("Falta Ubicación / 위치 필요"); return
            val = cant
        else:
            tot = 0
            for d in db.collection(st.session_state.categoria).where("item", "==", cod).stream(): tot += d.to_dict().get('cantidad', 0)
            if cant > tot: st.error(f"Stock insuficiente / 재고 부족 (Max: {tot})"); return
            if not dest: st.error("Falta Quien Retira / 수령자 필요"); return
            val = -cant
            
        url_foto = "NO FOTO"
        if foto:
            try:
                bucket = storage.bucket()
                nombre_archivo = f"evidencias/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{cod}.jpg"
                blob = bucket.blob(nombre_archivo)
                blob.upload_from_file(foto, content_type='image/jpeg')
                blob.make_public(); url_foto = blob.public_url
            except Exception as e: st.error(f"Error foto: {e}"); url_foto = "ERROR"

        datos_guardar = {
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), 
            "item": cod, 
            "cantidad": val, 
            "ubicacion": ubi, 
            "registrado_por": st.session_state.user, 
            "solicitante": dest, 
            "foto_url": url_foto
        }
        
        if sub_categoria:
            datos_guardar["categoria_detalle"] = sub_categoria

        db.collection(st.session_state.categoria).add(datos_guardar)
        st.success("EXITO / 성공")
        
    if st.button("VOLVER / 돌아가기"): 
        if st.session_state.get('es_invitado', False): st.session_state.user = None; st.session_state.page = 'login'
        else: st.session_state.page = 'menu'
        st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO / 코드").upper()
    s = 0; u_list = set()
    
    # Detección
    coleccion_detectada = None 
    
    if c:
        for col in ["materiales", "holders"]:
            docs = list(db.collection(col).where("item", "==", c).stream())
            if len(docs) > 0:
                coleccion_detectada = col.upper() # DETECTADO
                
            for d in docs:
                dt = d.to_dict(); s += dt.get('cantidad', 0)
                l = dt.get('ubicacion', '').upper()
                if "SALIDA" not in l and l != "": u_list.add(l)
    
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("STOCK / 재고", s)
    c2.metric("UBICACIÓN / 위치", ", ".join(u_list) if u_list else "---")
    st.divider()

    # --- PANEL EXCLUSIVO DE YAKO ---
    if st.session_state.user == "YAKO" and c:
        st.markdown("""<div class="yako-adjust"><h3>⚠️ ADMIN PANEL (YAKO)</h3></div>""", unsafe_allow_html=True)
        
        # 1. AJUSTE DE STOCK
        st.markdown("#### 1. AJUSTE DE STOCK / 재고 조정")
        col_adj1, col_adj2 = st.columns(2)
        
        with col_adj1:
            # LÓGICA DE FIJADO (LOCK):
            if coleccion_detectada == "HOLDERS":
                idx_def = 1
                esta_fijo = True # BLOQUEADO
            elif coleccion_detectada == "MATERIALES":
                idx_def = 0
                esta_fijo = True # BLOQUEADO
            else:
                idx_def = 0
                esta_fijo = False # DESBLOQUEADO (Nuevo)
            
            target_sel = st.selectbox("Colección / 컬렉션", ["MATERIALES", "HOLDERS"], index=idx_def, disabled=esta_fijo, key="adj_col")
            target_col = target_sel.lower()
            
        with col_adj2:
            adj_qty = st.number_input("Cantidad (+/-) / 수량", step=1, value=0, key="adj_qty")
        
        st.caption("Ejemplo: 5 (Sumar) / -3 (Restar) / 예: 더하려면 5, 빼려면 -3")
        
        if st.button("CONFIRMAR AJUSTE / 조정 확인", key="btn_conf_adj"):
            if adj_qty != 0:
                db.collection(target_col).add({
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "item": c,
                    "cantidad": adj_qty,
                    "ubicacion": "AJUSTE MANUAL YAKO",
                    "registrado_por": "YAKO",
                    "solicitante": "AJUSTE DIRECTO",
                    "foto_url": "NO FOTO",
                    "tipo": "AJUSTE"
                })
                st.success(f"Ajuste de {adj_qty} aplicado a {c} / 조정 완료.")
                st.rerun() 
            else: st.warning("Cantidad es 0 / 수량이 0입니다.")

        st.divider()

        # 2. EDITAR CATEGORÍA
        st.markdown("#### 2. EDITAR CATEGORÍA / 카테고리 편집")
        st.caption("Actualiza la categoría de este código en TODOS los registros históricos. / 모든 기록 업데이트.")
        
        new_cat_yako = st.selectbox("NUEVA CATEGORÍA / 새 카테고리", ["ROBOT", "GUN", "JIG", "ATD", "STUD ARC", "STUD RESISTENCE", "CO2", "SEALER", "H.W", "OTRO"], key="cat_yako_update")
        
        if st.button("ACTUALIZAR CATEGORÍA / 카테고리 업데이트", key="btn_cat_upd"):
            m_docs = db.collection("materiales").where("item", "==", c).stream()
            for d in m_docs: db.collection("materiales").document(d.id).update({"categoria_detalle": new_cat_yako})
            
            h_docs = db.collection("holders").where("item", "==", c).stream()
            for d in h_docs: db.collection("holders").document(d.id).update({"categoria_detalle": new_cat_yako})
            
            st.success("Categoría actualizada correctamente / 카테고리 업데이트 완료")
            st.rerun()

        st.divider()

    if st.button("VOLVER / 돌아가기"):
        if st.session_state.user is None: st.session_state.page = 'login'
        else: st.session_state.page = 'menu'
        st.rerun()

def admin():
    st.title("PANEL ADMIN / 관리자")
    t1, t2, t3, t4, t5 = st.tabs(["BORRAR/삭제", "EXCEL/엑셀", "STOCK/재고", "PERFIL/프로필", "USUARIOS/사용자"])
    
    with t1:
        col_sel = st.selectbox("Categoría / 카테고리", ["MATERIALES", "HOLDERS"]); 
        col = col_sel.lower()
        c = st.text_input("Código a Borrar / 삭제할 코드").upper()
        if st.button("BORRAR DEFINITIVAMENTE / 영구 삭제", key="btn_borrar_item"):
            docs = db.collection(col).where("item", "==", c).stream()
            count = 0
            for d in docs: db.collection(col).document(d.id).delete(); count+=1
            if count > 0: st.success("Borrado / 삭제됨")
            else: st.warning("No encontrado / 찾을 수 없음")

    with t2:
        ce_sel = st.selectbox("Descargar / 다운로드", ["MATERIALES", "HOLDERS"])
        ce = ce_sel.lower()
        if st.button("GENERAR EXCEL / 엑셀 생성", key="btn_excel"):
            data = []
            for d in db.collection(ce).stream():
                dt = d.to_dict(); q = dt.get('cantidad', 0)
                tipo_mov = "AJUSTE MANUAL / 수동 조정" if dt.get('tipo') == "AJUSTE" else ("ENTRADA / 입고" if q>=0 else "SALIDA / 출고")
                
                data.append({
                    "FECHA / 날짜": dt.get('fecha', ''), 
                    "REGISTRADO POR / 등록자": dt.get('registrado_por', ''), 
                    "ITEM / 항목": dt.get('item', ''), 
                    "CANTIDAD / 수량": q, 
                    "TIPO / 유형": tipo_mov, 
                    "CATEGORÍA / 카테고리": dt.get('categoria_detalle', '---'),
                    "UBICACIÓN / 위치": dt.get('ubicacion', ''), 
                    "SOLICITANTE / 요청자": dt.get('solicitante', ''), 
                    "FOTO / 사진 (LINK)": dt.get('foto_url', 'NO')
                })
            
            if data:
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("DESCARGAR CSV / 다운로드", csv, f"Reporte_{ce}.csv", "text/csv")
            else: st.warning("Vacío / 비어 있음")

    with t3:
        cat_sel = st.selectbox("Categoría / 카테고리", ["MATERIALES", "HOLDERS"], key="mas"); 
        cat_st = cat_sel.lower()
        txt = st.text_area("Formato: ID CANT UBI / 형식: ID 수량 위치")
        if st.button("CARGAR LISTA / 목록 업로드", key="btn_cargar"):
            for l in txt.split('\n'):
                p = l.replace('\t', ' ').split()
                if len(p)>=3: db.collection(cat_st).add({"fecha": datetime.now().strftime("%Y-%m-%d"), "item": p[0].upper(), "cantidad": int(p[1]), "ubicacion": p[2].upper(), "registrado_por": st.session_state.user, "tipo": "MASIVA"})
            st.success("Cargado / 완료")

    with t4:
        if st.session_state.user == "YAKO":
            n = st.text_input("Nuevo Nombre / 새 이름"); 
            p = st.text_input("Nueva Clave / 새 비밀번호", type="password"); 
            p2 = st.text_input("Confirmar / 확인", type="password")
            if st.button("ACTUALIZAR / 업데이트", key="btn_update_yako"):
                if p==p2 and n: db.collection("USUARIOS").document("YAKO").update({"nombre": n, "clave": p}); st.success("OK")

    with t5:
        if st.session_state.user == "YAKO":
            us = []; u_ids = []
            for u in db.collection("USUARIOS").stream():
                if u.id != "YAKO":
                    d = u.to_dict(); nombre = d.get('nombre_personal', 'SIN NOMBRE'); estado = d.get('estado', '')
                    us.append(f"{u.id} - {nombre} ({estado})"); u_ids.append(u.id)
            if us:
                s = st.selectbox("Usuario / 사용자", us)
                sid = u_ids[us.index(s)]
                c1, c2 = st.columns(2)
                if c1.button("ACTIVAR / 활성화", key="btn_activar_user"): 
                    db.collection("USUARIOS").document(sid).update({"estado": "ACTIVO"}); st.success("OK"); st.rerun()
                if c2.button("BORRAR / 삭제", key="btn_borrar_user"): 
                    db.collection("USUARIOS").document(sid).delete(); st.success("Eliminado / 삭제됨"); st.rerun()
            else: st.info("No hay usuarios / 사용자 없음")

    if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): st.session_state.page = 'menu'; st.rerun()

if st.session_state.page == 'login': login()
elif st.session_state.page == 'registro': registro()
elif st.session_state.page == 'cambio_clave': cambio_clave()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
