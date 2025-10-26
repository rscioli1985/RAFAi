#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.backend.models import (  # noqa: E402
    Organization,
    OrganizationMembership,
    Role,
    User,
    UserRole,
)
from services.common.db import SessionLocal  # noqa: E402


def seed_org(slug: str, name: str, description: str | None, owner_email: str) -> None:
    with SessionLocal() as session:
        org = session.query(Organization).filter(Organization.slug == slug).one_or_none()
        if org:
            org.name = name
            org.description = description
            print(f"[seed-org] Updated organization {slug}")
        else:
            org = Organization(slug=slug, name=name, description=description)
            session.add(org)
            session.flush()
            print(f"[seed-org] Created organization {slug}")

        user = session.query(User).filter(User.email == owner_email).one_or_none()
        if not user:
            raise SystemExit(f"User {owner_email} not found. Seed the user first.")

        membership = (
            session.query(OrganizationMembership)
            .filter(
                OrganizationMembership.organization_id == org.id,
                OrganizationMembership.user_id == user.id,
            )
            .one_or_none()
        )
        if membership is None:
            membership = OrganizationMembership(organization_id=org.id, user_id=user.id, title="Founder")
            session.add(membership)
            session.flush()
            print(f"[seed-org] Added membership for {owner_email}")
        else:
            print(f"[seed-org] Membership already exists for {owner_email}")

        role_slug = f"{slug}-owner"
        role = session.query(Role).filter(Role.slug == role_slug).one_or_none()
        if role is None:
            role = Role(
                name=f"{name} Owner",
                slug=role_slug,
                scope="organization",
                organization_id=org.id,
                description="Full administrative access for the organization.",
            )
            session.add(role)
            session.flush()
            print(f"[seed-org] Created role {role_slug}")

        assignment = (
            session.query(UserRole)
            .filter(UserRole.membership_id == membership.id, UserRole.role_id == role.id)
            .one_or_none()
        )
        if assignment is None:
            session.add(UserRole(membership_id=membership.id, role_id=role.id))
            print(f"[seed-org] Assigned role {role_slug} to {owner_email}")
        else:
            print(f"[seed-org] Role {role_slug} already assigned to {owner_email}")

        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed an organization and owner membership.")
    parser.add_argument("--slug", required=True, help="Organization slug, e.g., goanalog")
    parser.add_argument("--name", required=True, help="Organization name")
    parser.add_argument("--owner-email", required=True, help="Email of existing user to assign owner role")
    parser.add_argument("--description", default=None)
    args = parser.parse_args()

    seed_org(args.slug, args.name, args.description, args.owner_email)


if __name__ == "__main__":
    main()
