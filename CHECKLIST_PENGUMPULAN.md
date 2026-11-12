# Checklist pengumpulan (dipetakan ke ketentuan tugas)

| Ketentuan di tugas | Bukti di repositori | Status |
|---|---|---|
| Minimal 2 DBMS berbeda | PostgreSQL (`provinsi`, `luas_karhutla`) + MongoDB Atlas (`hotspot_detail`) | ✅ kode siap; ⬜ database cloud dibuat & di-seed |
| Konektor Python | SQLAlchemy + psycopg2, PyMongo | ✅ |
| Integrasi dengan Pandas | `merge(..., on="kode_wilayah", validate="one_to_one")` di `app.py` | ✅ |
| Web framework + pustaka visual | Streamlit + Plotly | ✅ |
| Deploy live & publik | Streamlit Community Cloud | ⬜ isi Secrets, pastikan dua status sidebar hijau |
| Kredensial aman, tanpa hardcode | `st.secrets` / env var; `.gitignore` memuat `secrets.toml` | ✅ |
| Studi kasus & alasan dua DBMS | README bagian 1 | ✅ |
| Tautan sumber data primer | README bagian 6 (SIPONGI KEMENHUT) | ⬜ isi URL halaman unduhan |
| Skrip DDL / seed | `database/schema.sql`, `seed_data.py`, `prepare_data.py`, `data/*.csv`, `data/raw/*.xlsx` | ✅ |
| Tautan referensi kode | README bagian 7 | ⬜ pertahankan hanya repositori yang benar-benar kamu baca |
| `app.py`, `requirements.txt`, README lengkap | ada | ✅ |
| Diagram arsitektur, alur pipeline, fitur interaktif | README bagian 2 & 3 | ✅ |

## Isian form LMS
- Nama lengkap & NIM
- URL aplikasi live: `[ISI]`
- URL repositori GitHub (publik): `[ISI]`
- URL sumber data asli: halaman SiPongi+ tempat kamu mengunduh kedua berkas
- URL referensi kode: repositori pada README bagian 7 (sesuaikan)

## Sebelum submit, cek di aplikasi live
- [ ] Sidebar: 🐘 PostgreSQL dan 🍃 MongoDB hijau
- [ ] Tidak ada banner error; peta, tren, dan tab gabungan tampil
- [ ] Repositori publik tidak memuat password (cek juga riwayat commit)
- [ ] Hapus file lama di repo: `data/kesehatan_provinsi.csv`, `data/telemetri_provinsi.csv`, `database/seed_mongodb.json`, `database/reference_data.py`
