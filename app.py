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
        st.error(f"Error Conexión: {e}")

db = firestore.client()

# --- ESTILOS ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; }
    .stButton>button { background-color: white; color: black; border-radius: 5px; width: 100%; font-weight: bold; border: 2px solid red; }
    div[data-testid="stTextInput"] label, div[data-testid="stSelectbox"] label { color: yellow !important; }
    .stTextInput>div>div>input { text-align: center; background-color: #111; color: cyan !important; font-size: 20px; }
    div[data-testid="stMetric"] { background-color: #111; padding: 10px; border-radius: 10px; border: 1px solid #333; text-align: center; }
    .qr-container { background-color: white; padding: 10px; border-radius: 10px; display: inline-block; text-align: center; }
    .center-content { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- VARIABLES DE SESIÓN ---
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None
if 'user_status' not in st.session_state: st.session_state.user_status = None

# ================= FUNCIONES =================

def ir(acc, cat):
    st.session_state.accion = acc; st.session_state.categoria = cat
    st.session_state.page = 'form'; st.rerun()

def buscar():
    st.header("BUSCAR / 검색")
    # Entrada de texto única para Nombre o ID
    busqueda = st.text_input("NOMBRE o ID / 이름 또는 ID").upper().strip()

    if busqueda:
        resultados = []
        for col in ["materiales", "holders"]:
            # Buscamos en toda la base de datos para filtrar localmente (es más flexible)
            docs = db.collection(col).stream()
            for d in docs:
                data = d.to_dict()
                nombre = str(data.get('nombre', '')).upper()
                idx = str(data.get('item', '')).upper()
                
                # Si coincide el nombre o el ID lo agregamos a la lista
                if busqueda in nombre or busqueda == idx:
                    data['categoria_db'] = col # Guardamos de qué tabla viene
                    resultados.append(data)
        
        if len(resultados) > 1:
            st.warning(f"Se encontraron {len(resultados)} coincidencias. Selecciona una:")
            # Creamos una lista de opciones legibles
            opciones = {f"{r['nombre']} ({r['item']})": r for r in resultados}
            seleccion = st.selectbox("Resultados encontrados:", list(opciones.keys()))
            item_elegido = opciones[seleccion]
        elif len(resultados) == 1:
            item_elegido = resultados[0]
        else:
            st.error("No se encontró nada / 검색 결과 없음")
            item_elegido = None

        if item_elegido:
            # Una vez tenemos el item (ya sea directo o por lista), mostramos la info
            nombre_f = item_elegido.get('nombre', 'SIN NOMBRE')
            id_f = item_elegido.get('item', '---')
            col_f = item_elegido['categoria_db']
            
            # Calcular Stock Real
            docs_stock = db.collection(col_f).where("item", "==", id_f).stream()
            total_stock = sum([doc.to_dict().get('cantidad', 0) for doc in docs_stock])
            
            st.markdown(f"<h2 style='color: red;'>{nombre_f}</h2>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            c1.metric("STOCK TOTAL", total_stock)
            c2.metric("ID", id_f)

            st.markdown('<div class="center-content">', unsafe_allow_html=True)
            
            # QR CENTRADO
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={id_f}"
            st.markdown(f'<div class="qr-container"><img src="{qr_url}"><br><b style="color:black">QR {id_f}</b></div>', unsafe_allow_html=True)
            
            # IMAGEN CENTRADA
            foto_url = item_elegido.get('foto_url', '')
            if foto_url and foto_url not in ["NO FOTO", "ERROR"]:
                st.image(foto_url, width=400, caption=f"Referencia: {nombre_f}")
            
            st.markdown('</div>', unsafe_allow_html=True)

    if st.button("VOLVER / 돌아가기"):
        st.session_state.page = 'menu' if st.session_state.user else 'login'; st.rerun()

# ================= VISTAS RESTANTES (RESUMIDAS) =================

def login():
    st.title("LOGIN / 로그인")
    u = st.text_input("Usuario").upper().strip()
    p = st.text_input("Clave", type="password")
    if st.button("ENTRAR"):
        doc = db.collection("USUARIOS").document(u).get()
        if doc.exists and str(doc.to_dict().get('clave')) == p:
            st.session_state.user = u
            st.session_state.user_status = "YAKO" if u == "YAKO" else "ACTIVO"
            st.session_state.page = 'menu'; st.rerun()
        else: st.error("Error")
    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("SALIDA MATERIALES"): ir("SALIDA", "materiales")
    if c2.button("SALIDA HOLDERS"): ir("SALIDA", "holders")
    if st.button("🔍 BUSCAR"): st.session_state.page = 'buscar'; st.rerun()

def menu():
    st.title("MENÚ / 메뉴")
    st.info(f"Usuario: {st.session_state.user}")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("ENTRADA MAT"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT"): ir("SALIDA", "materiales")
    with c2:
        if st.button("ENTRADA HOL"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL"): ir("SALIDA", "holders")
    if st.button("🔍 BUSCAR"): st.session_state.page = 'buscar'; st.rerun()
    if st.button("SALIR"): st.session_state.user=None; st.session_state.page='login'; st.rerun()

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'buscar': buscar()
