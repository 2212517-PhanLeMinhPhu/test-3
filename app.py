import pandas as pd
import json
import matplotlib.pyplot as plt

# 1. ĐỌC VÀ TIỀN XỬ LÝ DỮ LIỆU
file_path = 'Quan trắc thực địa (1).json' # Đảm bảo file nằm cùng thư mục
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

df = pd.DataFrame(data)

# Chuyển đổi định dạng thời gian (YYYY-MM-DD HH-MM-SS)
df['Thời gian'] = pd.to_datetime(df['Thời gian'], format='%Y-%m-%d %H-%M-%S')

# Xử lý sự khác biệt về tên cột (Độ ẩm vs humiKK)
if 'Độ ẩm' in df.columns and 'humiKK' in df.columns:
    df['Moisture'] = df['Độ ẩm'].fillna(df['humiKK']).astype(float)
elif 'Độ ẩm' in df.columns:
    df['Moisture'] = df['Độ ẩm'].astype(float)
else:
    df['Moisture'] = df['humiKK'].astype(float)

# Lọc STT từ 1 đến 5
df['STT'] = pd.to_numeric(df['STT'], errors='coerce')
df = df[df['STT'].isin([1, 2, 3, 4, 5])]

# Lọc khung giờ từ 5:00 AM đến 23:59 PM
df = df.set_index('Thời gian')
df_filtered = df.between_time('05:00', '23:59').reset_index()

# 2. LỌC MỘT NGÀY TƯỚI BAO NHIÊU LẦN
# Sắp xếp theo STT và Thời gian để tính độ lệch
df_filtered = df_filtered.sort_values(by=['STT', 'Thời gian'])

# Tính sự chênh lệch độ ẩm giữa 2 lần đo liên tiếp
df_filtered['Moisture_Diff'] = df_filtered.groupby('STT')['Moisture'].diff()

# Giả định: Nếu độ ẩm tăng đột ngột > 5 đơn vị, đó là 1 lần tưới. 
# (Bạn có thể thay đổi số 5.0 này cho phù hợp với thực tế cảm biến của bạn)
THRESHOLD = 5.0 
df_filtered['Is_Watering'] = df_filtered['Moisture_Diff'] > THRESHOLD

# Đếm số lần tưới theo ngày và STT
df_filtered['Ngày'] = df_filtered['Thời gian'].dt.date
watering_counts = df_filtered[df_filtered['Is_Watering']].groupby(['Ngày', 'STT']).size().reset_index(name='Số lần tưới')

print("--- THỐNG KÊ SỐ LẦN TƯỚI TRONG NGÀY ---")
print(watering_counts.to_string(index=False))
print("-" * 40)

# 3. VẼ BIỂU ĐỒ DẠNG LÊN XUỐNG (LINE CHART)
plt.figure(figsize=(14, 7))

for stt in range(1, 6):
    df_stt = df_filtered[df_filtered['STT'] == stt]
    if not df_stt.empty:
        plt.plot(df_stt['Thời gian'], df_stt['Moisture'], label=f'Khu vực {stt}', marker='.', linewidth=1.5)

plt.title('Biểu đồ biến thiên Độ ẩm theo thời gian (05:00 - 23:59)', fontsize=14, fontweight='bold')
plt.xlabel('Thời gian', fontsize=12)
plt.ylabel('Độ ẩm (%)', fontsize=12)
plt.legend(title="Số thứ tự (STT)")
plt.grid(True, linestyle='--', alpha=0.7)
plt.xticks(rotation=45)
plt.tight_layout()

# Hiển thị biểu đồ
plt.show()
plt.savefig('bieu_do_do_am.png')
print("Đã lưu biểu đồ thành công!")
