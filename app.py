import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import psycopg2
from pymongo import MongoClient
import os

# 1. Konfigurasi Halaman
st.set_page_config(page_title="Multi-DBMS Karhutla & ISPA Pipeline", page_icon="🚨", layout="wide")

st.title("🚨 Multi-DBMS Data Pipeline: Karhutla, ISPU & ISPA Crisis Center")
st.caption("Integrasi Data Relational (PostgreSQL/Supabase) + NoSQL Document (MongoDB Atlas)")

# 2. Parameter Koneksi Database
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "postgres")
PG_USER = os.getenv("PG_USER", "postgres")
PG_PASS = os.getenv("PG_PASS", "password")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# 3. Fungsi Ambil & Gabung Data (Data Federation)
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
            'lahan_terbakar_ha': [3200.5, 4800.0, 3900.2, 1200.0, 50.0],
            'lat': [0.5104, -1.6815, -0.0263, -1.6101, -6.2088],
            'lon': [101.4383, 113.3824, 109.3425, 103.6131, 106.8456]
        })

    return pd.merge(df_pg, df_mongo, on='prov_id')

df_raw = fetch_and_integrate_data()

# 4. Sidebar Filter
st.sidebar.header("🔍 Filter & Kontrol Dashboard")
selected_prov = st.sidebar.multiselect(
    "Pilih Provinsi:",
    options=df_raw["nama_provinsi"].unique(),
    default=df_raw["nama_provinsi"].unique()
)

min_ispu = st.sidebar.slider(
    "Filter Minimal Batas ISPU (PM2.5):",
    min_value=int(df_raw["ispu_pm25"].min()),
    max_value=int(df_raw["ispu_pm25"].max()),
    value=int(df_raw["ispu_pm25"].min())
)

# Terapkan Filter
df = df_raw[(df_raw["nama_provinsi"].isin(selected_prov)) & (df_raw["ispu_pm25"] >= min_ispu)]

if df.empty:
    st.warning("⚠️ Tidak ada data yang sesuai dengan kombinasi filter Anda.")
else:
    # 5. Status Peringatan Dini (Early Warning System)
    avg_ispu = df['ispu_pm25'].mean()
    if avg_ispu > 300:
        st.error("🚨 **STATUS DARURAT BENCANA**: Rata-rata ISPU wilayah terpilih berada dalam kategori BERBAHAYA (>300)!")
    elif avg_ispu > 200:
        st.warning("⚠️ **STATUS SIAGA**: Rata-rata ISPU wilayah terpilih berada dalam kategori SANGAT TIDAK SEHAT (200-300).")
    else:
        st.info("✅ **STATUS WASPADA/AMAN**: Rata-rata ISPU masih dalam ambang batas toleransi.")

    # 6. Ringkasan KPI Metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("DBMS 1: Total ISPA", f"{df['total_ispa'].sum():,} Jiwa")
    c2.metric("DBMS 1: Korban Meninggal ✝️", f"{df['korban_meninggal'].sum():,} Jiwa")
    c3.metric("DBMS 2: Total Hotspot", f"{df['titik_hotspot'].sum():,} Titik")
    c4.metric("DBMS 2: Rata-rata ISPU", f"{df['ispu_pm25'].mean():.1f}")
    c5.metric("Luas Terbakar", f"{df['lahan_terbakar_ha'].sum():,.1f} Ha")

    st.divider()

    # 7. Visualisasi Grafik Interaktif
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Korelasi ISPU (MongoDB) vs Korban Meninggal (PostgreSQL)")
        fig_scatter = px.scatter(
            df, x="ispu_pm25", y="korban_meninggal", size="total_ispa", 
            color="nama_provinsi", hover_name="nama_provinsi",
            labels={"ispu_pm25": "Nilai ISPU PM2.5", "korban_meninggal": "Korban Meninggal (Jiwa)"}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col_r:
        st.subheader("Top Provinsi Korban Meninggal Dunia")
        fig_bar = px.bar(
            df.sort_values('korban_meninggal'), x="korban_meninggal", y="nama_provinsi", 
            orientation='h', color="korban_meninggal", color_continuous_scale="Reds",
            labels={"korban_meninggal": "Jumlah Korban", "nama_provinsi": "Provinsi"}
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # 8. Peta Sebaran Spasial Hotspot
    st.subheader("🗺️ Peta Sebaran Titik Hotspot & ISPU Spasial")
    fig_map = px.scatter_geo(
        df, lat="lat", lon="lon", color="ispu_pm25", size="titik_hotspot",
        hover_name="nama_provinsi", scope="asia",
        center={"lat": -2.5, "lon": 118.0},
        title="Distribusi Hotspot Karhutla di Indonesia"
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # 9. Tabel & Fitur Ekspor Data CSV
    with st.expander("📄 Lihat Hasil Penggabungan Data (Data Federation / Join)"):
        st.dataframe(df, use_container_width=True)
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Unduh Data Gabungan (CSV)",
            data=csv_data,
            file_name="multi_dbms_karhutla_integrated.csv",
            mime="text/csv"
        )