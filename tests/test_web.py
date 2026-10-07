import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibi_bank.web import create_app


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.environment = patch.dict(
            "os.environ",
            {
                "VIBI_DB_PATH": str(Path(self.temp_dir.name) / "web.sqlite3"),
                "VIBI_SECRET_KEY": "test-secret-key-that-is-long-enough",
            },
        )
        self.environment.start()
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.environment.stop()
        self.temp_dir.cleanup()

    def csrf_token(self, page: str) -> str:
        response = self.client.get(page)
        match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
        self.assertIsNotNone(match)
        return match.group(1).decode()

    def test_registration_dashboard_csrf_and_sign_out(self):
        token = self.csrf_token("/register")
        response = self.client.post(
            "/register",
            data={
                "csrf_token": token,
                "full_name": "Casey Example",
                "email": "casey@example.test",
                "phone": "+91 98765 43210",
                "password": "valid-demo-password",
                "address": "12 Demo Street",
                "city": "Pune",
                "state": "Maharashtra",
                "postal_code": "411001",
                "country": "India",
                "account_type": "savings",
                "demo_acknowledgement": "yes",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"TOTAL AVAILABLE BALANCE", response.data)
        self.assertIn(b"DEMO ENVIRONMENT", response.data)
        self.assertIn(b"VIBI Savings", response.data)
        token = self.csrf_token("/dashboard")
        transaction_response = self.client.post(
            "/transaction",
            data={"csrf_token": token, "action": "deposit", "amount": "24.50"},
            follow_redirects=True,
        )
        self.assertEqual(transaction_response.status_code, 200)
        activity = self.client.get("/api/activity")
        self.assertEqual(activity.status_code, 200)
        self.assertEqual(activity.json["account"]["balance"], "24.50")

        bad_post = self.client.post("/transaction", data={"action": "deposit", "amount": "50"})
        self.assertEqual(bad_post.status_code, 400)

        token = self.csrf_token("/dashboard")
        response = self.client.post(
            "/logout", data={"csrf_token": token}, follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sign in to VIBI", response.data)

    def test_registration_requires_demo_acknowledgement(self):
        token = self.csrf_token("/register")
        response = self.client.post(
            "/register",
            data={
                "csrf_token": token,
                "full_name": "Casey Example",
                "email": "casey@example.test",
                "phone": "+91 98765 43210",
                "password": "valid-demo-password",
                "address": "12 Demo Street",
                "city": "Pune",
                "state": "Maharashtra",
                "postal_code": "411001",
                "country": "India",
                "account_type": "everyday",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Please confirm that this is a demo account application.", response.data)
        self.assertIn(b'value="Casey Example"', response.data)


if __name__ == "__main__":
    unittest.main()
