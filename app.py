import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt
import numpy as np

# 1. CÀI ĐẶT GIAO DIỆN TRANG WEB
st.set_page_config(page_title="Dashboard Quan Trắc", layout="wide")
st.title("🌱 Bảng Điều Khiển Cảm Biến Quan Trắc Thực Địa")

# 2. ĐỌC DỮ LIỆU
file_path = 'data.json' # Nhớ đảm bảo tên file trên GitHub chính xác là data.json

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    df['Thời gian'] = pd.to_datetime(df['Thời gian'], format='%Y-%m-%d %H-%M-%S')

    # Xử lý cột độ ẩm
    if 'Độ ẩm' in df.columns and 'humiKK' in df.columns:
        df['Moisture'] = df['Độ ẩm'].fillna(df['humiKK']).astype(float)
    elif 'Độ ẩm' in df.columns:
        df['Moisture'] = df['Độ ẩm'].astype(float)
    else:
        df['Moisture'] = df['humiKK'].astype(float)

    df['STT'] = pd.to_numeric(df['STT'], errors='coerce')
    df = df[df['STT'].isin([1, 2, 3, 4, 5])]

    df = df.set_index('Thời gian')
    df_filtered = df.between_time('05:00', '23:59').reset_index()

    # 3. TÍNH TOÁN SỐ LẦN TƯỚI
    df_filtered = df_filtered.sort_values(by=['STT', 'Thời gian'])
    df_filtered['Moisture_Diff'] = df_filtered.groupby('STT')['Moisture'].diff()

    THRESHOLD = 5.0 
    watering_events = df_filtered[df_filtered['Moisture_Diff'] > THRESHOLD].copy()
    watering_events['Ngày'] = watering_events['Thời gian'].dt.date

    watering_counts = watering_events.groupby(['Ngày', 'STT']).size().reset_index(name='Số lần tưới')

    all_stts = pd.DataFrame({'STT': [1, 2, 3, 4, 5]})
    if not watering_counts.empty:
        unique_days = watering_counts['Ngày'].unique()
        idx = pd.MultiIndex.from_product([unique_days, all_stts['STT']], names=['Ngày', 'STT'])
        watering_counts = watering_counts.set_index(['Ngày', 'STT']).reindex(idx, fill_value=0).reset_index()

    # 4. HIỂN THỊ LÊN TRANG WEB STREAMLIT (Thay vì dùng print)
    st.subheader("📊 Bảng thống kê số lần tưới trong ngày")
    st.dataframe(watering_counts, use_container_width=True) # Hiện bảng trên web
    
    st.info("Lưu ý: STT 1, 2, 4 có số lần tưới = 0 vì cảm biến không ghi nhận được sự thay đổi độ ẩm.")

    # 5. VẼ VÀ HIỂN THỊ BIỂU ĐỒ LÊN WEB (Thay vì dùng plt.show)
    if not watering_counts.empty:
        st.subheader("📈 Biểu đồ chi tiết")
        day_to_plot = watering_counts['Ngày'].iloc[0]
        plot_data = watering_counts[watering_counts['Ngày'] == day_to_plot]
        
        # Khởi tạo khung vẽ
        fig, ax = plt.subplots(figsize=(10, 5))
        bars = ax.bar(plot_data['STT'].astype(str), plot_data['Số lần tưới'], color='skyblue', edgecolor='black')
        
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 0.1, int(yval), ha='center', va='bottom', fontweight='bold')

        ax.set_title(f'Số lần tưới của các khu vực trong ngày {day_to_plot}', fontsize=14)
        ax.set_xlabel('Khu vực (STT)')
        ax.set_ylabel('Tổng số lần tưới')
        ax.set_yticks(np.arange(0, max(plot_data['Số lần tưới'].max() + 2, 5), 1))
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Lệnh quan trọng nhất để đưa biểu đồ lên web
        st.pyplot(fig) 

except FileNotFoundError:
    # Nếu quên upload data.json, web sẽ hiện thông báo lỗi màu đỏ này thay vì trắng tinh
    st.error("🚨 Không tìm thấy file dữ liệu. Vui lòng kiểm tra xem bạn đã upload file data.json lên GitHub chưa!")
