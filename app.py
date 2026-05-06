import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage 
import pandas as pd
from datetime import datetime
import os
import random
import numpy as np
import cv2
import re
import urllib.parse
import io
import unicodedata 
from collections import defaultdict

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="YAKO PRO WEB", page_icon="📦", layout="centered")

# --- CONEXIÓN FIREBASE ---
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

# --- OPTIMIZACIÓN: CACHÉ DE INVENTARIO ---
@st.cache_data
def obtener_inventario():
    datos = []
    try:
        for col in ["materiales", "holders"]:
            docs = db.collection(col).stream()
            for d in docs:
                item = d.to_dict()
                item['cat_db'] = col
                item['label'] = f"{str(item.get('nombre', '')).upper()} | {str(item.get('item', '')).upper()}"
                item['doc_id'] = d.id 
                datos.append(item)
        return datos
    except Exception as e:
        return []

# ================= FUNCIONES PARA KPI Y CLASIFICACIÓN =================

def clasificar_tipo(descripcion):
    """Clasifica el material en categorías según palabras clave."""
    if not descripcion:
        return "OTRO"
    d = descripcion.upper()
    if any(p in d for p in ["FANUC", "ROBOT", "RBT"]):
        return "FANUC"
    if "JIG" in d or "FIXTURE" in d:
        return "JIG"
    if "HOLDER" in d:
        return "HOLDER"
    if any(p in d for p in ["SENSOR", "PRT", "PRDT", "PRFT"]):
        return "HW (Sensor)"
    if any(p in d for p in ["CYLINDER", "CILINDRO", "ASB", "TCM"]):
        return "CILINDRO"
    if any(p in d for p in ["VALVULA", "VUVG", "SY3120"]):
        return "VALVULA"
    return "OTRO"

def calcular_puntaje_y_grado(uso_promedio, costo_score=1, tiempo_entrega_score=1, frecuencia_uso_score=3, cantidad_equipos_score=1):
    """
    Calcula puntaje total, grado, % stock, stock mínimo y máximo.
    Los valores por defecto se pueden ajustar según el criterio real.
    """
    puntaje_total = costo_score + tiempo_entrega_score + frecuencia_uso_score + cantidad_equipos_score
    if puntaje_total >= 13:
        grado = "A"
    elif puntaje_total >= 9:
        grado = "B"
    elif puntaje_total >= 5:
        grado = "C"
    else:
        grado = "D"
    
    # Porcentaje de stock necesario según puntaje (según tu tabla)
    if puntaje_total <= 4:
        pct_stock = 0.5   # 50%
    elif puntaje_total <= 8:
        pct_stock = 0.75  # 75%
    elif puntaje_total <= 12:
        pct_stock = 1.0   # 100%
    else:
        pct_stock = 3.0   # 300%
    
    stock_minimo = uso_promedio * pct_stock
    stock_maximo = stock_minimo * 2   # según tu fórmula N = M + (M*100%)
    return puntaje_total, grado, stock_minimo, stock_maximo

def recalcular_stock_por_item():
    """
    Devuelve un dict con item -> {stock_actual, nombre, cat_db, ubicacion, movimientos}
    Suma todas las cantidades (entradas positivas, salidas negativas).
    """
    items_data = defaultdict(lambda: {"stock": 0, "nombre": "", "cat_db": "", "ubicacion": "", "movimientos": []})
    for doc in obtener_inventario():
        cod = doc.get('item')
        if not cod:
            continue
        items_data[cod]["stock"] += doc.get('cantidad', 0)
        items_data[cod]["nombre"] = doc.get('nombre', '')
        items_data[cod]["cat_db"] = doc.get('cat_db', '')
        items_data[cod]["ubicacion"] = doc.get('ubicacion', '')
        items_data[cod]["movimientos"].append({
            "fecha": doc.get('fecha'),
            "cantidad": doc.get('cantidad', 0),
            "tipo": "ENTRADA" if doc.get('cantidad',0) > 0 else "SALIDA"
        })
    return items_data

def actualizar_campos_kpi(uso_promedio_default=5):
    """
    Actualiza todos los documentos de 'materiales' y 'holders' con los campos:
    tipo, grado, stock_minimo, stock_maximo, uso_promedio.
    (Se ejecuta una sola vez o cuando se agreguen nuevos materiales)
    """
    items_totales = defaultdict(lambda: {"stock": 0, "nombre": "", "doc_ids": [], "cat_db": ""})
    for col in ["materiales", "holders"]:
        docs = db.collection(col).stream()
        for doc in docs:
            data = doc.to_dict()
            cod = data.get('item')
            if not cod:
                continue
            items_totales[cod]["stock"] += data.get('cantidad', 0)
            items_totales[cod]["nombre"] = data.get('nombre', '')
            items_totales[cod]["doc_ids"].append(doc.id)
            items_totales[cod]["cat_db"] = col
    
    for cod, info in items_totales.items():
        nombre = info["nombre"]
        tipo = clasificar_tipo(nombre)
        # Aquí podrías usar el uso_promedio real si lo tienes, si no, usamos el default
        puntaje, grado, stock_min, stock_max = calcular_puntaje_y_grado(uso_promedio_default)
        for doc_id in info["doc_ids"]:
            db.collection(info["cat_db"]).document(doc_id).update({
                "tipo": tipo,
                "grado": grado,
                "stock_minimo": round(stock_min, 2),
                "stock_maximo": round(stock_max, 2),
                "uso_promedio": uso_promedio_default
            })
    # Limpiar caché
    obtener_inventario.clear()
    st.success("✅ Campos KPI actualizados en todos los documentos.")

def registrar_kpi_mensual():
    """Calcula el stock rate actual y lo guarda en la colección 'historial_kpi' con la fecha actual."""
    items_data = recalcular_stock_por_item()
    total = len(items_data)
    if total == 0:
        return None
    ok_count = 0
    for cod, info in items_data.items():
        # Obtener stock_min y stock_max desde el primer documento de ese item
        doc_sample = None
        for col in ["materiales", "holders"]:
            docs = db.collection(col).where("item", "==", cod).limit(1).stream()
            for d in docs:
                doc_sample = d.to_dict()
                break
            if doc_sample:
                break
        if doc_sample:
            stock_min = doc_sample.get('stock_minimo', 0)
            stock_max = doc_sample.get('stock_maximo', 0)
            stock_act = info["stock"]
            if stock_min <= stock_act <= stock_max:
                ok_count += 1
        else:
            # si no tiene campos, no contar
            pass
    rate = (ok_count / total * 100) if total > 0 else 0
    mes_actual = datetime.now().strftime("%Y-%m")
    doc_ref = db.collection("historial_kpi").document(mes_actual)
    doc_ref.set({
        "mes": mes_actual,
        "stock_rate": rate,
        "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_materiales": total,
        "materiales_ok": ok_count
    })
    return rate

# --- UTILIDADES TÉCNICAS EXISTENTES (QR, etc.) ---

def obtener_url_final(url):
    if not url or str(url).upper() in ["NO FOTO", "NAN", "NONE", "0", ""]:
        return None
    url_limpia = str(url).strip()
    if "drive.google.com" in url_limpia:
        match = re.search(r'(?:id=|d/|file/d/)([-\w]{25,})', url_limpia)
        if match:
            return f'https://drive.google.com/uc?export=download&id={match.group(1)}'
    if not url_limpia.startswith("http"):
        return None
    return url_limpia

def decodificar_qr(foto):
    try:
        foto.seek(0)
        file_bytes = np.asarray(bytearray(foto.read()), dtype=np.uint8)
        img = cv2.imdecode(file_bytes, 1)
        detector = cv2.QRCodeDetector()
        data, bbox, _ = detector.detectAndDecode(img)
        if data:
            return str(data).upper()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        data2, _, _ = detector.detectAndDecode(thresh)
        if data2:
            return str(data2).upper()
    except Exception as e: 
        return None
    return None

def ir(acc, cat):
    st.session_state.accion = acc
    st.session_state.categoria = cat
    st.session_state.page = 'form'
    st.session_state.pop('busqueda_input', None)
    st.rerun()

# --- ESTILOS VISUALES (igual que original) ---
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

# --- INICIALIZACIÓN DE SESIÓN ---
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'busqueda_input' not in st.session_state: st.session_state.busqueda_input = "" 

# ================= VISTAS (login, menu, buscar, formulario, admin, etc.) =================

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
            st.success(f"User temporal / 임시 사용자: {u} | Pass / 비밀번호: {p}")
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
        if not st.session_state.user:
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
    col_v, _ = st.columns([0.4, 0.6])
    with col_v:
        if st.button("GUARDAR Y ENTRAR / 저장 및 입장"):
            if nuevo_u and nueva_p:
                if nuevo_u != st.session_state.user:
                    doc_check = db.collection("USUARIOS").document(nuevo_u).get()
                    if doc_check.exists:
                        st.error("⚠️ El usuario ya existe. Elige otro. / 사용자 이름이 이미 존재합니다. 다른 이름을 선택하세요.")
                        return
                db.collection("USUARIOS").document(nuevo_u).set({"clave": nueva_p, "estado": "ACTIVO"})
                if nuevo_u != st.session_state.user:
                    db.collection("USUARIOS").document(st.session_state.user).delete()
                st.session_state.user = nuevo_u
                st.session_state.page = 'menu'
                st.success("✅ Datos actualizados! / 데이터 업데이트 완료!")
                st.rerun()
            else:
                st.error("⚠️ Completa ambos campos. / 두 필드를 모두 입력하세요.")

def menu():
    st.markdown("<h1>ALMACÉN / 창고</h1>", unsafe_allow_html=True)
    usuario_actual = st.session_state.user if st.session_state.user else "INVITADO"
    st.info(f"HOLA / 안녕하세요: {usuario_actual}")
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
    st.header("BUSCAR MATERIAL / 재료 검색 (con mapa de racks)")
    busqueda = st.text_input("ESCRIBE ID o NOMBRE / 코드 또는 이름 입력", key="busqueda_input_buscar").upper().strip()
    item_seleccionado = None
    stock_total = 0
    foto_url = None
    nombre_item = ""
    id_f = ""
    col_f = ""
    rack_highlight = None
    ubicacion_raw = ""
    
    if busqueda:
        inventario_total = obtener_inventario()
        coincidencias = [item for item in inventario_total if busqueda in str(item.get('nombre', '')).upper() or busqueda in str(item.get('item', '')).upper()]
        if coincidencias:
            if len(coincidencias) > 1:
                st.info(f"⚠️ HAY {len(coincidencias)} COINCIDENCIAS. / {len(coincidencias)}개의 일치 항목이 있습니다.")
            opciones = list(set([c['label'] for c in coincidencias])) 
            seleccion = st.selectbox("RESULTADOS / 검색 결과:", opciones)
            item_seleccionado = next(c for c in coincidencias if c['label'] == seleccion)
            id_f = item_seleccionado.get('item')
            col_f = item_seleccionado['cat_db']
            nombre_item = item_seleccionado.get('nombre', '')
            ubicacion_raw = item_seleccionado.get('ubicacion', '')
            rack_match = re.match(r'([A-Z]+\d*)', ubicacion_raw.upper())
            rack_highlight = rack_match.group(1) if rack_match else None
            stock_total = sum([d.get('cantidad', 0) for d in inventario_total if d.get('item') == id_f and d.get('cat_db') == col_f])
            foto_url = obtener_url_final(item_seleccionado.get('foto_url', ''))
        else:
            st.warning("No se encontraron resultados / 결과 없음")
    
    # Mapa de racks (mismo código que tenías)
    st.subheader("🗺️ MAPA DE RACKS / 랙 지도")
    def rack_color(name):
        return "#8FC360" if (rack_highlight and name == rack_highlight) else "#8B0000"
    map_html = f'''
    <div style="position: relative; width: 530px; height: 550px; margin: 0 auto; background-color: black; border: 2px solid #333; border-radius: 10px;">
        <div style="position: absolute; left: 110px; top: 20px; width: 120px; height: 50px; background-color: {rack_color("G1")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg); text-shadow: 1px 1px 0px black;">G1</span></div>
        <div style="position: absolute; left: 230px; top: 20px; width: 120px; height: 50px; background-color: {rack_color("G2")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg); text-shadow: 1px 1px 0px black;">G2</span></div>
        <div style="position: absolute; left: 350px; top: 20px; width: 120px; height: 50px; background-color: {rack_color("G3")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg); text-shadow: 1px 1px 0px black;">G3</span></div>
        <div style="position: absolute; left: 40px; top: 20px; width: 60px; height: 100px; background-color: {rack_color("H2")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; text-shadow: 1px 1px 0px black;">H2</span></div>
        <div style="position: absolute; left: 40px; top: 120px; width: 60px; height: 100px; background-color: {rack_color("H1")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; text-shadow: 1px 1px 0px black;">H1</span></div>
        <div style="position: absolute; left: 110px; top: 100px; width: 120px; height: 50px; background-color: {rack_color("I1")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg); text-shadow: 1px 1px 0px black;">I1</span></div>
        <div style="position: absolute; left: 230px; top: 100px; width: 120px; height: 50px; background-color: {rack_color("I2")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg); text-shadow: 1px 1px 0px black;">I2</span></div>
        <div style="position: absolute; left: 110px; top: 160px; width: 120px; height: 50px; background-color: {rack_color("K1")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg); text-shadow: 1px 1px 0px black;">K1</span></div>
        <div style="position: absolute; left: 230px; top: 160px; width: 120px; height: 50px; background-color: {rack_color("K2")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg); text-shadow: 1px 1px 0px black;">K2</span></div>
        <div style="position: absolute; left: 410px; top: 85px; width: 60px; height: 70px; background-color: {rack_color("F1")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; text-shadow: 1px 1px 0px black;">F1</span></div>
        <div style="position: absolute; left: 410px; top: 155px; width: 60px; height: 70px; background-color: {rack_color("F2")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; text-shadow: 1px 1px 0px black;">F2</span></div>
        <div style="position: absolute; left: 410px; top: 225px; width: 60px; height: 70px; background-color: {rack_color("F3")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; text-shadow: 1px 1px 0px black;">F3</span></div>
        <div style="position: absolute; left: 410px; top: 225px; width: 60px; height: 70px; background-color: {rack_color("F4")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; text-shadow: 1px 1px 0px black;">F4</span></div>
        <div style="position: absolute; left: 410px; top: 295px; width: 60px; height: 70px; background-color: {rack_color("F5")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; text-shadow: 1px 1px 0px black;">F5</span></div>
        <div style="position: absolute; left: 410px; top: 365px; width: 60px; height: 70px; background-color: {rack_color("F6")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 5px rgba(0,0,0,0.5);"><span style="color: white; font-weight: bold; font-size: 18px; text-shadow: 1px 1px 0px black;">F6</span></div>
    </div>
    '''
    st.markdown(map_html, unsafe_allow_html=True)
    
    if item_seleccionado:
        st.markdown(f"<h2 style='text-align:center;'>{nombre_item}</h2>", unsafe_allow_html=True)
        if stock_total <= 5:
            st.warning(f"⚠️ STOCK BAJO: Quedan {stock_total} unidades / 재고 부족: {stock_total}개 남음")
        col1, col2 = st.columns(2)
        col1.metric("STOCK ACTUAL / 재고", max(0, stock_total))
        col2.metric("UBICACIÓN / 위치", ubicacion_raw if ubicacion_raw else "---")
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
        if foto_url:
            st.markdown(f'<div class="photo-right"><img src="{foto_url}" style="width:100%; border-radius:15px;"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="photo-right" style="text-align:center; color:gray;">Sin foto / 사진 없음</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        if st.session_state.user == "YAKO":
            st.markdown("<br>")
            st.markdown("<h4 style='text-align: center; color: yellow;'>📸 AGREGAR / ACTUALIZAR FOTO (SOLO YAKO)</h4>", unsafe_allow_html=True)
            col_f1, col_f2 = st.columns([0.7, 0.3])
            with col_f1:
                nueva_foto_url = st.text_input("PEGA EL ENLACE AQUÍ (Drive, web, etc.) / 사진 링크", key=f"foto_input_{id_f}")
            with col_f2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 GUARDAR FOTO / 사진 저장", key=f"btn_foto_{id_f}"):
                    if nueva_foto_url:
                        with st.spinner("Guardando en la base de datos... / 저장 중..."):
                            docs_update = db.collection(col_f).where("item", "==", id_f).stream()
                            for doc in docs_update:
                                db.collection(col_f).document(doc.id).update({"foto_url": nueva_foto_url})
                            obtener_inventario.clear() 
                            st.success("✅ FOTO ACTUALIZADA PARA TODOS / 사진 업데이트 완료")
                            st.rerun()
                    else:
                        st.warning("⚠️ Pegue un enlace antes de guardar. / 링크를 붙여넣으세요.")
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
        cam = st.camera_input("SCAN", key="qr_cam_input") 
        if cam:
            res = decodificar_qr(cam)
            if res:
                texto_qr_limpio = res.strip()
                if st.session_state.get("busqueda_input", "") != texto_qr_limpio:
                    st.session_state["busqueda_input"] = texto_qr_limpio
                    st.rerun()
            else:
                st.warning("⚠️ No se detectó un QR claro. Intenta acercarlo, quitar reflejos o mejorar la luz.")
            
    busqueda_form = st.text_input("BUSCAR ID O NOMBRE / 코드 또는 이름 검색", key="busqueda_input").upper().strip()
    cod_final = ""
    nombre_final = ""
    es_nuevo = False
    
    if busqueda_form:
        termino_busqueda = busqueda_form.split("/")[-1].strip() if "/" in busqueda_form else busqueda_form
        inventario_total = obtener_inventario()
        coincidencias = []
        coincidencia_exacta = None
        for item in inventario_total:
            if item['cat_db'] == cat:
                nom = str(item.get('nombre', '')).upper()
                idx = str(item.get('item', '')).upper()
                if termino_busqueda == idx:
                    coincidencia_exacta = item
                    break 
                elif termino_busqueda in nom or termino_busqueda in idx:
                    coincidencias.append(item)
        if coincidencia_exacta:
            coincidencias_unicas = [coincidencia_exacta]
        else:
            coincidencias_unicas = []
            vistos = set()
            for c in coincidencias:
                if c['label'] not in vistos:
                    vistos.add(c['label'])
                    coincidencias_unicas.append(c)
        coincidencias = coincidencias_unicas
        
        if acc == "SALIDA":
            if coincidencias:
                if len(coincidencias) == 1:
                    cod_final, nombre_final = coincidencias[0]['item'], coincidencias[0].get('nombre', '')
                    st.success(f"✅ Seleccionado: {coincidencias[0]['label']}")
                else:
                    opciones = [c['label'] for c in coincidencias]
                    seleccion = st.selectbox("COINCIDENCIAS ENCONTRADAS / 일치 항목:", opciones)
                    item_sel = next(c for c in coincidencias if c['label'] == seleccion)
                    cod_final, nombre_final = item_sel['item'], item_sel.get('nombre', '')
            else:
                st.error("⚠️ MATERIAL NO ENCONTRADO.")
        else: # ENTRADA
            if coincidencias:
                if len(coincidencias) == 1 and coincidencia_exacta:
                    opciones = [coincidencias[0]['label']] + ["➕ CREAR NUEVO MATERIAL / 새 자재 생성"]
                else:
                    opciones = [c['label'] for c in coincidencias] + ["➕ CREAR NUEVO MATERIAL / 새 자재 생성"]
                seleccion = st.selectbox("SELECCIONA O CREA NUEVO / 선택 또는 새로 만들기:", opciones)
                if seleccion == "➕ CREAR NUEVO MATERIAL / 새 자재 생성": 
                    es_nuevo = True
                else:
                    item_sel = next(c for c in coincidencias if c['label'] == seleccion)
                    cod_final, nombre_final = item_sel['item'], item_sel.get('nombre', '')
            else:
                st.warning("⚠️ No encontrado. Se registrará como NUEVO MATERIAL.")
                es_nuevo = True
            if es_nuevo:
                nuevo_id = st.text_input("ID DEL MATERIAL / 자재 코드", value=termino_busqueda).upper().strip()
                nuevo_nom = st.text_input("NOMBRE DEL MATERIAL / 자재 이름").upper().strip()
                cod_final, nombre_final = nuevo_id, nuevo_nom

    cant = st.number_input("CANTIDAD / 수량", min_value=1, key="cant1")
    cant_conf = st.number_input("CONFIRMAR CANTIDAD / 수량 확인", min_value=0, key="cant2")
    if cant != cant_conf and cant_conf > 0: st.error("⚠️ LAS CANTIDADES NO COINCIDEN")

    foto_evidencia = None
    if acc == "SALIDA":
        solicitante = st.text_input("NOMBRE SOLICITANTE / 신청자 이름").upper().strip()
        linea_uso = st.text_input("LÍNEA EN LA QUE SE UTILIZARÁ / 사용할 라인").upper().strip()
        with st.expander("📸 CAPTURAR EVIDENCIA / 증거 사진"):
            foto_evidencia = st.camera_input("FOTO EVIDENCIA", key="evidencia_cam_input")
        ubi = "SALIDA"
        bloqueado = (cant != cant_conf) or (not solicitante) or (not linea_uso) or (not cod_final)
    else: # ENTRADA
        ubi = st.text_input("UBICACIÓN / 위치").upper().strip()
        solicitante, linea_uso = "", ""
        bloqueado = (cant != cant_conf) or (not ubi) or (not cod_final) or (es_nuevo and not nombre_final)
        
    col_v, _ = st.columns([0.4, 0.6])
    with col_v:
        if st.button("REGISTRAR / 등록", disabled=bloqueado):
            url_foto_final = "SIN EVIDENCIA"
            fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            if foto_evidencia:
                with st.spinner("Subiendo evidencia..."):
                    nombre_archivo = f"evidencias/EVIDENCIA_{nombre_final}_{linea_uso}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg".replace(" ", "_")
                    bucket = storage.bucket()
                    blob = bucket.blob(nombre_archivo)
                    blob.upload_from_string(foto_evidencia.getvalue(), content_type='image/jpeg')
                    blob.make_public()
                    url_foto_final = blob.public_url
            # Al guardar, también podemos actualizar campos KPI opcionalmente (opcional)
            db.collection(cat).add({
                "fecha": fecha_str, "item": cod_final, "nombre": nombre_final,
                "cantidad": cant if acc == "ENTRADA" else -cant, "ubicacion": ubi, 
                "solicitante": solicitante, "linea_uso": linea_uso,
                "evidencia_url": url_foto_final,
                "registrado_por": st.session_state.user if st.session_state.user else "INVITADO"
            })
            obtener_inventario.clear() 
            st.session_state.pop('busqueda_input', None)
            st.success("✅ REGISTRADO CON ÉXITO")
            st.balloons()
            st.rerun() 
        if st.button("VOLVER / 돌아가기"): 
            st.session_state.pop('busqueda_input', None)
            st.session_state.page = 'login' if st.session_state.user == "INVITADO" else 'menu'
            st.rerun()

def admin():
    st.markdown("<h1>PANEL CONTROL / 제어판</h1>", unsafe_allow_html=True)
    es_yako = (st.session_state.user == "YAKO")
    
    # Creamos 6 pestañas (la última es KPI)
    if es_yako:
        t1, t2, t3, t4, t5, t6 = st.tabs(["BORRAR / 삭제", "EXCEL DETALLADO / 엑셀", "CARGA MASIVA / 대량 로드", "USUARIOS / 사용자", "ESCANEAR TEXTO / 텍스트 스캔", "📊 KPI"])
    else:
        t2, t3 = st.tabs(["EXCEL DETALLADO / 엑셀", "CARGA MASIVA / 대량 로드"])
    
    if es_yako:
        with t1:
            st.markdown("<h3 style='color:red;'>BORRADO DE STOCK / 재고 삭제 🔗</h3>", unsafe_allow_html=True)
            cdb = st.selectbox("CATEGORÍA / 카테고리", ["materiales", "holders"])
            del_id = st.text_input("ID ESPECÍFICO (DEJAR VACÍO PARA TODO) / 특정 ID (모두 삭제하려면 비워 두세요)").upper()
            if st.checkbox("SÍ, ESTOY SEGURO / 네, 확실합니다"):
                if st.button("🔴 EJECUTAR BORRADO / 삭제 실행"):
                    if del_id:
                        docs_ref = db.collection(cdb).where("item", "==", del_id).stream()
                    else:
                        docs_ref = db.collection(cdb).stream()
                    docs_borrar = list(docs_ref)
                    total_borrar = len(docs_borrar)
                    if total_borrar == 0:
                        st.warning("⚠️ No hay registros para borrar. / 삭제할 레코드가 없습니다.")
                    else:
                        barra_borrado = st.progress(0, text=f"🗑️ Iniciando borrado de {total_borrar} registros...")
                        for i, doc in enumerate(docs_borrar):
                            db.collection(cdb).document(doc.id).delete()
                            barra_borrado.progress((i+1)/total_borrar)
                        barra_borrado.empty()
                        obtener_inventario.clear() 
                        st.success(f"✅ BORRADO COMPLETADO: {total_borrar} registros eliminados.")
                        st.rerun()
        
        with t2:  # EXCEL
            ce = st.selectbox("REPORTE / 보고서", ["materiales", "holders"])
            if st.button("📥 GENERAR EXCEL / 엑셀 생성"):
                data = [d.to_dict() for d in db.collection(ce).order_by("fecha").stream()]
                if data:
                    df = pd.DataFrame(data)
                    for col in ['fecha', 'item', 'nombre', 'cantidad', 'ubicacion', 'solicitante', 'linea_uso', 'evidencia_url', 'registrado_por']:
                        if col not in df.columns: df[col] = ''
                    df = df.rename(columns={'fecha':'FECHA / 날짜','item':'ID','nombre':'NOMBRE / 이름','cantidad':'CANTIDAD / 수량','ubicacion':'UBICACIÓN / 위치','solicitante':'SOLICITANTE / 신청자','linea_uso':'LÍNEA_USO / 사용 라인','evidencia_url':'EVIDENCIA / 증거','registrado_por':'USUARIO / 사용자'})
                    cols_export = [c for c in ['FECHA / 날짜','ID','NOMBRE / 이름','CANTIDAD / 수량','UBICACIÓN / 위치','SOLICITANTE / 신청자','LÍNEA_USO / 사용 라인','EVIDENCIA / 증거','USUARIO / 사용자'] if c in df.columns]
                    csv = df[cols_export].to_csv(index=False).encode('utf-8-sig')
                    st.download_button("Descargar / 다운로드", csv, f"Reporte_{ce}.csv", "text/csv")
        
        with t3:  # CARGA MASIVA
            dest = st.selectbox("DESTINO / 목적지", ["materiales", "holders"])
            arch = st.file_uploader("Subir .xlsx / .xlsx 업로드", type=['xlsx'])
            if arch and st.button("🚀 INICIAR CARGA / 로드 시작"):
                try:
                    df_in = pd.read_excel(arch, engine='openpyxl').fillna('')
                    def limpiar_columna(col):
                        c = str(col).split('/')[0].strip().upper()
                        c = ''.join(char for char in unicodedata.normalize('NFKD', c) if unicodedata.category(char) != 'Mn')
                        return c
                    df_in.columns = [limpiar_columna(c) for c in df_in.columns]
                    if df_in.empty:
                        st.error("⚠️ El archivo Excel está vacío. / 엑셀 파일이 비어 있습니다.")
                    else:
                        total_filas = len(df_in)
                        barra = st.progress(0)
                        for i, (_, f) in enumerate(df_in.iterrows()):
                            item_id = str(f.get('ID', '')).strip()
                            if not item_id: continue
                            raw_cant = str(f.get('CANTIDAD', '0')).strip()
                            if '.' in raw_cant: raw_cant = raw_cant.split('.')[0]
                            cant_limpia = re.sub(r'\D', '', raw_cant) 
                            cantidad_final = int(cant_limpia) if cant_limpia else 0
                            db.collection(dest).add({
                                "nombre": str(f.get('NOMBRE','')).upper(),
                                "item": item_id.upper(),
                                "cantidad": cantidad_final,
                                "ubicacion": str(f.get('UBICACION','ALM')).upper(),
                                "foto_url": str(f.get('FOTO','NO FOTO')),
                                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "registrado_por": st.session_state.user if st.session_state.user else "ADMIN"
                            })
                            barra.progress((i+1)/total_filas)
                        barra.empty()
                        obtener_inventario.clear() 
                        st.success("✅ CARGA MASIVA COMPLETADA AL 100%")
                        st.balloons()
                except Exception as e:
                    st.error(f"⚠️ Error al procesar el Excel: {e}")
        
        with t4:  # USUARIOS
            uds = db.collection("USUARIOS").stream()
            for u in uds:
                ud = u.to_dict()
                with st.container():
                    st.markdown(f'<div class="user-card">ID: {u.id} | Clave: {ud.get("clave")} | Estado: {ud.get("estado")}</div>', unsafe_allow_html=True)
                    if u.id != "YAKO":
                        if st.button("BORRAR USUARIO / 사용자 삭제", key=f"d_{u.id}"): 
                            db.collection("USUARIOS").document(u.id).delete()
                            st.rerun()
        
        with t5:  # ESCANEAR TEXTO (OCR)
            st.markdown("<h3 style='color:red;'>ESCANEAR TEXTO (OCR) / 텍스트 스캔 🔗</h3>", unsafe_allow_html=True)
            cam_ocr = st.camera_input("CÁMARA OCR / OCR 카메라", key="cam_ocr")
            if cam_ocr:
                try:
                    import pytesseract
                    from PIL import Image
                    import xlsxwriter
                    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                    img_pil = Image.open(cam_ocr)
                    texto_extraido = pytesseract.image_to_string(img_pil).strip()
                    if texto_extraido:
                        st.success("✅ Texto detectado / 텍스트 감지됨")
                        texto_final = st.text_area("TEXTO EXTRAÍDO (Editable) / 추출된 텍스트 (편집 가능)", value=texto_extraido, height=150)
                        output = io.BytesIO()
                        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
                        worksheet = workbook.add_worksheet("OCR_DATA")
                        worksheet.set_column('A:A', 40)
                        worksheet.set_column('B:B', 60)
                        cell_format = workbook.add_format({'text_wrap': True, 'valign': 'vcenter'})
                        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'align': 'center', 'border': 1})
                        worksheet.write('A1', 'FOTO CAPTURADA / 캡처된 사진', header_format)
                        worksheet.write('B1', 'TEXTO DETECTADO / 감지된 텍스트', header_format)
                        img_data = io.BytesIO(cam_ocr.getvalue())
                        worksheet.insert_image('A2', 'foto.png', {'image_data': img_data, 'x_scale': 0.3, 'y_scale': 0.3})
                        worksheet.write('B2', texto_final, cell_format)
                        worksheet.set_row(1, 150)
                        workbook.close()
                        output.seek(0)
                        st.download_button("📥 DESCARGAR EXCEL CON FOTO Y TEXTO / 엑셀 다운로드", output, f"OCR_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    else:
                        st.warning("⚠️ No se detectó texto claro en la imagen.")
                except ImportError:
                    st.error("⚠️ Faltan librerías. Ejecuta: pip install pytesseract xlsxwriter pillow")
                except Exception as e:
                    st.error(f"⚠️ Error de OCR: {e}")
        
        with t6:  # NUEVA PESTAÑA KPI
            st.markdown("<h3 style='color:red;'>📈 KPI - GESTIÓN DE RESURTIMIENTO (재고 관리 KPI)</h3>", unsafe_allow_html=True)
            st.info("Esta sección calcula automáticamente el **Spare part stock rate** según los criterios de resurtimiento.")
            
            # Botón para actualizar campos KPI (tipo, grado, stock_min, stock_max) en todos los documentos
            if st.button("🔄 ACTUALIZAR CAMPOS KPI (calcular grados y stocks)"):
                with st.spinner("Procesando todos los materiales... Esto puede tardar unos segundos."):
                    uso_default = st.number_input("Uso promedio mensual (si no se tiene el dato)", min_value=1, value=5)
                    actualizar_campos_kpi(uso_promedio_default=uso_default)
                    st.success("Campos KPI actualizados correctamente. Ahora puedes ver los indicadores.")
                    st.rerun()
            
            # Botón para registrar el KPI del mes actual (guardar histórico)
            if st.button("📅 REGISTRAR KPI DEL MES ACTUAL (guardar historial)"):
                rate = registrar_kpi_mensual()
                if rate is not None:
                    st.success(f"KPI mensual registrado: {rate:.1f}% para {datetime.now().strftime('%Y-%m')}")
                else:
                    st.warning("No hay materiales para calcular el KPI.")
            
            # Obtener datos actualizados
            items_data = recalcular_stock_por_item()
            if not items_data:
                st.warning("No hay materiales cargados en el inventario.")
            else:
                # Construir DataFrame detallado
                registros = []
                for cod, info in items_data.items():
                    # Buscar un documento de ese item para obtener los campos KPI
                    doc_sample = None
                    for col in ["materiales", "holders"]:
                        docs = db.collection(col).where("item", "==", cod).limit(1).stream()
                        for d in docs:
                            doc_sample = d.to_dict()
                            break
                        if doc_sample:
                            break
                    if doc_sample:
                        tipo = doc_sample.get('tipo', clasificar_tipo(info["nombre"]))
                        grado = doc_sample.get('grado', 'C')
                        stock_min = doc_sample.get('stock_minimo', 0)
                        stock_max = doc_sample.get('stock_maximo', 0)
                    else:
                        tipo = clasificar_tipo(info["nombre"])
                        grado = 'C'
                        stock_min = 0
                        stock_max = 0
                    stock_actual = info["stock"]
                    dentro_rango = (stock_min <= stock_actual <= stock_max) if stock_max > 0 else False
                    registros.append({
                        "Código": cod,
                        "Nombre": info["nombre"],
                        "Tipo": tipo,
                        "Grado": grado,
                        "Stock actual": stock_actual,
                        "Stock mínimo": round(stock_min, 2),
                        "Stock máximo": round(stock_max, 2),
                        "¿Stock OK?": "✅" if dentro_rango else "❌"
                    })
                
                df_kpi = pd.DataFrame(registros)
                total_items = len(df_kpi)
                ok_items = (df_kpi["¿Stock OK?"] == "✅").sum()
                stock_rate = (ok_items / total_items * 100) if total_items > 0 else 0
                
                st.metric("📦 TASA DE STOCK (Spare part stock rate)", f"{stock_rate:.1f}%", delta=f"{ok_items} de {total_items} materiales cumplen")
                
                # Ranking según tabla estándar
                if stock_rate >= 100:
                    rank = "S (110%)"
                elif stock_rate >= 75:
                    rank = "A (100%)"
                elif stock_rate >= 60:
                    rank = "B (90%)"
                elif stock_rate >= 40:
                    rank = "C (80%)"
                else:
                    rank = "D (70%)"
                st.info(f"🏆 Ranking según estándar: **{rank}**")
                
                # Gráfica de cumplimiento por categoría
                st.subheader("📊 Cumplimiento por categoría")
                cumplimiento_por_tipo = df_kpi.groupby("Tipo").apply(
                    lambda x: (x["¿Stock OK?"] == "✅").sum() / len(x) * 100
                ).sort_values(ascending=False)
                st.bar_chart(cumplimiento_por_tipo)
                
                # Tabla detallada
                with st.expander("📋 Ver detalles de todos los materiales"):
                    st.dataframe(df_kpi, use_container_width=True)
                
                # Materiales con stock bajo
                st.subheader("⚠️ Materiales con stock bajo (actual < mínimo)")
                bajos = df_kpi[df_kpi["Stock actual"] < df_kpi["Stock mínimo"]]
                if not bajos.empty:
                    st.dataframe(bajos[["Código", "Nombre", "Stock actual", "Stock mínimo"]])
                else:
                    st.success("✅ No hay materiales por debajo del stock mínimo.")
                
                # Exportar a Excel
                if st.button("📥 Exportar reporte KPI a Excel"):
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_kpi.to_excel(writer, sheet_name="KPIs", index=False)
                        resumen = pd.DataFrame({
                            "Métrica": ["Tasa de stock", "Ranking obtenido", "Total materiales", "Materiales OK"],
                            "Valor": [f"{stock_rate:.1f}%", rank, total_items, ok_items]
                        })
                        resumen.to_excel(writer, sheet_name="Resumen", index=False)
                        # Si hay histórico, agregar también
                        hist = pd.DataFrame([d.to_dict() for d in db.collection("historial_kpi").stream()])
                        if not hist.empty:
                            hist.to_excel(writer, sheet_name="Historial mensual", index=False)
                    output.seek(0)
                    st.download_button("Descargar Excel", output, "Reporte_KPI_completo.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                
                # Gráfica anual (si existe historial)
                st.subheader("📈 Evolución mensual del KPI (PLAN vs ACTUAL)")
                hist_docs = list(db.collection("historial_kpi").order_by("mes").stream())
                if hist_docs:
                    hist_data = []
                    for doc in hist_docs:
                        data = doc.to_dict()
                        hist_data.append({"mes": data.get("mes"), "stock_rate": data.get("stock_rate", 0)})
                    df_hist = pd.DataFrame(hist_data)
                    # Simulamos un PLAN (podría ser constante o variable según mes)
                    df_hist["PLAN"] = 75  # Meta del 75% (ajustable)
                    st.line_chart(df_hist.set_index("mes")[["stock_rate", "PLAN"]])
                else:
                    st.info("Aún no hay historial mensual. Registra el KPI cada mes usando el botón 'REGISTRAR KPI DEL MES ACTUAL'.")
    
    # Parte común para usuarios no YAKO (solo pestañas de Excel y carga)
    if not es_yako:
        with t2:
            ce = st.selectbox("REPORTE / 보고서", ["materiales", "holders"])
            if st.button("📥 GENERAR EXCEL / 엑셀 생성"):
                data = [d.to_dict() for d in db.collection(ce).order_by("fecha").stream()]
                if data:
                    df = pd.DataFrame(data)
                    for col in ['fecha', 'item', 'nombre', 'cantidad', 'ubicacion', 'solicitante', 'linea_uso', 'evidencia_url', 'registrado_por']:
                        if col not in df.columns: df[col] = ''
                    df = df.rename(columns={'fecha':'FECHA / 날짜','item':'ID','nombre':'NOMBRE / 이름','cantidad':'CANTIDAD / 수량','ubicacion':'UBICACIÓN / 위치','solicitante':'SOLICITANTE / 신청자','linea_uso':'LÍNEA_USO / 사용 라인','evidencia_url':'EVIDENCIA / 증거','registrado_por':'USUARIO / 사용자'})
                    cols_export = [c for c in ['FECHA / 날짜','ID','NOMBRE / 이름','CANTIDAD / 수량','UBICACIÓN / 위치','SOLICITANTE / 신청자','LÍNEA_USO / 사용 라인','EVIDENCIA / 증거','USUARIO / 사용자'] if c in df.columns]
                    csv = df[cols_export].to_csv(index=False).encode('utf-8-sig')
                    st.download_button("Descargar / 다운로드", csv, f"Reporte_{ce}.csv", "text/csv")
        with t3:
            dest = st.selectbox("DESTINO / 목적지", ["materiales", "holders"])
            arch = st.file_uploader("Subir .xlsx / .xlsx 업로드", type=['xlsx'])
            if arch and st.button("🚀 INICIAR CARGA / 로드 시작"):
                try:
                    df_in = pd.read_excel(arch, engine='openpyxl').fillna('')
                    def limpiar_columna(col):
                        c = str(col).split('/')[0].strip().upper()
                        c = ''.join(char for char in unicodedata.normalize('NFKD', c) if unicodedata.category(char) != 'Mn')
                        return c
                    df_in.columns = [limpiar_columna(c) for c in df_in.columns]
                    if df_in.empty:
                        st.error("⚠️ El archivo Excel está vacío.")
                    else:
                        total_filas = len(df_in)
                        barra = st.progress(0)
                        for i, (_, f) in enumerate(df_in.iterrows()):
                            item_id = str(f.get('ID', '')).strip()
                            if not item_id: continue
                            raw_cant = str(f.get('CANTIDAD', '0')).strip()
                            if '.' in raw_cant: raw_cant = raw_cant.split('.')[0]
                            cant_limpia = re.sub(r'\D', '', raw_cant) 
                            cantidad_final = int(cant_limpia) if cant_limpia else 0
                            db.collection(dest).add({
                                "nombre": str(f.get('NOMBRE','')).upper(),
                                "item": item_id.upper(),
                                "cantidad": cantidad_final,
                                "ubicacion": str(f.get('UBICACION','ALM')).upper(),
                                "foto_url": str(f.get('FOTO','NO FOTO')),
                                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "registrado_por": st.session_state.user if st.session_state.user else "ADMIN"
                            })
                            barra.progress((i+1)/total_filas)
                        barra.empty()
                        obtener_inventario.clear() 
                        st.success("✅ CARGA MASIVA COMPLETADA AL 100%")
                except Exception as e:
                    st.error(f"⚠️ Error al procesar el Excel: {e}")

    st.markdown("<br><br>", unsafe_allow_html=True)
    col_v, _ = st.columns([0.4, 0.6])
    with col_v:
        if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): 
            st.session_state.page = 'menu'
            st.rerun()

# ================= NAVEGACIÓN PRINCIPAL =================
if st.session_state.page == 'login': login()
elif st.session_state.page == 'cambiar_datos': cambiar_datos()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'admin': admin()
