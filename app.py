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
        st.error(f"Error Conexión: {e}")

db = firestore.client()

# --- ESTILOS VISUALES (Basado en tus imágenes) ---
st.markdown("""
    <style>
    .stApp { background-color: black; color: white; }
    h1, h2, h3 { color: red !important; text-align: center; font-weight: bold; }
    .stButton>button { 
        background-color: white; 
        color: black; 
        border-radius: 2px; 
        width: 100%; 
        font-weight: bold; 
        border: 2px solid red;
        height: 45px;
    }
    .stButton>button:hover { background-color: red; color: white; }
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label { color: yellow !important; font-weight: bold; }
    .stTextInput>div>div>input { background-color: #262730; color: white !important; }
    .center-container { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZACIÓN DE SESIÓN ---
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user' not in st.session_state: st.session_state.user = None

def ir(acc, cat, page='form'):
    st.session_state.accion = acc
    st.session_state.categoria = cat
    st.session_state.page = page
    st.rerun()

# ================= VISTAS =================

def login():
    # Sección Superior: Login
    st.markdown("<h1>LOGIN / 로그인</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:red;'>ALMACÉN / 창고 🔗</h3>", unsafe_allow_html=True)
    
    u_in = st.text_input("Usuario / 사용자").upper().strip()
    p_in = st.text_input("Clave / 비밀번호", type="password").strip()
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("ENTRAR / 입장"):
            doc = db.collection("USUARIOS").document(u_in).get()
            if doc.exists and str(doc.to_dict().get('clave')) == p_in:
                st.session_state.user = u_in
                st.session_state.page = 'menu'
                st.rerun()
            else: st.error("Error de credenciales")
    with c2:
        if st.button("REGISTRARSE / 등록"):
            u, p = f"USER{random.randint(10,99)}", f"{random.randint(100,999)}"
            db.collection("USUARIOS").document(u).set({"clave": p, "estado": "ACTIVO"})
            st.success(f"User: {u} | Pass: {p}")
    
    st.markdown("<br><hr>", unsafe_allow_html=True)

    # Sección Inferior: Salida Rápida (Como en tu primera imagen)
    st.markdown("<h2>SALIDA RÁPIDA / 빠른 출고</h2>", unsafe_allow_html=True)
    
    cr1, cr2 = st.columns(2)
    with cr1:
        if st.button("SALIDA MATERIALES / 자재 출고"): ir("SALIDA", "materiales")
    with cr2:
        if st.button("SALIDA HOLDERS / 홀더 출고"): ir("SALIDA", "holders")
    
    if st.button("🔍 BUSCAR MATERIAL / 재고 검색"): 
        st.session_state.page = 'buscar'
        st.rerun()

    st.markdown('<div class="center-container">', unsafe_allow_html=True)
    st.image("https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExNWVzMWpmNWtnZjhhaG1xazd2YmlyeGJha295ZzduNDA3M3hxcXhpZyZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWUmY3Q9cw/5Lk5l5T3HSCS1luPVk/giphy.gif", width=300)
    st.markdown('</div>', unsafe_allow_html=True)

def menu():
    st.markdown("<h1>ALMACÉN / 창고</h1>", unsafe_allow_html=True)
    st.info(f"HOLA / 안녕하세요: {st.session_state.user}")
    
    # Grid de Materiales y Holders (Segunda imagen)
    col_mat, col_hol = st.columns(2)
    
    with col_mat:
        st.markdown("### MATERIALES / 자재")
        if st.button("ENTRADA MAT / 자재 입고"): ir("ENTRADA", "materiales")
        if st.button("SALIDA MAT / 자재 출고"): ir("SALIDA", "materiales")
        
    with col_hol:
        st.markdown("### HOLDERS / 홀더")
        if st.button("ENTRADA HOL / 홀더 입고"): ir("ENTRADA", "holders")
        if st.button("SALIDA HOL / 홀더 출고"): ir("SALIDA", "holders")
    
    st.markdown("<br><hr>", unsafe_allow_html=True)
    
    # Botones inferiores alineados a la izquierda
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

# --- LAS DEMÁS FUNCIONES (buscar, formulario, admin) SE MANTIENEN IGUAL ---
def buscar():
    st.header("BUSCAR / 검색")
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu'; st.rerun()
    # ... (Resto del código de búsqueda)

def formulario():
    cat, acc = st.session_state.get('categoria'), st.session_state.get('accion')
    st.header(f"{cat.upper()} - {acc}")
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu'; st.rerun()
    # ... (Resto del código de formulario)

def admin():
    st.title("PANEL CONTROL")
    if st.button("VOLVER / 돌아가기"): st.session_state.page = 'menu'; st.rerun()
    # ... (Resto del código admin)

# --- NAVEGACIÓN ---
if st.session_state.page == 'login': login()
elif st.session_state.page == 'menu': menu()
elif st.session_state.page == 'buscar': buscar()
elif st.session_state.page == 'form': formulario()
elif st.session_state.page == 'admin': admin()
