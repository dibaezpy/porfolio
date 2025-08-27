import streamlit as st
import pnl

st.set_page_config(page_title="Panel de Módulos", layout="wide")

st.sidebar.title("Navegación")
st.sidebar.caption("build: app.py v1")   # ← marca rápida
submodulo = st.sidebar.selectbox("📊 Submódulo Administración:", ["P&L"], index=0)

if submodulo == "P&L":
    pnl.show()
