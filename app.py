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
    
    /* 1. Nhãn Tiêu đề bên ngoài (Tải lên file...) */
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
        background-color: #161b22 !important;  
        border: 2px dashed #00d4ff !important; 
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
        background-color: #FFFFFF !important; 
        color: #000000 !important;            
        font-weight: bold !important;         
        padding: 4px 10px;
        border-radius: 5px;
        display: inline-block;
        margin-bottom: 5px;
    }
    
    /* 4. Nút Browse files */
    [data-testid="stFileUploaderDropzone"] button {
        background-color: #FFFFFF !important; 
        color: #000000 !important;            
        font-weight: bold !important;         
        border: 2px solid #000000 !important; 
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
    # ĐÃ SỬA: Không dùng .lower() nữa để giữ nguyên tên cột (Thời gian, STT,...)
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
    # Tìm cột thời gian không phân biệt hoa thường
    for col in df.columns:
        if 'thời gian' in col.lower() or 'time' in col.lower():
            time_col = col # Giữ đúng định dạng tên gốc (VD: "Thời gian")
            df[col] = pd.to_datetime(df[col].astype(str).str.replace('-', ':').str.replace(' ', 'T'), errors='coerce')
            break
            
    # Ép kiểu dữ liệu số cho các cột còn lại
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
        
        # Tìm cột STT một cách linh hoạt
        stt_col = next((c for c in df.columns if 'stt' in c.lower()), None)
        
        if stt_col:
            stt_list = sorted(df[stt_col].dropna().unique().astype(str))
            selected_stt = st.sidebar.selectbox("Chọn Mã thiết bị (STT):", stt_list)
            df_filtered = df[df[stt_col].astype(str) == selected_stt]
        else:
            df_filtered = df

        if time_col and not df_filtered.empty:
            st.subheader(f"📈 Biểu đồ thông số")
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
                st.warning("Vui lòng chọn ít nhất một thông số để hiển thị.")
        else:
            st.error("Dữ liệu không có thông tin thời gian hợp lệ.")
            
    except Exception as e:
        st.error(f"Lỗi: {e}")
else:
    st.info("👈 Hãy tải file JSON ở thanh bên trái để bắt đầu!")
