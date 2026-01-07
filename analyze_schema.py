import pandas as pd
import json

# Note: Using the exact path found in directory listing
file_path = "/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/Turkish Super League/Fenerbahçe/mixed-seasons/Fenerbahçe_Games_Input.csv"
try:
    df = pd.read_csv(file_path)
    print(json.dumps({
        "columns": df.columns.tolist(),
        "first_row": df.iloc[0].to_dict() if not df.empty else {},
        "shape": df.shape
    }, default=str)) # Use str for any non-serializable types
except Exception as e:
    print(f"Error: {e}")
