"""
Storage layer for the quiz app.

Primary backend: Google Sheets (via gspread), matching the user's chosen
architecture. If Streamlit secrets for a GCP service account aren't
configured (e.g. during local development before the Sheet is provisioned),
this module transparently falls back to local JSON/CSV files under
data/ and local_results/, so the app is fully runnable without live
Google credentials.

Sheets layout (once configured), all in one spreadsheet:
  - "cse_credentials"     columns: reg_no, name, password
  - "mechanical_credentials"  columns: reg_no, name, password
  - "results"             columns: timestamp, department, subject_code,
                           reg_no, name, attempt_no, score, total, percentage,
                           flagged, tab_switch_count, answers_json
"""
import json
import os
import csv
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "..", "data")
LOCAL_RESULTS_DIR = os.path.join(HERE, "..", "local_results")
RESULTS_CSV = os.path.join(LOCAL_RESULTS_DIR, "results.csv")

RESULT_FIELDS = [
    "timestamp", "department", "subject_code", "reg_no", "name",
    "attempt_no", "score", "total", "percentage", "flagged",
    "tab_switch_count", "answers_json", "question_ids_json",
]


def _load_local_credentials():
    path = os.path.join(DATA_DIR, "credentials.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _get_gspread_client():
    """Returns a gspread client + spreadsheet, or (None, None) if secrets aren't set up."""
    try:
        import streamlit as st
        if "gcp_service_account" not in st.secrets:
            return None, None
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        client = gspread.authorize(creds)
        sheet_url = st.secrets["google_sheets"]["spreadsheet_url"]
        spreadsheet = client.open_by_url(sheet_url)
        return client, spreadsheet
    except Exception:
        return None, None


def is_sheets_configured():
    _, spreadsheet = _get_gspread_client()
    return spreadsheet is not None


def get_credentials(department):
    """Returns {reg_no: {"name":..., "password":...}} for the given department."""
    _, spreadsheet = _get_gspread_client()
    if spreadsheet is not None:
        try:
            ws = spreadsheet.worksheet(f"{department}_credentials")
            rows = ws.get_all_records()
            return {
                str(r["reg_no"]): {"name": r["name"], "password": str(r["password"])}
                for r in rows
            }
        except Exception:
            pass
    return _load_local_credentials().get(department, {})


def _ensure_local_results_file():
    os.makedirs(LOCAL_RESULTS_DIR, exist_ok=True)
    if not os.path.exists(RESULTS_CSV):
        with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=RESULT_FIELDS).writeheader()


def save_result(record):
    """record: dict matching RESULT_FIELDS (minus timestamp, which is added here)."""
    record = dict(record)
    record["timestamp"] = datetime.datetime.now().isoformat(timespec="seconds")

    _, spreadsheet = _get_gspread_client()
    if spreadsheet is not None:
        try:
            ws = spreadsheet.worksheet("results")
            ws.append_row([record.get(f, "") for f in RESULT_FIELDS], value_input_option="RAW")
            return
        except Exception:
            pass

    _ensure_local_results_file()
    with open(RESULTS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        writer.writerow({k: record.get(k, "") for k in RESULT_FIELDS})


def get_attempts(reg_no, subject_code):
    """Returns list of previous attempt records for this student+subject (for attempt numbering & history)."""
    records = []
    _, spreadsheet = _get_gspread_client()
    if spreadsheet is not None:
        try:
            ws = spreadsheet.worksheet("results")
            rows = ws.get_all_records()
            records = [r for r in rows if str(r.get("reg_no")) == str(reg_no) and r.get("subject_code") == subject_code]
            return records
        except Exception:
            pass

    _ensure_local_results_file()
    with open(RESULTS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("reg_no") == str(reg_no) and row.get("subject_code") == subject_code:
                records.append(row)
    return records


def get_all_results(department=None, subject_code=None):
    """Returns every result record, optionally filtered by department and/or subject_code.
    Used by the faculty dashboard for CSV/PDF export."""
    records = []
    _, spreadsheet = _get_gspread_client()
    if spreadsheet is not None:
        try:
            ws = spreadsheet.worksheet("results")
            records = ws.get_all_records()
        except Exception:
            records = None
    if records is None or spreadsheet is None:
        _ensure_local_results_file()
        with open(RESULTS_CSV, newline="", encoding="utf-8") as f:
            records = list(csv.DictReader(f))

    if department:
        records = [r for r in records if r.get("department") == department]
    if subject_code:
        records = [r for r in records if r.get("subject_code") == subject_code]
    return records


def _matches(row, timestamp, reg_no, subject_code, attempt_no):
    return (
        str(row.get("timestamp")) == str(timestamp)
        and str(row.get("reg_no")) == str(reg_no)
        and str(row.get("subject_code")) == str(subject_code)
        and str(row.get("attempt_no")) == str(attempt_no)
    )


def delete_result(timestamp, reg_no, subject_code, attempt_no):
    """Deletes the single result row matching all four fields (their combination is
    effectively unique — a student can't submit two attempts of the same subject in
    the same second). Returns True if a row was deleted."""
    _, spreadsheet = _get_gspread_client()
    if spreadsheet is not None:
        try:
            ws = spreadsheet.worksheet("results")
            all_values = ws.get_all_values()
            header, rows = all_values[0], all_values[1:]
            for i, row in enumerate(rows):
                record = dict(zip(header, row))
                if _matches(record, timestamp, reg_no, subject_code, attempt_no):
                    ws.delete_rows(i + 2)  # +1 header, +1 1-indexed
                    return True
            return False
        except Exception:
            pass

    _ensure_local_results_file()
    with open(RESULTS_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    remaining = [r for r in rows if not _matches(r, timestamp, reg_no, subject_code, attempt_no)]
    deleted = len(remaining) != len(rows)
    if deleted:
        with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
            writer.writeheader()
            for r in remaining:
                writer.writerow({k: r.get(k, "") for k in RESULT_FIELDS})
    return deleted
