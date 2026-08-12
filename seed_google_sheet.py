"""
Run this once, AFTER .streamlit/secrets.toml is filled in with a real
service account and spreadsheet URL, to create/populate the worksheets:
  - cse_credentials
  - mechanical_credentials
  - results (header row only)

Usage:  python seed_google_sheet.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gspread
from google.oauth2.service_account import Credentials
import toml

from utils.storage import RESULT_FIELDS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def main():
    secrets_path = os.path.join(HERE, ".streamlit", "secrets.toml")
    if not os.path.exists(secrets_path):
        print("Missing .streamlit/secrets.toml — copy secrets.toml.example and fill it in first.")
        return

    secrets = toml.load(secrets_path)
    creds = Credentials.from_service_account_info(secrets["gcp_service_account"], scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(secrets["google_sheets"]["spreadsheet_url"])

    with open(os.path.join(HERE, "data", "credentials.json"), encoding="utf-8") as f:
        creds_data = json.load(f)

    for dept in ("cse", "mechanical"):
        title = f"{dept}_credentials"
        try:
            ws = spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(title=title, rows=200, cols=3)
        ws.clear()
        rows = [["reg_no", "name", "password"]]
        for reg_no, info in sorted(creds_data.get(dept, {}).items()):
            rows.append([reg_no, info["name"], info["password"]])
        ws.update(rows)
        print(f"Seeded {title}: {len(rows) - 1} students")

    try:
        results_ws = spreadsheet.worksheet("results")
    except gspread.WorksheetNotFound:
        results_ws = spreadsheet.add_worksheet(title="results", rows=1000, cols=len(RESULT_FIELDS))
        results_ws.update([RESULT_FIELDS])
        print("Created results worksheet with header row")
    else:
        header = results_ws.row_values(1)
        if header and "quiz_no" not in header:
            print(
                "results worksheet already exists but predates the 'quiz_no' column — "
                "add a 'quiz_no' column to the sheet manually (existing rows can be left "
                "blank; they're treated as Quiz 1)."
            )
        else:
            print("results worksheet already exists — left untouched")


if __name__ == "__main__":
    main()
