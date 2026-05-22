import gspread
from oauth2client.service_account import ServiceAccountCredentials

def read_google_sheet():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "credentials.json", scope
        )

        client = gspread.authorize(creds)

        # ✅ AHA SHEET (INPUT)
        SHEET_URL = "https://docs.google.com/spreadsheets/d/1nS3RQmR5TG7F5K86ZU3jyfgumY-BL94Kerupr6L5r9Y/edit#gid=0"

        sheet = client.open_by_url(SHEET_URL).sheet1

        records = sheet.get_all_records()

        print(f"📊 Found {len(records)} rows in AHA Sheet")

        return records

    except Exception as e:
        print("❌ Google Sheets error:", str(e))
        return []