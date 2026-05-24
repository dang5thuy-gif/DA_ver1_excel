import pandas as pd

df = pd.read_excel('outputs/churn_list.xlsx')

print("🔥 TOP 20 KHÁCH HÀNG NGUY CƠ CHURN CAO NHẤT")
print("="*80)
top20 = df.head(20)[['LoyaltyNumber', 'Country', 'LoyaltyStatus', 'CLV', 
                     'Recency', 'Frequency', 'TotalRevenue', 'ChurnScore', 'ChurnRisk']]
print(top20)

print(f"\nTổng số khách hàng nguy cơ High: {len(df[df['ChurnRisk'] == 'High'])}")
print(f"Tổng số khách hàng nguy cơ Medium: {len(df[df['ChurnRisk'] == 'Medium'])}")