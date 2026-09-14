#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Derive the OpenAPI, JSON Schema, MCP and Arazzo artifacts from the SCIM profile.

SCIM is the one standard in this programme that OpenAPI describes cleanly. S3 identifies
operations by query subresource, Ethereum puts the method in a JSON body, and CKAN hangs
everything off one action path — all three needed a labelled convenience or a different
format of record. SCIM is ordinary REST with real paths, so the OpenAPI here IS the
artifact of record.
"""
import json
from datetime import date
from pathlib import Path

import yaml

try:
    Dumper = yaml.CSafeDumper
except AttributeError:
    Dumper = yaml.SafeDumper

HERE = Path(__file__).resolve().parent.parent
STD = HERE / "standard" / "scim-2.0"
SPDX_ART = "# SPDX-License-Identifier: CC-BY-NC-SA-4.0\n"
profile = yaml.safe_load((STD / "profile.yml").read_text())
ops = profile["operations"]
core = [o for o in ops if o["tier"] == "core"]
kept = [o for o in ops if o["tier"] in ("core", "extended")]

CORE_URN = "urn:ietf:params:scim:schemas:core:2.0"
MSG_URN = "urn:ietf:params:scim:api:messages:2.0"

COMMON = {
    "ListResponse": {
        "type": "object",
        "description": (f"RFC 7644 Section 3.4.2. Every query answers in this envelope, "
                        f"identified by {MSG_URN}:ListResponse."),
        "required": ["schemas", "totalResults"],
        "properties": {
            "schemas": {"type": "array", "items": {"const": f"{MSG_URN}:ListResponse"}},
            "totalResults": {"type": "integer"},
            "startIndex": {"type": "integer", "description": "1-based, not 0-based."},
            "itemsPerPage": {"type": "integer"},
            "Resources": {"type": "array", "items": {"type": "object"}},
        },
    },
    "Error": {
        "type": "object",
        "description": (f"RFC 7644 Section 3.12. Identified by {MSG_URN}:Error. `status` is "
                        "a STRING carrying the HTTP status code, which is a common source of "
                        "client bugs."),
        "required": ["schemas", "status"],
        "properties": {
            "schemas": {"type": "array", "items": {"const": f"{MSG_URN}:Error"}},
            "status": {"type": "string"},
            "scimType": {"type": "string",
                         "enum": ["invalidFilter", "tooMany", "uniqueness", "mutability",
                                  "invalidSyntax", "invalidPath", "noTarget", "invalidValue",
                                  "invalidVers", "sensitive"]},
            "detail": {"type": "string"},
        },
    },
    "User": {
        "type": "object",
        "description": (f"RFC 7643 Section 4.1. Core schema {CORE_URN}:User. Only `userName` "
                        "is REQUIRED: \"Each User MUST include a non-empty userName value... "
                        "This attribute is REQUIRED and is case insensitive.\""),
        "required": ["schemas", "userName"],
        "properties": {
            "schemas": {"type": "array", "items": {"type": "string"},
                        "description": f"Includes {CORE_URN}:User."},
            "id": {"type": "string", "readOnly": True},
            "externalId": {"type": "string"},
            "userName": {"type": "string"},
            "name": {"type": "object", "properties": {
                "formatted": {"type": "string"}, "familyName": {"type": "string"},
                "givenName": {"type": "string"}}},
            "displayName": {"type": "string"},
            "active": {"type": "boolean"},
            "emails": {"type": "array", "items": {"type": "object", "properties": {
                "value": {"type": "string"}, "type": {"type": "string"},
                "primary": {"type": "boolean"}}}},
            "meta": {"$ref": "#/components/schemas/Meta"},
        },
    },
    "Group": {
        "type": "object",
        "description": f"RFC 7643 Section 4.2. Core schema {CORE_URN}:Group.",
        "required": ["schemas", "displayName"],
        "properties": {
            "schemas": {"type": "array", "items": {"type": "string"}},
            "id": {"type": "string", "readOnly": True},
            "displayName": {"type": "string"},
            "members": {"type": "array", "items": {"type": "object", "properties": {
                "value": {"type": "string"}, "$ref": {"type": "string"},
                "type": {"type": "string"}}}},
            "meta": {"$ref": "#/components/schemas/Meta"},
        },
    },
    "Meta": {
        "type": "object",
        "description": "RFC 7643 Section 3.1 common attributes.",
        "properties": {
            "resourceType": {"type": "string"}, "created": {"type": "string"},
            "lastModified": {"type": "string"}, "location": {"type": "string"},
            "version": {"type": "string"},
        },
    },
}

paths = {}
for o in kept:
    body = None
    if o["resource"] in ("/Users", "/Me"):
        body = "User"
    elif o["resource"] == "/Groups":
        body = "Group"
    entry = {
        "operationId": (o["method"].lower()
                        + o["path"].replace("/", " ").replace("{id}", "ById").title()
                        .replace(" ", "").replace(".", "")),
        "summary": o["summary"],
        "description": (f"{o['evidence']}\n\nRFC 7644 Section {o['rfc_section']}. "
                        f"Normative force: **{o['normative_force']}** — {o['normative_citation']}"),
        "tags": [o["resource"].lstrip("/.") or "Root"],
        "x-tier": o["tier"],
        "x-rfc-section": o["rfc_section"],
        "x-normative-force": o["normative_force"],
        "x-providers-declaring": o["providers_declaring"],
        "responses": {
            "200": {"description": "Success.", "content": {"application/scim+json": {
                "schema": {"$ref": "#/components/schemas/"
                                   + ("ListResponse" if o["path"].endswith(("s", "Config"))
                                      and "{id}" not in o["path"] and o["method"] == "GET"
                                      else (body or "ListResponse"))}}}},
            "400": {"description": "SCIM error.", "content": {"application/scim+json": {
                "schema": {"$ref": "#/components/schemas/Error"}}}},
        },
    }
    if o["method"] in ("POST", "PUT", "PATCH") and body:
        entry["requestBody"] = {"required": True, "content": {"application/scim+json": {
            "schema": {"$ref": f"#/components/schemas/{body}"}}}}
    if "{id}" in o["path"]:
        entry["parameters"] = [{"name": "id", "in": "path", "required": True,
                                "schema": {"type": "string"},
                                "description": "The resource's service-provider id."}]
    paths.setdefault(o["path"], {})[o["method"].lower()] = entry

openapi = {
    "openapi": "3.1.0",
    "info": {
        "title": "SCIM 2.0 — API Commons profile",
        "summary": "SCIM as the industry actually implements it, beside what the RFC says.",
        "description": (
            "**SCIM is ratified, so this is not a description of the standard — RFC 7643 and "
            "RFC 7644 already are that.** This is the other axis: every operation carries "
            "`x-normative-force` quoting what the RFC says about it, and `x-tier` measuring "
            "what the industry declares.\n\n"
            "The gap is the artifact. SCIM's three discovery endpoints — the mechanism that "
            "would let a client adapt to a server's capabilities — are declared by about a "
            "third of implementers, and the RFC does not compel them, so a client cannot "
            "rely on discovery and has no grounds to complain.\n\n"
            f"Vendor-tier operations are graded in `profile.yml` and excluded here. "
            "Measured across "
            f"{profile['method']['cohort']} providers that publish a SCIM path, out of "
            f"{profile['method']['claimants']} that mention SCIM."
        ),
        "version": "2.0",
        "contact": {"name": "API Commons", "url": "https://apicommons.org"},
        "license": {"name": "CC-BY-NC-SA-4.0",
                    "url": "https://creativecommons.org/licenses/by-nc-sa/4.0/"},
    },
    "externalDocs": {"description": "RFC 7644 — SCIM Protocol",
                     "url": "https://www.rfc-editor.org/rfc/rfc7644"},
    "servers": [{"url": "https://{host}/scim/v2", "variables": {
        "host": {"default": "example.com", "description": "Any SCIM service provider."}}}],
    "tags": [{"name": t} for t in sorted({o["resource"].lstrip("/.") or "Root" for o in kept})],
    "paths": paths,
    "components": {"schemas": COMMON},
}
(STD / "openapi.yml").write_text(
    SPDX_ART + yaml.dump(openapi, Dumper=Dumper, sort_keys=False, width=100,
                         allow_unicode=True))

written = []
for name, schema in COMMON.items():
    doc = dict(schema)
    doc["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    doc["$id"] = ("https://raw.githubusercontent.com/api-commons/identity/main/"
                  f"standard/scim-2.0/schema/{name}.json")
    doc["title"] = f"SCIM {name}"
    (STD / "schema" / f"{name}.json").write_text(json.dumps(doc, indent=2) + "\n")
    written.append(f"{name}.json")

tools = []
for o in core:
    tools.append({
        "name": "scim_" + o["operation"].lower().replace(" ", "_").replace("/", "")
                .replace("{", "").replace("}", ""),
        "description": (f"{o['summary']} Core tier: declared by {o['percent_of_cohort']}% "
                        "of the measured cohort."),
        "inputSchema": {"type": "object", "required": ["base_url"], "properties": {
            "base_url": {"type": "string", "format": "uri",
                         "description": "The SCIM base URI, e.g. https://example.com/scim/v2"},
            "id": {"type": "string", "description": "Resource id, for single-resource operations."},
            "body": {"type": "object", "description": "SCIM resource for POST, PUT and PATCH."},
        }},
        "_meta": {"apicommons.org/standard": "scim-2.0", "apicommons.org/tier": "core",
                  "apicommons.org/operation": o["operation"],
                  "apicommons.org/rfc-section": o["rfc_section"],
                  "apicommons.org/auth": "Every SCIM operation is authenticated. There is no "
                                         "anonymous mode, which is why this profile has no "
                                         "tested grade."},
    })
(STD / "mcp" / "tools.json").write_text(json.dumps({
    "$comment": ("MCP tool definitions for the core tier of the SCIM 2.0 profile. Generated "
                 "by scripts/build-artifacts.py. SPDX-License-Identifier: CC-BY-NC-SA-4.0"),
    "standard": "scim-2.0", "tier": "core", "tools": tools}, indent=2) + "\n")

arazzo = {
    "arazzo": "1.0.1",
    "info": {
        "title": "SCIM 2.0 core conformance",
        "version": "1.0.0",
        "summary": "Ask the server what it supports, then provision and de-provision a user.",
        "description": (
            "The flow opens with GET /ServiceProviderConfig even though only about a third of "
            "the cohort declares it, because that is the point: a client that wants to adapt "
            "to a server's capabilities has exactly one mechanism, the RFC does not compel a "
            "server to provide it, and most do not. If step one fails, the rest of the flow "
            "still runs — the client is simply flying blind, which is the normal condition.\n\n"
            "Every operation is authenticated. Run it against a tenant you control: it "
            "creates a user and deletes it again."
        ),
    },
    "sourceDescriptions": [{"name": "profile", "url": "../openapi.yml", "type": "openapi"}],
    "workflows": [{
        "workflowId": "core-conformance",
        "summary": "ServiceProviderConfig, then create, read, and delete a User.",
        "description": "Every step is a core or discovery operation from RFC 7644 Table 2.",
        "inputs": {"type": "object", "properties": {
            "userName": {"type": "string", "default": "api-commons-conformance"}}},
        "steps": [
            {"stepId": "discover",
             "description": "GET /ServiceProviderConfig — declared by only a third of the cohort.",
             "operationId": "$sourceDescriptions.profile.getServiceproviderconfig",
             "successCriteria": [{"condition": "$statusCode == 200"}],
             "onFailure": [{"name": "continueBlind", "type": "goto", "stepId": "createUser",
                            "criteria": [{"condition": "$statusCode != 200"}]}]},
            {"stepId": "createUser", "description": "POST /Users — the operation everyone has.",
             "operationId": "$sourceDescriptions.profile.postUsers",
             "successCriteria": [{"condition": "$statusCode == 201"},
                                 {"context": "$response.body", "condition": "$.id",
                                  "type": "jsonpath"}],
             "outputs": {"userId": "$response.body#/id"}},
            {"stepId": "readUser", "description": "GET /Users/{id} — read back what was created.",
             "operationId": "$sourceDescriptions.profile.getUsersById",
             "successCriteria": [{"condition": "$statusCode == 200"},
                                 {"context": "$response.body", "condition": "$.userName",
                                  "type": "jsonpath"}]},
            {"stepId": "deleteUser", "description": "DELETE /Users/{id} — leave no residue.",
             "operationId": "$sourceDescriptions.profile.deleteUsersById",
             "successCriteria": [{"condition": "$statusCode == 204"}]},
        ],
        "outputs": {"userId": "$steps.createUser.outputs.userId"},
    }],
}
(STD / "arazzo" / "core-conformance.yml").write_text(
    SPDX_ART + yaml.dump(arazzo, Dumper=Dumper, sort_keys=False, width=100, allow_unicode=True))

print(f"openapi.yml  {len(paths)} paths, {sum(len(v) for v in paths.values())} operations")
print(f"schema/      {len(written)} documents: {', '.join(written)}")
print(f"mcp/         {len(tools)} core tools")
print(f"arazzo/      core-conformance.yml (4 steps)")
