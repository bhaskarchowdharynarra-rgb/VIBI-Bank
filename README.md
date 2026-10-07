# VIBI Bank

VIBI Bank is a local banking **demo** with web, desktop, and command-line interfaces. All three interfaces use the same Python service and SQLite database, so demo profiles and simulated transactions are shared.

> **Not a real bank:** this project does not connect to financial institutions, payment networks, credit bureaus, or real-time payment services. Balances, transfers, and loan requests are fictional and have no monetary value. Do not enter real banking credentials or personal financial information.

## Requirements

- Python 3.10 or newer
- `pip` for installing Flask, used by the web interface
- Tkinter for the desktop interface (usually included with the standard Windows Python installer)

## Install

From the project directory, run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, run the venv's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Start an interface

```powershell
python -m vibi_bank web
python -m vibi_bank desktop
python -m vibi_bank cli
```

The web demo listens on `http://127.0.0.1:5000` by default. It is bound to the local machine; do not expose it to a public network. The desktop and CLI launch separately and use the same database.

## Demo features

- Open an Everyday, Savings, or Student demo account with a unique VIBI demo account number. The web sign-up collects a name, email, phone number, mailing address, and a password; account type is saved with the profile.
- Existing local databases are upgraded automatically to support the additional profile and account-type fields.
- Add or withdraw simulated funds, check balances, and transfer between demo accounts.
- View transaction history; the web dashboard refreshes activity every 10 seconds.
- Submit education, gold-pledge, and secured-loan demo requests. Requests are recorded as **demo requests received** only: no real eligibility decision, loan approval, or disbursement occurs.
- Passwords are salted and hashed with PBKDF2-HMAC-SHA256; monetary values are stored as integer paise in SQLite.

The web account-opening form requires explicit acknowledgment that it creates a local software demo profile only. Account types are illustrative and do not imply real-world rates, fees, eligibility, or banking services. The app does not collect government ID numbers or perform KYC. Use fictional information only.

By default, the database file is `vibi_bank.sqlite3` in the current working directory. Set `VIBI_DB_PATH` to use another local path. For the web interface, set `VIBI_SECRET_KEY` to a long random value for a stable session-signing key. The app generates a temporary key when one is not configured, which signs users out after a restart.

## Tests

```powershell
python -m unittest discover -s tests -v
```
