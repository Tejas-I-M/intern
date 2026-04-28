import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path = os.path.join(BASE_DIR, "data", "processed", "master_dataset.csv")
output_path = os.path.join(BASE_DIR, "reports", "data_dictionary.xlsx")

# Load dataset
df = pd.read_csv(data_path)

# Create dictionary dataframe
data_dict = pd.DataFrame({
    "Column Name": df.columns,
    "Data Type": df.dtypes.values,
    "Description": [""] * len(df.columns)  # You can fill manually later
})

# Save to Excel
data_dict.to_excel(output_path, index=False)

print("✅ Data Dictionary Generated Successfully!")