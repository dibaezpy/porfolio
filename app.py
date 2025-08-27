import streamlit as st
import pnl_view  # <-- importa el módulo que sí existe

st.set_page_config(page_title="Panel de Módulos", layout="wide")
st.sidebar.title("Navegación")
submodulo = st.sidebar.selectbox("📊 Submódulo Administración:", ["P&L"], index=0)

if submodulo == "P&L":
    pnl_view.show()
