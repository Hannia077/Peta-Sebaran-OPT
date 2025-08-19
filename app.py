import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import matplotlib.cm as cm
import matplotlib.colors as colors
import base64

st.set_page_config(page_title="Peta OPT", layout="wide")

# ========= Background gambar + overlay (gambar tetap, tanpa text shadow) =========
def add_bg_with_overlay(image_file, overlay_alpha=0.55):  # 0 (transparan) - 1 (opaque)
    with open(image_file, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    st.markdown(f"""
    <style>
    /* Gambar background + overlay putih agar konten kebaca */
    [data-testid="stAppViewContainer"] {{
        background:
            linear-gradient(rgba(255,255,255,{overlay_alpha}), rgba(255,255,255,{overlay_alpha})),
            url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
        background-position: center;
    }}

    /* Header transparan, sidebar sedikit transparan */
    [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
    [data-testid="stSidebar"] {{ background: rgba(255,255,255,0.7); }}

    /* Hapus shadow pada tulisan */
    h1, h2, h3, h4, h5, h6, p, span, label, div {{
        text-shadow: none !important;
    }}

    /* Semua title/judul bold */
    h1, h2, h3, h4, h5, h6, label {{
        font-weight: 800 !important;
    }}

    /* Label filter khusus (Filter Kecamatan, Desa, OPT, dsb) */
    label.css-16idsys.e16fv1kl2 {{
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        color: #000000 !important;
    }}

    /* Map full width */
    .map-wrap iframe, .map-wrap div, .map-wrap {{ width: 100% !important; }}

    /* Sedikit rapihin tabel/upload/filter */
    .block-container {{ padding-top: 1rem; }}
    </style>
    """, unsafe_allow_html=True)

# panggil dengan file lokalmu
add_bg_with_overlay("bg.png", overlay_alpha=0.55)

# ========= Komponen UI =========
st.title("Visualisasi Peta Sebaran OPT di Sidoarjo")

# kotak sukses custom (vibrant, solid)
def success_box(msg):
    st.markdown(
        f"""
        <div style="
            background:#28a745;
            color:#ffffff;
            padding:10px 14px;
            border-radius:10px;
            font-weight:600;
            border:1px solid #1f8f3a;">
            {msg}
        </div>
        """,
        unsafe_allow_html=True
    )


# Upload file data
uploaded_file = st.file_uploader("📤 Upload file Excel/CSV", type=["csv", "xlsx"])

# Baca SHP

gdf = gpd.read_file("Data/ADMINISTRASIDESA_AR_25K.shp")
gdf.to_file("Data/nama_file.geojson", driver="GeoJSON")

# Kolom join
gdf["DESA_JOIN"] = gdf["NAMOBJ"].astype(str).str.strip().str.upper()
gdf["KECAMATAN_JOIN"] = gdf["WADMKC"].astype(str).str.strip().str.upper()

if uploaded_file is not None:
    # Baca data
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    df["DESA_JOIN"] = df["Desa"].astype(str).str.strip().str.upper()
    df["KECAMATAN_JOIN"] = df["Kecamatan"].astype(str).str.strip().str.upper()

    success_box("✅ Data berhasil diupload!")
    st.dataframe(df.head())

    # ---------------- Dropdown Filter ----------------
    col1, col2, col3, col5, col4  = st.columns(5)

    kecamatan_list = sorted(df["Kecamatan"].dropna().unique().tolist())
    with col1:
        kecamatan_filter = st.multiselect("Filter Kecamatan", ["Semua"] + kecamatan_list, default=["Semua"])

    if "Semua" not in kecamatan_filter:
        desa_list = sorted(
            df[df["Kecamatan"].isin(kecamatan_filter)]["Desa"].dropna().unique().tolist()
        )
    else:
        desa_list = sorted(df["Desa"].dropna().unique().tolist())

    with col2:
        desa_filter = st.multiselect("Filter Desa", ["Semua"] + desa_list, default=["Semua"])

    opt_list = sorted(df["OPT"].dropna().unique().tolist())
    with col3:
        opt_filter = st.multiselect("Filter OPT", ["Semua"] + opt_list, default=["Semua"])

    with col5:
        value_options = ["Serangan", "Pengendalian", "Puso"]
        value_filter = st.multiselect(
            "Pilih Data yang Ditampilkan",
            ["Semua"] + value_options,
            default=["Semua"]
        )

    bulan_list = sorted(df["Bulan"].dropna().unique().tolist())
    with col4:
        bulan_filter = st.multiselect("Filter Bulan", ["Semua"] + bulan_list, default=["Semua"])

    # ---------------- Filter Dataframe ----------------
    filtered_df = df.copy()
    if "Semua" not in kecamatan_filter:
        filtered_df = filtered_df[filtered_df["Kecamatan"].str.upper().isin([k.upper() for k in kecamatan_filter])]
    if "Semua" not in desa_filter:
        filtered_df = filtered_df[filtered_df["Desa"].str.upper().isin([d.upper() for d in desa_filter])]
    if "Semua" not in opt_filter:
        filtered_df = filtered_df[filtered_df["OPT"].str.upper().isin([o.upper() for o in opt_filter])]
    if "Semua" not in bulan_filter:
        filtered_df = filtered_df[filtered_df["Bulan"].astype(str).str.upper().isin([str(b).upper() for b in bulan_filter])]

    merged = gdf.merge(df, on=["DESA_JOIN", "KECAMATAN_JOIN"], how="left", suffixes=('', '_data'))

    # Warna per kecamatan
    kecamatan_unique = gdf["KECAMATAN_JOIN"].dropna().unique()
    cmap = cm.get_cmap('tab20', len(kecamatan_unique))
    color_dict = {kec: colors.rgb2hex(cmap(i)[:3]) for i, kec in enumerate(kecamatan_unique)}

    # ---------------- Style Function ----------------
    def style_function(feature):
        kec = feature["properties"].get("KECAMATAN_JOIN")
        desa = feature["properties"].get("DESA_JOIN")
        opt = feature["properties"].get("OPT")
        bulan = feature["properties"].get("Bulan")

        # cek apakah filter aktif
        filter_active = (
            ("Semua" not in kecamatan_filter) or
            ("Semua" not in desa_filter) or
            ("Semua" not in opt_filter) or
            ("Semua" not in bulan_filter)
        )

        match_filter = True
        if "Semua" not in kecamatan_filter and (kec is None or kec.upper() not in [k.upper() for k in kecamatan_filter]):
            match_filter = False
        if "Semua" not in desa_filter and (desa is None or desa.upper() not in [d.upper() for d in desa_filter]):
            match_filter = False
        if "Semua" not in opt_filter and (opt is None or opt.upper() not in [o.upper() for o in opt_filter]):
            match_filter = False
        if "Semua" not in bulan_filter and (bulan is None or str(bulan).upper() not in [str(b).upper() for b in bulan_filter]):
            match_filter = False

        if filter_active:
            if match_filter:
                # area sesuai filter → warnanya lebih bold + border tebal merah
                return {
                    "fillColor": color_dict.get(kec, "#ffcc00"),
                    "color": "black",
                    "weight": 0.5,
                    "fillOpacity": 0.9
                }
            else:
                # area lain → abu-abu samar
                return {
                    "fillColor": "lightgray",
                    "color": "black",
                    "weight": 0.5,
                    "fillOpacity": 0.2
                }
        # kalau filter belum dipakai → tampilkan normal
        return {
            "fillColor": color_dict.get(kec, "lightblue"),
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.6
        }

    # ---------------- Tooltip Dinamis ----------------
    tooltip_fields = ["DESA_JOIN", "KECAMATAN_JOIN", "OPT", "Bulan"]
    tooltip_aliases = ["Desa:", "Kecamatan:", "OPT:", "Bulan:"]

    if "Semua" in value_filter:
        tooltip_fields += value_options
        tooltip_aliases += ["Serangan (Ha):", "Pengendalian (Ha):", "Puso (Ha):"]
    else:
        if "Serangan" in value_filter:
            tooltip_fields.append("Serangan")
            tooltip_aliases.append("Serangan (Ha):")
        if "Pengendalian" in value_filter:
            tooltip_fields.append("Pengendalian")
            tooltip_aliases.append("Pengendalian (Ha):")
        if "Puso" in value_filter:
            tooltip_fields.append("Puso")
            tooltip_aliases.append("Puso (Ha):")

    # ---------------- Peta (full width, tanpa frame putih) ----------------
    m = folium.Map(location=[-7.45, 112.7], zoom_start=10)
    folium.GeoJson(
        merged,
        name="Data Desa",
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=tooltip_fields,
            aliases=tooltip_aliases,
            localize=True
        )
    ).add_to(m)

    # bungkus iframe map agar 100% lebar container
    st.markdown('<div class="map-wrap">', unsafe_allow_html=True)
    st_folium(m, height=650, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.info("⬆ Silakan upload file data terlebih dahulu.")
