import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px

# --- 0. CẤU HÌNH GIAO DIỆN TỐI & TÙY CHỈNH NÚT UPLOAD ---
st.set_page_config(page_title="JSON Data Pro - Custom Upload", layout="wide")

st.markdown("""
    <style>
    /* Nền chính của app (Dark Mode) */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    /* Tùy chỉnh Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* --- SỬA LẠI KHUNG UPLOAD CHUẨN XÁC --- */
    
    /* 1. Nhãn Tiêu đề bên ngoài (Tải lên file...) - Nằm giữa, chữ trắng để dễ nhìn trên nền tối */
    [data-testid="stFileUploader"] label {
        display: block;
        text-align: center !important;
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
        margin-bottom: 10px !important;
    }

    /* 2. Khung kéo thả (Dropzone) - Nền tối, Viền Cyan nét đứt */
    [data-testid="stFileUploaderDropzone"] {
        background-color: #161b22 !important;  /* NỀN TỐI */
        border: 2px dashed #00d4ff !important; /* VIỀN CYAN */
        border-radius: 12px;
        padding: 20px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
    }

    /* 3. Phần CHỮ bên trong khung (Drag and drop...) - Chữ đen, Nền trắng, In đậm, Căn giữa */
    [data-testid="stFileUploaderDropzone"] section div div span,
    [data-testid="stFileUploaderDropzone"] small {
        background-color: #FFFFFF !important; /* NỀN TRẮNG CHỈ CHO CHỮ */
        color: #000000 !important;            /* CHỮ ĐEN */
        font-weight: bold !important;         /* IN ĐẬM */
        padding: 4px 10px;
        border-radius: 5px;
        display: inline-block;
        margin-bottom: 5px;
    }
    
    /* 4. Nút Browse files (Nút bấm tải file) - Chữ đen, nền trắng */
    [data-testid="stFileUploaderDropzone"] button {
        background-color: #FFFFFF !important; /* Nền trắng */
        color: #000000 !important;            /* Chữ đen */
        font-weight: bold !important;         /* In đậm */
        border: 2px solid #000000 !important; /* Viền đen cho nút */
        margin: 10px auto 0 auto;
        display: block;
    }

    /* Các tiêu đề khác vẫn giữ chữ trắng */
    h1, h2, h3, p {
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Công cụ Phân tích Dữ liệu Quan trắc")

# --- 1. CÁC HÀM XỬ LÝ DỮ LIỆU ---
@st.cache_data
def normalize_keys(data):
    if isinstance(data, list): return [normalize_keys(item) for item in data]
    elif isinstance(data, dict): return {str(k).strip().lower(): normalize_keys(v) for k, v in data.items()}
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
    
    time_col = None
    for col in df.columns:
        if 'thời gian' in col.lower() or 'time' in col.lower():
            time_col = col
            df[col] = pd.to_datetime(df[col].astype(str).str.replace('-', ':').str.replace(' ', 'T'), errors='coerce')
            break
            
    for col in df.columns:
        if col != time_col: df[col] = pd.to_numeric(df[col], errors='ignore')
    return df, time_col

# --- 2. GIAO DIỆN SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Cấu hình")
    uploaded_file = st.file_uploader("TẢI LÊN FILE JSON QUAN TRẮC", type=['json'])

# --- 3. HIỂN THỊ DỮ LIỆU ---
if uploaded_file is not None:
    try:
        df, time_col = load_and_process_data(uploaded_file.getvalue())
        stt_col = next
