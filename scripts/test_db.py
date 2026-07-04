"""Test DATABASE_URL and create tables if missing."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from database import DATABASE_URL, engine
import models

def main():
    print(f"URL host: {DATABASE_URL.split('@')[-1].split('/')[0]}")
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
        print("connection: OK")
    models.Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")
        ).fetchall()
        if rows:
            print("tables:", [r[0] for r in rows])
        else:
            print("tables: (sqlite or empty)")


if __name__ == "__main__":
    main()
