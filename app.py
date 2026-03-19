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
    .yako-adjust { border: 2px solid red; padding: 15px; border-radius: 10px; margin-top: 20px; background-color: #220000; }
    .img-container { border: 2px solid #333; border-radius: 10px; padding: 5px; background-color: #000; text-align: center; margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'user' not in st.session_state: st.session_state.user = None
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
            if not user_input:
                st.warning("Escribe un usuario / 사용자 이름을 입력하세요")
            else:
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

    cod = st.text_input("ID / CÓDIGO / 코드", key="reg_cod").upper().strip()
    cant = st.number_input("CANTIDAD / 수량", min_value=1, step=1, value=None, placeholder="Escribe aquí / 여기에 쓰기", key="reg_cant")
    st.caption("Por seguridad, confirma la cantidad / 보안을 위해 수량을 확인하세요:")
    conf = st.number_input("CONFIRMAR CANTIDAD / 수량 확인", min_value=1, step=1, value=None, placeholder="Repite el número / 숫자 반복", key="reg_conf")

    sub_categoria = None

    if acc == "ENTRADA":
        ubi = st.text_input("UBICACIÓN / 위치", key="reg_ubi").upper().strip()
        st.write("---")
        opciones_cat = ["ROBOT", "GUN", "JIG", "ATD", "STUD ARC", "STUD RESISTENCE", "CO2", "SEALER", "H.W", "OTRO"]
        sub_categoria = st.selectbox("CATEGORÍA (OPCIONAL) / 카테고리 (선택)", opciones_cat, index=None, placeholder="Seleccionar / 선택", key="reg_cat")
        st.write("---")
        dest = "ALMACEN"
    else:
        ubi = "SALIDA / 출고"
        dest = st.text_input("QUIEN RETIRA / 수령자 (Manual)", key="reg_dest").upper().strip()
    
    st.write("---")
    foto = st.camera_input("FOTO EVIDENCIA / 증거 사진", key="reg_foto")
    st.write("---")
    
    boton_registrar = st.button("REGISTRAR / 등록")

    if boton_registrar:
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
            "ubicacion": ubi, # CORREGIDO A UBICACION
            "registrado_por": st.session_state.user, 
            "solicitante": dest, 
            "foto_url": url_foto
        }
        
        if sub_categoria: datos_guardar["categoria_detalle"] = sub_categoria

        db.collection(st.session_state.categoria).add(datos_guardar)
        st.success("✅ ÉXITO / 성공"); st.rerun()
        
    if st.button("VOLVER / 돌아가기"): 
        if st.session_state.get('es_invitado', False): st.session_state.user = None; st.session_state.page = 'login'
        else: st.session_state.page = 'menu'
        st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    c = st.text_input("ID / CÓDIGO / 코드 (Parcial o Completo)").upper().strip()
    
    s = 0; u_list = set(); foto_mostrar = None
    coleccion_detectada = None 
    final_code_to_use = None
    
    if c:
        matches = []
        for col in ["materiales", "holders"]:
            all_docs_search = db.collection(col).stream()
            for d in all_docs_search:
                dt = d.to_dict()
                item_code = dt.get('item', '')
                if c in item_code: matches.append((item_code, col))

        unique_matches = sorted(list(set(matches)))
        
        if len(unique_matches) == 0: st.warning("No encontrado")
        elif len(unique_matches) > 1:
            st.info(f"Se encontraron {len(unique_matches)} coincidencias:")
            opciones = [f"{m[0]} ({m[1].upper()})" for m in unique_matches]
            seleccion = st.selectbox("Selecciona uno / 선택하세요", opciones)
            final_code_to_use = seleccion.split(" (")[0]
            coleccion_detectada = seleccion.split(" (")[1].replace(")", "").lower()
        else:
            final_code_to_use = unique_matches[0][0]
            coleccion_detectada = unique_matches[0][1].lower()

    if final_code_to_use:
        docs_res = db.collection(coleccion_detectada).where("item", "==", final_code_to_use).stream()
        for dr in docs_res:
            dt_r = dr.to_dict()
            s += dt_r.get('cantidad', 0)
            # BUSCAR EN 'ubicacion' o 'ubi' por si hay datos mezclados
            l = str(dt_r.get('ubicacion', dt_r.get('ubi', ''))).upper()
            if "SALIDA" not in l and "AJUSTE" not in l and l != "" and l != "NONE": u_list.add(l)
            if dt_r.get('foto_url') and dt_r.get('foto_url') not in ["NO FOTO", "ERROR"]:
                foto_mostrar = dt_r.get('foto_url')

        st.subheader(f"RESULTADO: {final_code_to_use}")
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("STOCK / 재고", s)
        c2.metric("UBICACIÓN / 위치", ", ".join(u_list) if u_list else "---")
        st.divider()
        
        if foto_mostrar:
            try:
                st.markdown('<div class="img-container">', unsafe_allow_html=True)
                st.image(foto_mostrar, caption=f"ID: {final_code_to_use}")
                st.markdown('</div>', unsafe_allow_html=True)
            except:
                st.info("Imagen no disponible temporalmente / 사진을 현재 사용할 수 없습니다")

        if st.session_state.user == "YAKO":
            st.markdown("""<div class="yako-adjust"><h3>⚠️ ADMIN PANEL (YAKO)</h3></div>""", unsafe_allow_html=True)
            st.markdown("#### 1. AJUSTE DE STOCK")
            ca1, ca2, ca3 = st.columns(3)
            with ca1: st.text(f"Colección: {coleccion_detectada.upper()}")
            with ca2: aq = st.number_input("Cantidad (+/-)", step=1, key="aq")
            with ca3: au = st.text_input("Ubicación Real", key="au").upper()
            if st.button("CONFIRMAR AJUSTE"):
                if aq != 0:
                    db.collection(coleccion_detectada).add({"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": final_code_to_use, "cantidad": aq, "ubicacion": au if au else "AJUSTE", "registrado_por": "YAKO", "solicitante": "AJUSTE", "foto_url": "NO FOTO", "tipo": "AJUSTE"})
                    st.success("Ajustado"); st.rerun()

            st.divider()
            st.markdown("#### 2. CORREGIR UBICACIÓN HISTÓRICA")
            nh = st.text_input("Nueva Ubicación Única").upper()
            if st.button("ACTUALIZAR TODO EL HISTORIAL"):
                docs_up = db.collection(coleccion_detectada).where("item", "==", final_code_to_use).stream()
                for du in docs_up: db.collection(coleccion_detectada).document(du.id).update({"ubicacion": nh})
                st.success("Ubicaciones actualizadas"); st.rerun()

    if st.button("VOLVER / 돌아가기"):
        if st.session_state.user is None: st.session_state.page = 'login'
        else: st.session_state.page = 'menu'
        st.rerun()

def admin():
    st.title("PANEL ADMIN / 관리자")
    t1, t2, t3, t4, t5 = st.tabs(["BORRAR/삭제", "EXCEL/엑셀", "STOCK/재고", "PERFIL/프로필", "USUARIOS/사용자"])
    
    with t1:
        cs = st.selectbox("Categoría", ["MATERIALES", "HOLDERS"]); cl = cs.lower()
        bc = st.text_input("Código a Borrar").upper()
        if st.button("BORRAR DEFINITIVAMENTE"):
            docs_b = db.collection(cl).where("item", "==", bc).stream()
            for db_i in docs_b: db.collection(cl).document(db_i.id).delete()
            st.success("Borrado")
        st.divider()
        if st.button("🔥 BORRAR TODA LA COLECCIÓN 🔥"):
            all_b = db.collection(cl).stream()
            for ab in all_b: db.collection(cl).document(ab.id).delete()
            st.success("Colección vacía")

    with t2:
        ce_s = st.selectbox("Descargar", ["MATERIALES", "HOLDERS"]); ce_l = ce_s.lower()
        if st.button("GENERAR EXCEL"):
            data_e = []
            for d in db.collection(ce_l).stream():
                dt = d.to_dict(); q = dt.get('cantidad', 0)
                data_e.append({"FECHA": dt.get('fecha'), "REGISTRADO POR": dt.get('registrado_por'), "ITEM": dt.get('item'), "CANTIDAD": q, "UBICACIÓN": dt.get('ubicacion', dt.get('ubi', '')), "SOLICITANTE": dt.get('solicitante'), "FOTO": dt.get('foto_url')})
            if data_e:
                df = pd.DataFrame(data_e)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("DESCARGAR CSV", csv, f"{ce_l}.csv", "text/csv")

    with t3:
        cm_s = st.selectbox("Categoría masiva", ["MATERIALES", "HOLDERS"], key="mas"); cm_l = cm_s.lower()
        txt = st.text_area("ID CANT UBICACION")
        if st.button("CARGAR LISTA"):
            for l in txt.split('\n'):
                p = l.replace('\t', ' ').split()
                if len(p)>=3: db.collection(cm_l).add({"fecha": datetime.now().strftime("%Y-%m-%d"), "item": p[0].upper(), "cantidad": int(p[1]), "ubicacion": p[2].upper(), "registrado_por": st.session_state.user, "tipo": "MASIVA", "foto_url": "NO FOTO"})
            st.success("Cargado")

    with t4:
        if st.session_state.user == "YAKO":
            un = st.text_input("Nuevo Nombre Yako"); up = st.text_input("Nueva Clave Yako", type="password")
            if st.button("ACTUALIZAR YAKO"):
                db.collection("USUARIOS").document("YAKO").update({"nombre_personal": un, "clave": up})
                st.success("OK")

    with t5:
        if st.session_state.user == "YAKO":
            for u in db.collection("USUARIOS").stream():
                if u.id != "YAKO":
                    ud = u.to_dict()
                    st.write(f"{u.id} - {ud.get('nombre_personal')} ({ud.get('estado')})")
                    if st.button(f"ACTIVAR {u.id}"): db.collection("USUARIOS").document(u.id).update({"estado": "ACTIVO"}); st.rerun()
                    if st.button(f"ELIMINAR {u.id}"): db.collection("USUARIOS").document(u.id).delete(); st.rerun()

    if st.button("VOLVER AL MENÚ"): st.session_state.page = 'menu'; st.rerun()

if st.session_state.page == 'login': login()
elif st.session_state.page == 'cambio_clave': cambio_clave()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'admin': admin()
