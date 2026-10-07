from __future__ import annotations

from getpass import getpass

from .core import BankService, BankingError


def _show_account(bank: BankService, user_id: int) -> None:
    account = bank.summary(user_id)
    print(f"\nVIBI Bank demo account · {account['account_number']}")
    print(f"Account holder: {account['name']}")
    print(f"Available demo balance: ₹{account['balance']}\n")


def _run_transaction(bank: BankService, user_id: int, action: str) -> None:
    amount = input("Amount (INR): ").strip()
    recipient = input("Recipient VIBI demo account number: ").strip() if action == "transfer" else None
    account = bank.transact(user_id, action, amount, recipient)
    print(f"Demo transaction complete. Updated balance: ₹{account['balance']}")


def _loan_request(bank: BankService, user_id: int) -> None:
    print("1. Education  2. Gold pledge  3. Secured")
    selection = input("Select request type: ").strip()
    loan_type = {"1": "education", "2": "gold", "3": "secured"}.get(selection)
    if loan_type is None:
        raise BankingError("Choose 1, 2, or 3.")
    amount = input("Requested amount (INR): ").strip()
    if loan_type == "education":
        details = input("Student status and two proofs (comma separated): ")
    elif loan_type == "gold":
        details = input("Gold and quantity in grams (example: Gold, 12.5): ")
    else:
        details = input("Collateral document type: ")
    bank.apply_for_loan(user_id, loan_type, amount, details)
    print("Demo loan request received; no real loan is approved or funded.")


def run() -> None:
    bank = BankService()
    print("VIBI BANK · LOCAL DEMO ONLY\n")
    while True:
        selection = input("1. Sign in  2. Create demo account  0. Exit\nChoice: ").strip()
        if selection == "0":
            return
        try:
            if selection == "2":
                account = bank.register(
                    input("Full name: "),
                    input("Email: "),
                    getpass("Password (10+ characters): "),
                )
                user_id = account["user_id"]
                print(f"Demo account created: {account['account_number']}")
            elif selection == "1":
                account = bank.authenticate(input("Email: "), getpass("Password: "))
                user_id = account["user_id"]
            else:
                print("Choose 0, 1, or 2.")
                continue
        except BankingError as error:
            print(f"Unable to continue: {error}")
            continue

        while True:
            try:
                _show_account(bank, user_id)
                print("1. Add demo funds  2. Withdraw  3. Check balance")
                print("4. Transfer  5. Request a demo loan  6. Recent activity  0. Sign out")
                choice = input("Choice: ").strip()
                if choice == "0":
                    break
                if choice == "1":
                    _run_transaction(bank, user_id, "deposit")
                elif choice == "2":
                    _run_transaction(bank, user_id, "withdraw")
                elif choice == "3":
                    _show_account(bank, user_id)
                elif choice == "4":
                    _run_transaction(bank, user_id, "transfer")
                elif choice == "5":
                    _loan_request(bank, user_id)
                elif choice == "6":
                    activity = bank.transactions(user_id)
                    if not activity:
                        print("No demo activity yet.")
                    for item in activity:
                        print(f"{item['created_at']} · {item['description']} · ₹{item['amount']}")
                else:
                    print("Choose a listed option.")
            except BankingError as error:
                print(f"Request not completed: {error}")


if __name__ == "__main__":
    run()
