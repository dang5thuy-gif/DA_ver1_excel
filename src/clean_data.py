# ============================================
# SALES DATA CLEANING PIPELINE
# File: DB.xlsx
# ============================================

import pandas as pd
import numpy as np

# ============================================
# 1. LOAD DATASET
# ============================================

file_path = "data/DB.xlsx"

df = pd.read_excel(
    file_path,
    sheet_name="FILE_DATA_HANDONLAB2"
)

print("Shape before cleaning:", df.shape)

# ============================================
# 2. REMOVE UNNECESSARY COLUMNS
# ============================================

# Remove unnecessary column
if 'Column1' in df.columns:
    df.drop(columns=['Column1'], inplace=True)

# ============================================
# 3. REMOVE DUPLICATE RECORDS
# ============================================

duplicate_count = df.duplicated().sum()
print("Duplicate rows:", duplicate_count)

df = df.drop_duplicates()

# ============================================
# 4. HANDLE MISSING VALUES
# ============================================

# Check missing values
print("\nMissing Values:")
print(df.isnull().sum())

# Fill numeric columns with median
numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns

for col in numeric_cols:
    df[col] = df[col].fillna(df[col].median())

# Fill text columns with 'Unknown'
text_cols = df.select_dtypes(include=['object', 'string']).columns

for col in text_cols:
    df[col] = df[col].fillna("Unknown")

# ============================================
# 5. STANDARDIZE TEXT DATA
# ============================================

# Remove leading/trailing spaces
for col in text_cols:
    df[col] = df[col].astype(str).str.strip()

# Standardize text capitalization
columns_to_standardize = [
    'Gender',
    'Education',
    'Marital Status',
    'Country',
    'Province or State',
    'Product Line',
    'LoyaltyStatus'
]

for col in columns_to_standardize:
    if col in df.columns:
        df[col] = df[col].str.title()

# ============================================
# 6. FIX INCONSISTENT GENDER VALUES
# ============================================

if 'Loyalty#' in df.columns and 'Gender' in df.columns:

    # Get the most frequent gender per customer
    gender_mode = (
        df.groupby('Loyalty#')['Gender']
        .agg(lambda x: x.mode()[0])
    )

    # Replace inconsistent gender values
    df['Gender'] = df['Loyalty#'].map(gender_mode)

    print("\nInconsistent gender fixed successfully.")

# ============================================
# 7. CONVERT DATA TYPES
# ============================================

# Convert integer columns
int_columns = [
    'Order Year',
    'Quantity Sold'
]

for col in int_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col],
            errors='coerce'
        ).fillna(0).astype(int)

# Convert float columns
float_columns = [
    'Revenue',
    'Unit Cost',
    'Unit Sale Price',
    'Income',
    'Customer Lifetime Value',
    'Latitude',
    'Longitude'
]

for col in float_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col],
            errors='coerce'
        )

# ============================================
# 8. VALIDATE REVENUE CALCULATION
# ============================================

if all(col in df.columns for col in [
    'Quantity Sold',
    'Unit Sale Price'
]):

    # Calculate expected revenue
    df['Calculated Revenue'] = (
        df['Quantity Sold'] *
        df['Unit Sale Price']
    )

    # Compare with actual revenue
    if 'Revenue' in df.columns:
        df['Revenue Difference'] = (
            df['Revenue'] -
            df['Calculated Revenue']
        )

# ============================================
# 9. CREATE KPI COLUMNS
# ============================================

# Calculate total cost and profit
if all(col in df.columns for col in [
    'Revenue',
    'Unit Cost',
    'Quantity Sold'
]):

    df['Total Cost'] = (
        df['Unit Cost'] *
        df['Quantity Sold']
    )

    df['Profit'] = (
        df['Revenue'] -
        df['Total Cost']
    )

# Calculate profit margin
if 'Profit' in df.columns and 'Revenue' in df.columns:

    df['Profit Margin (%)'] = np.where(
        df['Revenue'] != 0,
        (df['Profit'] / df['Revenue']) * 100,
        0
    )

# ============================================
# 10. DETECT OUTLIERS USING IQR METHOD
# ============================================

outlier_columns = [
    'Revenue',
    'Quantity Sold',
    'Customer Lifetime Value'
]

for col in outlier_columns:

    if col in df.columns:

        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)

        IQR = Q3 - Q1

        lower_bound = Q1 - (1.5 * IQR)
        upper_bound = Q3 + (1.5 * IQR)

        df[f'{col}_Outlier'] = np.where(
            (df[col] < lower_bound) |
            (df[col] > upper_bound),
            'Yes',
            'No'
        )

# ============================================
# 11. REMOVE IMPOSSIBLE VALUES
# ============================================

# Remove negative revenue
if 'Revenue' in df.columns:
    df = df[df['Revenue'] >= 0]

# Remove invalid quantity
if 'Quantity Sold' in df.columns:
    df = df[df['Quantity Sold'] > 0]

# Remove negative unit cost
if 'Unit Cost' in df.columns:
    df = df[df['Unit Cost'] >= 0]

# Reset dataframe index
df.reset_index(drop=True, inplace=True)

# ============================================
# 12. EXPORT CLEANED DATA
# ============================================

output_file = "Cleaned_DB.xlsx"

df.to_excel(output_file, index=False)

print("\n================================")
print("DATA CLEANING COMPLETED")
print("================================")
print("Final Shape:", df.shape)
print("Cleaned file saved as:", output_file)