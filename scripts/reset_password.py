"""Reset a user's password in the database."""

import argparse
import getpass
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from database import SessionLocal, engine
import models
from auth import get_password_hash


def load_dotenv():
    env_path = os.path.join(ROOT, ".env")
    if not os.path.exists(env_path):
        return
    for line in open(env_path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main():
    parser = argparse.ArgumentParser(description="Reset password for an existing user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", help="New password (omit to prompt securely)")
    args = parser.parse_args()

    password = args.password or getpass.getpass("New password: ")
    if len(password) < 6:
        print("Password must be at least 6 characters.", file=sys.stderr)
        sys.exit(1)

    load_dotenv()
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.username == args.username.strip()).first()
        if not user:
            print(f"User '{args.username}' not found.", file=sys.stderr)
            sys.exit(1)
        user.hashed_password = get_password_hash(password)
        db.commit()
        print(f"Password updated for '{user.username}'.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
