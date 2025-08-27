import pandas as pd
import streamlit as st

@st.cache_data
def load_data():
    # Lee solo cuando se llama al módulo, no al import
    return pd.read_excel("base.xlsx", engine="openpyxl")

def show():
    st.title("P&L • base.xlsx")
    try:
        df = load_data()
    except ImportError as e:
        st.error("Falta 'openpyxl'. Verifica requirements.txt con: openpyxl>=3.1.2")
        return
    except FileNotFoundError:
        st.error("No encuentro 'base.xlsx' en la raíz del repo.")
        return
    st.dataframe(df, use_container_width=True)
