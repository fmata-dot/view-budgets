#!/usr/bin/env python3
"""
push_budgets_to_sql.py
------------------------------------------------------------------
Reads the Labor Budget Template and Census Budget Template tabs from
the Master Budget Templates Google Sheet, previews exactly what
would change, and -- only after you confirm -- calls
usp_UpsertLaborBudget / usp_UpsertCensusBudget in SQL Server for
each row.

This is a manual, run-it-yourself tool: nothing runs on a schedule,
and nothing is written to SQL Server without an explicit "yes" (or
the --yes flag, if you decide later to schedule it).

SETUP (one-time)
1. pip install -r requirements.txt
2. Install "ODBC Driver 18 for SQL Server" if it isn't already on
   this machine (Microsoft's own installer; search "ODBC Driver for
   SQL Server download").
3. In Google Cloud Console: create a service account, enable the
   Google Sheets API for that project, download the service
   account's JSON key, and share the "Master Budget Templates"
   sheet with the service account's email address (Viewer access is
   enough -- this script only reads the sheet).
4. Copy .env.example to .env and fill in your real values:
     GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_SHEET_ID,
     SQL_SERVER, SQL_DATABASE, SQL_USER, SQL_PASSWORD
5. Make sure upsert_labor_budget.sql and upsert_census_budget.sql
   have been run against your database (they create/replace the two
   stored procedures this script calls) -- and that the table names
   inside them match your real Labor/Census budget tables.
6. Run:  python push_budgets_to_sql.py
   Add --yes to skip the confirmation prompt once you trust it.

WHAT IT WON'T DO
- It won't guess at a FacilityID/PositionID you haven't filled in --
  rows missing a required field are reported and skipped, not
  guessed at.
- It won't touch a row's ID if you didn't set one -- blank ID means
  insert, exactly like the sheet's own instructions.
- It won't overwrite a row under an ID that doesn't exist -- the
  stored procedures raise an error instead, so a typo'd ID can't
  silently create an orphaned duplicate.
"""

import os
import sys

import gspread
import pyodbc
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

from budget_parsing import (
    build_preview,
    is_blank_row,
    parse_census_row,
    parse_labor_row,
)

load_dotenv()

LABOR_TAB = "Labor Budget Template"
CENSUS_TAB = "Census Budget Template"
HEADER_ROW = 2  # row 1 = instructional notes, row 2 = real column headers


def env(name):
    val = os.environ.get(name)
    if not val:
        print(f"Missing required setting '{name}'. Copy .env.example to .env and fill it in.")
        sys.exit(1)
    return val


def get_sheet_records(sheet_id, service_account_file, tab_name):
    creds = Credentials.from_service_account_file(
        service_account_file,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(tab_name)
    all_values = ws.get_all_values()

    headers = all_values[HEADER_ROW - 1]
    data_rows = all_values[HEADER_ROW:]

    records = []
    for row in data_rows:
        if is_blank_row(row):
            continue
        records.append(dict(zip(headers, row)))
    return records


def get_sql_connection(server, database, user, password):
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={server};DATABASE={database};"
        f"UID={user};PWD={password};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(conn_str)


def push_labor_row(cursor, row):
    cursor.execute(
        "{CALL dbo.usp_UpsertLaborBudget (?,?,?,?,?,?,?,?,?,?,?,?,?)}",
        row["id"], row["org"], row["facility_id"], row["facility_code"],
        row["position_id"], row["type"], row["input"], row["alt_ppd_input"],
        row["wage_amount"], row["weekend_work"], row["start_date"], row["end_date"],
        row["position_name"],
    )
    result = cursor.fetchone()
    return result.ResultID if result else None


def push_census_row(cursor, row):
    cursor.execute(
        "{CALL dbo.usp_UpsertCensusBudget (?,?,?,?,?,?,?,?)}",
        row["id"], row["org"], row["facility_id"], row["facility_code"],
        row["payer_type"], row["input"], row["start_date"], row["end_date"],
    )
    result = cursor.fetchone()
    return result.ResultID if result else None


def main():
    skip_confirm = "--yes" in sys.argv

    sheet_id = env("GOOGLE_SHEET_ID")
    service_account_file = env("GOOGLE_SERVICE_ACCOUNT_FILE")

    print("Reading Google Sheet...")
    labor_records = get_sheet_records(sheet_id, service_account_file, LABOR_TAB)
    census_records = get_sheet_records(sheet_id, service_account_file, CENSUS_TAB)

    labor_rows, errors = [], []
    for i, rec in enumerate(labor_records, start=HEADER_ROW + 1):
        try:
            labor_rows.append(parse_labor_row(rec))
        except ValueError as e:
            errors.append(f"Labor row {i}: {e}")

    census_rows = []
    for i, rec in enumerate(census_records, start=HEADER_ROW + 1):
        try:
            census_rows.append(parse_census_row(rec))
        except ValueError as e:
            errors.append(f"Census row {i}: {e}")

    if errors:
        print("\nSkipping rows with problems (fix these in the sheet and re-run):")
        for e in errors:
            print("  -", e)

    if not labor_rows and not census_rows:
        print("\nNothing valid to push. Exiting.")
        return

    print()
    if labor_rows:
        print(build_preview("labor", labor_rows))
    if census_rows:
        print(build_preview("census", census_rows))

    if not skip_confirm:
        answer = input("\nPush these to SQL Server? [y/N] ").strip().lower()
        if answer != "y":
            print("Cancelled -- nothing was written.")
            return

    print("\nConnecting to SQL Server...")
    conn = get_sql_connection(
        env("SQL_SERVER"), env("SQL_DATABASE"), env("SQL_USER"), env("SQL_PASSWORD")
    )
    cursor = conn.cursor()

    pushed, failed = 0, 0
    for row in labor_rows:
        try:
            result_id = push_labor_row(cursor, row)
            conn.commit()
            print(f"  OK   labor  -> ID {result_id}")
            pushed += 1
        except Exception as e:
            conn.rollback()
            print(f"  FAIL labor  (Facility {row['facility_id']}, Position {row['position_id']}): {e}")
            failed += 1

    for row in census_rows:
        try:
            result_id = push_census_row(cursor, row)
            conn.commit()
            print(f"  OK   census -> ID {result_id}")
            pushed += 1
        except Exception as e:
            conn.rollback()
            print(f"  FAIL census (Facility {row['facility_id']}, {row['payer_type']}): {e}")
            failed += 1

    conn.close()
    print(f"\nDone. {pushed} row(s) pushed, {failed} failed.")


if __name__ == "__main__":
    main()
