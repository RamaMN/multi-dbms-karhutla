# Folder data

## raw/ (berkas mentah, tidak diubah)
| Berkas | Isi |
|---|---|
| `luas-karhutla-provinsi.xlsx` | Luas karhutla (ha) per provinsi, 2018–2026 (2026 = data berjalan) |
| `sebaran-hotspot.xlsx` | Sheet `Akumulasi` (ringkasan) dan `Detail` (1.276 titik hotspot, 11–12 Nov 2026) |

Sumber: **SIPONGI KEMENHUT** (Sistem Pemantauan Karhutla, Kementerian Kehutanan), diakses 12 November 2026.
SiPongi+ mewajibkan setiap penggunaan datanya mencantumkan sumber tersebut.

## Berkas bersih (hasil `python database/prepare_data.py`)
### luas_karhutla_provinsi.csv → PostgreSQL (`provinsi` + `luas_karhutla`)
| Kolom | Keterangan |
|---|---|
| kode_wilayah | kode 2 digit provinsi (kunci integrasi) |
| provinsi | nama provinsi |
| wilayah | pengelompokan dari digit pertama kode (Sumatera, Jawa, Bali & Nusa Tenggara, Kalimantan, Sulawesi, Maluku, Papua) |
| tahun, luas_ha | tahun dan luas terbakar (hektare) |

### hotspot_detail.csv → MongoDB (`hotspot_detail`)
| Kolom | Keterangan |
|---|---|
| kode_wilayah, provinsi | hasil pemetaan nama provinsi ke kode |
| provinsi_asal | nama provinsi pada berkas mentah |
| kab_kota, kecamatan, desa | lokasi administratif |
| waktu | waktu deteksi (ISO, zona WIB +07:00) |
| satelit, confidence | satelit (NASA-MODIS/NOAA20/NOAA21) dan tingkat kepercayaan (High/Medium/Low) |
| latitude, longitude | koordinat; disimpan sebagai GeoJSON Point `[lon, lat]` |

## Transformasi & validasi yang dilakukan
- Angka berformat Indonesia (`1.284,70`) diubah menjadi `1284.70`.
- Jumlah seluruh provinsi per tahun dicocokkan dengan baris **Total** pada berkas (semua tahun cocok).
- Total titik sheet `Akumulasi` dicocokkan dengan sheet `Detail` (1.276 = 1.276).
- Nama provinsi hotspot yang berbeda dari berkas luas dipetakan: `Kepulauan Bangka Belitung` → `Bangka Belitung`; `IKN` → `Kalimantan Timur` (asumsi pengelompokan; nama asli tetap tersimpan di `provinsi_asal`).

## Memperbarui data
1. Unduh ulang kedua berkas dari SiPongi+ ke `data/raw/` (nama sama).
2. `python database/prepare_data.py` lalu `python database/seed_data.py`.
3. Di aplikasi klik **Muat ulang data**.
