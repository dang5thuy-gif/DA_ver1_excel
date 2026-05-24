import pandas as pd

df = pd.read_excel('outputs/churn_list.xlsx')

print("📊 BÁO CÁO PHÂN TÍCH CHURN")
print("="*90)

# Phân bố rủi ro
print(df['ChurnRisk'].value_counts())
print("\nTỷ lệ:")
print(df['ChurnRisk'].value_counts(normalize=True)*100)

# Top 20 churn cao nhất
print("\n🔥 TOP 20 KHÁCH HÀNG NGUY CƠ CAO NHẤT")
top20 = df.nlargest(20, 'ChurnScore')[['LoyaltyNumber', 'Country', 'LoyaltyStatus', 
                                       'CLV', 'Recency', 'Frequency', 'TotalRevenue', 
                                       'ChurnScore', 'ChurnRisk']]
print(top20)

# Phân tích theo quốc gia
print("\n🌍 Phân bố churn theo Quốc gia:")
print(df.groupby('Country')['ChurnRisk'].value_counts().unstack())

# Phân tích theo LoyaltyStatus
print("\n⭐ Phân bố churn theo Loyalty Status:")
print(df.groupby('LoyaltyStatus')['ChurnRisk'].value_counts().unstack())