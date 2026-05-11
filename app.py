import streamlit as st
import pandas as pd
import numpy as np
import json
import plotly.express as px

# --- 0. CẤU HÌNH GIAO DIỆN ---
st.set_page_config(page_title="Data Pro - Nông Nghiệp Thông Minh", layout="wide")

with st.sidebar:
    st.header("🎨 Giao diện")
    dark_mode = st.toggle("Chế độ Tối (Dark Mode)", value=True)

bg_color, text_color, sidebar_bg, upload_label_color, dropzone_bg, dropzone_text, plotly_template = (
    ("#0E1117", "#FAFAFA", "#161b22", "#ffffff", "#161b22", "#ffffff", "plotly_dark") if dark_mode 
    else ("#FFFFFF", "#31333F", "#F0F2F6", "#31333F", "#f9f9f9", "#31333F", "plotly")
)

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; color: {text_color}; }}
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg}; border-right: 1px solid #30363d; }}
    [data-testid="stFileUploaderDropzone"] {{ border: 3px dashed #00d4ff !important; border-radius: 12px; }}
    h1, h2, h3 {{ color: {text_color} !important; }}
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Phân tích Dữ liệu Quan trắc Tưới & Nhỏ giọt")

# --- 1. CÁC HÀM XỬ LÝ DỮ LIỆU AN TOÀN ---
def normalize_keys(data):
    if isinstance(data, list): return [normalize_keys(item) for item in data]
    elif isinstance(data, dict): return {str(k).strip(): normalize_keys(v) for k, v in data.items()}
    return data

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

def parse_sensor_string(cell_value):
    if pd.isna(cell_value) or str(cell_value).strip() == "":
        return np.nan
    val_str = str(cell_value).strip()
    if '/' in val_str and '-' in val_str:
        vals = []
        for item in val_str.split():
            if '/' in item:
                try: vals.append(float(item.split('/')[1]))
                except ValueError: pass
        if vals: return np.mean(vals)
    try: return float(val_str)
    except ValueError: return val_str

def safe_json_load(file_bytes):
    text = file_bytes.decode('utf-8-sig').strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        data = []
        for line in text.split('\n'):
            line = line.strip()
            if line:
                try: data.append(json.loads(line))
                except: pass
        return data

def process_sensor_data(file_bytes):
    raw_data = safe_json_load(file_bytes)
    if not raw_data: return pd.DataFrame(), None
    if isinstance(raw_data, dict): raw_data = [raw_data]
    
    clean_json = normalize_keys(raw_data)
    flat_list = [flatten_json(item) for item in clean_json]
    df = pd.DataFrame(flat_list)
    
    df.columns = df.columns.str.strip().str.capitalize()
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    
    time_col = None
    for col in df.columns:
        if 'thời gian' in col.lower() or 'time' in col.lower():
            time_col = col 
            df[col] = pd.to_datetime(df[col], errors='coerce')
            # Kiểm tra an toàn trước khi loại bỏ múi giờ
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.tz_localize(None) 
            break
            
    for col in df.columns:
        if col != time_col and 'id' not in col.lower() and 'file' not in col.lower(): 
            df[col] = df[col].apply(parse_sensor_string)
            # FIX LỖI: Chuyển đổi kiểu dữ liệu thủ công, bỏ tham số errors='ignore'
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass # Bỏ qua nếu cột là chuỗi (ví dụ: Bơm, Van), giữ nguyên định dạng chữ
    
    df = df.dropna(axis=1, how='all')
    return df, time_col

# --- 2. GIAO DIỆN UPLOAD ---
with st.sidebar:
    st.markdown("---")
    uploaded_files = st.file_uploader("TẢI LÊN CÁC FILE JSON", type=['json'], accept_multiple_files=True)

# --- 3. HIỂN THỊ DỮ LIỆU ---
if uploaded_files:
    try:
        all_dfs = []
        global_time_col = None
        
        for file in uploaded_files:
            df_temp, time_col = process_sensor_data(file.getvalue())
            if not df_temp.empty:
                df_temp = df_temp.copy()
                df_temp['Tên File'] = str(file.name)
                all_dfs.append(df_temp)
                if time_col:
                    global_time_col = time_col
                
        if not all_dfs:
            st.error("Không tìm thấy dữ liệu hợp lệ trong các file tải lên.")
        else:
            df = pd.concat(all_dfs, ignore_index=True)
            
            # --- BỘ LỌC DỮ LIỆU ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("🎛️ BỘ LỌC DỮ LIỆU")
            
            if 'Tên File' in df.columns:
                file_list = df['Tên File'].dropna().unique().tolist()
                selected_file = st.sidebar.selectbox("📂 Chọn File:", ["Tất cả (Gộp chung)"] + file_list)
                if selected_file != "Tất cả (Gộp chung)":
                    df = df[df['Tên File'] == selected_file]
            else:
                selected_file = "Tất cả (Gộp chung)"
            
            stt_col = next((c for c in df.columns if 'stt' in c.lower()), None)
            khu_col = next((c for c in df.columns if 'tên khu' in c.lower()), None)
            
            col1, col2 = st.sidebar.columns(2)
            if stt_col:
                stt_list = sorted(df[stt_col].dropna().unique().astype(str))
                selected_stt = col1.selectbox("Mã (STT):", ["Tất cả"] + stt_list)
                if selected_stt != "Tất cả":
                    df = df[df[stt_col].astype(str) == selected_stt]
                    
            if khu_col:
                khu_list = sorted(df[khu_col].dropna().unique().astype(str))
                selected_khu = col2.selectbox("Tên khu:", ["Tất cả"] + khu_list)
                if selected_khu != "Tất cả":
                    df = df[df[khu_col].astype(str) == selected_khu]

            df_filtered = df.copy()

            # --- VẼ BIỂU ĐỒ ---
            if global_time_col and not df_filtered.empty:
                st.subheader(f"📈 Biểu đồ thông số: {selected_file}")
                
                df_filtered = df_filtered.dropna(subset=[global_time_col]).sort_values(by=global_time_col)
                
                numeric_cols = df_filtered.select_dtypes(include=[np.number]).columns.tolist()
                if stt_col in numeric_cols: numeric_cols.remove(stt_col)
                
                if not numeric_cols:
                    st.warning("Không tìm thấy dữ liệu dạng số nào có thể vẽ biểu đồ.")
                else:
                    selected_metrics = st.multiselect(
                        "Chọn thông số hiển thị:", 
                        numeric_cols, 
                        default=[c for c in numeric_cols if c in ["Ec", "Ph", "Nhiệt độ ec"]] if numeric_cols else None
                    )

                    if selected_metrics:
                        fig = px.line(
                            df_filtered, 
                            x=global_time_col, 
                            y=selected_metrics, 
                            template=plotly_template
                        )
                        fig.update_traces(mode='lines+markers', line=dict(width=2.5), marker=dict(size=6))
                        fig.update_layout(
                            hovermode='x unified', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        with st.expander("🔍 Xem bảng dữ liệu chi tiết"):
                            cols = df_filtered.columns.tolist()
                            first_cols = [c for c in [global_time_col, 'Tên File', khu_col, 'Trạng thái'] if c in cols]
                            rest_cols = [c for c in cols if c not in first_cols]
                            st.dataframe(df_filtered[first_cols + rest_cols], use_container_width=True)
                    else:
                        st.warning("Vui lòng chọn ít nhất một thông số.")
            else:
                st.error("Dữ liệu trống hoặc file đang xem không có thông tin thời gian hợp lệ.")
    except Exception as e:
        st.exception(e)
else:
    st.info("👈 Hãy tải các file JSON ở thanh bên trái để bắt đầu!")
