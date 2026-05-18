import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage 
import pandas as pd
from datetime import datetime
import os
import random
import re
import urllib.parse
import io
import unicodedata 
import time
import cv2
import numpy as np
from PIL import Image
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr

# --- CONFIGURACIÓN DE PÁGINA / 페이지 설정 ---
st.set_page_config(page_title="YAKO PRO WEB", page_icon="📦", layout="wide")

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

# --- OPTIMIZACIÓN: CACHÉ DE INVENTARIO ---
@st.cache_data(ttl=60, show_spinner=False)
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

# --- UTILIDADES TÉCNICAS / 기술 유틸리티 ---
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

# --- FUNCIÓN PARA NORMALIZAR TEXTO Y BUSCAR COINCIDENCIAS ---
def normalizar_texto(texto):
    if not texto:
        return ""
    texto = str(texto).upper().strip()
    for simbolo in ['/', '|', '-', '_', '.', ',', ';', ':', '#', '$', '%', '&', '*', '(', ')', '[', ']', '{', '}', '\\', '=', '+']:
        texto = texto.replace(simbolo, ' ')
    texto = ' '.join(texto.split())
    return texto

def buscar_coincidencia_por_qr(texto_qr, inventario_total):
    if not texto_qr:
        return None
    
    texto_normalizado_qr = normalizar_texto(texto_qr)
    
    for item in inventario_total:
        nombre = str(item.get('nombre', '')).upper()
        item_id = str(item.get('item', '')).upper()
        
        if texto_qr == nombre or texto_qr == item_id:
            return item
        
        nombre_normalizado = normalizar_texto(nombre)
        id_normalizado = normalizar_texto(item_id)
        
        if texto_normalizado_qr == nombre_normalizado or texto_normalizado_qr == id_normalizado:
            return item
        
        if texto_qr in item_id or item_id in texto_qr:
            return item
        if texto_qr in nombre or nombre in texto_qr:
            return item
    
    return None

def ir(acc, cat):
    st.session_state.accion = acc
    st.session_state.categoria = cat
    st.session_state.page = 'form'
    st.session_state.pop('busqueda_input', None)
    st.rerun()

# --- FUNCIÓN GENERAR PDF ETIQUETAS ---
def generar_pdf_etiquetas(nombres, ids):
    from reportlab.platypus import Flowable
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF
    from reportlab.graphics.barcode import qr
    
    class QRCodeImage(Flowable):
        def __init__(self, data, size=60):
            Flowable.__init__(self)
            self.data = data
            self.size = size

        def draw(self):
            qr_code = qr.QrCodeWidget(self.data)
            bounds = qr_code.getBounds()
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
           
            drawing = Drawing(self.size, self.size)
            drawing.add(qr_code)
            scale = self.size / width
            drawing.scale(scale, scale)
           
            self.canv.saveState()
            X = -5
            Y = -50
            self.canv.translate(X, Y)
            renderPDF.draw(drawing, self.canv, 0, 0)
            self.canv.restoreState()
    
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    story = []
    
    estilo_texto = getSampleStyleSheet()['Normal']
    estilo_texto.alignment = 1
    estilo_texto.fontName = 'Helvetica-Bold'
    estilo_texto.fontSize = 11
    estilo_texto.leading = 12  

    for nombre, id_val in zip(nombres, ids):
        TAMANO_QR = 100
        codigo_qr = QRCodeImage(f"{nombre}|{id_val}", size=TAMANO_QR)
        
        nombre_para = Paragraph(nombre.upper(), estilo_texto)
        
        data_table = [
            [codigo_qr, "STOCK"],
            ["", nombre_para],
            [f"ID: {id_val}", ""]
        ]
        
        col_widths = [1.4 * inch, 3.0 * inch]
        row_heights = [0.3 * inch, 1.1 * inch, 0.4 * inch]
       
        t = Table(data_table, colWidths=col_widths, rowHeights=row_heights)
        
        t.setStyle(TableStyle([
            ('SPAN', (0, 0), (0, 1)),
            ('SPAN', (0, 2), (1, 2)),
            ('ALIGN', (0, 0), (0, 1), 'LEFT'),
            ('VALIGN', (0, 0), (0, 1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),
            ('ALIGN', (1, 1), (1, 1), 'CENTER'),
            ('VALIGN', (1, 1), (1, 1), 'MIDDLE'),
            ('LEFTPADDING', (1, 1), (1, 1), 8),
            ('RIGHTPADDING', (1, 1), (1, 1), 8),
            ('ALIGN', (0, 2), (1, 2), 'CENTER'),
            ('VALIGN', (0, 2), (1, 2), 'MIDDLE'),
            ('FONTSIZE', (0, 2), (1, 2), 16),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (1, 0), (1, 0), colors.darkslategray),
            ('TEXTCOLOR', (1, 0), (1, 0), colors.white),
            ('BACKGROUND', (0, 2), (1, 2), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        story.append(t)
        story.append(Spacer(1, 0.25 * inch))
    
    doc.build(story)
    output.seek(0)
    return output

# --- FUNCIONES PARA ACTUALIZAR (SOLO YAKO) ---
def actualizar_ubicacion(item_id, categoria, nueva_ubicacion):
    try:
        docs = db.collection(categoria).where("item", "==", item_id).stream()
        count = 0
        for doc in docs:
            db.collection(categoria).document(doc.id).update({"ubicacion": nueva_ubicacion.upper()})
            count += 1
        if count > 0:
            st.cache_data.clear()
        return count > 0
    except Exception as e:
        st.error(f"Error al actualizar ubicación: {e}")
        return False

def actualizar_stock_directo(item_id, categoria, nuevo_stock):
    try:
        docs = db.collection(categoria).where("item", "==", item_id).stream()
        count = 0
        for doc in docs:
            db.collection(categoria).document(doc.id).update({"cantidad": nuevo_stock})
            count += 1
        if count > 0:
            st.cache_data.clear()
        return count > 0
    except Exception as e:
        st.error(f"Error al actualizar stock: {e}")
        return False

def actualizar_posicion_y_tamanio(item_id, categoria, pos_x, pos_y, tamanio):
    try:
        docs = db.collection(categoria).where("item", "==", item_id).stream()
        count = 0
        for doc in docs:
            db.collection(categoria).document(doc.id).update({
                "pos_x": pos_x, 
                "pos_y": pos_y,
                "tamanio": tamanio
            })
            count += 1
        if count > 0:
            st.cache_data.clear()
        return count > 0
    except Exception as e:
        st.error(f"Error al actualizar posición/tamaño: {e}")
        return False

# --- OBTENER UBICACIÓN DE UN ITEM ---
def obtener_ubicacion_item(item_id, categoria):
    try:
        docs = db.collection(categoria).where("item", "==", item_id).stream()
        for doc in docs:
            return doc.to_dict().get('ubicacion', 'SIN UBICACION')
        return "SIN UBICACION"
    except Exception as e:
        return "SIN UBICACION"

# --- MOTOR DE ESCANEO DE QR (SOLO OPENCV) ---
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

# --- ESTILOS VISUALES ---
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
if 'busqueda_input' not in st.session_state: st.session_state.busqueda_input = "" 

# ================= VISTAS =================

def login():
    st.markdown("<h1>LOGIN / 로그인</h1>", unsafe_allow_html=True)
    st.markdown("<h3>ALMACÉN / 창고 🔗</h3>", unsafe_allow_html=True)
    
    u_in = st.text_input("USUARIO / 사용자").upper().strip()
    p_in = st.text_input("CLAVE / 비밀번호", type="password").strip()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("ENTRAR / 입장"):
            try:
                doc = db.collection("USUARIOS").document(u_in).get()
                if doc.exists and str(doc.to_dict().get('clave')) == p_in:
                    st.session_state.user = u_in
                    if doc.to_dict().get('estado') == "NUEVO":
                        st.session_state.page = 'cambiar_datos'
                    else:
                        st.session_state.page = 'menu'
                    st.rerun()
                else:
                    st.error("Error de credenciales / 자격 증명 오류")
            except Exception as e:
                st.error(f"Error de conexión: {e}")
    with col2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USER{random.randint(10,99)}", f"{random.randint(100,999)}"
            try:
                db.collection("USUARIOS").document(u).set({"clave": p, "estado": "NUEVO"})
                st.success(f"User temporal / 임시 사용자: {u} | Pass / 비밀번호: {p}")
            except Exception as e:
                st.error(f"Error al registrar: {e}")
            
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
        st.session_state.page = 'buscar'
        st.rerun()
    
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
                    try:
                        doc_check = db.collection("USUARIOS").document(nuevo_u).get()
                        if doc_check.exists:
                            st.error("⚠️ El usuario ya existe. Elige otro. / 사용자 이름이 이미 존재합니다. 다른 이름을 선택하세요.")
                            return
                    except Exception as e:
                        st.error(f"Error: {e}")
                        return
                
                try:
                    db.collection("USUARIOS").document(nuevo_u).set({
                        "clave": nueva_p, 
                        "estado": "ACTIVO"
                    })
                    if nuevo_u != st.session_state.user:
                        db.collection("USUARIOS").document(st.session_state.user).delete()
                        
                    st.session_state.user = nuevo_u
                    st.session_state.page = 'menu'
                    st.success("✅ Datos actualizados! / 데이터 업데이트 완료!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.error("⚠️ Completa ambos campos. / 두 필드를 모두 입력하세요.")

def menu():
    st.markdown("<h1>ALMACÉN / 창고</h1>", unsafe_allow_html=True)
    usuario_actual = st.session_state.user if st.session_state.user else "INVITADO"
    st.info(f"HOLA / 안녕하세요: {usuario_actual}")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<h3>MATERIALES / 자재</h3>", unsafe_allow_html=True)
        if st.button("ENTRADA MAT / 자재 입고"):
            ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT / 자재 출고"):
            ir("SALIDA", "materiales")
    with c2:
        st.markdown("<h3>HOLDERS / 홀더</h3>", unsafe_allow_html=True)
        if st.button("ENTRADA HOL / 홀더 입고"):
            ir("ENTRADA", "holders")
        if st.button("SALIDA HOL / 홀더 출고"):
            ir("SALIDA", "holders")
    
    st.divider()
    
    col_btn, _ = st.columns([0.4, 0.6])
    with col_btn:
        if st.button("BUSCAR / 검색"):
            st.session_state.page = 'buscar'
            st.rerun()
        if st.button("PANEL CONTROL / 제어판"):
            st.session_state.page = 'admin'
            st.rerun()
        if st.button("SALIR / 로그아웃"):
            st.session_state.user = None
            st.session_state.page = 'login'
            st.rerun()

# ================= FUNCIÓN BUSCAR CORREGIDA =================
def buscar():
    st.header("BUSCAR MATERIAL / 재료 검색")
    
    # --- LECTOR QR PARA BUSCAR ---
    with st.expander("📷 ESCANEAR QR PARA BUSCAR / 검색용 QR 스캔"):
        cam_qr = st.camera_input("SCAN QR / QR 스캔", key="qr_cam_buscar")
        if cam_qr:
            with st.spinner("📷 Escaneando QR... / QR 스캔 중..."):
                time.sleep(0.3)
                texto_qr = decodificar_qr(cam_qr)
                if texto_qr:
                    st.success(f"✅ QR detectado: {texto_qr} / QR 감지됨")
                    # Guardar directamente en el campo de búsqueda
                    st.session_state["busqueda_input_buscar"] = texto_qr
                    st.rerun()
                else:
                    st.error("⚠️ No se detectó un QR claro. / 명확한 QR이 감지되지 않았습니다.")
    
    busqueda = st.text_input("ESCRIBE ID o NOMBRE / 코드 또는 이름 입력", key="busqueda_input_buscar").upper().strip()
    
    item_seleccionado = None
    stock_total = 0
    foto_url = None
    nombre_item = ""
    id_f = ""
    col_f = ""
    rack_highlight = None
    ubicacion_raw = ""
    pos_x = 50
    pos_y = 50
    tamanio_img = 100
    
    if busqueda:
        with st.spinner("🔍 Buscando en la base de datos... / 데이터베이스 검색 중..."):
            time.sleep(0.3)
            inventario_total = obtener_inventario()
            # Buscar coincidencias exactas
            coincidencias = []
            for item in inventario_total:
                nombre = str(item.get('nombre', '')).upper()
                item_id = str(item.get('item', '')).upper()
                if busqueda == nombre or busqueda == item_id:
                    coincidencias = [item]
                    break
                elif busqueda in nombre or busqueda in item_id:
                    coincidencias.append(item)
            
            if coincidencias:
                if len(coincidencias) > 1:
                    st.info(f"⚠️ HAY {len(coincidencias)} COINCIDENCIAS. / {len(coincidencias)}개의 일치 항목이 있습니다.")
                    
                if len(coincidencias) > 1:
                    opciones = list(set([c['label'] for c in coincidencias])) 
                    seleccion = st.selectbox("RESULTADOS / 검색 결과:", opciones)
                    item_seleccionado = next(c for c in coincidencias if c['label'] == seleccion)
                else:
                    item_seleccionado = coincidencias[0]
                
                id_f = item_seleccionado.get('item')
                col_f = item_seleccionado['cat_db']
                nombre_item = item_seleccionado.get('nombre', '')
                ubicacion_raw = item_seleccionado.get('ubicacion', '')
                pos_x = item_seleccionado.get('pos_x', 50)
                pos_y = item_seleccionado.get('pos_y', 50)
                tamanio_img = item_seleccionado.get('tamanio', 100)
                
                if col_f == "holders":
                    rack_match = re.match(r'([A-Z]+\d*)', ubicacion_raw.upper())
                    rack_highlight = rack_match.group(1) if rack_match else None
                
                stock_total = 0
                for item in inventario_total:
                    if item.get('item') == id_f and item.get('cat_db') == col_f:
                        stock_total += item.get('cantidad', 0)
                
                foto_url = obtener_url_final(item_seleccionado.get('foto_url', ''))
                st.balloons()
            else:
                st.warning(f"No se encontraron resultados para: {busqueda} / 결과 없음")
    
    # --- MAPA DE RACKS SOLO PARA HOLDERS ---
    if item_seleccionado and col_f == "holders":
        st.subheader("🗺️ MAPA DE RACKS / 랙 지도")
        
        def rack_color(name):
            return "#8FC360" if (rack_highlight and name == rack_highlight) else "#8B0000"
        
        map_html = f'''
        <div style="position: relative; width: 530px; height: 550px; margin: 0 auto; background-color: black; border: 2px solid #333; border-radius: 10px;">
            <div style="position: absolute; left: 110px; top: 20px; width: 120px; height: 50px; background-color: {rack_color("G1")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg);">G1</span></div>
            <div style="position: absolute; left: 230px; top: 20px; width: 120px; height: 50px; background-color: {rack_color("G2")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg);">G2</span></div>
            <div style="position: absolute; left: 350px; top: 20px; width: 120px; height: 50px; background-color: {rack_color("G3")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg);">G3</span></div>
            <div style="position: absolute; left: 40px; top: 20px; width: 60px; height: 100px; background-color: {rack_color("H2")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px;">H2</span></div>
            <div style="position: absolute; left: 40px; top: 120px; width: 60px; height: 100px; background-color: {rack_color("H1")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px;">H1</span></div>
            <div style="position: absolute; left: 110px; top: 100px; width: 120px; height: 50px; background-color: {rack_color("I1")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg);">I1</span></div>
            <div style="position: absolute; left: 230px; top: 100px; width: 120px; height: 50px; background-color: {rack_color("I2")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg);">I2</span></div>
            <div style="position: absolute; left: 110px; top: 160px; width: 120px; height: 50px; background-color: {rack_color("K1")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg);">K1</span></div>
            <div style="position: absolute; left: 230px; top: 160px; width: 120px; height: 50px; background-color: {rack_color("K2")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px; transform: rotate(90deg);">K2</span></div>
            <div style="position: absolute; left: 410px; top: 85px; width: 60px; height: 70px; background-color: {rack_color("F1")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px;">F1</span></div>
            <div style="position: absolute; left: 410px; top: 155px; width: 60px; height: 70px; background-color: {rack_color("F2")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px;">F2</span></div>
            <div style="position: absolute; left: 410px; top: 225px; width: 60px; height: 70px; background-color: {rack_color("F3")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px;">F3</span></div>
            <div style="position: absolute; left: 410px; top: 295px; width: 60px; height: 70px; background-color: {rack_color("F4")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px;">F4</span></div>
            <div style="position: absolute; left: 410px; top: 365px; width: 60px; height: 70px; background-color: {rack_color("F5")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px;">F5</span></div>
            <div style="position: absolute; left: 410px; top: 435px; width: 60px; height: 70px; background-color: {rack_color("F6")}; border: 2px solid white; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><span style="color: white; font-weight: bold; font-size: 18px;">F6</span></div>
        </div>
        '''
        st.markdown(map_html, unsafe_allow_html=True)
    
    if item_seleccionado:
        st.markdown(f"<h2 style='text-align:center;'>{nombre_item}</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        col1.metric("STOCK ACTUAL / 재고", max(0, stock_total))
        col2.metric("UBICACIÓN / 위치", ubicacion_raw if ubicacion_raw else "---")
        
        if st.session_state.user == "YAKO":
            st.markdown("---")
            st.markdown("<h4 style='text-align: center; color: #FFD700;'>🔧 ADMINISTRACIÓN RÁPIDA (SOLO YAKO) / 빠른 관리 (YAKO만 가능)</h4>", unsafe_allow_html=True)
            
            col_ubi1, col_ubi2, col_ubi3 = st.columns([0.5, 0.25, 0.25])
            with col_ubi1:
                nueva_ubicacion = st.text_input("📍 NUEVA UBICACIÓN / 새 위치", value=ubicacion_raw if ubicacion_raw else "", key="nueva_ubicacion_input")
            with col_ubi2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔄 ACTUALIZAR UBICACIÓN / 위치 업데이트", key="btn_actualizar_ubicacion"):
                    if nueva_ubicacion and nueva_ubicacion != ubicacion_raw:
                        with st.spinner("Actualizando ubicación... / 위치 업데이트 중..."):
                            time.sleep(0.5)
                            if actualizar_ubicacion(id_f, col_f, nueva_ubicacion):
                                st.success(f"✅ Ubicación actualizada: {ubicacion_raw} → {nueva_ubicacion.upper()}")
                                st.balloons()
                                time.sleep(0.8)
                                st.rerun()
                    elif not nueva_ubicacion:
                        st.warning("⚠️ Ingrese una nueva ubicación / 새 위치를 입력하세요.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_stock1, col_stock2, col_stock3 = st.columns([0.5, 0.25, 0.25])
            with col_stock1:
                nuevo_stock_valor = st.number_input("📦 NUEVO STOCK / 새 재고량", min_value=0, value=int(stock_total), key="nuevo_stock_input")
            with col_stock2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 ACTUALIZAR STOCK / 재고 업데이트", key="btn_actualizar_stock"):
                    if nuevo_stock_valor != stock_total:
                        with st.spinner("Actualizando stock... / 재고 업데이트 중..."):
                            time.sleep(0.5)
                            if actualizar_stock_directo(id_f, col_f, nuevo_stock_valor):
                                st.success(f"✅ Stock actualizado: {stock_total} → {nuevo_stock_valor}")
                                st.balloons()
                                time.sleep(0.8)
                                st.rerun()
                    else:
                        st.info("El stock no ha cambiado / 재고가 변경되지 않았습니다.")
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<h5 style='color: #00FF00;'>🖼️ AJUSTAR IMAGEN / 이미지 조정</h5>", unsafe_allow_html=True)
            
            col_x1, col_y1, col_size1 = st.columns(3)
            with col_x1:
                nueva_pos_x = st.slider("📍 POSICIÓN X (%)", min_value=0, max_value=100, value=int(pos_x), key="pos_x_slider")
                st.caption("0% = izquierda, 50% = centro, 100% = derecha")
            with col_y1:
                nueva_pos_y = st.slider("📍 POSICIÓN Y (%)", min_value=0, max_value=100, value=int(pos_y), key="pos_y_slider")
                st.caption("0% = arriba, 50% = centro, 100% = abajo")
            with col_size1:
                nuevo_tamanio = st.slider("📏 TAMAÑO DE IMAGEN (%)", min_value=20, max_value=100, value=int(tamanio_img), key="tamanio_slider")
                st.caption(f"{nuevo_tamanio}% del tamaño original")
            
            col_btn1, col_btn2, col_btn3 = st.columns([0.35, 0.3, 0.35])
            with col_btn2:
                if st.button("🎯 GUARDAR CONFIGURACIÓN DE IMAGEN / 이미지 설정 저장", key="btn_guardar_posicion"):
                    if (nueva_pos_x != pos_x or nueva_pos_y != pos_y or nuevo_tamanio != tamanio_img):
                        with st.spinner("Guardando configuración de imagen... / 이미지 설정 저장 중..."):
                            if actualizar_posicion_y_tamanio(id_f, col_f, nueva_pos_x, nueva_pos_y, nuevo_tamanio):
                                st.success(f"✅ Configuración guardada: X={nueva_pos_x}%, Y={nueva_pos_y}%, Tamaño={nuevo_tamanio}%")
                                st.balloons()
                                time.sleep(0.8)
                                st.rerun()
                    else:
                        st.info("La configuración no ha cambiado / 설정이 변경되지 않았습니다.")
        
        if stock_total <= 5 and stock_total > 0:
            st.warning(f"⚠️ STOCK BAJO: Quedan {stock_total} unidades / 재고 부족: {stock_total}개 남음")
        elif stock_total <= 0:
            st.error(f"❌ STOCK AGOTADO: {stock_total} unidades / 재고 없음: {stock_total}개")
        
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
            ancho_max = int(280 * (tamanio_img / 100))
            alto_max = int(240 * (tamanio_img / 100))
            
            st.markdown(f'''
            <div style="position: relative; width: 400px; height: 300px; margin: 0 auto; border: 1px dashed #444; border-radius: 10px; background-color: #0a0a0a;">
                <div style="position: absolute; left: {pos_x}%; top: {pos_y}%; transform: translate(-50%, -50%);">
                    <img src="{foto_url}" style="max-width: {ancho_max}px; max-height: {alto_max}px; border-radius: 15px; border: 3px solid red; box-shadow: 0px 4px 15px rgba(255, 0, 0, 0.5);">
                </div>
                <div style="position: absolute; bottom: 5px; right: 10px; font-size: 10px; color: #666;">
                    X:{pos_x}% Y:{pos_y}% | Tamaño: {tamanio_img}%
                </div>
            </div>
            ''', unsafe_allow_html=True)
            st.caption("🖱️ Las coordenadas X e Y definen la posición de la imagen dentro del recuadro gris. El tamaño es ajustable por YAKO.")
        else:
            st.markdown(f'''
            <div style="position: relative; width: 400px; height: 300px; margin: 0 auto; border: 1px dashed #444; border-radius: 10px; background-color: #0a0a0a; display: flex; align-items: center; justify-content: center;">
                <span style="color: gray; text-align: center;">Sin foto / 사진 없음<br><span style="font-size: 12px;">Sube una imagen usando el enlace abajo</span></span>
            </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.user == "YAKO":
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<h4 style='text-align: center; color: yellow;'>📸 AGREGAR / ACTUALIZAR FOTO (SOLO YAKO)</h4>", unsafe_allow_html=True)
            col_f1, col_f2 = st.columns([0.7, 0.3])
            with col_f1:
                nueva_foto_url = st.text_input("PEGA EL ENLACE AQUÍ (Drive, web, etc.) / 사진 링크", key=f"foto_input_{id_f}")
                st.caption("Ejemplo: https://ejemplo.com/mi-foto.jpg")
            with col_f2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 GUARDAR FOTO / 사진 저장", key=f"btn_foto_{id_f}"):
                    if nueva_foto_url:
                        with st.spinner("Guardando en la base de datos... / 저장 중..."):
                            docs_update = db.collection(col_f).where("item", "==", id_f).stream()
                            for doc in docs_update:
                                db.collection(col_f).document(doc.id).update({"foto_url": nueva_foto_url})
                            st.cache_data.clear()
                            st.success("✅ FOTO ACTUALIZADA PARA TODOS / 사진 업데이트 완료")
                            st.rerun()
                    else:
                        st.warning("⚠️ Pegue un enlace antes de guardar. / 링크를 붙여넣으세요.")
    
    st.markdown("<br>", unsafe_allow_html=True)
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
    
    # --- ESCANEO QR CON BÚSQUEDA INTELIGENTE ---
    with st.expander("📷 CÁMARA QR / QR 카메라 - Escanea cualquier QR / 모든 QR 스캔"):
        cam = st.camera_input("SCAN / 스캔", key="qr_cam_input")
        if cam:
            with st.spinner("📷 Escaneando QR... / QR 스캔 중..."):
                time.sleep(0.3)
                res = decodificar_qr(cam)
                if res:
                    st.success(f"✅ QR detectado: {res} / QR 감지됨")
                    st.session_state["busqueda_input"] = res
                    st.rerun()
                else:
                    st.error("⚠️ No se detectó un QR claro. / 명확한 QR이 감지되지 않았습니다.")
    
    busqueda_form = st.text_input("BUSCAR ID O NOMBRE / 코드 또는 이름 검색", key="busqueda_input").upper().strip()
    
    cod_final = ""
    nombre_final = ""
    es_nuevo = False
    ubicacion_item = "SIN UBICACION"
    
    if busqueda_form:
        with st.spinner("🔍 Buscando en inventario... / 재고 검색 중..."):
            time.sleep(0.3)
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
                        ubicacion_item = obtener_ubicacion_item(cod_final, cat)
                        st.success(f"✅ Seleccionado: {coincidencias[0]['label']}")
                    else:
                        opciones = [c['label'] for c in coincidencias]
                        seleccion = st.selectbox("COINCIDENCIAS ENCONTRADAS / 일치 항목:", opciones)
                        item_sel = next(c for c in coincidencias if c['label'] == seleccion)
                        cod_final, nombre_final = item_sel['item'], item_sel.get('nombre', '')
                        ubicacion_item = obtener_ubicacion_item(cod_final, cat)
                else:
                    st.error("⚠️ MATERIAL NO ENCONTRADO.")
            else:  # ENTRADA
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
    
    if cant != cant_conf and cant_conf > 0:
        st.error("⚠️ LAS CANTIDADES NO COINCIDEN")

    foto_evidencia = None
    if acc == "SALIDA":
        solicitante = st.text_input("NOMBRE SOLICITANTE / 신청자 이름").upper().strip()
        linea_uso = st.text_input("LÍNEA EN LA QUE SE UTILIZARÁ / 사용할 라인").upper().strip()
        
        with st.expander("📸 CAPTURAR EVIDENCIA / 증거 사진"):
            foto_evidencia = st.camera_input("FOTO EVIDENCIA", key="evidencia_cam_input")
        
        ubi = ubicacion_item if ubicacion_item else "SIN UBICACION"
        bloqueado = (cant != cant_conf) or (not solicitante) or (not linea_uso) or (not cod_final)
    else:
        ubi = st.text_input("UBICACIÓN / 위치").upper().strip()
        solicitante, linea_uso = "", ""
        bloqueado = (cant != cant_conf) or (not ubi) or (not cod_final) or (es_nuevo and not nombre_final)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_v, _ = st.columns([0.4, 0.6])
    with col_v:
        if st.button("REGISTRAR / 등록", disabled=bloqueado):
            url_foto_final = "SIN EVIDENCIA"
            fecha_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            if foto_evidencia:
                with st.spinner("📤 Subiendo evidencia... / 증거 업로드 중..."):
                    nombre_archivo = f"evidencias/EVIDENCIA_{nombre_final}_{linea_uso}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg".replace(" ", "_")
                    bucket = storage.bucket()
                    blob = bucket.blob(nombre_archivo)
                    blob.upload_from_string(foto_evidencia.getvalue(), content_type='image/jpeg')
                    blob.make_public()
                    url_foto_final = blob.public_url

            with st.spinner("💾 Guardando registro... / 등록 저장 중..."):
                db.collection(cat).add({
                    "fecha": fecha_str, "item": cod_final, "nombre": nombre_final,
                    "cantidad": cant if acc == "ENTRADA" else -cant, "ubicacion": ubi, 
                    "solicitante": solicitante, "linea_uso": linea_uso,
                    "evidencia_url": url_foto_final,
                    "registrado_por": st.session_state.user if st.session_state.user else "INVITADO",
                    "pos_x": 50,
                    "pos_y": 50,
                    "tamanio": 100
                })
                st.cache_data.clear()
                st.session_state.pop('busqueda_input', None)
                st.success("✅ REGISTRADO CON ÉXITO")
                st.balloons()
                time.sleep(1)
                st.rerun() 
        
        if st.button("VOLVER / 돌아가기"): 
            st.session_state.pop('busqueda_input', None)
            st.session_state.page = 'login' if st.session_state.user == "INVITADO" else 'menu'
            st.rerun()

def admin():
    st.markdown("<h1>PANEL CONTROL / 제어판</h1>", unsafe_allow_html=True)
    
    es_yako = (st.session_state.user == "YAKO")
    
    if es_yako:
        t1, t2, t3, t4, t5, t6 = st.tabs(["BORRAR / 삭제", "EXCEL DETALLADO / 엑셀", "CARGA MASIVA / 대량 로드", "USUARIOS / 사용자", "ESCANEAR TEXTO / 텍스트 스캔", "GENERAR ETIQUETAS / 라벨 생성"])
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
                        barra_borrado = st.progress(0, text=f"🗑️ Iniciando borrado de {total_borrar} registros... / {total_borrar}개 레코드 삭제 시작...")
                        
                        for i, doc in enumerate(docs_borrar):
                            db.collection(cdb).document(doc.id).delete()
                            porcentaje_borrado = (i + 1) / total_borrar
                            barra_borrado.progress(porcentaje_borrado, text=f"⏳ Borrando {i+1} de {total_borrar} registros... ({int(porcentaje_borrado * 100)}%)")
                            
                        barra_borrado.empty()
                        st.cache_data.clear()
                        st.success(f"✅ BORRADO COMPLETADO: {total_borrar} registros eliminados. / 삭제 완료: {total_borrar}개 레코드 삭제됨.")
                        st.rerun()
                
    with t2:
        ce = st.selectbox("REPORTE / 보고서", ["materiales", "holders"])
        if st.button("📥 GENERAR EXCEL / 엑셀 생성"):
            with st.spinner("Generando reporte... / 보고서 생성 중..."):
                data = [d.to_dict() for d in db.collection(ce).order_by("fecha").stream()]
                if data:
                    for d in data:
                        d['nombre'] = d.get('nombre', 'SIN NOMBRE')
                        d['item'] = d.get('item', 'SIN ID')
                        
                    df = pd.DataFrame(data)
                    
                    for col in ['fecha', 'item', 'nombre', 'cantidad', 'ubicacion', 'solicitante', 'linea_uso', 'evidencia_url', 'registrado_por']:
                        if col not in df.columns:
                            df[col] = ''
                            
                    df = df.rename(columns={
                        'fecha': 'FECHA / 날짜',
                        'item': 'ID',
                        'nombre': 'NOMBRE / 이름',
                        'cantidad': 'CANTIDAD / 수량',
                        'ubicacion': 'UBICACIÓN / 위치',
                        'solicitante': 'SOLICITANTE / 신청자',
                        'linea_uso': 'LÍNEA_USO / 사용 라인', 
                        'evidencia_url': 'EVIDENCIA / 증거',
                        'registrado_por': 'USUARIO / 사용자'
                    })
                    cols_to_export = [c for c in ['FECHA / 날짜', 'ID', 'NOMBRE / 이름', 'CANTIDAD / 수량', 'UBICACIÓN / 위치', 'SOLICITANTE / 신청자', 'LÍNEA_USO / 사용 라인', 'EVIDENCIA / 증거', 'USUARIO / 사용자'] if c in df.columns]
                    csv = df[cols_to_export].to_csv(index=False).encode('utf-8-sig')
                    st.download_button("Descargar / 다운로드", csv, f"Reporte_{ce}.csv", "text/csv")
                
    with t3:
        dest = st.selectbox("DESTINO / 목적지", ["materiales", "holders"])
        
        if dest == "holders":
            st.markdown("""
            <div style="background-color: #1a1a1a; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                <p style="color: #FFD700; font-weight: bold;">📌 FORMATO ESPERADO PARA HOLDERS / 홀더 형식:</p>
                <p style="color: white;">• Columna <span style="color: #00FF00;">NUMERO</span> → ID del holder (ej: HD12345)</p>
                <p style="color: white;">• Columna <span style="color: #00FF00;">QTY</span> → Cantidad inicial (ej: 10, 25, 0)</p>
                <p style="color: white;">• Columna <span style="color: #00FF00;">RACK</span> → Ubicación (ej: G1, F2, H1)</p>
                <p style="color: #FF8888;">⚠️ El campo NOMBRE se copiará automáticamente desde NUMERO</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background-color: #1a1a1a; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
                <p style="color: #FFD700; font-weight: bold;">📌 FORMATO ESPERADO PARA MATERIALES / 자재 형식:</p>
                <p style="color: white;">• Columna <span style="color: #00FF00;">NOMBRE</span> → Nombre del material</p>
                <p style="color: white;">• Columna <span style="color: #00FF00;">ID</span> → Código del material</p>
                <p style="color: white;">• Columna <span style="color: #00FF00;">CANTIDAD</span> → Stock inicial (opcional)</p>
                <p style="color: white;">• Columna <span style="color: #00FF00;">UBICACION</span> → Rack o ubicación (opcional)</p>
                <p style="color: white;">• Columna <span style="color: #00FF00;">FOTO</span> → URL de imagen (opcional)</p>
            </div>
            """, unsafe_allow_html=True)
        
        arch = st.file_uploader("Subir .xlsx / .xlsx 업로드", type=['xlsx'])
        if arch:
            if st.button("🚀 INICIAR CARGA / 로드 시작"):
                try:
                    with st.spinner("Procesando archivo... / 파일 처리 중..."):
                        df_in = pd.read_excel(arch, engine='openpyxl')
                        df_in = df_in.fillna('')
                        
                        def limpiar_columna(col):
                            c = str(col).split('/')[0].strip().upper()
                            c = ''.join(char for char in unicodedata.normalize('NFKD', c) if unicodedata.category(char) != 'Mn')
                            return c
                        
                        df_in.columns = [limpiar_columna(c) for c in df_in.columns]
                        
                        st.info(f"📊 Columnas detectadas: {', '.join(df_in.columns.tolist())}")
                        
                        if dest == "holders":
                            col_numero = None
                            col_qty = None
                            col_rack = None
                            
                            for col in df_in.columns:
                                if col in ['NUMERO', 'NUM', 'ID', 'HOLDER', 'HOLDER_ID', 'CODIGO']:
                                    col_numero = col
                                if col in ['QTY', 'CANTIDAD', 'STOCK', 'CANT', 'QUANTITY']:
                                    col_qty = col
                                if col in ['RACK', 'UBICACION', 'UBICACIÓN', 'POSICION', 'LOCATION']:
                                    col_rack = col
                            
                            if col_numero is None:
                                st.error("❌ No se encontró una columna para NUMERO/ID")
                            else:
                                total_filas = len(df_in)
                                barra_progreso = st.progress(0, text=f"🚀 Iniciando carga de {total_filas} holders... / {total_filas}개 홀더 로드 시작...")
                                registros_cargados = 0
                                
                                for i, (_, f) in enumerate(df_in.iterrows()):
                                    numero = str(f.get(col_numero, '')).strip().upper()
                                    
                                    if not numero:
                                        continue
                                    
                                    cantidad = 0
                                    if col_qty:
                                        try:
                                            qty_val = str(f.get(col_qty, '0')).strip()
                                            qty_val = re.sub(r'[^\d-]', '', qty_val)
                                            cantidad = int(float(qty_val)) if qty_val else 0
                                        except:
                                            cantidad = 0
                                    
                                    ubicacion = "SIN UBICACION"
                                    if col_rack:
                                        ubicacion = str(f.get(col_rack, 'SIN UBICACION')).strip().upper()
                                        if not ubicacion:
                                            ubicacion = "SIN UBICACION"
                                    
                                    db.collection(dest).add({
                                        "nombre": numero,
                                        "item": numero,
                                        "cantidad": cantidad,
                                        "ubicacion": ubicacion,
                                        "foto_url": "NO FOTO",
                                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                        "registrado_por": st.session_state.user if st.session_state.user else "ADMIN",
                                        "pos_x": 50,
                                        "pos_y": 50,
                                        "tamanio": 100
                                    })
                                    registros_cargados += 1
                                    barra_progreso.progress((i + 1) / total_filas, text=f"⏳ Procesando {i+1} de {total_filas}... Cargados: {registros_cargados}")
                                
                                barra_progreso.empty()
                                st.cache_data.clear()
                                st.success(f"✅ CARGA COMPLETADA: {registros_cargados} holders registrados / {registros_cargados}개 홀더 등록됨")
                                if col_qty:
                                    st.info(f"📊 Cantidad (QTY) leída desde columna: {col_qty}")
                                if col_rack:
                                    st.info(f"📍 Ubicación (RACK) leída desde columna: {col_rack}")
                                st.balloons()
                        
                        else:
                            col_nombre = None
                            col_id = None
                            col_cantidad = None
                            col_ubicacion = None
                            col_foto = None
                            
                            for col in df_in.columns:
                                if col in ['NOMBRE', 'NAME', 'PRODUCTO']:
                                    col_nombre = col
                                if col in ['ID', 'CODIGO', 'CODE']:
                                    col_id = col
                                if col in ['CANTIDAD', 'STOCK', 'QTY']:
                                    col_cantidad = col
                                if col in ['UBICACION', 'UBICACIÓN', 'RACK']:
                                    col_ubicacion = col
                                if col in ['FOTO', 'URL', 'IMAGEN']:
                                    col_foto = col
                            
                            if col_nombre is None or col_id is None:
                                st.error("❌ Para MATERIALES se necesitan NOMBRE e ID")
                            else:
                                total_filas = len(df_in)
                                barra_progreso = st.progress(0, text=f"🚀 Iniciando carga de {total_filas} materiales... / {total_filas}개 자재 로드 시작...")
                                registros_cargados = 0
                                
                                for i, (_, f) in enumerate(df_in.iterrows()):
                                    nombre = str(f.get(col_nombre, '')).strip().upper()
                                    item_id = str(f.get(col_id, '')).strip().upper()
                                    
                                    if not nombre or not item_id:
                                        continue
                                    
                                    cantidad_raw = str(f.get(col_cantidad, '0')) if col_cantidad else '0'
                                    cantidad_limpia = re.sub(r'\D', '', cantidad_raw)
                                    cantidad_final = int(cantidad_limpia) if cantidad_limpia else 0
                                    
                                    ubicacion = str(f.get(col_ubicacion, 'ALM')).strip().upper() if col_ubicacion else 'ALM'
                                    foto_url = str(f.get(col_foto, 'NO FOTO')) if col_foto else 'NO FOTO'
                                    
                                    db.collection(dest).add({
                                        "nombre": nombre,
                                        "item": item_id,
                                        "cantidad": cantidad_final,
                                        "ubicacion": ubicacion,
                                        "foto_url": foto_url,
                                        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                        "registrado_por": st.session_state.user if st.session_state.user else "ADMIN",
                                        "pos_x": 50,
                                        "pos_y": 50,
                                        "tamanio": 100
                                    })
                                    registros_cargados += 1
                                    barra_progreso.progress((i + 1) / total_filas, text=f"⏳ Procesando {i+1} de {total_filas}... Cargados: {registros_cargados}")
                                
                                barra_progreso.empty()
                                st.cache_data.clear()
                                st.success(f"✅ CARGA COMPLETADA: {registros_cargados} materiales registrados / {registros_cargados}개 자재 등록됨")
                                st.balloons()
                                
                except Exception as e:
                    st.error(f"⚠️ Error: {e}")
            
    if es_yako:
        with t4:
            st.markdown("<h3>👥 USUARIOS REGISTRADOS / 등록된 사용자</h3>", unsafe_allow_html=True)
            uds = db.collection("USUARIOS").stream()
            for u in uds:
                ud = u.to_dict()
                with st.container():
                    st.markdown(f'<div class="user-card">ID: {u.id} | Clave: {ud.get("clave")} | Estado: {ud.get("estado")}</div>', unsafe_allow_html=True)
                    if u.id != "YAKO":
                        if st.button("BORRAR USUARIO / 사용자 삭제", key=f"d_{u.id}"): 
                            db.collection("USUARIOS").document(u.id).delete()
                            st.rerun()

        with t5:
            st.markdown("<h3 style='color:red;'>ESCANEAR TEXTO (OCR) / 텍스트 스캔 🔗</h3>", unsafe_allow_html=True)
            st.info("Captura una imagen para extraer su texto y descargar un Excel con la foto y el resultado. / 이미지를 캡처하여 텍스트를 추출하고 엑셀을 다운로드하세요.")
            
            cam_ocr = st.camera_input("CÁMARA OCR / OCR 카메라", key="cam_ocr")
            
            if cam_ocr:
                try:
                    import pytesseract
                    import xlsxwriter
                    
                    with st.spinner("Procesando imagen... / 이미지 처리 중..."):
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
                        
                        st.download_button(
                            label="📥 DESCARGAR EXCEL CON FOTO Y TEXTO / 엑셀 다운로드",
                            data=output,
                            file_name=f"OCR_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.warning("⚠️ No se detectó texto claro en la imagen. / 이미지에서 텍스트를 찾을 수 없습니다.")
                except Exception as e:
                    st.error(f"⚠️ Error OCR: {e}")
        
        with t6:
            st.markdown("<h3 style='color:green;'>🏷️ GENERAR ETIQUETAS QR / QR 라벨 생성</h3>", unsafe_allow_html=True)
            st.info("Genera un PDF con etiquetas QR para holders/materiales. / 홀더/자재용 QR 라벨 PDF를 생성합니다.")
            
            col_q1, col_q2 = st.columns(2)
            with col_q1:
                st.markdown("**📝 NOMBRES / 이름**")
                nombres_text = st.text_area("Escribe un nombre por línea:", height=200, key="nombres_etiquetas")
            with col_q2:
                st.markdown("**🔢 IDs / 코드**")
                ids_text = st.text_area("Escribe un ID por línea:", height=200, key="ids_etiquetas")
            
            if st.button("🎨 GENERAR PDF / PDF 생성", type="primary"):
                nombres = [n.strip().upper() for n in nombres_text.split("\n") if n.strip()]
                ids = [i.strip().upper() for i in ids_text.split("\n") if i.strip()]
                
                if not nombres or not ids:
                    st.error("❌ Debes escribir al menos un nombre y un ID")
                elif len(nombres) != len(ids):
                    st.error(f"⚠️ Los nombres y IDs no coinciden: {len(nombres)} nombres vs {len(ids)} IDs")
                else:
                    with st.spinner("Generando PDF con etiquetas... / PDF 생성 중..."):
                        try:
                            pdf_buffer = generar_pdf_etiquetas(nombres, ids)
                            st.success(f"✅ PDF generado con {len(nombres)} etiquetas / {len(nombres)}개 라벨 생성됨")
                            st.balloons()
                            st.download_button(
                                label="📥 DESCARGAR PDF / PDF 다운로드",
                                data=pdf_buffer,
                                file_name=f"etiquetas_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                mime="application/pdf"
                            )
                        except Exception as e:
                            st.error(f"❌ Error al generar PDF: {e}")
            
            st.markdown("---")
            st.markdown("""
            <div style="background-color: #1a1a1a; padding: 15px; border-radius: 10px;">
                <p style="color: #FFD700;">💡 EJEMPLO / 예시:</p>
                <p style="color: white;">Nombres:<br>HOLDER PRINCIPAL<br>HOLDER SECUNDARIO</p>
                <p style="color: white;">IDs:<br>HD001<br>HD002</p>
            </div>
            """, unsafe_allow_html=True)
                    
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_v, _ = st.columns([0.4, 0.6])
    with col_v:
        if st.button("VOLVER AL MENÚ / 메뉴로 돌아가기"): 
            st.session_state.page = 'menu'
            st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login':
    login()
elif st.session_state.page == 'cambiar_datos':
    cambiar_datos()
elif st.session_state.page == 'menu':
    menu()
elif st.session_state.page == 'buscar':
    buscar()
elif st.session_state.page == 'form':
    formulario()
elif st.session_state.page == 'admin':
    admin()
