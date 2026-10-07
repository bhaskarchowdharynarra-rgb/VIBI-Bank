from __future__ import annotations

import hmac
import os
import secrets
from functools import wraps

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for

from .core import BankService, BankingError


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SECRET_KEY=os.environ.get("VIBI_SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("VIBI_COOKIE_SECURE", "").lower() == "true",
        MAX_CONTENT_LENGTH=16 * 1024,
    )
    bank = BankService()
    app.extensions["vibi_bank"] = bank

    def csrf_token() -> str:
        if "csrf_token" not in session:
            session["csrf_token"] = secrets.token_urlsafe(32)
        return session["csrf_token"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_post_requests() -> None:
        if request.method == "POST":
            expected = session.get("csrf_token", "")
            supplied = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token", "")
            if not expected or not supplied or not hmac.compare_digest(expected, supplied):
                abort(400, description="Invalid or expired request token. Refresh and try again.")

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        return response

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please sign in to continue.", "info")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    @app.get("/")
    def index():
        return redirect(url_for("dashboard" if "user_id" in session else "login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            try:
                if request.form.get("demo_acknowledgement") != "yes":
                    raise BankingError("Please confirm that this is a demo account application.")
                summary = bank.register(
                    request.form.get("full_name", ""),
                    request.form.get("email", ""),
                    request.form.get("password", ""),
                    phone=request.form.get("phone", ""),
                    address=request.form.get("address", ""),
                    city=request.form.get("city", ""),
                    state=request.form.get("state", ""),
                    postal_code=request.form.get("postal_code", ""),
                    country=request.form.get("country", ""),
                    account_type=request.form.get("account_type", ""),
                )
                session.clear()
                session["user_id"] = summary["user_id"]
                session["csrf_token"] = secrets.token_urlsafe(32)
                flash("Your VIBI demo account is ready.", "success")
                return redirect(url_for("dashboard"))
            except BankingError as error:
                flash(str(error), "error")
        return render_template(
            "register.html",
            form_values=request.form if request.method == "POST" else {},
        )

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            try:
                summary = bank.authenticate(
                    request.form.get("email", ""),
                    request.form.get("password", ""),
                )
                session.clear()
                session["user_id"] = summary["user_id"]
                session["csrf_token"] = secrets.token_urlsafe(32)
                return redirect(url_for("dashboard"))
            except BankingError as error:
                flash(str(error), "error")
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        flash("You have been signed out.", "info")
        return redirect(url_for("login"))

    @app.get("/dashboard")
    @login_required
    def dashboard():
        user_id = session["user_id"]
        return render_template(
            "dashboard.html",
            account=bank.summary(user_id),
            transactions=bank.transactions(user_id, 8),
            applications=bank.loan_applications(user_id, 5),
        )

    @app.post("/transaction")
    @login_required
    def transaction():
        action = request.form.get("action", "")
        try:
            bank.transact(
                session["user_id"],
                action,
                request.form.get("amount", ""),
                request.form.get("recipient_account"),
            )
            flash("Demo transaction completed successfully.", "success")
        except BankingError as error:
            flash(str(error), "error")
        return redirect(url_for("dashboard"))

    @app.post("/loan")
    @login_required
    def loan():
        try:
            bank.apply_for_loan(
                session["user_id"],
                request.form.get("loan_type", ""),
                request.form.get("amount", ""),
                request.form.get("details", ""),
            )
            flash("Demo loan request received. No real credit decision or funds are involved.", "success")
        except BankingError as error:
            flash(str(error), "error")
        return redirect(url_for("dashboard") + "#loans")

    @app.get("/api/activity")
    @login_required
    def activity():
        user_id = session["user_id"]
        return jsonify(
            account=bank.summary(user_id),
            transactions=bank.transactions(user_id, 8),
            applications=bank.loan_applications(user_id, 5),
        )

    return app


def run() -> None:
    host = os.environ.get("VIBI_HOST", "127.0.0.1")
    port = int(os.environ.get("VIBI_PORT", "5000"))
    create_app().run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run()
