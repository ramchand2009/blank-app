# drive_utils.py
import pandas as pd
import io
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import tempfile

# Authenticate Google Drive
# In production, use streamlit's secrets to load client_secrets.json

def authenticate_drive():
    if not os.path.exists("client_secrets.json"):
        with open("client_secrets.json", "w") as f:
            f.write(st.secrets["client_secrets_json"])

    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    gauth.SaveCredentialsFile("mycreds.txt")
    return GoogleDrive(gauth)

drive = authenticate_drive()

def read_excel_from_drive(file_id):
    file = drive.CreateFile({'id': file_id})
    file.FetchMetadata()
    file.GetContentFile('temp.xlsx')
    return pd.read_excel('temp.xlsx', engine='openpyxl')

def read_csv_from_drive(file_id):
    file = drive.CreateFile({'id': file_id})
    file.FetchMetadata()
    file.GetContentFile('temp.csv')
    return pd.read_csv('temp.csv')

def write_df_to_drive(df, file_id, file_type="csv"):
    file = drive.CreateFile({'id': file_id})

    if file_type == "csv":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', encoding='utf-8') as tmp:
            df.to_csv(tmp.name, index=False)
            file.SetContentFile(tmp.name)
    elif file_type == "excel":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            with pd.ExcelWriter(tmp.name, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            file.SetContentFile(tmp.name)

    file.Upload()
