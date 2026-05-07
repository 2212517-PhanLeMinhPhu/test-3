import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import plotly.express as px

# --- 0. CẤU HÌNH GIAO DIỆN TỐI & LÀM NỔI BẬT PHẦN UPLOAD ---
st.set_page_config(page_title="JSON Data Pro - Dark Mode Enhanced", layout="wide")

st.markdown("""
    <style>
    /* Nền chính của app */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    /* Tùy chỉnh Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* --- PHẦN SỬA ĐỔI CHÍNH: LÀM NỔI BẬT UPLOAD FILE --- */
    [data-testid="stFileUploader"] {
        background-color: #1f2937; /* Nền xám xanh đậm hơn để tách biệt */
        padding: 15px;
        border-radius: 12px;
        border: 2px dashed #00d4ff; /* Viền nét đứt màu Cyan sáng */
        margin-bottom: 20px;
    }
    
    /* Làm nổi bật chữ "Chọn file JSON..." (Label) */
    [data-testid="stFileUploader"] label {
        color: #ffcc00 !important; /* Màu vàng sáng cực kỳ dễ nhìn */
        font-weight: bold !important;
        font-size: 1.1rem !important;
        margin-bottom: 10px;
    }
    
    /* Chỉnh màu chữ hướng dẫn bên trong (Drag and drop...) */
    [data-testid="stFileUploader"] section div div {
        color: #ffffff !important;
    }
    
    /* Hiệu ứng khi di chuột vào vùng upload */
    [data-testid="stFileUploader"]:hover {
        border-color: #ffcc00; /* Đổi viền sang vàng khi rê chuột */
        transition: 0.3s;
    }
    /* -------------------------------------------------- */

    /* Màu chữ tiêu đề và các phần khác */
    h1, h2, h3, p, span {
        color: #ffffff !important;
    }
    
    /* Nút bấm (Sidebar) */
    .stButton>button {
        width: 100%;
        background-color: #00d4ff;
        color: #000000;
        font-weight: bold;
        border-radius: 8px;
        border: none;
    }
    .stButton>button:hover {
        background-color: #ffcc00;
        color: #000000;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Công cụ Phân tích Dữ liệu Quan trắc")

# --- 1. CÁC HÀM XỬ LÝ DỮ LIỆU (Giữ nguyên từ code cũ của bạn) ---
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
    uploaded_file = st.file_uploader("Tải lên file JSON quan trắc", type=['json'])

# --- 3. HIỂN THỊ DỮ LIỆU ---
if uploaded_file is not None:
    try:
        df, time_col = load_and_process_data(uploaded_file.getvalue())
        
        stt_col = next((c for c in df.columns if 'stt' in c.lower()), None)
        
        if stt_col:
            stt_list = sorted(df[stt_col].unique().astype(str))
            selected_stt = st.sidebar.selectbox("Chọn Mã thiết bị (STT):", stt_list)
            df_filtered = df[df[stt_col].astype(str) == selected_stt]
        else:
            df_filtered = df
            st.sidebar.warning("Không tìm thấy cột STT.")

        if time_col and not df_filtered.empty:
            st.subheader(f"📈 Biểu đồ thông số - Thiết bị {selected_stt if stt_col else ''}")
            
            numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
            if stt_col in numeric_cols: numeric_cols.remove(stt_col)
            
            selected_metrics = st.multiselect("Chọn thông số:", numeric_cols, default=numeric_cols[:2] if len(numeric_cols) > 1 else numeric_cols)

            if selected_metrics:
                fig = px.line(
                    df_filtered, x=time_col, y=selected_metrics,
                    template="plotly_dark", markers=True
                )
                fig.update_layout(
                    hovermode="x unified",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("Xem chi tiết bảng dữ liệu"):
                    st.dataframe(df_filtered, use_container_width=True)
        else:
            st.error("Dữ liệu không có thông tin thời gian hợp lệ.")
    except Exception as e:
        st.error(f"Lỗi: {e}")
else:
    st.info("👈 Hãy bắt đầu bằng cách tải file JSON ở thanh bên trái!")
