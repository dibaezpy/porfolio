import streamlit as st
import pnl  # tu módulo actual

st.set_page_config(page_title="Panel de Módulos", layout="wide")

st.sidebar.title("Navegación")
submodulo = st.sidebar.selectbox("📊 Submódulo Administración:", ["P&L"], index=0)

if submodulo == "P&L":
    pnl.show()   # llama al módulo P&L
