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
    
    /* --- CẤU HÌNH KHUNG UPLOAD CHUẨN TRUNG TÂM --- */
    
    /* 1. Nhãn Tiêu đề bên ngoài - Căn giữa tuyệt đối & Đổi màu TRẮNG */
    [data-testid="stFileUploader"] label {
        display: flex !important;
        width: 100% !important;
        justify-content: center !important;
        margin-bottom: 5px !important;
    }
    
    [data-testid="stFileUploader"] label p {
        color: #ffffff !important; 
        font-weight: bold !important;
        font-size: 1.1rem !important;
        text-align: center !important;
        margin: 0 !important;
    }

    /* 2. Khung kéo thả (Dropzone) - Nền TỐI, Viền Cyan, Căn giữa */
    [data-testid="stFileUploaderDropzone"] {
        background-color: #161b22 !important;  /* Trả lại nền tối để chữ trắng nổi bật */
        border: 3px dashed #00d4ff !important; 
        border-radius: 12px;
        padding: 30px 20px;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;     
        justify-content: center !important;  
        text-align: center !important;
    }

    /* 3. Chữ bên trong khung - Màu TRẮNG, In đậm, Căn giữa */
    [data-testid="stFileUploaderDropzone"] div, 
    [data-testid="stFileUploaderDropzone"] span, 
    [data-testid="stFileUploaderDropzone"] small {
        color: #ffffff !important;    /* Đã đổi sang màu TRẮNG theo yêu cầu */
        font-weight: bold !important; 
        text-align: center !important;
        width: 100%;
        display: block;
    }
    
    /* 4. Nút bấm Browse files - Căn giữa, nền Cyan, CHỮ ĐEN */
    [data-testid="stFileUploaderDropzone"] button {
        background-color: #00d4ff !important; 
        color: #000000 !important;            
        font-weight: bold !important;         
        border: none !important; 
        border-radius: 8px;
        padding: 8px 20px;
        margin-top: 15px !important;
        display: inline-block;
    }

    /* Giữ màu trắng cho các thành phần tiêu đề khác */
    h1, h2, h3 { color: #ffffff !important; }
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
        stt_col = next((c for c in df.columns if 'stt' in c.lower()), None)
        
        if stt_col:
            stt_list = sorted(df[stt_col].dropna().unique().astype(str))
            selected_stt = st.sidebar.selectbox("Chọn Mã thiết bị (STT):", stt_list)
            df_filtered = df[df[stt_col].astype(str) == selected_stt]
        else:
            df_filtered = df

        if time_col and not df_filtered.empty:
            st.subheader(f"📈 Biểu đồ thông số cho thiết bị {selected_stt if stt_col else ''}")
            numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
            if stt_col in numeric_cols: numeric_cols.remove(stt_col)
            
            selected_metrics = st.multiselect("Chọn thông số:", numeric_cols, default=numeric_cols[:2] if len(numeric_cols) > 1 else numeric_cols)

            if selected_metrics:
                fig = px.line(df_filtered, x=time_col, y=selected_metrics, template="plotly_dark", markers=True)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Xem bảng dữ liệu"):
                    st.dataframe(df_filtered, use_container_width=True)
            else:
                st.warning("Vui lòng chọn ít nhất một thông số.")
    except Exception as e:
        st.error(f"Lỗi: {e}")
else:
    st.info("👈 Hãy tải file JSON ở thanh bên trái để bắt đầu!")
