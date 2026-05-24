import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime

engine = create_engine('mssql+pyodbc://localhost/ChurnDW?trusted_connection=yes&driver=ODBC+Driver+17+for+SQL+Server')

print("📤 Đang đẩy kết quả Churn Score vào SQL...")

# Đọc file chính
df = pd.read_excel('outputs/churn_list_full.xlsx')

df['SnapshotDate'] = datetime.now().date()
df['ModelName'] = 'RandomForest'
df['ModelVersion'] = 'v1.0'
df['UpdatedAt'] = datetime.now()

df.to_sql('ChurnScoreRaw', engine, schema='stg', if_exists='replace', index=False)

print("✅ Đã đẩy thành công vào bảng stg.ChurnScoreRaw")
print("Bạn có thể xem trong SQL: SELECT TOP 20 * FROM stg.ChurnScoreRaw")