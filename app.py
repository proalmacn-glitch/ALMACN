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
import urllib.parse

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
def obtener_url_final(url):
    if not url or str(url).upper() in ["NO FOTO", "NAN", "NONE", "0"]:
        return None
    url_limpia = str(url).strip()
    if "drive.google.com" in url_limpia:
        match = re.search(r'(?:id=|d/|file/d/)([-\w]{25,})', url_limpia)
        if match:
            return f'https://drive.google.com/uc?export=download&id={match.group(1)}'
    return url_limpia

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
    h1, h2, h3 { color: red !important; text-align: center; font-weight: bold; }
    .stButton>button { background-color: white; color: black; border-radius: 2px; width: 100%; font-weight: bold; border: 2px solid red; height: 45px;}
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label, div[data-testid="stNumberInput"] label { color: yellow !important; font-weight: bold; }
    .stTextInput>div>div>input { text-align: center; background-color: #262730; color: cyan !important; font-size: 20px; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 45px !important; color: #00cccc !important; text-align: center !important; }
    div[data-testid="stMetricLabel"] { font-size: 18px !important; color: white !important; text-align: center !important; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; }
    
    .media-container { display: flex; flex-direction: row; flex-wrap: wrap; justify-content: center; align-items: center; gap: 20px; width: 100%; margin-top: 20px; }
    .photo-right { flex: 1; max-width: 400px; min-width: 280px; border-radius: 15px; border: 3px solid red; box-shadow: 0px 4px 15px rgba(255, 0, 0, 0.5); }
    .qr-left { background-color: #1a1a1a; padding: 15px; border-radius: 15px; border: 1px solid #333; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    .center-container { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; text-align: center; }
    
    .user-card { border: 1px solid #444; padding: 15px; border-radius: 10px; margin-bottom: 10px; background-color: #0e0e0e; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

# ================= VISTAS / 보기 =================

def login():
    st.markdown("<h1>LOGIN / 로그인</h1>", unsafe_allow_html=True)
    st.markdown("<h3>ALMACÉN / 창고 🔗</h3>", unsafe_allow_html=True)
    
    u_in = st.text_input("USUARIO / 사용자").upper().strip()
    p_in = st.text_input("CLAVE / 비밀번호", type="password").strip()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(u_in).get()
            if doc.exists and str(doc.to_dict().get('clave')) == p_in:
                st.session_state.user = u_in
                if doc.to_dict().get('estado') == "NUEVO":
                    st.session_state.page = 'cambiar_datos'
                else:
                    st.session_state.page = 'menu'
                st.rerun()
            else: st.error("Error de credenciales / 자격 증명 오류")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USER{random.randint(10,99)}", f"{random.randint(100,999)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "NUEVO"})
            st.success(f"User temporal: {u} | Pass: {p}")
            
    st.divider()
    
    st.markdown("<h2>SALIDA RÁPIDA / 빠른 출고</h2>", unsafe_allow_html=True)
    c5, c6 = st.columns(2)
    with c5:
        if st.button("SALIDA MATERIALES / 자재 출고"):
            st.session_state.user = "INVITADO"
            ir("SALIDA", "materiales")
    with c6:
        if st.button("SALIDA HOLDERS / 홀더 출고"):
            st.session_state.user = "INVITADO"
            ir("SALIDA", "holders")
    
    if st.button("🔍 BUSCAR MATERIAL / 재고 검색"): 
        st.session_state.user = "INVITADO"
        st.session_state.page = 'buscar'; st.rerun()
    
    st.markdown('<div class="center-container">', unsafe_allow_html=True)
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif")
    st.markdown('</div>', unsafe_allow_html=True)

def cambiar_datos():
    st.markdown("<h1>ACTUALIZAR DATOS / 데이터 업데이트</h1>", unsafe_allow_html=True)
    st.info("⚠️ Para continuar, por favor personaliza tu usuario y contraseña. / 계속하려면 사용자 이름과 비밀번호를 설정하세요.")
    
    nuevo_u = st.text_input("NUEVO USUARIO / 새 사용자").upper().strip()
    nueva_p = st.text_input("NUEVA CLAVE / 새 비밀번호", type="password").strip()
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_v, _ = st.columns([0.4, 0.6])
    with col_v:
        if st.button("GUARDAR Y ENTRAR / 저장 및 입장"):
            if nuevo_u and nueva_p:
                if nuevo_u != st.session_state.user:
                    doc_check = db.collection("USUARIOS").document(nuevo_u).get()
                    if doc_check.exists:
                        st.error("⚠️ El usuario ya existe. Elige otro. / 사용자 이름이 이미 존재합니다.")
                        return
                
                db.collection("USUARIOS").document(nuevo_u).set({
                    "clave": nueva_p, 
                    "estado": "ACTIVO"
                })
                if nuevo_u != st.session_state.user:
                    db.collection("USUARIOS").document(st.session_state.user).delete()
                    
                st.session_state.user = nuevo_u
                st.session_state.page = 'menu'
                st.success("✅ Datos actualizados!")
                st.rerun()
            else:
                st.error("⚠️ Completa ambos campos.")

def menu():
    st.markdown("<h1>ALMACÉN / 창고</h1>", unsafe_allow_html=True)
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<h3>MATERIALES / 자재</h3>", unsafe_allow_html=True)
        if st.button("ENTRADA MAT / 자재 입고"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT / 자재 출고"): ir("SALIDA", "materiales")
    with c2:
        st.markdown("<h3>HOLDERS / 홀더</h3>", unsafe_allow_html=True)
        if st.button("ENTRADA HOL / 홀더 입고"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL / 홀더 출고"): ir("SALIDA", "holders")
    
    st.divider()
    
    col_btn, _ = st.columns([0.4, 0.6])
    with col_btn:
        if st.button("BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
        if st.button("PANEL CONTROL / 제어판"): st.session_state.page = 'admin'; st.rerun()
        if st.button("SALIR / 로그아웃"): st.session_state.user=None; st.session_state.page='login'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    busqueda = st.text_input("ESCRIBE NOMBRE O ID / ID o 이름 입력").upper().strip()
    
    if busqueda:
        coincidencias = []
        for col in ["materiales", "holders"]:
            docs = db.collection(col).stream()
            for d in docs:
                data = d.to_dict()
                nom = str(data.get('nombre', '')).upper()
                idx = str(data.get('item', '')).upper()
                if busqueda in nom or busqueda in idx:
                    data['cat_db'] = col
                    data['label'] = f"{nom} | {idx}"
                    coincidencias.append(data)
        
        if coincidencias:
            opciones = [c['label'] for c in coincidencias]
            seleccion = st.selectbox("RESULTADOS / 검색 결과:", opciones)
            item = next(c for c in coincidencias if c['label'] == seleccion)
            
            id_f, col_f = item.get('item'), item['cat_db']
            nombre_item = item.get('nombre', '')
            st.markdown(f"<h2>{nombre_item}</h2>", unsafe_allow_html=True)
            
            docs_s = db.collection(col_f).where("item", "==", id_f).stream()
            tot = sum([d.to_dict().get('cantidad', 0) for d in docs_s])
            
            if tot <= 5:
                st.warning(f"⚠️ STOCK BAJO: Quedan {tot} unidades / 재고 부족: {tot}개 남음")
            
            c1, c2 = st.columns(2)
            c1.metric("STOCK ACTUAL / 재고", max(0, tot))
            c2.metric("UBICACIÓN / 위치", item.get('ubicacion', '---'))
            
            st.divider()
            st.markdown('<div class="media-container">', unsafe_allow_html=True)
            
            nombre_id_qr = f"{nombre_item}/{id_f}"
            nombre_codificado = urllib.parse.quote(nombre_id_qr)
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={nombre_codificado}&bgcolor=000000&color=ffffff"
            
            st.markdown(f'''
                <div class="qr-left">
                    <img src="{qr_url}" width="150">
                    <div style="margin-top:5px; font-size:12px; color:gray;">QR {nombre_id_qr}</div>
                </div>
            ''', unsafe_allow_html=True)
            
            foto_url = obtener_url_final(item.get('foto_url', ''))
            if foto_url:
                st.markdown(f'''
                    <div class="photo-right">
                        <img src="{foto_url}" style="width:100%; border-radius:15px;">
                    </div>
                ''', unsafe_allow_html=True)
            else:
                st.markdown('<div class="photo-right" style="text-align:center; color:gray;">Sin foto / 사진 없음</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No se encontraron resultados / 결과 없음")

    # --- SEGURIDAD: REDIRECCIÓN PARA INVITADOS ---
    if st.button("VOLVER / 돌아가기"): 
        if st.session_state.user == "INVITADO":
            st.session_state.user = None
            st.session_state.page = 'login'
        else:
            st.session_state.page = 'menu'
        st.rerun()

def formulario():
    cat, acc = st.session_state.get('categoria'), st.session_state.get('accion')
    st.markdown(f"<h1>{cat.upper()} - {acc}</h1>", unsafe_allow_html=True)
    
    with st.expander("📷 CÁMARA QR / QR 카메라"):
        cam = st.camera_input("SCAN")
        if cam:
            res = decodificar_qr(cam)
            if res and res != st.session_state.scanned_id:
                st.session_state.scanned_id = res
                st.rerun()
            
    busqueda_form = st.text_input("ID O NOMBRE / 코드 또는 이름", value=st.session_state.scanned_id).upper().strip()
    cod_final = ""
    
    if busqueda_form:
        termino_busqueda = busqueda_form.split("/")[-1].strip() if "/" in busqueda_form else busqueda_form
        
        coincidencias = []
        seen = set()
        docs = db.collection(cat).stream()
        for d in docs:
            data = d.to_dict()
            nom = str(data.get('nombre', '')).upper()
            idx = str(data.get('item', '')).upper()
            
            if termino_busqueda in nom or termino_busqueda in idx:
                if idx not in seen:
                    seen.add(idx)
                    data['label'] = f"{nom} | {idx}"
                    coincidencias.append(data)
        
        if coincidencias:
            if len(coincidencias) == 1:
                cod_final = coincidencias[0]['item']
                st.success(f"✅ Seleccionado: {coincidencias[0]['label']}")
            else:
                opciones = [c['label'] for c in coincidencias]
                seleccion = st.selectbox("COINCIDENCIAS ENCONTRADAS / 일치 항목:", opciones)
                item_sel = next(c for c in coincidencias if c['label'] == seleccion)
                cod_final = item_sel['item']
        else:
            st.warning("⚠️ No encontrado en la base de datos.")
            cod_final = busqueda_form

    cant = st.number_input("CANTIDAD / 수량", min_value=1, key="cant1")
    cant_conf = st.number_input("CONFIRMAR CANTIDAD / 수량 확인", min_value=0, key="cant2")
    
    if cant != cant_conf and cant_conf > 0:
        st.error("⚠️ LAS CANTIDADES NO COINCIDEN / 수량이 일치하지 않습니다")

    if acc == "SALIDA":
        solicitante = st.text_input("NOMBRE SOLICITANTE / 신청자 이름").upper().strip()
        ubi = "SALIDA"
        bloqueado = (cant != cant_conf) or (not solicitante) or (not cod_final)
    else: # ENTRADA
        ubi = st.text_input("UBICACIÓN / 위치").upper().strip()
        solicitante = ""
        bloqueado = (cant != cant_conf) or (not ubi) or (not cod_final)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_v, _ = st.columns([0.4, 0.6])
    with col_v:
        if st.button("REGISTRAR / 등록", disabled=bloqueado):
            if cod_final:
                db.collection(cat).add({
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "item": cod_final,
                    "cantidad": cant if acc == "ENTRADA" else -cant, "ubicacion": ubi, 
                    "solicitante": solicitante,
                    "registrado_por": st.session_state.user
                })
                st.success("✅ REGISTRADO / 등록 완료")
                st.balloons()
                st.session_state.scanned_id = "" 
            else:
                st.error("Por favor, ingresa el ID.")
        
        # --- SEGURIDAD: REDIRECCIÓN PARA INVITADOS ---
        if st.button("VOLVER / 돌아가기"): 
            st.session_state.scanned_id = "" 
            if st.session_state.user == "INVITADO":
                st.session_state.user = None
                st.session_state.page = 'login'
            else:
                st.session_state.page = 'menu'
            st.rerun()

def admin():
    st.markdown("<h1>PANEL CONTROL / 제어판</h1>", unsafe_allow_html=True)
    
    es_yako = (st.session_state.user == "YAKO")
    
    if es_yako:
        t1, t2, t3, t4 = st.tabs(["BORRAR / 삭제", "EXCEL DETALLADO / 엑셀", "CARGA MASIVA / 대량 로드", "USUARIOS / 사용자"])
    else:
        t2, t3 = st.tabs(["EXCEL DETALLADO / 엑셀", "CARGA MASIVA / 대량 로드"])
    
    if es_yako:
        with t1:
            st.markdown("<h3 style='color:red;'>BORRADO DE STOCK / 재고 삭제 🔗</h3>", unsafe_allow_html=True)
            cdb = st.selectbox("CATEGORÍA / 카테고리", ["materiales", "holders"])
            del_id = st.text_input("ID ESPECÍFICO (DEJAR VACÍO PARA TODO) / 특정 ID (모두 삭제하려면 비워 두세요)").upper()
            if st.checkbox("SÍ, ESTOY SEGURO / 네, 확실합니다"):
                if st.button("🔴 EJECUTAR BORRADO / 삭제 실행"):
                    ds = db.collection(cdb).where("item", "==", del_id).stream() if del_id else db.collection(cdb).stream()
                    for d in ds: db.collection(cdb).document(d.id).delete()
                    st.success("BORRADO COMPLETADO / 삭제 완료"); st.rerun()
                
    with t2:
        ce = st.selectbox("REPORTE / 보고서", ["materiales", "holders"])
        if st.button("📥 GENERAR EXCEL / 엑셀 생성"):
            data = [d.to_dict() for d in db.collection(ce).order_by("fecha").stream()]
            if data:
                df = pd.DataFrame(data).rename(columns={'fecha':'FECHA','item':'ID','nombre':'NOMBRE','cantidad':'MOV','ubicacion':'UBICACIÓN','solicitante':'SOLICITANTE','registrado_por':'USUARIO'})
                cols_to_export = [c for c in ['FECHA','ID','NOMBRE','MOV','UBICACIÓN','SOLICITANTE','USUARIO'] if c in df.columns]
                csv = df[cols_to_export].to_csv(index=False).encode('utf-8-sig')
                st.download_button("Descargar / 다운로드", csv, f"Reporte_{ce}.csv", "text/csv")
                
    with t3:
        dest = st.selectbox("DESTINO / 목적지", ["materiales", "holders"])
        arch = st.file_uploader("Subir .xlsx / .xlsx 업로드", type=['xlsx'])
        if arch and st.button("🚀 INICIAR CARGA / 로드 시작"):
            df_in = pd.read_excel(arch)
            for _, f in df_in.iterrows():
                db.collection(dest).add({
                    "nombre": str(f.get('NOMBRE','')).upper(),
                    "item": str(f.get('ID','')).upper(),
                    "cantidad": int(f.get('CANTIDAD',0)),
                    "ubicacion": str(f.get('UBICACIÓN','ALM')).upper(),
                    "foto_url": str(f.get('FOTO','NO FOTO')),
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "registrado_por": st.session_state.user if st.session_state.user else "ADMIN"
                })
            st.success("CARGA LISTA / 로드 완료")
            
    if es_yako:
        with t4:
            uds = db.collection("USUARIOS").stream()
            for u in uds:
                ud = u.to_dict()
                with st.container():
                    st.markdown(f'<div class="user-card">ID: {u.id} | Clave: {ud.get("clave")} | Estado: {ud.get("estado")}</div>', unsafe_allow_html=True)
                    if u.id != "YAKO":
                        if st.button("BORRAR USUARIO / 사용자 삭제", key=f"d_{u.id}"): 
                            db.collection("USUARIOS").document(u.id).delete()
                            st.rerun()
                    
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_v, _ = st.columns([0.4, 0.6])
    with col_v:
        if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): 
            st.session_state.page = 'menu'
            st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'cambiar_datos': cambiar_datos()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'admin': admin()
