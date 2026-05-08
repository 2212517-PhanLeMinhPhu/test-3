import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px
import unicodedata

# --- 0. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="JSON Data Pro", layout="wide")

with st.sidebar:
    st.header("🎨 Giao diện")
    dark_mode = st.toggle("Chế độ Tối (Dark Mode)", value=True)

if dark_mode:
    bg_color, text_color, sidebar_bg, upload_label_color, dropzone_bg, dropzone_text, plotly_template = "#0E1117", "#FAFAFA", "#161b22", "#ffffff", "#161b22", "#ffffff", "plotly_dark"
else:
    bg_color, text_color, sidebar_bg, upload_label_color, dropzone_bg, dropzone_text, plotly_template = "#FFFFFF", "#31333F", "#F0F2F6", "#31333F", "#f9f9f9", "#31333F", "plotly"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg}; border-right: 1px solid #30363d; }}
    [data-testid="stFileUploader"] label {{ display: flex !important; width: 100% !important; justify-content: center !important; margin-bottom: 5px !important; }}
    [data-testid="stFileUploader"] label p {{ color: {upload_label_color} !important; font-weight: bold !important; font-size: 1.1rem !important; text-align: center !important; margin: 0 !important; }}
    [data-testid="stFileUploaderDropzone"] {{ background-color: {dropzone_bg} !important; border: 3px dashed #00d4ff !important; border-radius: 12px; padding: 30px 20px; text-align: center !important; }}
    [data-testid="stFileUploaderDropzone"] div, [data-testid="stFileUploaderDropzone"] span, [data-testid="stFileUploaderDropzone"] small {{ color: {dropzone_text} !important; font-weight: bold !important; text-align: center !important; width: 100%; display: block; }}
    [data-testid="stFileUploaderDropzone"] button {{ background-color: #00d4ff !important; color: #000000 !important; font-weight: bold !important; border: none !important; border-radius: 8px; padding: 8px 20px; margin-top: 15px !important; display: inline-block; }}
    h1, h2, h3 {{ color: {text_color} !important; }}
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Công cụ Phân tích Dữ liệu Quan trắc")

# --- 1. XỬ LÝ DỮ LIỆU CỐT LÕI ---
@st.cache_data
def parse_json_data(file_bytes):
    raw_data = json.loads(file_bytes)
    df = pd.json_normalize(raw_data)
    
    # Chuẩn hóa tên cột
    df.columns = [unicodedata.normalize('NFC', str(c)).strip().lower() for c in df.columns]
    
    # --- ĐÃ FIX LỖI Ở ĐÂY ---
    # Lọc bỏ các cột trùng tên phát sinh do quá trình đưa về chữ thường
    # Giữ lại cột xuất hiện đầu tiên, xóa các cột bị trùng tên phía sau
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    # Bỏ các cột hệ thống (như _id.$oid)
    cols_to_drop = [c for c in df.columns if '_id' in c]
    df.drop(columns=cols_to_drop, inplace=True, errors='ignore')
    
    time_col = None
    stt_col = None
    
    # Xác định cột thời gian và thiết bị
    for col in df.columns:
        if 'thời gian' in col or 'time' in col or 'tg' in col:
            time_col = col
            break # Tìm thấy cột khớp thì dừng, tránh chọn nhầm cột khác
            
    for col in df.columns:
        if 'stt' in col:
            stt_col = col
            break
            
    # Xử lý thời gian (Đã bao gồm xử lý Mix Timezones)
    if time_col:
        df[time_col] = pd.to_datetime(df[time_col], errors='coerce', utc=True)
        try:
            df[time_col] = df[time_col].dt.tz_convert('Asia/Ho_Chi_Minh')
        except Exception:
            pass 
            
        df.dropna(subset=[time_col], inplace=True)
        
    # Xử lý STT
    if stt_col:
        df[stt_col] = df[stt_col].astype(str).str.replace(r'\.0$', '', regex=True)
        
    # Ép kiểu dữ liệu số
    for col in df.columns:
        if col != time_col and col != stt_col:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    # Xóa các cột rỗng (Toàn NaN)
    df.dropna(axis=1, how='all', inplace=True)
    
    return df, time_col, stt_col

# --- 2. GIAO DIỆN UPLOAD ---
with st.sidebar:
    st.markdown("---")
    uploaded_file = st.file_uploader("TẢI LÊN FILE JSON QUAN TRẮC", type=['json'])

# --- 3. HIỂN THỊ DỮ LIỆU ---
if uploaded_file is not None:
    try:
        with st.spinner("Đang phân tích dữ liệu... Vui lòng đợi nhé!"):
            df, time_col, stt_col = parse_json_data(uploaded_file.getvalue())
            
        if stt_col and not df[stt_col].empty:
            stt_list = sorted(df[stt_col].dropna().unique().tolist())
            selected_stt = st.sidebar.selectbox("Chọn Mã thiết bị (STT):", stt_list)
            df_filtered = df[df[stt_col] == selected_stt]
        else:
            df_filtered = df

        if time_col and not df_filtered.empty:
            st.subheader("📈 Biểu đồ thông số")
            
            numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
            if time_col in numeric_cols: numeric_cols.remove(time_col)
            if stt_col in numeric_cols: numeric_cols.remove(stt_col)
            
            selected_metrics = st.multiselect("Chọn thông số:", numeric_cols, default=numeric_cols[:2] if len(numeric_cols) > 1 else numeric_cols)

            if selected_metrics:
                fig = px.line(df_filtered, x=time_col, y=selected_metrics, template=plotly_template, markers=True)
                
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis_title="Thời gian",
                    yaxis_title="Giá trị",
                    hovermode="x unified"
                )
                fig.update_xaxes(showspikes=True, spikecolor="gray", spikesnap="cursor", spikemode="across")
                fig.update_yaxes(showspikes=True, spikecolor="gray", spikemode="across")
                
                st.plotly_chart(fig, use_container_width=True)
                with st.expander("Xem bảng dữ liệu chi tiết"):
                    st.dataframe(df_filtered, use_container_width=True)
            else:
                st.warning("Vui lòng chọn ít nhất một thông số.")
        else:
            st.error("Không tìm thấy dữ liệu thời gian hợp lệ hoặc file đang trống.")
    except Exception as e:
        st.error(f"Đã xảy ra sự cố ngoài ý muốn: {e}")
        st.info("Vui lòng chụp màn hình nếu dòng màu đỏ này vẫn xuất hiện!")
else:
    st.info("👈 Hãy tải file JSON ở thanh bên trái để bắt đầu!")
