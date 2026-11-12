"""Mengubah berkas mentah SiPongi+ (data/raw/*.xlsx) menjadi CSV bersih di data/.

    python database/prepare_data.py

Keluaran:
  data/luas_karhutla_provinsi.csv  -> PostgreSQL (tabel provinsi + luas_karhutla)
  data/hotspot_detail.csv          -> MongoDB (koleksi hotspot_detail)

Sumber berkas mentah: SIPONGI KEMENHUT (sipongi.gakkum.kehutanan.go.id), diakses 12 November 2026.
"""
import csv
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_LUAS = ROOT / "data" / "raw" / "luas-karhutla-provinsi.xlsx"
RAW_HOTSPOT = ROOT / "data" / "raw" / "sebaran-hotspot.xlsx"
OUT_LUAS = ROOT / "data" / "luas_karhutla_provinsi.csv"
OUT_HOTSPOT = ROOT / "data" / "hotspot_detail.csv"

# Nama pada berkas hotspot yang berbeda dengan berkas luas.
# IKN berada di wilayah Kalimantan Timur (asumsi pengelompokan; nama asli disimpan di kolom provinsi_asal).
ALIAS = {"Kepulauan Bangka Belitung": "Bangka Belitung", "IKN": "Kalimantan Timur"}

# Pengelompokan wilayah berdasarkan digit pertama kode wilayah.
WILAYAH = {"1": "Sumatera", "2": "Sumatera", "3": "Jawa", "5": "Bali & Nusa Tenggara",
           "6": "Kalimantan", "7": "Sulawesi", "8": "Maluku", "9": "Papua"}


def parse_id_number(v):
    """'1.284,70' -> 1284.70 (format angka Indonesia); angka biasa dikembalikan apa adanya."""
    if isinstance(v, (int, float)):
        return float(v)
    return float(str(v).strip().replace(".", "").replace(",", "."))


def prepare_luas():
    raw = pd.read_excel(RAW_LUAS, dtype=str)
    total = raw[raw["Kode Wilayah"].isna()].iloc[0]
    prov = raw[raw["Kode Wilayah"].notna()].copy()
    year_cols = [c for c in raw.columns if str(c).isdigit()]
    rows = []
    for _, r in prov.iterrows():
        kode = str(r["Kode Wilayah"]).strip().zfill(2)
        for c in year_cols:
            rows.append({"kode_wilayah": kode, "provinsi": r["Provinsi"].strip(),
                         "wilayah": WILAYAH[kode[0]], "tahun": int(c), "luas_ha": round(parse_id_number(r[c]), 2)})
    out = pd.DataFrame(rows)
    # validasi: jumlah semua provinsi harus sama dengan baris Total pada berkas
    print("Validasi total tahunan (jumlah provinsi vs baris Total pada berkas):")
    for c in year_cols:
        s, t = out.loc[out["tahun"] == int(c), "luas_ha"].sum(), parse_id_number(total[c])
        print(f"  {c}: {s:>14,.2f} vs {t:>14,.2f}  {'OK' if abs(s - t) < 1 else 'BEDA'}")
    out.to_csv(OUT_LUAS, index=False)
    print(f"-> {OUT_LUAS.name}: {len(out)} baris, {out['kode_wilayah'].nunique()} provinsi, tahun {min(out.tahun)}-{max(out.tahun)}")
    return out


def prepare_hotspot(luas):
    name2kode = luas.drop_duplicates("kode_wilayah").set_index("provinsi")["kode_wilayah"].to_dict()
    d = pd.read_excel(RAW_HOTSPOT, sheet_name="Detail")
    d["provinsi_asal"] = d["Provinsi"].str.strip()
    d["provinsi"] = d["provinsi_asal"].replace(ALIAS)
    d["kode_wilayah"] = d["provinsi"].map(name2kode)
    if d["kode_wilayah"].isna().any():
        raise ValueError(f"Provinsi tidak dikenal: {sorted(d.loc[d.kode_wilayah.isna(), 'provinsi'].unique())}")
    d["waktu"] = [datetime.strptime(f"{t} {w.replace(' WIB', '')}", "%d-%m-%Y %H:%M").strftime("%Y-%m-%dT%H:%M:00+07:00")
                  for t, w in zip(d["Tanggal"], d["Waktu"])]
    out = d.rename(columns={"Kab Kota": "kab_kota", "Kecamatan": "kecamatan", "Desa": "desa", "Satelit": "satelit",
                            "Confidence": "confidence", "Latitude": "latitude", "Longitude": "longitude"})
    out = out[["kode_wilayah", "provinsi", "provinsi_asal", "kab_kota", "kecamatan", "desa", "waktu",
               "satelit", "confidence", "latitude", "longitude"]]
    out.to_csv(OUT_HOTSPOT, index=False, quoting=csv.QUOTE_MINIMAL)
    print(f"-> {OUT_HOTSPOT.name}: {len(out)} titik, {out['kode_wilayah'].nunique()} provinsi, "
          f"{out['waktu'].min()} s.d. {out['waktu'].max()}")
    print("   dipetakan lewat alias:", d.loc[d.provinsi_asal != d.provinsi, "provinsi_asal"].value_counts().to_dict())
    # validasi silang dengan sheet Akumulasi
    acc = pd.read_excel(RAW_HOTSPOT, sheet_name="Akumulasi")
    print(f"   sheet Akumulasi: {int(acc['Counter'].sum())} titik (Detail: {len(d)})")


if __name__ == "__main__":
    prepare_hotspot(prepare_luas())
