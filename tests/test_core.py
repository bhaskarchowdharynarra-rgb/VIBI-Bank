import tempfile
import unittest
from pathlib import Path
import sqlite3

from vibi_bank.core import BankService, BankingError


class BankServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.bank = BankService(Path(self.temp_dir.name) / "test.sqlite3")
        self.first = self.bank.register("Avery Example", "avery@example.test", "good-password-1")
        self.second = self.bank.register("Bailey Example", "bailey@example.test", "good-password-2")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registration_authentication_and_duplicate_email(self):
        self.assertTrue(self.first["account_number"].startswith("VIB"))
        self.assertEqual(self.first["account_type"], "everyday")
        self.assertEqual(self.bank.summary(self.first["user_id"])["account_type"], "everyday")
        self.assertEqual(
            self.bank.authenticate("AVERY@example.test", "good-password-1")["user_id"],
            self.first["user_id"],
        )
        with self.assertRaisesRegex(BankingError, "already exists"):
            self.bank.register("Another Name", "avery@example.test", "another-password")
        with self.assertRaisesRegex(BankingError, "incorrect"):
            self.bank.authenticate("avery@example.test", "wrong-password")

    def test_account_opening_profile_and_account_type_validation(self):
        account = self.bank.register(
            "  Taylor   Example ",
            "taylor@example.test",
            "good-password-3",
            phone="+91 98765 43210",
            address="12 Demo Street",
            city="Pune",
            state="Maharashtra",
            postal_code="411001",
            country="India",
            account_type="student",
        )
        self.assertEqual(account["name"], "Taylor Example")
        self.assertEqual(account["account_type"], "student")
        with self.assertRaisesRegex(BankingError, "phone number"):
            self.bank.register(
                "Jordan Example", "jordan@example.test", "good-password-4",
                phone="not-a-phone", address="12 Demo Street", city="Pune",
                state="Maharashtra", postal_code="411001", country="India",
            )
        with self.assertRaisesRegex(BankingError, "account types"):
            self.bank.register(
                "Morgan Example", "morgan@example.test", "good-password-5",
                phone="+91 98765 43210", address="12 Demo Street", city="Pune",
                state="Maharashtra", postal_code="411001", country="India",
                account_type="premium",
            )

    def test_existing_database_schema_is_migrated(self):
        database = Path(self.temp_dir.name) / "legacy.sqlite3"
        connection = sqlite3.connect(database)
        try:
            connection.executescript(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    full_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                    account_number TEXT NOT NULL UNIQUE,
                    balance_cents INTEGER NOT NULL DEFAULT 0 CHECK(balance_cents >= 0),
                    created_at TEXT NOT NULL
                );
                INSERT INTO users(id, email, full_name, password_hash, created_at)
                    VALUES (1, 'legacy@example.test', 'Legacy User', 'hash', '2025-01-01');
                INSERT INTO accounts(id, user_id, account_number, balance_cents, created_at)
                    VALUES (1, 1, 'VIB0000000001', 0, '2025-01-01');
                """
            )
        finally:
            connection.close()
        migrated_bank = BankService(database)
        summary = migrated_bank.summary(1)
        self.assertEqual(summary["account_type"], "everyday")
        self.assertEqual(summary["name"], "Legacy User")

    def test_deposit_withdraw_and_reject_invalid_amounts(self):
        self.bank.transact(self.first["user_id"], "deposit", "150.25")
        self.bank.transact(self.first["user_id"], "withdraw", "50.10")
        account = self.bank.summary(self.first["user_id"])
        self.assertEqual(account["balance"], "100.15")
        for invalid in ("0", "-2", "1.234", "NaN", "not money"):
            with self.subTest(amount=invalid):
                with self.assertRaises(BankingError):
                    self.bank.transact(self.first["user_id"], "deposit", invalid)
        with self.assertRaisesRegex(BankingError, "Insufficient"):
            self.bank.transact(self.first["user_id"], "withdraw", "100.16")

    def test_transfer_updates_both_accounts_and_records_activity(self):
        self.bank.transact(self.first["user_id"], "deposit", "100")
        self.bank.transact(
            self.first["user_id"], "transfer", "35.50", self.second["account_number"]
        )
        self.assertEqual(self.bank.summary(self.first["user_id"])["balance"], "64.50")
        self.assertEqual(self.bank.summary(self.second["user_id"])["balance"], "35.50")
        self.assertEqual(self.bank.transactions(self.second["user_id"])[0]["type"], "transfer_received")
        with self.assertRaisesRegex(BankingError, "own account"):
            self.bank.transact(
                self.first["user_id"], "transfer", "1", self.first["account_number"]
            )

    def test_loan_requests_are_recorded_without_changing_balance(self):
        self.bank.apply_for_loan(
            self.first["user_id"], "education", "5000", "student, ID card, admission letter"
        )
        self.bank.apply_for_loan(self.first["user_id"], "gold", "2000", "Gold, 12.5")
        self.bank.apply_for_loan(self.first["user_id"], "secured", "10000", "House Documents")
        applications = self.bank.loan_applications(self.first["user_id"])
        self.assertEqual(len(applications), 3)
        self.assertTrue(all(item["status"] == "Demo request received" for item in applications))
        self.assertEqual(self.bank.summary(self.first["user_id"])["balance"], "0.00")
        with self.assertRaisesRegex(BankingError, "two proofs"):
            self.bank.apply_for_loan(self.first["user_id"], "education", "5000", "student, ID card")


if __name__ == "__main__":
    unittest.main()
