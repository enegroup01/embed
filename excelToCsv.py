import pandas as pd

# Specify the input XLSX file path
input_file = 'excel/eatEnjoy2-2.xlsx'

# Specify the output CSV file path
output_file = 'csv/eatEnjoy2-2.csv'

# Read the XLSX file
data_frame = pd.read_excel(input_file)

# Save the data frame as a CSV file
data_frame.to_csv(output_file, index=False)

print("CSV file saved successfully.")
