from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Iterator


class BankingError(Exception):
    """An expected, user-correctable banking operation error."""


class BankService:
    def __init__(self, database_path: str | Path | None = None) -> None:
        configured_path = database_path or os.environ.get("VIBI_DB_PATH", "vibi_bank.sqlite3")
        self.database_path = Path(configured_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._transaction() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    phone TEXT NOT NULL DEFAULT '',
                    address TEXT NOT NULL DEFAULT '',
                    city TEXT NOT NULL DEFAULT '',
                    state TEXT NOT NULL DEFAULT '',
                    postal_code TEXT NOT NULL DEFAULT '',
                    country TEXT NOT NULL DEFAULT 'India',
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                    account_number TEXT NOT NULL UNIQUE,
                    account_type TEXT NOT NULL DEFAULT 'everyday',
                    balance_cents INTEGER NOT NULL DEFAULT 0 CHECK(balance_cents >= 0),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL REFERENCES accounts(id),
                    transaction_type TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                    description TEXT NOT NULL,
                    related_account_number TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS loan_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    loan_type TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                    details TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Demo request received',
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS transactions_account_time
                    ON transactions(account_id, id DESC);
                """
            )
            user_columns = {
                    row["name"] for row in connection.execute("PRAGMA table_info(users)")
            }
            for column, definition in (
                    ("phone", "TEXT NOT NULL DEFAULT ''"),
                    ("address", "TEXT NOT NULL DEFAULT ''"),
                    ("city", "TEXT NOT NULL DEFAULT ''"),
                    ("state", "TEXT NOT NULL DEFAULT ''"),
                    ("postal_code", "TEXT NOT NULL DEFAULT ''"),
                    ("country", "TEXT NOT NULL DEFAULT 'India'"),
            ):
                    if column not in user_columns:
                        connection.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
            account_columns = {
                    row["name"] for row in connection.execute("PRAGMA table_info(accounts)")
            }
            if "account_type" not in account_columns:
                    connection.execute(
                        "ALTER TABLE accounts ADD COLUMN account_type TEXT NOT NULL DEFAULT 'everyday'"
                    )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _password_hash(password: str, salt: bytes | None = None) -> str:
        salt = salt or secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
        return f"{salt.hex()}:{digest.hex()}"

    @staticmethod
    def _valid_password(password: str) -> bool:
        return 10 <= len(password) <= 128

    @staticmethod
    def _amount_to_cents(amount: str | int | float | Decimal) -> int:
        try:
            value = Decimal(str(amount).strip())
            if not value.is_finite() or value <= 0:
                raise BankingError("Enter an amount greater than zero.")
            rounded = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if rounded != value:
                raise BankingError("Amounts can have no more than two decimal places.")
            cents = int(rounded * 100)
        except (InvalidOperation, ValueError):
            raise BankingError("Enter a valid amount.") from None
        if cents > 100_000_000_000:
            raise BankingError("The amount is above the demo transaction limit.")
        return cents

    @staticmethod
    def _account_number() -> str:
        return f"VIB{secrets.randbelow(10_000_000_000):010d}"

    def register(
        self,
        full_name: str,
        email: str,
        password: str,
        *,
        phone: str = "",
        address: str = "",
        city: str = "",
        state: str = "",
        postal_code: str = "",
        country: str = "",
        account_type: str = "everyday",
    ) -> dict:
        name = " ".join(full_name.split())
        normalized_email = email.strip().lower()
        if len(name) < 2 or len(name) > 100:
            raise BankingError("Enter a name between 2 and 100 characters.")
        if len(normalized_email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized_email):
            raise BankingError("Enter a valid email address.")
        if not self._valid_password(password):
            raise BankingError("Use a password between 10 and 128 characters.")
        normalized_phone = " ".join(phone.split())
        normalized_address = " ".join(address.split())
        normalized_city = " ".join(city.split())
        normalized_state = " ".join(state.split())
        normalized_postal_code = postal_code.strip().upper()
        normalized_country = " ".join(country.split())
        has_profile_details = any((
            normalized_phone, normalized_address, normalized_city, normalized_state,
            normalized_postal_code, normalized_country,
        ))
        if has_profile_details:
            if (
                not 7 <= len(normalized_phone) <= 20
                or not re.fullmatch(r"\+?[0-9() .-]+", normalized_phone)
                or not 7 <= sum(character.isdigit() for character in normalized_phone) <= 15
            ):
                raise BankingError("Enter a valid phone number with 7 to 15 digits.")
            if not 5 <= len(normalized_address) <= 150:
                raise BankingError("Enter a street address between 5 and 150 characters.")
            if not 2 <= len(normalized_city) <= 80:
                raise BankingError("Enter a city or town between 2 and 80 characters.")
            if not 2 <= len(normalized_state) <= 80:
                raise BankingError("Enter a state or region between 2 and 80 characters.")
            if not re.fullmatch(r"[A-Z0-9][A-Z0-9 -]{1,11}", normalized_postal_code):
                raise BankingError("Enter a valid postal code.")
            if not 2 <= len(normalized_country) <= 60:
                raise BankingError("Enter a country between 2 and 60 characters.")
        if account_type not in {"everyday", "savings", "student"}:
            raise BankingError("Choose one of the available demo account types.")

        password_hash = self._password_hash(password)
        with self._transaction() as connection:
            try:
                cursor = connection.execute(
                    "INSERT INTO users(email, full_name, phone, address, city, state, postal_code, "
                    "country, password_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        normalized_email, name, normalized_phone, normalized_address,
                        normalized_city, normalized_state, normalized_postal_code,
                        normalized_country, password_hash, self._now(),
                    ),
                )
            except sqlite3.IntegrityError as error:
                if "users.email" in str(error):
                    raise BankingError("An account with that email already exists.") from None
                raise
            user_id = cursor.lastrowid
            while True:
                account_number = self._account_number()
                try:
                    connection.execute(
                        "INSERT INTO accounts(user_id, account_number, account_type, balance_cents, "
                        "created_at) VALUES (?, ?, ?, 0, ?)",
                        (user_id, account_number, account_type, self._now()),
                    )
                    break
                except sqlite3.IntegrityError as error:
                    if "accounts.account_number" not in str(error):
                        raise
            return self._summary(connection, user_id)

    def authenticate(self, email: str, password: str) -> dict:
        normalized_email = email.strip().lower()
        with self._transaction() as connection:
            user = connection.execute(
                "SELECT id, password_hash FROM users WHERE email = ?", (normalized_email,)
            ).fetchone()
            if user is None:
                raise BankingError("Email or password is incorrect.")
            salt_hex, expected_hex = user["password_hash"].split(":", 1)
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 600_000
            )
            if not hmac.compare_digest(actual.hex(), expected_hex):
                raise BankingError("Email or password is incorrect.")
            return self._summary(connection, user["id"])

    def summary(self, user_id: int) -> dict:
        with self._transaction() as connection:
            return self._summary(connection, user_id)

    @staticmethod
    def _summary(connection: sqlite3.Connection, user_id: int) -> dict:
        row = connection.execute(
            """
            SELECT users.id, users.full_name, users.email, accounts.account_number,
                   accounts.account_type, accounts.balance_cents, accounts.created_at
            FROM users JOIN accounts ON accounts.user_id = users.id
            WHERE users.id = ?
            """,
            (user_id,),
        ).fetchone()
        if row is None:
            raise BankingError("Account not found. Please sign in again.")
        return {
            "user_id": row["id"],
            "name": row["full_name"],
            "email": row["email"],
            "account_number": row["account_number"],
            "account_type": row["account_type"],
            "balance": f"{row['balance_cents'] / 100:.2f}",
            "created_at": row["created_at"],
        }

    @staticmethod
    def _account_for_user(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row:
        account = connection.execute(
            "SELECT id, account_number, balance_cents FROM accounts WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if account is None:
            raise BankingError("Account not found. Please sign in again.")
        return account

    def transact(self, user_id: int, action: str, amount: str | int | float | Decimal,
                 recipient_account: str | None = None) -> dict:
        cents = self._amount_to_cents(amount)
        with self._transaction() as connection:
            account = self._account_for_user(connection, user_id)
            account_id = account["id"]
            account_number = account["account_number"]

            if action == "deposit":
                connection.execute(
                    "UPDATE accounts SET balance_cents = balance_cents + ? WHERE id = ?",
                    (cents, account_id),
                )
                self._record(connection, account_id, "deposit", cents, "Demo deposit")
            elif action == "withdraw":
                if account["balance_cents"] < cents:
                    raise BankingError("Insufficient demo balance.")
                connection.execute(
                    "UPDATE accounts SET balance_cents = balance_cents - ? WHERE id = ?",
                    (cents, account_id),
                )
                self._record(connection, account_id, "withdrawal", cents, "Demo withdrawal")
            elif action == "transfer":
                destination_number = (recipient_account or "").strip().upper()
                if destination_number == account_number:
                    raise BankingError("You cannot transfer to your own account.")
                recipient = connection.execute(
                    "SELECT id, account_number FROM accounts WHERE account_number = ?",
                    (destination_number,),
                ).fetchone()
                if recipient is None:
                    raise BankingError("The recipient VIBI demo account was not found.")
                if account["balance_cents"] < cents:
                    raise BankingError("Insufficient demo balance.")
                connection.execute(
                    "UPDATE accounts SET balance_cents = balance_cents - ? WHERE id = ?",
                    (cents, account_id),
                )
                connection.execute(
                    "UPDATE accounts SET balance_cents = balance_cents + ? WHERE id = ?",
                    (cents, recipient["id"]),
                )
                self._record(connection, account_id, "transfer", cents,
                             f"Transfer to {destination_number}", destination_number)
                self._record(connection, recipient["id"], "transfer_received", cents,
                             f"Transfer from {account_number}", account_number)
            else:
                raise BankingError("Choose a supported transaction.")
            return self._summary(connection, user_id)

    @staticmethod
    def _record(connection: sqlite3.Connection, account_id: int, kind: str, cents: int,
                description: str, related_account_number: str | None = None) -> None:
        connection.execute(
            "INSERT INTO transactions(account_id, transaction_type, amount_cents, description, "
            "related_account_number, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (account_id, kind, cents, description, related_account_number, BankService._now()),
        )

    def transactions(self, user_id: int, limit: int = 20) -> list[dict]:
        with self._transaction() as connection:
            account = self._account_for_user(connection, user_id)
            rows = connection.execute(
                """
                SELECT transaction_type, amount_cents, description, related_account_number, created_at
                FROM transactions WHERE account_id = ? ORDER BY id DESC LIMIT ?
                """,
                (account["id"], max(1, min(int(limit), 100))),
            ).fetchall()
            return [
                {
                    "type": row["transaction_type"],
                    "amount": f"{row['amount_cents'] / 100:.2f}",
                    "description": row["description"],
                    "related_account_number": row["related_account_number"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def apply_for_loan(self, user_id: int, loan_type: str, amount: str,
                       details: str) -> None:
        loan_type = loan_type.strip().lower()
        normalized_details = " ".join(details.split())
        if loan_type not in {"education", "gold", "secured"}:
            raise BankingError("Choose a supported demo loan type.")
        if len(normalized_details) < 2 or len(normalized_details) > 300:
            raise BankingError("Add the requested eligibility details (up to 300 characters).")
        cents = self._amount_to_cents(amount)
        if loan_type == "education":
            detail_parts = [part.strip() for part in normalized_details.split(",") if part.strip()]
            if len(detail_parts) < 3 or detail_parts[0].casefold() != "student":
                raise BankingError("Education demo requests require student status and two proofs.")
        elif loan_type == "gold":
            parts = normalized_details.split(",")
            if len(parts) < 2 or parts[0].casefold() != "gold":
                raise BankingError("Gold demo requests require gold and a quantity in grams.")
            try:
                quantity = Decimal(parts[1].strip())
            except InvalidOperation:
                raise BankingError("Enter a valid gold quantity in grams.") from None
            if not quantity.is_finite() or quantity <= 0:
                raise BankingError("Gold quantity must be greater than zero.")
        else:
            collateral = normalized_details.casefold()
            if not any(item in collateral for item in
                       ("house documents", "farm documents", "property documents")):
                raise BankingError("Secured demo requests require house, farm, or property documents.")

        with self._transaction() as connection:
            connection.execute(
                "INSERT INTO loan_applications(user_id, loan_type, amount_cents, details, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, loan_type, cents, normalized_details, self._now()),
            )

    def loan_applications(self, user_id: int, limit: int = 10) -> list[dict]:
        with self._transaction() as connection:
            rows = connection.execute(
                "SELECT loan_type, amount_cents, status, created_at FROM loan_applications "
                "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, max(1, min(int(limit), 100))),
            ).fetchall()
            return [
                {
                    "type": row["loan_type"],
                    "amount": f"{row['amount_cents'] / 100:.2f}",
                    "status": row["status"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
