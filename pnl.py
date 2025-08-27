import streamlit as st
import pandas as pd
from pathlib import Path

@st.cache_data
def load_data():
    xlsx = Path(__file__).parent / "base.xlsx"
    return pd.read_excel(xlsx, engine="openpyxl")

def show():
    st.title("P&L • base.xlsx")
    df = load_data()
    st.dataframe(df, use_container_width=True)
