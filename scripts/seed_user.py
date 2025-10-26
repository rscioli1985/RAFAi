#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.backend.models import User  # noqa: E402
from services.common.db import SessionLocal  # noqa: E402
from services.common.security import hash_password  # noqa: E402


def seed_user(email: str, password: str, full_name: str | None, display_name: str | None) -> None:
    password_hash = hash_password(password)
    with SessionLocal() as session:
        user = session.query(User).filter(User.email == email).one_or_none()
        if user:
            user.password_hash = password_hash
            if full_name:
                user.full_name = full_name
            if display_name:
                user.display_name = display_name
            print(f"[seed] Updated existing user {email}")
        else:
            user = User(
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                display_name=display_name or full_name,
            )
            session.add(user)
            print(f"[seed] Created user {email}")
        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or update a user record.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--full-name", dest="full_name", default=None)
    parser.add_argument("--display-name", dest="display_name", default=None)
    args = parser.parse_args()

    seed_user(args.email, args.password, args.full_name, args.display_name)


if __name__ == "__main__":
    main()
