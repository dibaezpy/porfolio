import streamlit as st
import pandas as pd
from pathlib import Path

@st.cache_data
def load_data():
    path = Path(__file__).parent / "base.xlsx"
    return pd.read_excel(path, engine="openpyxl")

def show():
    st.title("P&L • base.xlsx")
    try:
        df = load_data()
    except Exception as e:
        st.error(f"No pude leer 'base.xlsx'. Detalle: {type(e).__name__}: {e}")
        return
    st.dataframe(df, use_container_width=True)
