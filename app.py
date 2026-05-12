import streamlit as st
import pandas as pd
import numpy as np
import json
import re
import plotly.express as px
import io

# ==============================================================================
# --- CẤU HÌNH TRANG & THÔNG SỐ TỐI ƯU ---
# ==============================================================================
st.set_page_config(page_title="JSON Data Pro (Optimized)", layout="wide", page_icon="🌱")
# --- CẤU HÌNH THEME ---
if 'theme' not in st.session_state:
    st.session_state.theme = 'Light'

def toggle_theme():
    st.session_state.theme = 'Dark' if st.session_state.theme == 'Light' else 'Light'

# Thêm nút gạt ở Sidebar
st.sidebar.markdown("### 🎨 GIAO DIỆN")
theme_choice = st.sidebar.radio("Chọn chế độ hiển thị:", ["Sáng", "Tối"], 
                                 index=0 if st.session_state.theme == 'Light' else 1,
                                 key="theme_toggle_radio")
st.session_state.theme = "Dark" if theme_choice == "Tối" else "Light"
st.title("🌱 Công cụ Phân tích Dữ liệu Nông Nghiệp")

def apply_theme():
    if st.session_state.theme == "Dark":
        st.markdown("""
            <style>
            /* Nền chính và văn bản tổng thể */
            .stApp {
                background-color: #0E1117;
                color: #FFFFFF;
            }
            
            /* TÙY CHỈNH FILE UPLOADER TRONG DARK MODE */
            /* 1. Màu chữ của nhãn (Label) */
            div[data-testid="stFileUploader"] label {
                color: #0F0F0F !important;
            }
            /* 2. Màu chữ hướng dẫn (Drag and drop file here) */
            div[data-testid="stFileUploader"] section {
                color: #FFFFFF !important;
                background-color: #161B22; /* Làm nền uploader tối hơn một chút */
                border: 1px dashed #30363D;
            }
            /* 3. Màu chữ thông tin file hạn chế (Limit 200MB...) */
            div[data-testid="stFileUploader"] small {
                color: #8B949E !important;
            }

            /* Định dạng bảng dữ liệu */
            .stDataFrame, div[data-testid="stTable"] {
                background-color: #161B22;
            }
            
            /* Định dạng Tab */
            .stTabs [data-baseweb="tab-list"] {
                background-color: #0E1117;
            }
            .stTabs [data-baseweb="tab"] {
                color: #8B949E;
            }
            .stTabs [aria-selected="true"] {
                color: #58A6FF;
            }
            </style>
            """, unsafe_allow_html=True)
    else:
        # Chế độ Light Mode (Mặc định của Streamlit)
        st.markdown("""
            <style>
            .stApp {
                background-color: #FFFFFF;
                color: #000000;
            }
            </style>
            """, unsafe_allow_html=True)

apply_theme()

KHOANG_TOI_UU = {
    'TEMPKK': (-10.0, 100.0),       
    'HUMIKK': (0.0, 100.0),        
    'SOIL_ASKK': (0.0, 200000.0),   
    'AS': (0.0, 200000.0),          
    'NHIỆT ĐỘ': (-10.0, 100.0),    
    'ĐỘ ẨM': (0.0, 100.0),          
    'PH': (0.0, 14.0),             
    'TBPH': (0.0, 14.0),         
    'EC': (0.0, 10000.0),          
    'TBEC': (0.0, 10000.0),        
    'N': (0.0, 2000.0),             
    'P': (0.0, 2000.0),             
    'K': (0.0, 2000.0)               
}

# Tiền biên dịch Regex để tăng tốc xử lý vòng lặp (Cực kỳ quan trọng cho tốc độ)
PATTERN_DATETIME = re.compile(r'(\d{2}-\d{2}-\d{2})/([-+]?\d*\.?\d+)')
PATTERN_NUMBER = re.compile(r'[-+]?\d*\.?\d+')

# ==============================================================================
# 1. CÁC HÀM XỬ LÝ LÕI (CÓ CACHE)
# ==============================================================================
@st.cache_data(show_spinner=False)
#Chuẩn hóa toàn bộ các từ khóa (keys) trong dữ liệu JSON bằng cách xóa khoảng trắng thừa và chuyển về chữ thường
def normalize_keys(data):
    if isinstance(data, list):
        return [normalize_keys(item) for item in data]
    elif isinstance(data, dict):
        return {str(k).strip().lower(): normalize_keys(v) for k, v in data.items()}
    return data

#Chuyển đổi cấu trúc JSON phân cấp (nhiều lớp lồng nhau) thành một từ điển phẳng (một lớp duy nhất), trong đó các khóa được nối với nhau bằng dấu chấm.
@st.cache_data(show_spinner=False)
def flatten_json(y):
    out = {}
    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], name + a + '.')
        elif isinstance(x, list):
            for i, a in enumerate(x):
                flatten(a, name + str(i) + '.')
        else:
            out[name[:-1]] = x
    flatten(y)
    return out

#Hàm này dùng để điều phối chính để nạp file. Nó giải mã JSON, gọi hàm chuẩn hóa, làm phẳng dữ liệu, loại bỏ cột trống/trùng lặp và xử lý định dạng thời gian(_parsed_time)
@st.cache_data(show_spinner=False)
def load_and_process_data(file_bytes):
    try:
        raw_data = json.loads(file_bytes)
    except json.JSONDecodeError:
        raise ValueError("File tải lên không đúng định dạng JSON hợp lệ.")
        
    if isinstance(raw_data, dict): 
        raw_data = [raw_data]
    
    clean_json = normalize_keys(raw_data)
    df = pd.DataFrame([flatten_json(row) for row in clean_json])
    df = df.dropna(axis=1, how='all').loc[:, ~df.columns.duplicated()]
    
    # Tối ưu: Dùng numpy thay cho regex trong replace để tăng tốc Pandas
    df.replace("", np.nan, inplace=True)
    
    time_col = next((col for col in df.columns if 'time' in col.lower() or 'thời gian' in col.lower()), None)
    if time_col:
        # Tối ưu: Chỉ xử lý chuỗi cho các giá trị không bị NaN
        mask = df[time_col].notna()
        df.loc[mask, '_parsed_time'] = pd.to_datetime(
            df.loc[mask, time_col].astype(str).str.replace('-', ':').str.replace(':', '-', 2), 
            errors='coerce'
        )
    return df, time_col

# ==============================================================================
# 2. CÁC HÀM TIỆN ÍCH CHO BIỂU ĐỒ & BỘ LỌC
# ==============================================================================
#Tạo giao diện người dùng (UI) trên Streamlit để chọn khoảng thời gian theo các chế độ: tùy chọn, tuần, tháng hoặc quý.
def render_date_filter(min_date, max_date, key_prefix):
    if not min_date: return None, None
    
    mode = st.radio(
        "⏳ Kiểu lọc thời gian:", 
        ["Tùy chọn", "Theo Tuần (7 ngày)", "Theo Tháng", "Theo Quý"], 
        horizontal=True, 
        key=f"mode_{key_prefix}"
    )
    
    if mode == "Tùy chọn":
        sel_date = st.date_input("📅 Chọn khoảng ngày:", value=(min_date, max_date), min_value=min_date, max_value=max_date, key=f"date_{key_prefix}")
        start_d = sel_date[0] if sel_date else None
        end_d = sel_date[1] if sel_date and len(sel_date) == 2 else start_d
    else:
        start_d = st.date_input("📅 Chọn ngày bắt đầu:", value=min_date, min_value=min_date, max_value=max_date, key=f"start_{key_prefix}")
        if start_d:
            if mode == "Theo Tuần (7 ngày)":
                end_d = (pd.to_datetime(start_d) + pd.Timedelta(days=6)).date()
            elif mode == "Theo Tháng":
                end_d = (pd.to_datetime(start_d) + pd.DateOffset(months=1) - pd.Timedelta(days=1)).date()
            elif mode == "Theo Quý":
                end_d = (pd.to_datetime(start_d) + pd.DateOffset(months=3) - pd.Timedelta(days=1)).date()
            
            if end_d > max_date: end_d = max_date
            st.success(f"🎯 Sẽ lọc từ: **{start_d.strftime('%d/%m/%Y')}** đến **{end_d.strftime('%d/%m/%Y')}**")
        else:
            end_d = None
            
    return start_d, end_d

# Tối ưu: Đã thêm cache cho quá trình bóc tách tốn tài nguyên
@st.cache_data(show_spinner=False)
#Đây là hàm xử lý chuyên sâu cho dữ liệu cảm biến nông nghiệp. Nó sử dụng Biểu thức chính quy (Regex) để tách các cặp giá trị/ thời gian phức tạp nằm trong các ô dữ liệu.
def extract_sensor_data(df, selected_cols):
    records = []
    cols_to_extract = ['_parsed_time'] + selected_cols
    working_df = df[cols_to_extract].dropna(subset=['_parsed_time'])
    
    for row in working_df.itertuples(index=False):
        main_time = row[0]
        date_str = main_time.strftime('%Y-%m-%d')
        
        for i, col_name in enumerate(selected_cols, start=1):
            val = str(row[i]).strip()
            if not val or val.lower() == 'nan': continue
                
            col_upper = col_name.upper()
            
            def process_val(v_str):
                v = float(v_str)
                if col_upper in ['PH', 'TBPH'] and v > 14: return v / 100.0
                if col_upper in ['NHIỆT ĐỘ'] and v > 100: return v / 10.0
                return v
                
            # Sử dụng Regex đã biên dịch sẵn -> Xử lý mượt hơn 3-5 lần
            matches = PATTERN_DATETIME.findall(val)
            if matches:
                for t_str, v_str in matches:
                    try:
                        full_t_str = f"{date_str} {t_str.replace('-', ':')}"
                        records.append({'TG': pd.to_datetime(full_t_str), 'Giá trị': process_val(v_str), 'Chỉ số': col_upper})
                    except Exception:
                        pass
            else:
                num_match = PATTERN_NUMBER.search(val)
                if num_match:
                    try: 
                        records.append({'TG': main_time, 'Giá trị': process_val(num_match.group()), 'Chỉ số': col_upper})
                    except Exception:
                        pass
                    
    return pd.DataFrame(records)

#Khởi tạo biểu đồ đường (line chart) bằng thư viện Plotly. Hàm này tự động chọn chế độ dựng hình (WebGL cho dữ liệu lớn để mượt hơn) và cấu hình các thuộc tính như hanh trượt, điểm đánh dấu (markers) và đường hỗ trợ soi dữ liệu (spikes).
def generate_chart(df, title, is_multi=False):
    num_points = len(df)
    use_webgl = 'webgl' if num_points > 1000 else 'svg'
    show_markers = num_points <= 500
    
    # Chọn template dựa trên theme
    plotly_template = "plotly_dark" if st.session_state.theme == "Dark" else "plotly_white"
    
    if is_multi:
        fig = px.line(df, x='TG', y='Giá trị', color='Chỉ số', 
                      markers=show_markers, render_mode=use_webgl,
                      color_discrete_sequence=px.colors.qualitative.Set1,
                      template=plotly_template)
    else:
        fig = px.line(df, x='TG', y='Giá trị', 
                      markers=show_markers, render_mode=use_webgl,
                      template=plotly_template)
        
    fig.update_layout(
        title=f"<b>{title}</b>", 
        xaxis_title="Thời gian", 
        yaxis_title="Giá trị",
        hovermode="x unified", 
        dragmode='pan',
        paper_bgcolor='rgba(0,0,0,0)', # Làm nền trong suốt
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(rangeslider=dict(visible=False), type="date")
    )
    
    if num_points <= 1000:
        fig.update_xaxes(showspikes=True, spikecolor="gray", spikesnap="cursor", spikemode="across")
        fig.update_yaxes(showspikes=True, spikecolor="gray", spikemode="across")
        
    return fig, num_points

# ==============================================================================
# 3. XỬ LÝ GIAO DIỆN & FILE UPLOAD
# ==============================================================================
uploaded_file = st.file_uploader("Tải lên file JSON", type=['json'])

if uploaded_file is not None:
    try:
        with st.spinner("Đang xử lý và nạp dữ liệu siêu tốc..."):
            file_bytes = uploaded_file.getvalue().decode("utf-8")
            df, time_col = load_and_process_data(file_bytes)

        st.sidebar.markdown("### 🔍 BỘ LỌC TÙY CHỈNH")
        filterable_cols = [col for col in df.columns if col not in ['_parsed_time']]
        selected_key = st.sidebar.selectbox("1. Chọn trường dữ liệu (Key) muốn lọc:", options=["-- Không lọc --"] + filterable_cols)
        
        if selected_key != "-- Không lọc --":
            unique_values = df[selected_key].dropna().astype(str).unique()
            list_values = ["Tất cả"] + list(unique_values)
            selected_value = st.sidebar.selectbox(f"2. Chọn giá trị cho '{selected_key.upper()}':", options=list_values)
            
            if selected_value != "Tất cả":
                df = df[df[selected_key].astype(str) == selected_value].reset_index(drop=True)
                st.sidebar.success(f"✅ Đang lọc: {selected_key.upper()} = {selected_value}")
                if df.empty:
                    st.error("⚠️ Bộ lọc này không trả về kết quả nào. Vui lòng chọn giá trị khác!")
                    st.stop()

        exclude = [time_col, 'stt', 'tên khu', 'trạng thái', 'phương thức hoạt động', 'người điều khiển', '_parsed_time']
        numeric_options = [c for c in df.columns if c not in exclude and '_id' not in c]

        min_d, max_d = None, None
        if '_parsed_time' in df.columns:
            valid_ts = df['_parsed_time'].dropna()
            if not valid_ts.empty:
                min_d, max_d = valid_ts.min().date(), valid_ts.max().date()

        st.markdown("---")
        tab1, tab2, tab3 = st.tabs(["🗂️ Bảng dữ liệu", "📈 Biểu đồ Đơn", "📊 Biểu đồ Lồng nhau"])

        # ==========================================
        # TAB 1: BẢNG DỮ LIỆU
        # ==========================================
        with tab1:
            st.subheader("🌾 Bảng dữ liệu chi tiết")
            display_df = df.drop(columns=['_parsed_time'], errors='ignore').fillna("")
            col_h1, col_h2 = st.columns([3, 1])
            with col_h1: st.write(f"Đang hiển thị: **{len(df)}** bản ghi")
            with col_h2:
                csv = display_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Tải xuống CSV", data=csv, file_name='data_export.csv', mime='text/csv', use_container_width=True)
            st.dataframe(display_df, use_container_width=True)

        # ==========================================
        # TAB 2: BIỂU ĐỒ ĐƠN LẺ
        # ==========================================
        with tab2:
            st.write("⚙️ Thiết lập biểu đồ đơn lẻ")
            col1, col2 = st.columns([1, 2])
            with col1:
                start_d_2, end_d_2 = render_date_filter(min_d, max_d, "tab2")
                filter_data_2 = st.checkbox("✅ Lọc Sạch Dữ Liệu (Bỏ nhiễu)", value=True, key="filter_tab2")

            with col2:
                st.write("Chọn chỉ số:")
                cols_ui = st.columns(4)
                selected_keys_2 = [k for i, k in enumerate(numeric_options) if cols_ui[i % 4].checkbox(k.upper(), key=f"c_tab2_{k}")]

            if st.button("🚀 TẠO BIỂU ĐỒ ĐƠN", type="primary", key="btn_tab2"):
                if not selected_keys_2: st.warning("Hãy chọn ít nhất 1 chỉ số!")
                elif not start_d_2 or not end_d_2: st.warning("Vui lòng chọn khoảng thời gian hợp lệ!")
                else:
                    with st.spinner("Đang vẽ biểu đồ..."):
                        mask = (df['_parsed_time'].dt.date >= start_d_2) & (df['_parsed_time'].dt.date <= end_d_2)
                        filtered_df = df[mask]
                        chart_df = extract_sensor_data(filtered_df, selected_keys_2) 
                        
                        if not chart_df.empty:
                            for col in selected_keys_2:
                                sub_df = chart_df[chart_df['Chỉ số'] == col.upper()]
                                ten_chi_so = col.upper()
                                
                                if filter_data_2 and ten_chi_so in KHOANG_TOI_UU:
                                    min_val, max_val = KHOANG_TOI_UU[ten_chi_so]
                                    sub_df = sub_df[(sub_df['Giá trị'] >= min_val) & (sub_df['Giá trị'] <= max_val)]
                                
                                if sub_df.empty: continue
                                
                                # Tối ưu logic làm mượt thông minh (Smart Resampling)
                                pts_count = len(sub_df)
                                days_diff = (end_d_2 - start_d_2).days
                                rule = None
                                
                                if pts_count > 5000: rule = '1H' # Vượt 5000 điểm -> Ép gộp theo Giờ
                                if days_diff > 2: rule = '1D'    # Vượt 2 ngày -> Ép gộp theo Ngày
                                
                                if rule: 
                                    st.info(f"💡 Chỉ số {ten_chi_so} có quá nhiều dữ liệu ({pts_count} điểm). Hệ thống tự động gộp trung bình theo '{'Ngày' if rule=='1D' else 'Giờ'}' để biểu đồ mượt mà hơn.")
                                    plot_data = sub_df.set_index('TG').resample(rule)['Giá trị'].mean().dropna().reset_index()
                                else: 
                                    plot_data = sub_df.groupby('TG')['Giá trị'].mean().reset_index()
                                    
                                plot_data = plot_data.sort_values(by='TG')
                                fig, pts = generate_chart(plot_data, f"Chỉ số: {ten_chi_so}", is_multi=False)
                                st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
                                
                                with st.expander(f"📋 Bảng số liệu đối chứng ({pts} điểm)"):
                                    st.dataframe(plot_data, use_container_width=True)
                                st.write("---")
                        else: st.info("Không có dữ liệu hợp lệ.")

        # ==========================================
        # TAB 3: BIỂU ĐỒ LỒNG NHAU 
        # ==========================================
        with tab3:
            st.write("⚙️ Thiết lập biểu đồ lồng nhau")
            col1_m, col2_m = st.columns([1, 2])
            with col1_m:
                st.write("🎯 **Chọn chỉ số:**")
                check_multi_ui = st.columns(3)
                selected_keys_3 = [k for i, k in enumerate(numeric_options) if check_multi_ui[i % 3].checkbox(k.upper(), key=f"c_multi_{k}")]

            with col2_m:
                start_d_3, end_d_3 = render_date_filter(min_d, max_d, "tab3")
                filter_data_3 = st.checkbox("✅ Lọc Sạch Dữ Liệu (Bỏ nhiễu)", value=True, key="filter_tab3")

            if st.button("🚀 TẠO BIỂU ĐỒ ĐỐI CHIẾU", type="primary", key="btn_multi"):
                if len(selected_keys_3) < 2: st.warning("Hãy chọn ít nhất 2 chỉ số!")
                elif not start_d_3 or not end_d_3: st.warning("Vui lòng chọn khoảng thời gian hợp lệ!")
                else:
                    with st.spinner("Đang tổng hợp dữ liệu..."):
                        mask = (df['_parsed_time'].dt.date >= start_d_3) & (df['_parsed_time'].dt.date <= end_d_3)
                        filtered_df = df[mask]
                        multi_chart_df = extract_sensor_data(filtered_df, selected_keys_3) 
                        
                        if not multi_chart_df.empty:
                            clean_dfs = []
                            for col in selected_keys_3:
                                sub_df = multi_chart_df[multi_chart_df['Chỉ số'] == col.upper()]
                                ten_chi_so = col.upper()
                                if filter_data_3 and ten_chi_so in KHOANG_TOI_UU:
                                    min_val, max_val = KHOANG_TOI_UU[ten_chi_so]
                                    sub_df = sub_df[(sub_df['Giá trị'] >= min_val) & (sub_df['Giá trị'] <= max_val)]
                                if not sub_df.empty: clean_dfs.append(sub_df)
                                
                            multi_chart_df = pd.concat(clean_dfs) if clean_dfs else pd.DataFrame()
                            
                            if not multi_chart_df.empty:
                                pts_count = len(multi_chart_df)
                                days_diff = (end_d_3 - start_d_3).days
                                rule = None
                                
                                if pts_count > 10000: rule = '1H' 
                                if days_diff > 2: rule = '1D'    

                                if rule:
                                    st.info(f"💡 Hệ thống tự động gộp trung bình theo '{'Ngày' if rule=='1D' else 'Giờ'}' để tăng tốc độ hiển thị.")
                                    plot_data = multi_chart_df.set_index('TG').groupby('Chỉ số')['Giá trị'].resample(rule).mean().dropna().reset_index()
                                else: 
                                    plot_data = multi_chart_df.groupby(['TG', 'Chỉ số'])['Giá trị'].mean().reset_index()
                                    
                                plot_data = plot_data.sort_values(by='TG')
                                fig, pts = generate_chart(plot_data, "Biểu đồ Đối chiếu Trực tiếp", is_multi=True)
                                st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})
                                
                                with st.expander(f"📋 Bảng số liệu gộp ({pts} điểm)"):
                                    pivot_df = plot_data.pivot(index='TG', columns='Chỉ số', values='Giá trị').reset_index()
                                    st.dataframe(pivot_df, use_container_width=True)
                        else: st.info("Không có dữ liệu hợp lệ.")

    except Exception as e:
        st.error(f"Đã xảy ra lỗi: {e}")
