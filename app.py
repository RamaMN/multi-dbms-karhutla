import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import psycopg2
from pymongo import MongoClient
import os

st.set_page_config(page_title="Multi-DBMS Karhutla & ISPA Pipeline", page_icon="🚨", layout="wide")
st.title("🚨 Multi-DBMS Data Pipeline: Karhutla, ISPU & ISPA Crisis Center")
st.caption("Integrasi Data Relational (PostgreSQL/Supabase) + NoSQL Document (MongoDB Atlas)")

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "postgres")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASS = os.getenv("PG_PASS", "password")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

@st.cache_data(ttl=600)
def fetch_and_integrate_data():
    try:
        conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, database=PG_DB, user=PG_USER, password=PG_PASS)
        df_pg = pd.read_sql("SELECT prov_id, nama_provinsi, total_ispa, korban_meninggal FROM data_kesehatan;", conn)
        conn.close()
    except Exception:
        df_pg = pd.DataFrame({
            'prov_id': [1, 2, 3, 4, 5],
            'nama_provinsi': ['Riau', 'Kalimantan Tengah', 'Kalimantan Barat', 'Jambi', 'DKI Jakarta'],
            'total_ispa': [12500, 18400, 14200, 9800, 8500],
            'korban_meninggal': [12, 24, 18, 8, 3]
        })

    try:
        client = MongoClient(MONGO_URI)
        data_mongo = list(client['karhutla_db']['telemetri_sensor'].find({}, {'_id': 0}))
        df_mongo = pd.DataFrame(data_mongo)
        client.close()
    except Exception:
        df_mongo = pd.DataFrame({
            'prov_id': [1, 2, 3, 4, 5],
            'titik_hotspot': [185, 290, 210, 95, 12],
            'ispu_pm25': [280.5, 340.2, 295.0, 160.8, 85.0],
            'lahan_terbakar_ha': [3200.5, 4800.0, 3900.2, 1200.0, 50.0]
        })

    return pd.merge(df_pg, df_mongo, on='prov_id')

df = fetch_and_integrate_data()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("DBMS 1: Total ISPA", f"{df['total_ispa'].sum():,} Jiwa")
c2.metric("DBMS 1: Korban Meninggal ✝️", f"{df['korban_meninggal'].sum():,} Jiwa")
c3.metric("DBMS 2: Total Hotspot", f"{df['titik_hotspot'].sum():,} Titik")
c4.metric("DBMS 2: Rata-rata ISPU", f"{df['ispu_pm25'].mean():.1f}")
c5.metric("Luas Terbakar", f"{df['lahan_terbakar_ha'].sum():,.1f} Ha")

st.divider()
col_l, col_r = st.columns(2)
with col_l:
    st.subheader("Korelasi ISPU (MongoDB) vs Korban Meninggal (PostgreSQL)")
    fig_scatter = px.scatter(df, x="ispu_pm25", y="korban_meninggal", size="total_ispa", color="nama_provinsi", hover_name="nama_provinsi")
    st.plotly_chart(fig_scatter, use_container_width=True)
with col_r:
    st.subheader("Top Provinsi Korban Meninggal Dunia")
    fig_bar = px.bar(df.sort_values('korban_meninggal'), x="korban_meninggal", y="nama_provinsi", orientation='h', color="korban_meninggal", color_continuous_scale="Reds")
    st.plotly_chart(fig_bar, use_container_width=True)

with st.expander("📄 Lihat Hasil Penggabungan Data (Data Federation / Join)"):
    st.dataframe(df)