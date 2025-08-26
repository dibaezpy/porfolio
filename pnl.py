import pandas as pd
import streamlit as st

df = pd.read_excel("base.xlsx", engine="openpyxl")
st.title("Vista de base.xlsx")
st.dataframe(df, use_container_width=True)