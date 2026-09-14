#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the SCIM 2.0 profile from RFC 7644 and the declared-spec cohort.

SCIM IS NOT LIKE THE OTHER FIVE STANDARDS IN THIS PROGRAMME, and the difference is the
point of profiling it.

S3, the OpenAI API, CKAN and Ethereum JSON-RPC became standards by being copied; there is
no specification to check anyone against, so a profile IS the specification. SCIM was
ratified. RFC 7643 and RFC 7644 have said what a SCIM server is since 2015. Publishing a
description of SCIM would add nothing.

What is missing is the OTHER axis. So every operation here carries two gradings:

  normative   what the RFC says about it, with the section and the modal verb, quoted
              rather than paraphrased.
  tier        what the industry actually declares, measured the same way as every other
              profile in this programme.

The gap between them is the artifact. It is also why the normative column was read out of
the RFC text rather than written from memory: the first draft of this profile was going to
say the three discovery endpoints are REQUIRED and that half of implementers skip them.
RFC 7644 Section 4 says no such thing — it says they MAY be retrieved by GET, and uses
SHALL only for the shape of the response IF the endpoint answers. A profile that overstated
the specification to make its finding sharper would be worth less than no profile.
"""
import argparse, json
from collections import Counter
from datetime import date
from pathlib import Path

import yaml

try:
    Dumper = yaml.CSafeDumper
except AttributeError:
    Dumper = yaml.SafeDumper

HERE = Path(__file__).resolve().parent.parent
SPDX_ART = "# SPDX-License-Identifier: CC-BY-NC-SA-4.0\n"
CORE_MIN, EXTENDED_MIN = 50.0, 5.0

# RFC 7644 Table 2, Section 3.2. Transcribed from the RFC, not from memory.
OPERATIONS = [
    ("GET",    "/Users",                  "3.4.1", "List or query User resources."),
    ("POST",   "/Users",                  "3.3",   "Create a User."),
    ("GET",    "/Users/{id}",             "3.4.1", "Retrieve a known User."),
    ("PUT",    "/Users/{id}",             "3.5.1", "Replace a User."),
    ("PATCH",  "/Users/{id}",             "3.5.2", "Modify a User with a patch set."),
    ("DELETE", "/Users/{id}",             "3.6",   "Delete a User."),
    ("GET",    "/Groups",                 "3.4.1", "List or query Group resources."),
    ("POST",   "/Groups",                 "3.3",   "Create a Group."),
    ("GET",    "/Groups/{id}",            "3.4.1", "Retrieve a known Group."),
    ("PUT",    "/Groups/{id}",            "3.5.1", "Replace a Group."),
    ("PATCH",  "/Groups/{id}",            "3.5.2", "Modify a Group with a patch set."),
    ("DELETE", "/Groups/{id}",            "3.6",   "Delete a Group."),
    ("GET",    "/Me",                     "3.11",  "Alias for the authenticated subject."),
    ("POST",   "/Me",                     "3.11",  "Alias for the authenticated subject."),
    ("PUT",    "/Me",                     "3.11",  "Alias for the authenticated subject."),
    ("PATCH",  "/Me",                     "3.11",  "Alias for the authenticated subject."),
    ("DELETE", "/Me",                     "3.11",  "Alias for the authenticated subject."),
    ("GET",    "/ServiceProviderConfig",  "4",     "Retrieve the server's declared features."),
    ("GET",    "/ResourceTypes",          "4",     "Discover the resource types served."),
    ("GET",    "/ResourceTypes/{id}",     "4",     "Retrieve one resource type."),
    ("GET",    "/Schemas",                "4",     "Retrieve supported schemas."),
    ("GET",    "/Schemas/{id}",           "4",     "Retrieve one schema definition."),
    ("POST",   "/Bulk",                   "3.7",   "Apply bulk updates to many resources."),
    ("POST",   "/.search",                "3.4.3", "Query via POST when a GET would leak filters."),
]

# Normative force, quoted from RFC 7644. Where the RFC does not compel implementation, this
# says so — the absence of a MUST is itself a finding about a ratified standard.
NORMATIVE = {
    "/Users": ("defined", "RFC 7644 Section 3.2 Table 2 lists /Users with GET, POST, PUT, "
                          "PATCH and DELETE. The RFC defines the operations; it does not "
                          "compel a server to implement all of them."),
    "/Groups": ("defined", "RFC 7644 Section 3.2 Table 2 lists /Groups with the same five "
                           "methods as /Users, and with no weaker obligation attached."),
    "/Me": ("may", "RFC 7644 Section 3.11: a client \"MAY use a URL of the form "
                   "'<base-URI>/Me' as a URI alias for the User or other resource associated "
                   "with the currently authenticated subject\"."),
    "/ServiceProviderConfig": ("may-retrieve-shall-shape",
        "RFC 7644 Section 4: the three discovery endpoints \"MAY be retrieved using HTTP "
        "GET\". The obligation attaches to the SHAPE, not to implementation — this endpoint "
        "\"SHALL return responses with a JSON object using a 'schemas' attribute of "
        "'urn:ietf:params:scim:schemas:core:2.0:ServiceProviderConfig'\"."),
    "/ResourceTypes": ("may-retrieve-shall-shape",
        "RFC 7644 Section 4, same framing. Section 3.4.1 adds that clients \"SHOULD discover "
        "resource endpoints via the '/ResourceTypes' endpoint\" — an obligation on the "
        "CLIENT, which is only meetable if the server chose to implement it."),
    "/Schemas": ("may-retrieve-shall-shape",
        "RFC 7644 Section 4: \"An HTTP GET to the endpoint '/Schemas' SHALL return all "
        "supported schemas in ListResponse format.\" Again a shape obligation, not an "
        "implementation one."),
    "/Bulk": ("defined", "RFC 7644 Section 3.7 defines bulk operations. Section 3.2 Table 2 "
                         "lists POST /Bulk. Support is advertised through "
                         "ServiceProviderConfig's \"bulk\" attribute, which implies it is "
                         "optional."),
    "/.search": ("defined", "RFC 7644 Section 3.4.3 defines POST /.search so a client can "
                            "query without putting filter values in a URL."),
}


def resource(path):
    for key in ("/ServiceProviderConfig", "/ResourceTypes", "/Schemas", "/Users", "/Groups",
                "/Me", "/Bulk", "/.search"):
        if path.startswith(key):
            return key
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--declared", required=True)
    ap.add_argument("--cohort", type=int, required=True)
    ap.add_argument("--claimants", type=int, required=True)
    args = ap.parse_args()

    out_dir = HERE / "standard" / "scim-2.0"
    out_dir.mkdir(parents=True, exist_ok=True)
    declared = json.loads(Path(args.declared).read_text())

    operations, counts = [], Counter()
    for method, path, section, summary in OPERATIONS:
        key = f"{method} {path}"
        providers = sorted(declared.get(key, []))
        pct = round(100 * len(providers) / args.cohort, 1) if args.cohort else 0.0
        tier = "core" if pct >= CORE_MIN else ("extended" if pct >= EXTENDED_MIN else "vendor")
        counts[tier] += 1
        force, citation = NORMATIVE[resource(path)]
        operations.append({
            "operation": key,
            "method": method,
            "path": path,
            "resource": resource(path),
            "rfc_section": section,
            "summary": summary,
            "normative_force": force,
            "normative_citation": citation,
            "tier": tier,
            "providers_declaring": len(providers),
            "percent_of_cohort": pct,
            "evidence": (f"{len(providers)} of {args.cohort} providers that publish a SCIM "
                         f"path declare this operation ({pct}%)."),
        })

    profile = {
        "profile": "scim-2.0",
        "title": "SCIM 2.0",
        "originator": "IETF",
        "standard_class": "ratified",
        "standard_class_note": (
            "The other five profiles in this programme describe interfaces that became "
            "standards by being copied, where no specification exists to check anyone "
            "against. SCIM was ratified in 2015. Describing it again would add nothing; what "
            "is missing is the measurement of what the industry actually built, set beside "
            "what the RFC actually says."
        ),
        "generated": date.today().isoformat(),
        "generated_by": "scripts/build-profile.py",
        "upstream": {
            "specifications": [
                {"rfc": "RFC 7643", "title": "SCIM: Core Schema",
                 "url": "https://www.rfc-editor.org/rfc/rfc7643"},
                {"rfc": "RFC 7644", "title": "SCIM: Protocol",
                 "url": "https://www.rfc-editor.org/rfc/rfc7644"},
            ],
            "published": "September 2015",
            "license": ("IETF Trust. RFCs may be described, quoted and implemented freely; "
                        "this profile quotes normative language with its section and does not "
                        "reproduce the documents."),
            "operations": len(OPERATIONS),
            "source_note": ("The operation list is transcribed from RFC 7644 Section 3.2 "
                            "Table 2 and each normative claim is quoted from the RFC text, "
                            "not paraphrased from memory."),
        },
        "method": {
            "summary": ("Two gradings per operation. `normative_force` is what RFC 7644 says, "
                        "quoted. `tier` is what the industry declares, measured the same way "
                        "as every other profile here. The gap between them is the point."),
            "cohort": args.cohort,
            "claimants": args.claimants,
            "cohort_definition": (
                f"{args.claimants} providers in the API Evangelist catalog mention SCIM — the "
                "largest claim cohort of any standard in this programme. "
                f"{args.cohort} of them publish an OpenAPI containing a SCIM path, and those "
                "are the denominator."
            ),
            "why_no_probe": (
                "A SCIM endpoint is an identity surface and every operation on it is "
                "authenticated. There is no anonymous discriminator, so no `tested` grade is "
                "available — the same structural limit as S3, for the same reason."
            ),
            "thresholds": {"core": f">= {CORE_MIN}%", "extended": f">= {EXTENDED_MIN}%",
                           "vendor": f"< {EXTENDED_MIN}%"},
        },
        "counts": dict(counts),
        "operations": sorted(operations, key=lambda o: -o["percent_of_cohort"]),
    }
    (out_dir / "profile.yml").write_text(
        SPDX_ART + yaml.dump(profile, Dumper=Dumper, sort_keys=False, width=100,
                             allow_unicode=True))
    print(f"profile.yml   {len(operations)} operations graded  {dict(counts)}")
    print(f"cohort        {args.cohort} declaring of {args.claimants} claiming")


if __name__ == "__main__":
    main()
