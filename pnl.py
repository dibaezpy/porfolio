import pandas as pd
import streamlit as st

@st.cache_data
def load_data():
    return pd.read_excel("base.xlsx", engine="openpyxl")

def show():
    st.title("P&L • base.xlsx")
    df = load_data()
    st.dataframe(df, use_container_width=True)
