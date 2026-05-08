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
    # --- TONE MÀU TỐI ---
    bg_color = "#0E1117"
    text_color = "#FAFAFA"
    sidebar_bg = "#161b22"
    upload_label_color = "#ffffff"
    dropzone_bg = "#161b22"
    dropzone_text = "#ffffff"
    plotly_template = "plotly_dark"
else:
    # --- TONE MÀU SÁNG ---
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
    /* Nền chính của app */
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    /* Tùy chỉnh Sidebar */
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg};
        border-right: 1px solid #30363d;
    }}
    
    /* --- CẤU HÌNH KHUNG UPLOAD --- */
    [data-testid="stFileUploader"] label {{
        display: flex !important;
        width: 100% !important;
        justify-content: center !important;
        margin-bottom: 5px !important;
    }}
    
    [data-testid="stFileUploader"] label p {{
        color: {upload_label_color} !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
        text-align: center !important;
        margin: 0 !important;
    }}

    [data-testid="stFileUploaderDropzone"] {{
        background-color: {dropzone_bg} !important;
        border: 3px dashed #00d4ff !important; 
        border-radius: 12px;
        padding: 30px 20px;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;  
        text-align: center !important;
    }}
