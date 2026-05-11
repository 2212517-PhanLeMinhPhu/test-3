import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px

# --- 0. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="JSON Data Pro", layout="wide", page_icon="📊")

with st.sidebar:
    st.header("🎨 Giao diện")
    dark_mode = st.toggle("Chế độ Tối", value=True)

if dark_mode:
    bg_color, text_color, sidebar_bg = "#0E1117", "#FAFAFA", "#161b22"
    plotly_template = "plotly_dark"
    grid_color = "rgba(255, 255, 255, 0.1)"
else:
    bg_color, text_color, sidebar_bg = "#FFFFFF", "#31333F", "#F0F2F6"
    plotly_template = "plotly"
    grid_color = "rgba(0, 0, 0, 0.1)"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg}; border-right: 1px solid #30363d; }}
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
            df[col] = pd.to_datetime(df[col], errors='coerce', utc=True).dt.tz_localize(None)
            break
            
    for col in df.columns:
        if col != time_col: 
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(axis=1, how='all')
    return df, time_col

# --- 2. SIDEBAR UPLOAD ---
with st.sidebar:
    st.markdown("---")
    uploaded_file = st.file_uploader("TẢI LÊN FILE JSON", type=['json'])

# --- 3. HIỂN THỊ DỮ LIỆU ---
if uploaded_file is not None:
    try:
        df, time_col = load_and_process_data(uploaded_file.getvalue())
        
        # BỘ LỌC SIDEBAR
        with st.sidebar:
            st.header("🔍 Bộ lọc")
            stt_col = next((c for c in df.columns if 'stt' in c.lower()), None)
            
            if stt_col:
                stt_list = sorted(df[stt_col].dropna().unique().astype(str))
                selected_stt = st.selectbox("Chọn Mã thiết bị (STT):", stt_list)
                df_filtered = df[df[stt_col].astype(str) == selected_stt].copy()
            else:
                df_filtered = df.copy()

            if time_col and not df_filtered.empty:
                st.markdown("---")
                temp_time = df_filtered[time_col].dropna()
                if not temp_time.empty:
                    min_date, max_date = temp_time.min().date(), temp_time.max().date()
                    date_range = st.date_input("Khoảng thời gian:", value=(min_date, max_date), min_value=min_date, max_value=max_date)
                    
                    if isinstance(date_range, tuple) and len(date_range) == 2:
                        start_date, end_date = date_range
                        mask = (df_filtered[time_col].dt.date >= start_date) & (df_filtered[time_col].dt.date <= end_date)
                        df_filtered = df_filtered.loc[mask]

        # HIỂN THỊ BIỂU ĐỒ
        if time_col and not df_filtered.empty:
            st.subheader("📈 Phân tích thông số")
            df_filtered = df_filtered.dropna(subset=[time_col]).sort_values(by=time_col)
            numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
            if stt_col in numeric_cols: numeric_cols.remove(stt_col)
            
            if numeric_cols:
                selected_metrics = st.multiselect("Chọn thông số:", numeric_cols, default=[numeric_cols[0]])
                if selected_metrics:
                    # Sử dụng render mặc định để tránh lỗi shape
                    fig = px.line(
                        df_filtered, 
                        x=time_col, 
                        y=selected_metrics, 
                        template=plotly_template,
                        markers=True,
                        color_discrete_sequence=px.colors.qualitative.Vivid
                    )
                    
                    # Cấu hình đường nét theo chuẩn linear an toàn
                    fig.update_traces(
                        line=dict(width=2),
                        marker=dict(size=4),
                        connectgaps=True
                    )
                    
                    # Đổ bóng vùng dữ liệu (Fill)
                    if len(selected_metrics) == 1:
                        fig.update_traces(fill='tozeroy', fillalpha=0.15)

                    fig.update_layout(
                        hovermode='x unified',
                        height=600,
                        margin=dict(l=10, r=10, t=50, b=10),
                        xaxis=dict(gridcolor=grid_color, title="Thời gian"),
                        yaxis=dict(gridcolor=grid_color, title="Giá trị"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})
                    
                    with st.expander("📂 Xem dữ liệu chi tiết"):
                        st.dataframe(df_filtered, use_container_width=True)
                        csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
                        st.download_button("📥 Tải CSV", data=csv, file_name="data_filtered.csv", mime="text/csv")
            else:
                st.warning("Không tìm thấy dữ liệu dạng số.")
        else:
            st.error("Không có dữ liệu trong khoảng thời gian được chọn.")

    except Exception as e:
        st.error(f"Lỗi khi xử lý: {e}")
else:
    st.info("👈 Vui lòng tải file JSON ở menu bên trái!")
