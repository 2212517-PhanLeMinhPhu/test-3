import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px

# --- 0. CẤU HÌNH GIAO DIỆN & CHẾ ĐỘ SÁNG/TỐI ---
st.set_page_config(page_title="JSON Data Pro - Analytical", layout="wide", page_icon="📊")

# Tạo nút chuyển đổi ở Sidebar
with st.sidebar:
    st.header("🎨 Giao diện")
    dark_mode = st.toggle("Chế độ Tối (Dark Mode)", value=True)

# Thiết lập màu sắc dựa trên chế độ được chọn
if dark_mode:
    bg_color, text_color, sidebar_bg = "#0E1117", "#FAFAFA", "#161b22"
    accent_color = "#00d4ff"
    plotly_template = "plotly_dark"
else:
    bg_color, text_color, sidebar_bg = "#FFFFFF", "#31333F", "#F0F2F6"
    accent_color = "#007BFF"
    plotly_template = "plotly"

# Inject CSS tùy biến
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg}; border-right: 1px solid #30363d; }}
    [data-testid="stFileUploaderDropzone"] {{ border: 2px dashed {accent_color} !important; border-radius: 12px; }}
    h1, h2, h3 {{ color: {text_color} !important; }}
    .stMetric {{ background-color: {sidebar_bg}; padding: 10px; border-radius: 10px; border: 1px solid {accent_color}33; }}
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Công cụ Phân tích Dữ liệu Quan trắc")

# --- 1. CÁC HÀM XỬ LÝ DỮ LIỆU ---
@st.cache_data
def normalize_keys(data):
    if isinstance(data, list): return [normalize_keys(item) for item in data]
    elif isinstance(data, dict): return {str(k).strip(): normalize_keys(v) for k, v in data.items()}
    return data

@st.cache_data
def flatten_json(y):
    out = {}
    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x: flatten(x[a], name + a + '.')
        elif isinstance(x, list):
            for i, a in enumerate(x): flatten(a, name + str(i) + '.')
        else: out[name[:-1]] = x
    flatten(y)
    return out

@st.cache_data
def load_and_process_data(file_bytes):
    raw_data = json.loads(file_bytes)
    if isinstance(raw_data, dict): raw_data = [raw_data]
    clean_json = normalize_keys(raw_data)
    flat_list = [flatten_json(item) for item in clean_json]
    df = pd.DataFrame(flat_list)
    
    # Chuẩn hóa tên cột
    df.columns = df.columns.str.strip().str.capitalize()
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    
    time_col = None
    for col in df.columns:
        if any(k in col.lower() for k in ['thời gian', 'time']):
            time_col = col 
            # FIX LỖI MIXED TIMEZONES: ép về UTC sau đó gỡ múi giờ (localize None)
            df[col] = pd.to_datetime(df[col], errors='coerce', utc=True).dt.tz_localize(None)
            break
            
    for col in df.columns:
        if col != time_col: 
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Loại bỏ cột trống hoàn toàn
    df = df.dropna(axis=1, how='all')
    return df, time_col

# --- 2. GIAO DIỆN UPLOAD (SIDEBAR) ---
with st.sidebar:
    st.markdown("---")
    uploaded_file = st.file_uploader("TẢI LÊN FILE JSON QUAN TRẮC", type=['json'])

# --- 3. HIỂN THỊ DỮ LIỆU ---
if uploaded_file is not None:
    try:
        df, time_col = load_and_process_data(uploaded_file.getvalue())
        
        # --- BỘ LỌC SIDEBAR ---
        with st.sidebar:
            st.header("🔍 Bộ lọc dữ liệu")
            
            # 1. Lọc theo STT (Mã thiết bị)
            stt_col = next((c for c in df.columns if 'stt' in c.lower()), None)
            if stt_col:
                stt_list = sorted(df[stt_col].dropna().unique().astype(str))
                selected_stt = st.selectbox("Chọn Mã thiết bị (STT):", stt_list)
                df_filtered = df[df[stt_col].astype(str) == selected_stt].copy()
            else:
                df_filtered = df.copy()

            # 2. Lọc theo Khoảng ngày (Ngày/Tháng/Năm)
            if time_col and not df_filtered.empty:
                st.markdown("---")
