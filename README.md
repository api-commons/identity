# Identity

De facto standards for the identity layer, published by the
[API Commons](https://apicommons.org).

This repository is different from the other five in this programme, and the difference
is the reason it exists.

S3, the OpenAI API, CKAN's Action API and Ethereum JSON-RPC became standards by being
copied. No specification exists to check anyone against, so a profile IS the
specification. SCIM was ratified in 2015. RFC 7643 and RFC 7644 have said what a SCIM
server is for a decade, and publishing a description of SCIM would add nothing at all.

What is missing is the other axis. Every operation here carries two gradings: what the
RFC says about it, quoted with its section, and what the industry actually declares,
measured the same way as every other profile here. The gap between them is the artifact.

## The measured core

| Operation | Declaring | Share |
| --- | ---: | ---: |
| `GET /Users` | 53 | 68.8% |
| `POST /Users` | 52 | 67.5% |
| `GET /Users/{id}` | 51 | 66.2% |
| `PUT /Users/{id}` | 46 | 59.7% |
| `DELETE /Users/{id}` | 42 | 54.5% |

Five operations, all of them on /Users. Group management does not reach the core at all:
GET /Groups sits at 45.5%, barely two-thirds the rate of GET /Users. A client that
provisions users can rely on this surface; one that also manages group membership is
relying on something half the field publishes.

And PATCH — the operation SCIM defines for incremental change, and the one an identity
provider reaches for on every attribute update — is declared by 49.4%. It misses the
core tier by a single percentage point.

## Discovery is optional, and rare

| Discovery endpoint | Declaring | Share |
| --- | ---: | ---: |
| `GET /ResourceTypes` | 29 | 37.7% |
| `GET /Schemas` | 29 | 37.7% |
| `GET /ServiceProviderConfig` | 26 | 33.8% |
| `GET /Schemas/{id}` | 21 | 27.3% |
| `GET /ResourceTypes/{id}` | 15 | 19.5% |

These three endpoints are the ONLY mechanism a SCIM client has for adapting to a
server's capabilities. About a third of the measured cohort declares them.

The obvious thing to write here is that the RFC requires them and implementers ignore
it. That would be wrong, and checking is what stopped this profile from saying it. RFC
7644 Section 4 introduces all three with “MAY be retrieved using HTTP GET”, and uses
SHALL only for the SHAPE of the response if one comes — /Schemas “SHALL return all
supported schemas in ListResponse format”. There is no obligation to implement them.

So the finding is worse than non-compliance, not better: the specification made its own
discovery mechanism optional, most of the field declined it, and no one is in violation.
A SCIM client cannot rely on discovery and has no grounds to complain.

## Read the cohort

368 providers in the API Evangelist catalog mention SCIM — the largest claim cohort of
any standard in this programme. 77 publish an OpenAPI containing a SCIM path, and that
is the denominator for every share above. Of those, 51 declare at least one operation
from RFC 7644 Table 2; the rest publish something SCIM-shaped that does not map to the
standard surface, which is itself worth knowing.

A SCIM endpoint is an identity surface and every operation on it is authenticated. There
is no anonymous discriminator, so no `tested` grade is available — the same structural
limit as S3, for the same reason.

Evidence across 320 registry entries: **51 declared**, **269 prose**.

## What's here

```
standard/scim-2.0/
  profile.yml     24 operations, each with its RFC citation AND its measured tier
  openapi.yml     the artifact of record — SCIM is the one standard here OpenAPI fits cleanly
  schema/         JSON Schema 2020-12 for User, Group, ListResponse, Error and Meta
  mcp/tools.json  MCP tool definitions for the measured core
  arazzo/         discover, create, read, delete — and it runs even if discovery fails
  spectral/       generated from the profile, with fixtures and a harness
adopters/
  scim-2.0.yml    320 entries
  scim-2.0-matrix.md  operation by provider, with the normative column
scripts/          every artifact above is generated; none is hand-maintained
```

SCIM is the only standard in this programme whose OpenAPI is the artifact of record. S3
identifies operations by query subresource, Ethereum puts the method in a JSON body, and
CKAN hangs everything off one action path — each needed a labelled convenience or a
different format entirely. SCIM is ordinary REST with real paths.

## Check a provider

```
npx @stoplight/spectral-cli lint their-openapi.yaml \
  -r https://raw.githubusercontent.com/api-commons/identity/main/standard/scim-2.0/spectral/scim-profile.yaml
```

It checks the measured core as errors and discovery as a warning, because the RFC
compels one and not the other. Two more rules catch the mistakes that break generated
clients: a document that answers plain application/json rather than
application/scim+json, and an error `status` typed as an integer when RFC 7644 Section
3.12 carries it as a string.

**It does not check conformance to RFC 7644.** Filter syntax, PATCH semantics, sorting,
pagination and attribute mutability are all normative and none of them is visible in a
path. The RFC is the conformance authority; this measures interoperability with the SCIM
that exists.

## Provenance

Operations transcribed from RFC 7644 Section 3.2 Table 2. Every normative claim is
quoted from the RFC text with its section, not paraphrased. RFC 7643 and RFC 7644 are
IETF Standards Track documents; this profile quotes them and does not reproduce them.

Nothing here implies endorsement by the IETF or by any provider named in the registry.

## Part of API Commons

**Related**
- [adopters](https://github.com/api-commons/adopters) — the schema behind the registry
- [models](https://github.com/api-commons/models) · [blockchain](https://github.com/api-commons/blockchain) · [open-data](https://github.com/api-commons/open-data) · [storage](https://github.com/api-commons/storage)

## License

Artifacts are **[CC BY-NC-SA 4.0](LICENSE)**. Code in `scripts/` is **[Apache-2.0](LICENSE-CODE)**.
