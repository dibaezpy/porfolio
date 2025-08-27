import streamlit as st
import importlib

st.set_page_config(page_title="Panel de Módulos", layout="wide")
st.sidebar.title("Navegación")
submodulo = st.sidebar.selectbox("📊 Submódulo Administración:", ["P&L"], index=0)

if submodulo == "P&L":
    pnl = importlib.import_module("pnl2")  # << usa el módulo nuevo
    pnl.show()
