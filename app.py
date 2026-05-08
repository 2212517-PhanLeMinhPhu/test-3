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
    
    # 1. Xóa triệt để _id
    for item in raw_data:
        keys_to_delete = [k for k in item.keys() if '_id' in str(k).lower()]
        for k in keys_to_delete:
            del item[k]

    # 2. Làm phẳng JSON và tạo DataFrame siêu tốc
    flat_list = [flatten_json(item) for item in raw_data]
    df = pd.DataFrame(flat_list)
    
    # === FIX LỖI KEYERROR: ÉP CHUẨN TÊN CỘT ===
    # Đưa tất cả tên cột về: CHỮ THƯỜNG + XÓA DẤU CÁCH THỪA + CHUẨN HÓA UNICODE
    df.columns = [unicodedata.normalize('NFC', str(c)).strip().lower() for c in df.columns]
    
    time_col = None
    
    # 3. Tìm và xử lý cột thời gian an toàn
    for col in df.columns:
        if 'thời gian' in col or 'time' in col or 'tg' in col:
            time_col = col 
            parsed_time = pd.to_datetime(df[col], format='%Y-%m-%d %H-%M-%S', errors='coerce')
            df[col] = parsed_time.fillna(pd.to_datetime(df[col], errors='coerce'))
            break
            
    # 4. Chuyển các cột còn lại sang dạng số
    for col in df.columns:
        if col != time_col: 
            df[col] = pd.to_numeric(df[col], errors='ignore')
            
    # 5. Ép kiểu chuỗi để chống lỗi Arrow (Mixed types)
    for col in df.columns:
        if df[col].dtype == 'object' and col != time_col:
            df[col] = df[col].astype(str)
            
    return df, time_col

# --- 2. GIAO DIỆN UPLOAD (SIDEBAR) ---
with st.sidebar:
    st.markdown("---")
    uploaded_file = st.file_uploader("TẢI LÊN FILE JSON QUAN TRẮC", type=['json'])

# --- 3. HIỂN THỊ DỮ LIỆU ---
if uploaded_file is not None:
    try:
        with st.spinner("Đang phân tích dữ liệu... Vui lòng đợi nhé!"):
            df, time_col = load_and_process_data(uploaded_file.getvalue())
            
        stt_col = next((c for c in df.columns if 'stt' in c), None)
        
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
            # Chắc chắn cột thời gian không bị nhét vào trục Y gây lỗi
            if time_col in numeric_cols: numeric_cols.remove(time_col)
            
            selected_metrics = st.multiselect("Chọn thông số:", numeric_cols, default=numeric_cols[:2] if len(numeric_cols) > 1 else numeric_cols)

            if selected_metrics:
                fig = px.line(df_filtered, x=time_col, y=selected_metrics, template=plotly_template, markers=True)
                
                # Tùy chỉnh biểu đồ đẹp mắt và thêm đường gióng (Spikelines)
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
            st.error("Không tìm thấy dữ liệu thời gian hợp lệ hoặc dữ liệu đang trống.")
    except Exception as e:
        st.error(f"Đã có lỗi xảy ra trong quá trình đọc file: {e}")
else:
    st.info("👈 Hãy tải file JSON ở thanh bên trái để bắt đầu!")
