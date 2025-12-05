import os
import json
import gspread
import requests

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# =======================================================================
# CONFIG
# =======================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "pdf_processing", "client_secrets.json")
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, "pdf_processing", "brs-sheets-api.json")

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    # "https://www.googleapis.com/auth/spreadsheets"
]

# =======================================================================
# OAUTH HANDLER
# =======================================================================

def get_oauth_credentials():
    """
    Membuat credentials OAuth dari refresh_token + client_id + client_secret
    yang disimpan di client_secrets.json (tidak memakai InstalledAppFlow).
    """

    with open(CLIENT_SECRET_FILE, "r") as f:
        data = json.load(f)

    web = data["web"]

    refresh_token = web.get("refresh_token")
    if not refresh_token:
        raise ValueError("refresh_token tidak ditemukan di client_secrets.json")

    creds = Credentials(
        token=web.get("access_token"),      # boleh None, akan auto refresh
        refresh_token=refresh_token,
        token_uri=web["token_uri"],
        client_id=web["client_id"],
        client_secret=web["client_secret"],
        scopes=SCOPES,
    )

    # Refresh untuk memastikan access token valid
    creds.refresh(Request())

    return creds


def get_access_token():
    """Mengambil access token terbaru."""
    creds = get_oauth_credentials()
    return creds.token


# =======================================================================
# GOOGLE SHEETS & DRIVE API
# =======================================================================

# OAuth credentials untuk gspread & Drive API
creds = get_oauth_credentials()

# Gspread client
client = gspread.authorize(creds)

def authenticate_drive():
    """
    Mengautentikasi Google Drive API.
    """
    return build('drive', 'v3', credentials=creds)

def get_sheets_gid(drive_file_id):
    """
    Ambil daftar GID untuk setiap sheet di Google Sheets.
    """
    try:
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{drive_file_id}?fields=sheets(properties(sheetId,title))"
        
        # Ambil access token langsung dari kredensial
        access_token = get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers)
        print(response.json())  # Debugging, lihat apakah data muncul

        if response.status_code == 200:
            data = response.json()
            return {sheet["properties"]["title"]: sheet["properties"]["sheetId"] for sheet in data["sheets"]}
        else:
            print(f"⚠️ Gagal mendapatkan GID. Status: {response.status_code}, Response: {response.text}")
            return {}
    except Exception as e:
        print(f"Error fetching GID: {str(e)}")
        return {}



def get_sheets_preview(drive_file_id):
    """
    Mengambil daftar sheet dan link pratinjau dari Google Sheets.
    """
    try:
        spreadsheet = client.open_by_key(drive_file_id)
        sheets = spreadsheet.worksheets()

        preview_links = [{"name": sheet.title, "link": f"https://docs.google.com/spreadsheets/d/{drive_file_id}/edit?gid={sheet.id}#gid={sheet.id}"} for sheet in sheets]
        
        return preview_links
    except Exception as e:
        print(f"Error fetching sheets: {e}")
        return []
