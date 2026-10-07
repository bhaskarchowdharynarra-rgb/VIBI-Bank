from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .core import BankService, BankingError


NAVY = "#0b2033"
GREEN = "#26856c"
PALE = "#f3f6f5"


class VibiDesktop:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.bank = BankService()
        self.user_id: int | None = None
        self.root.title("VIBI Bank · Demo")
        self.root.geometry("920x660")
        self.root.minsize(760, 560)
        self.root.configure(bg=PALE)
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background=PALE)
        self.style.configure("TLabel", background=PALE, foreground=NAVY, font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground=NAVY)
        self.style.configure("Balance.TLabel", font=("Segoe UI", 28, "bold"), foreground=GREEN)
        self.style.configure("TButton", font=("Segoe UI", 10), padding=(11, 8))
        self.style.configure("Treeview", rowheight=32, font=("Segoe UI", 9))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))
        self.show_auth()

    def clear(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def show_auth(self) -> None:
        self.clear()
        frame = ttk.Frame(self.root, padding=48)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="VIBI BANK", font=("Segoe UI", 12, "bold"), foreground=GREEN).pack(anchor="w")
        ttk.Label(frame, text="Banking, in clear view.", style="Title.TLabel").pack(anchor="w", pady=(12, 4))
        ttk.Label(frame, text="Desktop banking experience · simulated account and funds").pack(anchor="w")
        form = ttk.Frame(frame, padding=(0, 28))
        form.pack(fill="x")
        self.auth_fields = {}
        for label, key, hidden in [
            ("Full name (for a new account)", "name", False),
            ("Email", "email", False),
            ("Password (10+ characters)", "password", True),
        ]:
            ttk.Label(form, text=label).pack(anchor="w", pady=(8, 4))
            entry = ttk.Entry(form, width=44, show="•" if hidden else "")
            entry.pack(anchor="w", ipady=5)
            self.auth_fields[key] = entry
        buttons = ttk.Frame(form)
        buttons.pack(anchor="w", pady=22)
        ttk.Button(buttons, text="Sign in", command=self.sign_in).pack(side="left", padx=(0, 9))
        ttk.Button(buttons, text="Create demo account", command=self.register).pack(side="left")
        ttk.Label(
            frame,
            text="DEMO ONLY — no real accounts, money, transfers, or loans. Never use a real banking password.",
            wraplength=680,
            foreground="#73818a",
        ).pack(anchor="w", side="bottom", pady=8)

    def sign_in(self) -> None:
        try:
            account = self.bank.authenticate(
                self.auth_fields["email"].get(), self.auth_fields["password"].get()
            )
            self.user_id = account["user_id"]
            self.show_dashboard()
        except BankingError as error:
            messagebox.showerror("Unable to sign in", str(error), parent=self.root)

    def register(self) -> None:
        try:
            account = self.bank.register(
                self.auth_fields["name"].get(),
                self.auth_fields["email"].get(),
                self.auth_fields["password"].get(),
            )
            self.user_id = account["user_id"]
            messagebox.showinfo(
                "Demo account created",
                f"Your VIBI demo account is {account['account_number']}.",
                parent=self.root,
            )
            self.show_dashboard()
        except BankingError as error:
            messagebox.showerror("Unable to create account", str(error), parent=self.root)

    def show_dashboard(self) -> None:
        if self.user_id is None:
            return
        self.clear()
        frame = ttk.Frame(self.root, padding=30)
        frame.pack(fill="both", expand=True)
        top = ttk.Frame(frame)
        top.pack(fill="x")
        ttk.Label(top, text="VIBI BANK", font=("Segoe UI", 12, "bold"), foreground=GREEN).pack(side="left")
        ttk.Button(top, text="Sign out", command=self.sign_out).pack(side="right")
        ttk.Label(frame, text="Account overview", style="Title.TLabel").pack(anchor="w", pady=(22, 2))
        self.name_label = ttk.Label(frame, text="")
        self.name_label.pack(anchor="w")
        self.balance_label = ttk.Label(frame, text="", style="Balance.TLabel")
        self.balance_label.pack(anchor="w", pady=(18, 2))
        self.account_label = ttk.Label(frame, text="")
        self.account_label.pack(anchor="w")
        buttons = ttk.Frame(frame)
        buttons.pack(anchor="w", pady=18)
        for text, action in [
            ("Add demo funds", "deposit"),
            ("Withdraw", "withdraw"),
            ("Transfer", "transfer"),
        ]:
            ttk.Button(buttons, text=text, command=lambda value=action: self.transact(value)).pack(
                side="left", padx=(0, 8)
            )
        ttk.Button(buttons, text="Request demo loan", command=self.loan).pack(side="left", padx=2)
        ttk.Button(buttons, text="Refresh", command=self.refresh).pack(side="left", padx=8)
        ttk.Label(frame, text="Recent activity").pack(anchor="w", pady=(10, 7))
        self.table = ttk.Treeview(frame, columns=("when", "description", "amount"), show="headings")
        self.table.heading("when", text="DATE")
        self.table.heading("description", text="DESCRIPTION")
        self.table.heading("amount", text="AMOUNT (INR)")
        self.table.column("when", width=200)
        self.table.column("description", width=420)
        self.table.column("amount", width=130, anchor="e")
        self.table.pack(fill="both", expand=True)
        ttk.Label(
            frame,
            text="Demo environment only. Balances and transactions have no real-world monetary value.",
            foreground="#73818a",
        ).pack(anchor="w", pady=(14, 0))
        self.refresh()

    def refresh(self) -> None:
        if self.user_id is None:
            return
        try:
            account = self.bank.summary(self.user_id)
            self.name_label.configure(text=f"Welcome, {account['name']}")
            self.balance_label.configure(text=f"₹{account['balance']}")
            self.account_label.configure(text=f"Demo account · {account['account_number']}")
            self.table.delete(*self.table.get_children())
            for item in self.bank.transactions(self.user_id, 30):
                self.table.insert(
                    "",
                    "end",
                    values=(item["created_at"], item["description"], f"₹{item['amount']}"),
                )
        except BankingError as error:
            messagebox.showerror("Unable to refresh", str(error), parent=self.root)

    def sign_out(self) -> None:
        self.user_id = None
        self.show_auth()

    def transact(self, action: str) -> None:
        if self.user_id is None:
            return
        amount = simpledialog.askstring("Demo transaction", "Amount in INR:", parent=self.root)
        if amount is None:
            return
        recipient = None
        if action == "transfer":
            recipient = simpledialog.askstring(
                "Demo transfer", "Recipient VIBI demo account number:", parent=self.root
            )
            if recipient is None:
                return
        try:
            self.bank.transact(self.user_id, action, amount, recipient)
            self.refresh()
            messagebox.showinfo("Completed", "Demo transaction completed.", parent=self.root)
        except BankingError as error:
            messagebox.showerror("Transaction not completed", str(error), parent=self.root)

    def loan(self) -> None:
        if self.user_id is None:
            return
        choice = simpledialog.askstring(
            "Demo loan request",
            "Type: education, gold, or secured",
            parent=self.root,
        )
        if choice is None:
            return
        loan_type = choice.strip().lower()
        amount = simpledialog.askstring("Demo loan request", "Requested amount (INR):", parent=self.root)
        if amount is None:
            return
        prompt = {
            "education": "Student status and two proofs, comma separated:",
            "gold": "Gold and quantity in grams (example: Gold, 12.5):",
            "secured": "Collateral document type:",
        }.get(loan_type, "Eligibility details:")
        details = simpledialog.askstring("Demo loan request", prompt, parent=self.root)
        if details is None:
            return
        try:
            self.bank.apply_for_loan(self.user_id, loan_type, amount, details)
            messagebox.showinfo(
                "Request received",
                "Demo request recorded. No real credit decision or funds are involved.",
                parent=self.root,
            )
        except BankingError as error:
            messagebox.showerror("Request not submitted", str(error), parent=self.root)


def run() -> None:
    root = tk.Tk()
    VibiDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    run()
