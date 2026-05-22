import pandas as pd
import os

HISTORY_FILE = "data/uploaded_history.csv"

def get_new_records(new_data):
    df_new = pd.DataFrame(new_data)

    if not os.path.exists(HISTORY_FILE):
        df_new.to_csv(HISTORY_FILE, index=False)
        return df_new

    df_old = pd.read_csv(HISTORY_FILE)

    df_combined = pd.concat([df_old, df_new]).drop_duplicates(
        subset=["Email"], keep=False
    )

    updated_history = pd.concat([df_old, df_new]).drop_duplicates(subset=["Email"])
    updated_history.to_csv(HISTORY_FILE, index=False)

    return df_combined