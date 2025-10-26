# GraphQL Entity Model — Organizations & Access Control

## Objectives
- Provide a consistent GraphQL schema for front-end clients to read/write organizational data.
- Align GraphQL types with SQLAlchemy models (`Organization`, `User`, `OrganizationMembership`, `Role`, `Permission`, `UserRole`).
- Support authorization guardrails by exposing permissions-derived capabilities in responses.

## Core Types
- `User`: id (UUID), email, fullName, displayName, isActive, lastSeenAt, memberships: `[OrganizationMembership!]`.
- `Organization`: id, name, slug, description, status, createdAt, updatedAt, members: `[OrganizationMembership!]`, roles: `[Role!]`.
- `OrganizationMembership`: id, organization, user, title, status, joinedAt, roles: `[Role!]`.
- `Role`: id, slug, name, description, scope, permissions: `[Permission!]`.
- `Permission`: id, code, name, description.
- `UserRole`: derived type (role + assignedAt); exposed via `OrganizationMembership.roles`.

## Queries
1. `viewer`: returns current `User` plus computed permissions.
2. `organizationBySlug(slug: String!)`: fetch single organization with paginated members.
3. `organizations(first:Int, after:String)`: list organizations current user can access.
4. `organizationMembers(orgId: UUID!, first:Int, after:String, roleSlug:String)`: cursor-based member listing with optional role filtering.
5. `roles(orgId: UUID)`: global + org-specific roles; include attached permissions.

## Mutations
1. `createOrganization(name, slug, description)`: auto-create membership + owner role assignment.
2. `inviteMember(orgId, email, roleSlugs[])`: create pending membership; email handled separately.
3. `updateMemberRoles(membershipId, roleSlugs[])`: replace assignments transactionally.
4. `updateOrganization(input)` and `deactivateOrganization`.
5. `createRole` / `updateRolePermissions` for custom org roles.

All mutations enforce authorization via permission checks resolved from `UserRole -> Role -> Permission`.

## Resolver/Service Strategy
- Implement Strawberry (preferred) or Ariadne schema layer within `services/backend/graphql/`.
- Reuse SQLAlchemy session from `services.common.db.get_session`.
- Map ORM models to Pydantic/GraphQL types via dataclass transformations to avoid N+1; use dataloaders keyed by ids.
- Authorization middleware:
  - Resolve viewer from request (API key or future auth).
  - Preload user memberships + roles and cache `permission_codes` in context.
  - Declarative decorator `@requires_permission("org.manage_members")`.

## Roadmap
1. Scaffold GraphQL app (router mounted at `/graphql`, with GraphiQL in non-prod).
2. Implement base schema + viewer/org queries.
3. Add pagination utilities + dataloaders.
4. Layer in mutations with optimistic concurrency (e-tags or updated_at checks).
5. Add tests (unit for resolvers, integration with TestClient and in-memory DB).
