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

# --- FUNCIÓN PARA CONVERTIR LINKS DE DRIVE / 드라이브 링크 변환 ---
def convertir_link_drive(url):
    """Convierte links de compartir de Google Drive en links de visualización directa."""
    if 'drive.google.com' in url:
        match = re.search(r'd/([^/]+)', url)
        if match:
            file_id = match.group(1)
            return f'https://drive.google.com/uc?export=view&id={file_id}'
    return url

# --- ESTILOS VISUALES / 시각적 스타일 (CENTRADOS) ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    .stButton>button { background-color: white; color: black; border-radius: 5px; width: 100%; font-weight: bold; border: 2px solid red; }
    
    /* Etiquetas amarillas */
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label { 
        color: yellow !important; font-size: 16px !important; 
    }

    /* Métricas: Cian Mate sin brillo excesivo */
    div[data-testid="stMetricValue"] { 
        font-size: 45px !important; color: #00cccc !important; text-align: center !important; 
    }
    div[data-testid="stMetricLabel"] { 
        font-size: 18px !important; color: white !important; text-align: center !important; 
    }
    div[data-testid="stMetric"] { 
        background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; 
    }
    
    /* CENTRADO DE QR E IMÁGENES */
    .center-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        width: 100%;
    }
    
    .qr-card {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        display: inline-block;
        margin-bottom: 20px;
    }

    /* Forzar centrado de componentes nativos de Streamlit */
    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'page' not in st.session_state: st.session_state.user = None; st.session_state.page = 'login'

# ================= VISTA: BUSCAR / 검색 (HÍBRIDA + LISTA) =================

def buscar():
    st.header("BUSCAR / 검색")
    query = st.text_input("NOMBRE o ID / 이름 또는 ID").upper().strip()

    if query:
        resultados = []
        for col in ["materiales", "holders"]:
            docs = db.collection(col).stream()
            for d in docs:
                data = d.to_dict()
                if query in str(data.get('nombre', '')).upper() or query == str(data.get('item', '')).upper():
                    data['categoria_db'] = col
                    resultados.append(data)
        
        item_elegido = None
        if len(resultados) > 1:
            st.warning(f"RESULTADOS ENCONTRADOS / 검색 결과: {len(resultados)}")
            opciones = {f"{r.get('nombre')} [{r.get('item')}]": r for r in resultados}
            seleccion = st.selectbox("SELECCIONA / 선택하세요:", list(opciones.keys()))
            item_elegido = opciones[seleccion]
        elif len(resultados) == 1:
            item_elegido = resultados[0]
        else:
            st.error("SIN RESULTADOS / 결과 없음")

        if item_elegido:
            id_f = item_elegido.get('item', '---')
            nombre_f = item_elegido.get('nombre', '---')
            col_f = item_elegido['categoria_db']
            
            # Stock acumulado
            docs_stock = db.collection(col_f).where("item", "==", id_f).stream()
            total_stock = sum([doc.to_dict().get('cantidad', 0) for doc in docs_stock])
            ubi_f = item_elegido.get('ubicacion', '---')

            st.markdown(f"<h2>{nombre_f}</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center;'>ID: {id_f}</p>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            c1.metric("STOCK TOTAL / 총 재고", total_stock)
            c2.metric("UBICACIÓN / 위치", ubi_f)

            st.divider()

            # --- SECCIÓN CENTRADA ---
            st.markdown('<div class="center-container">', unsafe_allow_html=True)
            
            # Código QR
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}"
            st.markdown(f'''
                <div class="qr-card">
                    <img src="{qr_url}"><br>
                    <b style="color: black;">CÓDIGO QR / QR 코드</b>
                </div>
            ''', unsafe_allow_html=True)
            
            # Imagen de Referencia (Google Drive compatible)
            foto_url = item_elegido.get('foto_url', '')
            if foto_url and foto_url not in ["NO FOTO", "ERROR"]:
                link_directo = convertir_link_drive(foto_url)
                st.image(link_directo, width=450, caption=f"REFERENCIA / 참조: {nombre_f}")
            
            st.markdown('</div>', unsafe_allow_html=True)

    if st.button("VOLVER / 돌아가기"):
        st.session_state.page = 'menu' if st.session_state.user else 'login'; st.rerun()

# ================= LOGIN Y MENÚ =================

def login():
    st.title("LOGIN / 로그인")
    u = st.text_input("Usuario / 사용자").upper().strip()
    p = st.text_input("Clave / 비밀번호", type="password")
    if st.button("ENTRAR / 입장"):
        doc = db.collection("USUARIOS").document(u).get()
        if doc.exists and str(doc.to_dict().get('clave')) == p:
            st.session_state.user = u
            st.session_state.page = 'menu'; st.rerun()
        else: st.error("DATOS INCORRECTOS / 잘못된 정보")
    
    st.divider()
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()

def menu():
    st.title("ALMACÉN / 창고")
    st.info(f"SESIÓN: {st.session_state.user}")
    if st.button("🔍 BUSCAR / 검색"): st.session_state.page = 'buscar'; st.rerun()
    if st.button("SALIR / 로그아웃"): 
        st.session_state.user = None; st.session_state.page = 'login'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'buscar': buscar()
