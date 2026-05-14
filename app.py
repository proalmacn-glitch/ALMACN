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
from PIL import Image
from pyzbar.pyzbar import decode
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr

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

# --- OPTIMIZACIÓN: CACHÉ DE INVENTARIO CON TTL MÁS LARGO ---
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
    if not texto_qr or not inventario_total:
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

# --- MOTOR DE ESCANEO DE QR ---
def decodificar_qr(foto):
    try:
        foto.seek(0)
        img = Image.open(foto)
        
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        codigos = decode(img)
        if codigos:
            return codigos[0].data.decode("utf-8").upper()
        
        img_gray = img.convert('L')
        codigos = decode(img_gray)
        if codigos:
            return codigos[0].data.decode("utf-8").upper()
            
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
    
    .image-container {
        position: relative;
        width: 400px;
        height: 300px;
        margin: 0 auto;
    }
    .positioned-image {
        position: absolute;
        transform: translate(-50%, -50%);
    }
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
    
    # GIF ANIMADO - SIEMPRE APARECE PARA TODOS
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
            if inventario_total:
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
                else:
                    st.warning("No se encontraron resultados / 결과 없음")
    
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
        
        # === SOLO YAKO: MODIFICAR UBICACIÓN, STOCK Y POSICIÓN ===
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

# --- FUNCIONES formulario() y admin() - mantenlas igual que en tu código original ---
# (Por límite de caracteres, no las incluyo aquí, pero debes mantener tus funciones formulario y admin)

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
