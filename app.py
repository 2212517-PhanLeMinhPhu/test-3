import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px

# --- 0. CẤU HÌNH GIAO DIỆN & CHẾ ĐỘ SÁNG/TỐI ---
st.set_page_config(page_title="JSON Data Pro - Theme Toggle", layout="wide")

# Tạo nút chuyển đổi ở Sidebar
with st.sidebar:
    st.header("🎨 Giao diện")
    dark_mode = st.toggle("Chế độ Tối (Dark Mode)", value=True)

# Thiết lập màu sắc dựa trên chế độ được chọn
if dark_mode:
    bg_color = "#0E1117"
    text_color = "#FAFAFA"
    sidebar_bg = "#161b22"
    upload_label_color = "#ffffff"
    dropzone_bg = "#161b22"
    dropzone_text = "#ffffff"
    plotly_template = "plotly_dark"
else:
    bg_color = "#FFFFFF"
    text_color = "#31333F"
    sidebar_bg = "#F0F2F6"
    upload_label_color = "#31333F"
    dropzone_bg = "#f9f9f9"
    dropzone_text = "#31333F"
    plotly_template = "plotly"

# Inject CSS tùy biến theo Theme
st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg}; border-right: 1px solid #30363d; }}
    [data-testid="stFileUploader"] label {{ display: flex !important; width: 100% !important; justify-content: center !important; margin-bottom: 5px !important; }}
    [data-testid="stFileUploader"] label p {{ color: {upload_label_color} !important; font-weight: bold !important; font-size: 1.1rem !important; text-align: center !important; margin: 0 !important; }}
    [data-testid="stFileUploaderDropzone"] {{ background-color: {dropzone_bg} !important; border: 3px dashed #00d4ff !important; border-radius: 12px; padding: 30px 20px; display: flex !important; flex-direction: column !important; align-items: center !important; justify-content: center !important; text-align: center !important; }}
    [data-testid="stFileUploaderDropzone"] div, [data-testid="stFileUploaderDropzone"] span, [data-testid="stFileUploaderDropzone"] small {{ color: {dropzone_text} !important; font-weight: bold !important; text-align: center !important; width: 100%; display: block; }}
    [data-testid="stFileUploaderDropzone"] button {{ background-color: #00d4ff !important; color: #000000 !important; font-weight: bold !important; border: none !important; border-radius: 8px; padding: 8px 20px; margin-top: 15px !important; display: inline-block; }}
    h1, h2, h3 {{ color: {text_color} !important; }}
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
    
    # Chuẩn hóa tên cột và LOẠI BỎ CỘT TRÙNG LẶP (Fix lỗi 'Nhiệt độ' 2 times)
    df.columns = df.columns.str.strip().str.capitalize()
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    
    time_col = None
    for col in df.columns:
        if 'thời gian' in col.lower() or 'time' in col.lower():
            time_col = col 
            # Dùng utc=True để fix lỗi Mixed Timezones
            df[col] = pd.to_datetime(df[col].astype(str).str.replace('-', ':').str.replace(' ', 'T'), errors='coerce', utc=True)
            df[col] = df[col].dt.tz_localize(None) 
            break
            
    for col in df.columns:
        if col != time_col: 
            # Dùng errors='coerce' thay vì 'ignore' để fix lỗi invalid error value
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df, time_col

# --- 2. GIAO DIỆN UPLOAD (SIDEBAR) ---
with st.sidebar:
    st.markdown("---")
    uploaded_file = st.file_uploader("TẢI LÊN FILE JSON QUAN TRẮC", type=['json'])

# --- 3. HIỂN THỊ DỮ LIỆU ---
if uploaded_file is not None:
    try:
        df, time_col = load_and_process_data(uploaded_file.getvalue())
        stt_col = next((c for c in df.columns if 'stt' in c.lower()), None)
        
        if stt_col:
            stt_list = sorted(df[stt_col].dropna().unique().astype(str))
            selected_stt = st.sidebar.selectbox("Chọn Mã thiết bị (STT):", stt_list)
            df_filtered = df[df[stt_col].astype(str) == selected_stt].copy()
        else:
            df_filtered = df.copy()

        if time_col and not df_filtered.empty:
            st.subheader("📈 Biểu đồ thông số")
            
            # Sắp xếp thời gian để biểu đồ không bị rối (Fix mạng nhện)
            df_filtered = df_filtered.sort_values(by=time_col, ascending=True)
            
            numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
            if stt_col in numeric_cols: numeric_cols.remove(stt_col)
            
            # Chỉ mặc định 1 thông số đầu tiên để không bị lệch thang đo (Fix lỗi biểu đồ loạn)
            selected_metrics = st.multiselect(
                "Chọn thông số:", 
                numeric_cols, 
                default=[numeric_cols[0]] if numeric_cols else None
            )

            if selected_metrics:
                # Vẽ biểu đồ với Plotly
                fig = px.line(
                    df_filtered, 
                    x=time_col, 
                    y=selected_metrics, 
                    template=plotly_template
                )
                
                # Bo cong mềm mại đường biểu đồ
                fig.update_traces(
                    line_shape='spline',
                    line=dict(width=2.5)
                )
                
                fig.update_layout(
                    hovermode='x unified',
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis_title="Thời gian",
                    yaxis_title="Giá trị",
                    legend=dict(
                        title="", 
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.05, 
                        xanchor="right", 
                        x=1
                    )
                )
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("Xem bảng dữ liệu"):
                    st.dataframe(df_filtered, use_container_width=True)
            else:
                st.warning("Vui lòng chọn ít nhất một thông số.")
        else:
            st.error("Không tìm thấy cột thời gian hợp lệ hoặc dữ liệu trống.")
    except Exception as e:
        st.error(f"Lỗi khi xử lý dữ liệu: {e}")
else:
    st.info("👈 Hãy tải file JSON ở thanh bên trái để bắt đầu!")
