# Identity and Users

The common identity vocabulary -- users, the groups and organizations they belong to, the roles and permissions they hold, the invitations that bring them in and the API keys they use -- distilled from the APIs that already exist. Cross-cutting: almost every other context has users, and this is where their shape is measured. Part of [Schema Commons](https://github.com/api-commons/schema-commons),
published by the [API Commons](https://apicommons.org).

Built from the providers tagged Identity, Authentication, Identity Federation, Access Control, IAM, Identity and Access Management, SSO, Single Sign-On, User Management, Authorization, CIAM in [APIs.io](https://apis.io) that
publish their own OpenAPI. Only harvested contracts count -- nothing API Evangelist
generated. Every number below is a count of providers.

## What the market already agrees on

<!-- commons:summary -->
| Concept | Expose it | Readable schema | Core properties (share) | Collection named |
| --- | ---: | ---: | --- | --- |
| user | 185 | 167 | id 84%, email 70%, name 51% | users 135, members 54, user 45, identities 14 |
| group | 84 | 76 | id 84%, name 78%, description 50% | groups 67, teams 15, group 12, team 6 |
| organization | 60 | 57 | name 84%, id 74%, created_at 51% | organizations 31, organization 12, tenants 11, org 9 |
| role | 63 | 58 | id 78%, name 78%, description 60% | roles 59, role 11 |
| permission | 46 | 40 | id 62%, name 62%, description 52% | permissions 29, scopes 20, entitlements 6, permission 4 |
| invite | 34 | 30 | email 73%, id 70%, role 63% | invitations 15, invite 11, invites 11, invitation 1 |
| api_key | 25 | 21 | id 90%, created_at 76%, key 71%, name 71% | tokens 10, api-keys 8, apikeys 3, keys 3 |

Cohort: 443 providers with harvested OpenAPI, 185 crosswalks. Of the providers exposing a user: 65% create, 85% list, 75% fetch, 53% update, 53% delete. Generated 2026-11-11 by build.py.
<!-- /commons:summary -->

Shares are of the providers with a readable resource schema for that concept. The
extended tier and the long tail of every concept are in [profile.yml](profile.yml).

## What the measurement shows

- A user agrees on id, email and name -- and only just on name: SCIM nests it as an object, others split first and last name, others carry a display name, so the most common resource in the catalog agrees on less than a CRM contact does.
- Roles and groups agree on name, id and description -- and a third of roles reference their permissions: RBAC is the same shape everywhere.
- An invite agrees on email, id and the role it grants: the minimum to bring someone in.
- API keys agree on id, name, key and created_at once only unambiguous paths count.

## Artifacts

- [openapi.yml](openapi.yml) -- OpenAPI 3.1 of the shared operations. No one serves it; it
  is the shape to map to. Lints clean against the
  [naming ruleset](https://github.com/api-commons/schema-commons/blob/main/ruleset/schema-commons-naming.yaml).
- [arazzo.yml](arazzo.yml) -- reference workflows composed only of the shared operations (compositions, not measurements).
- [schema/](schema) -- JSON Schema 2020-12 per concept; each property carries
  `x-commons-tier`, `x-commons-share`, `x-commons-providers` and the spellings seen.
- [crosswalk/](crosswalk) -- one per provider, common name -> their name, with the harvested
  spec and operations each mapping was read from.
- [adopters.yml](adopters.yml) -- who exposes which concept, linked to their APIs.io page.
- [concepts.yml](concepts.yml) -- the only hand-written input: concepts, path segments and
  their qualifiers, aliases, reviewed exclusions, merged duplicates, and the decisions below.
- [census/](census) -- the cohort and the raw census the profile is built from.

## Decisions

These are calls, not measurements, recorded so they can be revisited as the method matures.

- `/accounts` is not a user: reviewed, it was brokerage, bank and ad-platform accounts.
- API keys count only as api_keys, personal_access_tokens, or keys and tokens beneath a user, account or project. Bare keys, tokens and credentials were verifiable credentials, door-access credentials and signing keys as often as API keys.
- OAuth scopes and entitlements count as permissions: each is a grantable unit of access.
- An organization covers tenants and workspaces -- the boundary users are members of -- but residential tenants (ButterflyMX) are excluded.
- Invites are `/invites`: invite and invites lead (22 providers) invitations (15).
- Duplicates merged: ConductorOne (C1), Cerner into Oracle Health, three Cvent listings, EVE Online into CCP Games, Dynamic, Kinde.

## Rebuild

```bash
../schema-commons/scripts/run.sh .
```

## License

Artifacts CC BY-NC-SA 4.0 ([LICENSE](LICENSE)); code Apache 2.0 ([LICENSE-CODE](LICENSE-CODE)).
