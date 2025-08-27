import streamlit as st
import pnl  # <--- IMPORTA pnl.py (asegurate que exista con ese nombre)

st.set_page_config(page_title="Panel de Módulos", layout="wide")

st.sidebar.title("Navegación")
st.sidebar.caption("build v3")  # marca para verificar el deploy
submodulo = st.sidebar.selectbox("📊 Submódulo Administración:", ["P&L"], index=0)

if submodulo == "P&L":
    pnl.show()
