import pandas as pd
from sqlalchemy import create_engine, text
import time
import os
import traceback

# =====================================================================
# 1. KẾT NỐI
# =====================================================================
connection_string = 'mssql+pyodbc://localhost/ChurnDW?trusted_connection=yes&driver=ODBC+Driver+17+for+SQL+Server'
engine = create_engine(connection_string, pool_pre_ping=True)

# =====================================================================
# 2. ĐƯỜNG DẪN FILE
# =====================================================================
file_path = 'data/Cleaned_DB.xlsx'

if not os.path.exists(file_path):
    print(f"❌ Không tìm thấy file: {file_path}")
    exit()

print(f"✅ Tìm thấy file: {file_path}")

# =====================================================================
# 3. ĐỌC DỮ LIỆU
# =====================================================================
print("⏳ Đang đọc sheet 'CleanData'...")
start_time = time.time()

df = pd.read_excel(file_path, sheet_name='CleanData', engine='openpyxl')
print(f"✅ Đọc thành công: {len(df):,} dòng")

# =====================================================================
# 4. CHUẨN HÓA TÊN CỘT
# =====================================================================
df.columns = [col.strip().replace('#', 'Number').replace(' ', '_').replace('(', '').replace(')', '') 
              for col in df.columns]

# =====================================================================
# 5. TẠO SCHEMA stg
# =====================================================================
print("📌 Đang kiểm tra schema 'stg'...")
with engine.connect() as conn:
    conn.execute(text("IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'stg') EXEC('CREATE SCHEMA stg')"))
    conn.commit()
print("✅ Schema 'stg' OK")

# =====================================================================
# 6. NẠP DỮ LIỆU (GIẢM CHUNKSIZE + TẮT MULTI)
# =====================================================================
print("🚀 Đang nạp dữ liệu vào stg.CleanDataRaw... (có thể mất 1-2 phút)")

try:
    df.to_sql(
        name='CleanDataRaw',
        con=engine,
        schema='stg',
        if_exists='replace',
        index=False,
        chunksize=500,          # Giảm mạnh để tránh lỗi parameter
        method=None             # Tắt multi để an toàn
    )
    end_time = time.time()
    print(f"✅ THÀNH CÔNG! Đã nạp {len(df):,} dòng vào stg.CleanDataRaw.")
    print(f"⏱️ Thời gian: {end_time - start_time:.2f} giây")

except Exception as e:
    print("❌ LỖI khi nạp:")
    traceback.print_exc()