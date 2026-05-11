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
    
    df.columns = df.columns.str.strip().str.capitalize()
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    
    time_col = None
    for col in df.columns:
        if any(k in col.lower() for k in ['thời gian', 'time']):
            time_col = col 
            df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize(None)
            break
            
    for col in df.columns:
        if col != time_col: 
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df.dropna(axis=1, how='all'), time_col

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

            # 2. LỌC THEO NGÀY/THÁNG/NĂM (MỚI THÊM)
            if time_col and not df_filtered.empty:
                st.markdown("---")
                min_date = df_filtered[time_col].min().date()
                max_date = df_filtered[time_col].max().date()
                
                # Bộ chọn khoảng ngày (bao quát cả ngày, tháng, năm)
                date_range = st.date_input(
                    "Chọn khoảng thời gian:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                
                # Áp dụng bộ lọc thời gian
                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_date, end_date = date_range
                    mask = (df_filtered[time_col].dt.date >= start_date) & (df_filtered[time_col].dt.date <= end_date)
                    df_filtered = df_filtered.loc[mask]

        # --- HIỂN THỊ BIỂU ĐỒ ---
        if time_col and not df_filtered.empty:
            st.subheader("📈 Phân tích thông số quan trắc")
            
            df_filtered = df_filtered.dropna(subset=[time_col]).sort_values(by=time_col)
            numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
            if stt_col in numeric_cols: numeric_cols.remove(stt_col)
            
            if not numeric_cols:
                st.warning("Không tìm thấy dữ liệu dạng số.")
            else:
                selected_metrics = st.multiselect(
                    "Chọn thông số cần xem:", 
                    numeric_cols, 
                    default=[numeric_cols[0]] if numeric_cols else None
                )

                if selected_metrics:
                    fig = px.line(
                        df_filtered, 
                        x=time_col, 
                        y=selected_metrics, 
                        template=plotly_template,
                        markers=True # Thêm điểm mốc để dễ nhìn dữ liệu rời rạc
                    )
                    
                    fig.update_layout(
                        hovermode='x unified',
                        xaxis_title="Thời gian",
                        yaxis_title="Giá trị",
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("📂 Xem chi tiết bảng dữ liệu đã lọc"):
                        st.dataframe(df_filtered, use_container_width=True)
                else:
                    st.info("💡 Hãy chọn ít nhất một thông số ở trên để vẽ biểu đồ.")
        else:
            st.error("Không có dữ liệu trong khoảng thời gian đã chọn.")

    except Exception as e:
        st.error(f"Lỗi khi xử lý dữ liệu: {e}")
else:
    st.info("👈 Hãy tải file JSON ở thanh bên trái để bắt đầu phân tích!")
