import argparse
from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.init import init_db
from app.db.session import SessionLocal
from app.models.user import User, UserRole


def create_admin(email: str, full_name: str) -> None:
    password = getpass("Admin password (minimum 8 characters): ")
    confirmation = getpass("Confirm admin password: ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    init_db()
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == email.lower()))
        if existing is not None:
            raise SystemExit("A user with that email already exists.")
        db.add(
            User(
                email=email.lower(),
                full_name=full_name,
                password_hash=hash_password(password),
                role=UserRole.ADMIN,
            )
        )
        db.commit()
    print(f"Created admin account for {email.lower()}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Attendance platform administration utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    admin_parser = subparsers.add_parser("create-admin", help="Create the first admin account")
    admin_parser.add_argument("--email", required=True)
    admin_parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.email, args.name)


if __name__ == "__main__":
    main()
