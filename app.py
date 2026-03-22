import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage
import pandas as pd
from datetime import datetime
import os
import random
import requests

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="YAKO PRO WEB", page_icon="📦", layout="centered")

# --- CONEXIÓN FIREBASE ---
if not firebase_admin._apps:
    try:
        bucket_name = 'almacnn.firebasestorage.app'
        if "textkey" in st.secrets:
            cred = credentials.Certificate(dict(st.secrets["textkey"]))
            firebase_admin.initialize_app(cred, {'storageBucket': bucket_name})
    except Exception as e:
        st.error(f"Error Conexión: {e}")

db = firestore.client()

# --- ESTILOS VISUALES (REPLICANDO TUS FOTOS) ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; font-weight: bold; }
    .stButton>button { 
        background-color: white; color: black; border-radius: 5px; 
        width: 100%; font-weight: bold; border: 2px solid red; 
    }
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label { color: yellow !important; }
    .stMetric { background-color: #111; border: 1px solid #333; border-radius: 10px; padding: 10px; }
    div[data-testid="stMetricValue"] { color: cyan !important; font-size: 50px !important; text-align: center; }
    .yako-adjust { border: 2px solid red; padding: 15px; border-radius: 10px; background-color: #220000; }
    </style>
    """, unsafe_allow_html=True)

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None

# --- FUNCIONES DE NAVEGACIÓN ---
def ir(p): 
    st.session_state.page = p
    st.rerun()

# ================= VISTAS =================

def login():
    st.markdown("<h1>LOGIN / 로그인</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='color:red;'>ALMACÉN / 창고 🔗</h2>", unsafe_allow_html=True)
    
    u = st.text_input("Usuario / 사용자").upper().strip()
    p = st.text_input("Clave / 비밀번호", type="password")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(u).get()
            if doc.exists and str(doc.to_dict().get('clave')) == p:
                st.session_state.user = u
                st.session_state.user_status = doc.to_dict().get('estado')
                ir('menu')
            else: st.error("Error de acceso")
    with c2:
        if st.button("REGISTRARSE / 등록"):
            st.info("Contacta al administrador para el registro.")

    st.divider()
    st.markdown("<h3 style='color:white;'>SALIDA RÁPIDA / 빠른 출고</h3>", unsafe_allow_html=True)
    
    c3, c4 = st.columns(2)
    with c3:
        if st.button("SALIDA MATERIALES / 자재 출고"): ir('form_salida_mat')
    with c4:
        if st.button("SALIDA HOLDERS / 홀더 출고"): ir('form_salida_hol')
    
    if st.button("🔍 BUSCAR MATERIAL / 재고 검색"): ir('buscar')
    
    # Imagen del montacargas como en tu foto
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Forklift_icon.svg/1200px-Forklift_icon.svg.png", width=300)

def menu():
    st.markdown("<h1>ALMACÉN / 창고</h1>", unsafe_allow_html=True)
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
    
    col_mat, col_hol = st.columns(2)
    with col_mat:
        st.markdown("<h2 style='color:red;'>MATERIALES / 자재</h2>", unsafe_allow_html=True)
        if st.button("ENTRADA MAT / 자재 입고"): ir('form_entrada_mat')
        if st.button("SALIDA MAT / 자재 출고"): ir('form_salida_mat')
    
    with col_hol:
        st.markdown("<h2 style='color:red;'>HOLDERS / 홀더</h2>", unsafe_allow_html=True)
        if st.button("ENTRADA HOL / 홀더 입고"): ir('form_entrada_hol')
        if st.button("SALIDA HOL / 홀더 출고"): ir('form_salida_hol')
    
    st.divider()
    if st.button("BUSCAR / 검색"): ir('buscar')
    if st.session_state.user == "YAKO":
        if st.button("PANEL CONTROL / 제어판"): ir('admin')
    if st.button("SALIR / 로그아웃"): 
        st.session_state.user = None
        ir('login')

def buscar():
    st.markdown("<h1>BUSCAR / 검색</h1>", unsafe_allow_html=True)
    cod = st.text_input("ID / CÓDIGO / 코드").upper().strip()
    
    if cod:
        stock = 0
        ubis = []
        # Lógica para sumar stock y obtener ubicaciones
        for cat in ["materiales", "holders"]:
            docs = db.collection(cat).where("item", "==", cod).stream()
            for d in docs:
                data = d.to_dict()
                stock += data.get('cantidad', 0)
                u = data.get('ubicacion')
                if u and u not in ubis: ubis.append(u)
        
        st.markdown(f"<h3>RESULTADO: {cod}</h3>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.metric("STOCK / 재고", stock)
        with c2: st.metric("UBICACIÓN / 위치", ", ".join(ubis) if ubis else "---")
        
        # --- PANEL DE AJUSTE EXCLUSIVO YAKO ---
        if st.session_state.user == "YAKO":
            st.markdown('<div class="yako-adjust">', unsafe_allow_html=True)
            st.markdown("<h3>⚠️ AJUSTE YAKO / 야코 조정</h3>", unsafe_allow_html=True)
            new_q = st.number_input("Ajuste Cantidad (+/-)", step=1)
            new_u = st.text_input("Ubicación Nueva").upper().strip()
            
            if st.button("CONFIRMAR AJUSTE"):
                # Se guarda SIN la palabra "AJUSTE", solo el valor nuevo
                db.collection("materiales").add({
                    "item": cod,
                    "cantidad": new_q,
                    "ubicacion": new_u,
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "usuario": "YAKO"
                })
                st.success("Ajuste realizado correctamente.")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    if st.button("VOLVER / 돌아가기"): ir('menu')

# --- INICIO DE APP ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'buscar': buscar()
