"""Create a user from the command line when public registration is disabled."""

import argparse
import getpass
import sys

from database import SessionLocal, engine
import models
from auth import get_password_hash
import utils  # noqa: F401 — loads .env


def main():
    parser = argparse.ArgumentParser(description="Create a PDF Translator user account.")
    parser.add_argument("--username", required=True, help="Username (min 3 characters)")
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        sys.exit(1)
    if len(args.username.strip()) < 3:
        print("Username must be at least 3 characters.", file=sys.stderr)
        sys.exit(1)
    if len(password) < 6:
        print("Password must be at least 6 characters.", file=sys.stderr)
        sys.exit(1)

    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.username == args.username.strip()).first()
        if existing:
            print(f"User '{args.username}' already exists.", file=sys.stderr)
            sys.exit(1)

        user = models.User(
            username=args.username.strip(),
            hashed_password=get_password_hash(password),
        )
        db.add(user)
        db.commit()
        print(f"User '{args.username}' created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
