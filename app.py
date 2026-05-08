import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px

# --- 0. CẤU HÌNH GIAO DIỆN & CHẾ ĐỘ SÁNG/TỐI ---
st.set_page_config(page_title="JSON Data Pro - Theme Toggle", layout="wide") [cite: 1]

# Tạo nút chuyển đổi ở Sidebar
with st.sidebar: 
    st.header("🎨 Giao diện") 
    dark_mode = st.toggle("Chế độ Tối (Dark Mode)", value=True)

# Thiết lập màu sắc dựa trên chế độ được chọn [cite: 2]
if dark_mode:
    bg_color, text_color, sidebar_bg = "#0E1117", "#FAFAFA", "#161b22" [cite: 2]
    upload_label_color, dropzone_bg, dropzone_text = "#ffffff", "#161b22", "#ffffff" [cite: 2]
    plotly_template = "plotly_dark" [cite: 2]
else:
    bg_color, text_color, sidebar_bg = "#FFFFFF", "#31333F", "#F0F2F6" [cite: 2]
    upload_label_color, dropzone_bg, dropzone_text = "#31333F", "#f9f9f9", "#31333F" [cite: 2]
    plotly_template = "plotly" [cite: 2]

# Inject CSS tùy biến [cite: 3]
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg}; border-right: 1px solid #30363d; }}
    [data-testid="stFileUploader"] label p {{ color: {upload_label_color} !important; font-weight: bold !important; }}
    [data-testid="stFileUploaderDropzone"] {{
        background-color: {dropzone_bg} !important;
        border: 3px dashed #00d4ff !important;
        border-radius: 12px;
    }}
    h1, h2, h3 {{ color: {text_color} !important; }}
    </style>
    """, unsafe_allow_html=True) [cite: 3, 4, 6, 8]

st.title("📊 Công cụ Phân tích Dữ liệu Quan trắc") [cite: 14]

# --- 1. CÁC HÀM XỬ LÝ DỮ LIỆU ---
@st.cache_data
def normalize_keys(data): [cite: 15]
    if isinstance(data, list): return [normalize_keys(item) for item in data]
    elif isinstance(data, dict): return {str(k).strip(): normalize_keys(v) for k, v in data.items()}
    return data

@st.cache_data
def flatten_json(y): [cite: 15]
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
def load_and_process_data(file_bytes): [cite: 16]
    raw_data = json.loads(file_bytes) [cite: 16]
    if isinstance(raw_data, dict): raw_data = [raw_data] [cite: 16]
    clean_json = normalize_keys(raw_data) [cite: 16]
    flat_list = [flatten_json(item) for item in clean_json] [cite: 16]
    df = pd.DataFrame(flat_list) [cite: 16]
    
    time_col = None
    for col in df.columns:
        if any(key in col.lower() for key in ['thời gian', 'time']): [cite: 16]
            time_col = col 
            # FIX: Xử lý lỗi Mixed Timezones và định dạng thời gian
            df[col] = pd.to_datetime(df[col].astype(str), errors='coerce', utc=True) [cite: 16]
            df[col] = df[col].dt.tz_localize(None) 
            break
            
    for col in df.columns:
        if col != time_col: 
            # FIX: Đảm bảo errors là giá trị hợp lệ ('coerce' thay vì 'ignore' nếu cần ép kiểu số sạch)
            df[col] = pd.to_numeric(df[col], errors='coerce') [cite: 17]
    return df, time_col

# --- 2. GIAO DIỆN UPLOAD (SIDEBAR) ---
with st.sidebar: [cite: 17]
    st.markdown("---")
    uploaded_file = st.file_uploader("TẢI LÊN FILE JSON QUAN TRẮC", type=['json']) [cite: 17]

# --- 3. HIỂN THỊ DỮ LIỆU ---
if uploaded_file is not None: [cite: 18]
    try:
        df, time_col = load_and_process_data(uploaded_file.getvalue()) [cite: 18]
        stt_col = next((c for c in df.columns if 'stt' in c.lower()), None) [cite: 18]
        
        if stt_col: [cite: 18]
            stt_list = sorted(df[stt_col].dropna().unique().astype(str)) [cite: 18]
            selected_stt = st.sidebar.selectbox("Chọn Mã thiết bị (STT):", stt_list) [cite: 18]
            df_filtered = df[df[stt_col].astype(str) == selected_stt] [cite: 18]
        else:
            df_filtered = df

        if time_col and not df_filtered.empty: [cite: 19]
            st.subheader(f"📈 Biểu đồ thông số") [cite: 19]
            numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist() [cite: 19]
            if stt_col in numeric_cols: numeric_cols.remove(stt_col) [cite: 19]
            
            selected_metrics = st.multiselect("Chọn thông số:", numeric_cols, default=numeric_cols[:2] if len(numeric_cols) > 1 else numeric_cols) [cite: 19]

            if selected_metrics: [cite: 20]
                fig = px.line(df_filtered, x=time_col, y=selected_metrics, template=plotly_template, markers=True) [cite: 20]
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)') [cite: 20]
                st.plotly_chart(fig, use_container_width=True) [cite: 20]
                with st.expander("Xem bảng dữ liệu"): [cite: 20]
                    st.dataframe(df_filtered, use_container_width=True) [cite: 20]
            else:
                st.warning("Vui lòng chọn ít nhất một thông số.") [cite: 21]
        else:
            st.error("Không tìm thấy cột thời gian hợp lệ hoặc dữ liệu trống.")
    except Exception as e:
        st.error(f"Lỗi: {e}") [cite: 21]
else:
    st.info("👈 Hãy tải file JSON ở thanh bên trái để bắt đầu!") [cite: 21]
