#!/usr/bin/env python3
"""Delete all business data while preserving user accounts and passwords.

Run from the repository root:
    python delete_business_data.py
"""

import sys
from app import create_app


def main():
    app = create_app()
    with app.app_context():
        from app.services.admin.data_service import AdminDataService
        from app.models.user import User

        print("WARNING: This will permanently delete ALL business data except user accounts, roles, and permissions.")
        confirmation = input("Type DELETE_ALL_DATA to proceed: ").strip()
        if confirmation != "DELETE_ALL_DATA":
            print("Confirmation failed. No data was deleted.")
            sys.exit(0)

        preserved_users = User.query.count()
        print(f"Preserving {preserved_users} user account(s).")

        try:
            AdminDataService.delete_all_data_except_users()
            preserved_users_after = User.query.count()
            if preserved_users_after == preserved_users:
                print("Success: business data has been deleted. User accounts remain intact.")
            else:
                print("Warning: the number of preserved users changed unexpectedly.")
            print(f"Preserved user accounts: {preserved_users_after}")
        except Exception as exc:
            print(f"Error deleting business data: {exc}")
            sys.exit(1)


if __name__ == "__main__":
    main()
