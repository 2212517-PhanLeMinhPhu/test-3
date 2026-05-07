import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import plotly.express as px

# --- 0. CẤU HÌNH GIAO DIỆN TỐI (DARK MODE) ---
st.set_page_config(page_title="JSON Data Pro - Dark Mode", layout="wide")

# Inject CSS để ép nền đen và chữ trắng
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
    /* Màu chữ tiêu đề và văn bản */
    h1, h2, h3, p, span, label {
        color: #ffffff !important;
    }
    /* Tùy chỉnh các ô input/bảng */
    .stDataFrame, .stTable {
        background-color: #161b22;
    }
    /* Nút bấm */
    .stButton>button {
        background-color: #238636;
        color: white;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Công cụ Phân tích Dữ liệu (Giao diện Tối)")

# --- 1. TỐI ƯU HÓA HIỆU NĂNG VỚI CACHE ---
@st.cache_data
def normalize_keys(data):
    if isinstance(data, list):
        return [normalize_keys(item) for item in data]
    elif isinstance(data, dict):
        return {str(k).strip().lower(): normalize_keys(v) for k, v in data.items()}
    return data

@st.cache_data
def flatten_json(y):
    out = {}
    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x: 
                flatten(x[a], name + a + '.')
        elif isinstance(x, list):
            i = 0
            for a in x:
                flatten(a, name + str(i) + '.')
                i += 1
        else: 
            out[name[:-1]] = x
    flatten(y)
    return out

@st.cache_data
def load_and_process_data(file_bytes):
    raw_data = json.loads(file_bytes)
    if isinstance(raw_data, dict): 
        raw_data = [raw_data]
    
    # Làm sạch key
    clean_json = normalize_keys(raw_data)
    
    # Làm phẳng dữ liệu và chuyển sang DataFrame
    flat_list = [flatten_json(item) for item in clean_json]
    df = pd.DataFrame(flat_list)
    
    # Xử lý cột thời gian (Tìm cột có chữ 'thời gian' hoặc 'time')
    time_col = None
    for col in df.columns:
        if 'thời gian' in col.lower() or 'time' in col.lower():
            time_col = col
            df[col] = pd.to_datetime(df[col].astype(str).str.replace('-', ':').str.replace(' ', 'T'), errors='coerce')
            break
            
    # Chuyển đổi các cột số
    for col in df.columns:
        if col != time_col:
            df[col] = pd.to_numeric(df[col], errors='ignore')
            
    return df, time_col

# --- 2. GIAO DIỆN TẢI FILE ---
uploaded_file = st.sidebar.file_uploader("Tải lên file JSON quan trắc", type=['json'])

if uploaded_file is not None:
    try:
        df, time_col = load_and_process_data(uploaded_file.getvalue())
        
        # --- 3. BỘ LỌC (STT) ---
        # Tìm cột STT (không phân biệt hoa thường)
        stt_col = next((c for c in df.columns if 'stt' in c.lower()), None)
        
        if stt_col:
            stt_list = sorted(df[stt_col].unique().astype(str))
            selected_stt = st.sidebar.selectbox("Chọn Mã thiết bị (STT):", stt_list)
            df_filtered = df[df[stt_col].astype(str) == selected_stt]
        else:
            df_filtered = df
            st.sidebar.warning("Không tìm thấy cột STT để lọc.")

        # --- 4. VẼ BIỂU ĐỒ ---
        if time_col and not df_filtered.empty:
            st.subheader(f"📈 Biểu đồ thông số - Thiết bị {selected_stt if stt_col else ''}")
            
            # Lấy danh sách các cột là số để vẽ
            numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
            if stt_col in numeric_cols: numeric_cols.remove(stt_col)
            
            selected_metrics = st.multiselect("Chọn thông số hiển thị:", numeric_cols, default=numeric_cols[:2] if len(numeric_cols) > 1 else numeric_cols)

            if selected_metrics:
                # Vẽ biểu đồ với Plotly và Theme tối
                fig = px.line(
                    df_filtered, 
                    x=time_col, 
                    y=selected_metrics,
                    template="plotly_dark", # <--- QUAN TRỌNG: Chuyển biểu đồ sang màu tối
                    labels={time_col: "Thời gian"},
                    markers=True
                )
                
                fig.update_layout(
                    hovermode="x unified",
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend=dict(bgcolor='rgba(0,0,0,0)')
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Hiển thị bảng dữ liệu
                with st.expander("Xem chi tiết bảng dữ liệu"):
                    st.dataframe(df_filtered, use_container_width=True)
            else:
                st.info("Vui lòng chọn ít nhất một thông số để vẽ biểu đồ.")
        else:
            st.error("Dữ liệu không có thông tin thời gian hoặc bị trống.")

    except Exception as e:
        st.error(f"Đã xảy ra lỗi: {e}")
else:
    st.info("👋 Vui lòng tải file JSON ở thanh bên trái để bắt đầu.")
