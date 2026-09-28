# Setup, running, and testing (detailed)

This is the detailed companion to the top-level README. Start there for
a quick overview; come here when you're actually setting this up.

## One-time setup

**1. SQL Server side**

Run the four files in `sql/`, in order, against your database (SSMS,
Azure Data Studio, or `sqlcmd`) — skip `00_create_database.sql` if
you're pointing at a database that already exists. `02` and `03` use
`CREATE OR ALTER`, so re-running them later to make changes is safe.

**Check the table names and columns in `01_schema.sql` match your real
`LaborBudget`/`CensusBudget` tables first** — they're written against
the schema from the Google Sheet template, but this repo doesn't have
the actual production table DDL, so double-check types/nullability
before running any of this against production.

**2. Google service account** (lets the script *read* the sheet — it
never needs write access to the sheet itself)

- In [Google Cloud Console](https://console.cloud.google.com), create
  or pick a project, enable the **Google Sheets API**, then create a
  **Service Account** and download its JSON key.
- Open the Master Budget Templates sheet, click **Share**, and add the
  service account's email (looks like
  `something@project-id.iam.gserviceaccount.com`) as a **Viewer**.
- Save the downloaded JSON key file somewhere on your machine (not
  inside a shared/synced folder, and never commit it — it's already
  gitignored as `service-account.json`).

**3. Python environment**

```
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

(`requirements.txt` also works with plain `pip install -r requirements.txt`
if you'd rather skip the virtual env / editable install.)

You'll also need the **ODBC Driver 18 for SQL Server** installed
(Microsoft's installer — search "ODBC Driver for SQL Server download"
if it's not already on this machine; SSMS being installed doesn't
guarantee the driver is).

**4. Configuration**

For a real run:
```
copy .env.example .env
```
For a local test run against Docker instead:
```
copy .env.test.example .env.test
```
Then fill in the real service-account file path and SQL Server login
details. `GOOGLE_SHEET_ID` is already set — to the real Master Budget
Templates sheet in `.env.example`, and to the safe TEST COPY sheet in
`.env.test.example`.

## Running it

```
python -m budget_sync.push
```

It will:

1. Read both tabs, skipping blank rows.
2. Report (and skip) any row missing a required field, so a bad row
   never silently drops data or crashes the run.
3. Print a preview like:
   ```
   LABOR BUDGET -- 2 row(s) to push:
     INSERT FacilityID=205 PositionID=31 Type=FTE Input=2.0 (2026-09-01 to 2026-09-30)
     UPDATE FacilityID=205 PositionID=87 Type=HPPD Input=1.8 (2026-01-01 to 2026-12-31)
   ```
4. Ask `Push these changes to SQL Server? [y/N]` — nothing happens
   until you type `y`.
5. Call the stored procedure for each row, committing one at a time,
   and report OK/FAIL per row so one bad row never blocks the rest of
   the batch.

Useful flags:
- `--env-file .env.test` — run against the local Docker test env
  instead of production (see `testing-guide.md`).
- `--yes` — skip the confirmation prompt, for later unattended runs.
  Not recommended until you've trusted this on a handful of manual
  runs first.

## Testing

`testing-guide.md` has the full walkthrough. Short version:

- `pytest` runs the pure-logic unit tests — no credentials, no SQL
  Server, no network needed. This also runs automatically in GitHub
  Actions on every push (`.github/workflows/ci.yml`).
- For an actual end-to-end dry run (real sheet reading, real writes),
  `docker compose up` in `docker/` gives you a throwaway local SQL
  Server to point `push.py` at, alongside the TEST COPY of the sheet —
  so you can confirm this reads and writes correctly before it ever
  touches the production database.

## Why a stored procedure instead of raw INSERT/UPDATE from Python

Keeps the insert-vs-update decision (blank ID → insert, existing ID →
update, unknown ID → error rather than silent duplicate) as one tested
piece of logic in the database, callable the same way from this
script, from SSMS directly, or from anything else later (Power
Automate, a future web tool) — instead of re-implementing that logic
in every client.

## What's been verified vs. what's still untested

The `parsing.py` unit tests (field validation, HPPD/FTE checking,
ID-present-vs-blank logic, the preview text) have actually been run
(12/12 passing), not just syntax-checked.

This has **not** been run against the real Google Sheet, a real SQL
Server, or the actual production table schema — no credentials for
either exist outside Frank's own environment. Use the Docker test env
against the TEST COPY sheet first, and run `push.py` once against a
couple of test rows before trusting it with real budget data.
