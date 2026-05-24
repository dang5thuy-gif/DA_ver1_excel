import pandas as pd
from sqlalchemy import create_engine
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import os

# ====================== KẾT NỐI ======================
engine = create_engine('mssql+pyodbc://localhost/ChurnDW?trusted_connection=yes&driver=ODBC+Driver+17+for+SQL+Server')

print("📥 Đang tải dữ liệu...")
df = pd.read_sql("SELECT * FROM dw.CustomerSnapshot", engine)

# Feature Engineering
df['CLV_per_Month'] = df['CLV'] / (df['MonthsAsMember'].replace(0, 1))
df['Revenue_per_Order'] = df['TotalRevenue'] / (df['Frequency'].replace(0, 1))
df['Engagement_Score'] = df['Frequency'] * df['TotalRevenue'] / (df['Recency'] + 1)

features = ['MonthsAsMember', 'CLV', 'Frequency', 'TotalRevenue', 'AvgOrderValue',
            'TotalQuantity', 'Recency', 'CLV_per_Month', 'Revenue_per_Order', 'Engagement_Score']

X = df[features]
y = df['IsChurn']

# Train model
model = RandomForestClassifier(n_estimators=300, max_depth=12, random_state=42, class_weight='balanced')
model.fit(X, y)

df['ChurnScore'] = model.predict_proba(X)[:, 1]
df['ChurnRisk'] = pd.cut(df['ChurnScore'], bins=[0, 0.25, 0.6, 1.0], labels=['Low', 'Medium', 'High'])

# ====================== TẠO NHIỀU FILE OUTPUT (KHÔNG TIMESTAMP) ======================
os.makedirs('outputs', exist_ok=True)

# 1. File chính - Toàn bộ danh sách
df[['LoyaltyNumber', 'Country', 'Gender', 'LoyaltyStatus', 'CLV', 'Recency', 
    'Frequency', 'TotalRevenue', 'ChurnScore', 'ChurnRisk']].sort_values('ChurnScore', ascending=False)\
    .to_excel('outputs/churn_list_full.xlsx', index=False)

# 2. Chỉ khách hàng High Risk
high_risk = df[df['ChurnRisk'] == 'High'].sort_values('ChurnScore', ascending=False)
high_risk.to_excel('outputs/churn_high_risk.xlsx', index=False)

# 3. Báo cáo theo Quốc gia
country_report = df.groupby('Country').agg({
    'LoyaltyNumber': 'count',
    'ChurnScore': 'mean',
    'ChurnRisk': lambda x: (x == 'High').sum()
}).round(4)
country_report.to_excel('outputs/churn_by_country.xlsx')

# 4. Báo cáo theo Hạng thành viên
loyalty_report = df.groupby('LoyaltyStatus').agg({
    'LoyaltyNumber': 'count',
    'ChurnScore': 'mean',
    'ChurnRisk': lambda x: (x == 'High').sum()
}).round(4)
loyalty_report.to_excel('outputs/churn_by_loyalty.xlsx')

# 5. Top 100 khách hàng cần ưu tiên
top100 = df.nlargest(100, 'ChurnScore')
top100.to_excel('outputs/top100_churn.xlsx', index=False)

print(f"\n🎉 ĐÃ TẠO 5 FILE OUTPUT THÀNH CÔNG!")
print(f"📁 Thư mục outputs/ chứa:")
print(f"   • churn_list_full.xlsx")
print(f"   • churn_high_risk.xlsx")
print(f"   • churn_by_country.xlsx")
print(f"   • churn_by_loyalty.xlsx")
print(f"   • top100_churn.xlsx")