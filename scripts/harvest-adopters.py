#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build the S3 adopter registry.

This registry has no `tested` entries, for a structural reason rather than a budgetary one:
a SCIM endpoint is an identity surface and every operation on it is authenticated. There is
no anonymous discriminator to probe with, the same limit S3 has.

  declared   the provider publishes an OpenAPI containing SCIM paths. 77 of 368 — by far the
             largest claim cohort in this programme, and under a quarter of it is checkable.
  prose      mentions SCIM and publishes nothing a reader can check against.
"""
import argparse, json, os
from collections import Counter
from datetime import date
from pathlib import Path

import yaml

try:
    Loader, Dumper = yaml.CSafeLoader, yaml.CSafeDumper
except AttributeError:
    Loader, Dumper = yaml.SafeLoader, yaml.SafeDumper

ROOT = Path("/Users/kinlane/GitHub/all")
HERE = Path(__file__).resolve().parent.parent
TODAY = date.today().isoformat()
RELEVANT = {"Identity", "SCIM", "Single Sign On", "Authentication", "Authorization",
            "Directory", "API", "Security", "Provisioning"}

# Verified reachable on 2026-09-13. Their claim, attributed, with no support inferred.
MATRICES = {}  # no vendor conformance matrices are published for SCIM


def provider_facts(slug):
    path = ROOT / slug / "apis.yml"
    if not path.exists():
        return slug, None, []
    try:
        d = yaml.load(path.read_text(errors="ignore"), Loader=Loader)
    except Exception:
        return slug, None, []
    name = d.get("name") or slug
    tags = sorted({t for t in (d.get("tags") or []) if t in RELEVANT})
    claim = None
    for api in d.get("apis") or []:
        for prop in api.get("properties") or []:
            url = prop.get("url") or ""
            if prop.get("type") in ("Documentation", "SwaggerUI") and url.startswith("http"):
                claim = url
                break
        if claim:
            break
    if not claim:
        for prop in (d.get("properties") or []):
            url = prop.get("url") or ""
            if prop.get("type") in ("Website", "Documentation") and url.startswith("http"):
                claim = url
                break
    return name, claim, tags


def harvested_spec_url(slug):
    files = sorted(p for p in (ROOT / slug / "openapi" / "_original").glob("*")) \
        if (ROOT / slug / "openapi" / "_original").is_dir() else []
    if not files:
        return None
    return (f"https://raw.githubusercontent.com/api-evangelist/{slug}/main/"
            f"openapi/_original/{files[0].name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--declared", required=True)
    ap.add_argument("--claimants", required=True, help="JSON list of slugs")
    args = ap.parse_args()

    profile = yaml.load((HERE / "standard" / "scim-2.0" / "profile.yml").read_text(),
                        Loader=Loader)
    core = [o["operation"] for o in profile["operations"] if o["tier"] == "core"]
    extended = [o["operation"] for o in profile["operations"] if o["tier"] == "extended"]
    declared = json.loads(Path(args.declared).read_text())
    claimants = json.loads(Path(args.claimants).read_text())

    by_slug = {}
    for op, slugs in declared.items():
        for s in slugs:
            by_slug.setdefault(s, set()).add(op)

    adopters, skipped = [], []
    counts = Counter()
    for slug in sorted(set(claimants) | set(by_slug) | set(MATRICES)):
        name, claim_url, tags = provider_facts(slug)
        if slug in MATRICES:
            claim_url = MATRICES[slug]
        if not claim_url:
            skipped.append(slug)
            continue
        ops = by_slug.get(slug, set())
        entry = {
            "name": name, "aid": slug, "standard": "scim-2.0",
            "claim_url": claim_url, "source_date": TODAY,
            "evidence": "prose", "tier_claimed": None, "tier_verified": None,
            "software_version": None, "tags": tags,
        }
        if ops:
            entry["evidence"] = "declared"
            entry["evidence_url"] = harvested_spec_url(slug)
            counts["declared"] += 1
            reaches_core = set(core).issubset(ops)
            tier = "extended" if (reaches_core and ops & set(extended)) else \
                   ("core" if reaches_core else None)
            if tier:
                entry["tier_verified"] = tier
                entry["verified_on"] = TODAY
                counts[tier] += 1
            else:
                counts["no_tier"] += 1
                entry["divergence"] = [{
                    "operation": op,
                    "note": ("Not declared in the OpenAPI this provider publishes. With a "
                             "cohort of 12 that is weak evidence of absence rather than a "
                             "measured gap."),
                    "url": entry["evidence_url"] or claim_url,
                } for op in sorted(set(core) - ops)]
        elif slug in MATRICES:
            entry["evidence"] = "vendor-matrix"
            entry["evidence_url"] = MATRICES[slug]
            counts["vendor-matrix"] += 1
            entry["divergence"] = [{
                "operation": "*",
                "note": ("This provider publishes a compatibility table, recorded here as "
                         "their claim. No per-operation support is read from it: the table "
                         "renders client-side or does not mark support in any parseable "
                         "structure, and guessing which half of a list is supported would be "
                         "worse than recording nothing."),
                "url": MATRICES[slug],
            }]
        else:
            counts["prose"] += 1

        order = ["name", "aid", "standard", "claim_url", "source_date", "evidence",
                 "evidence_url", "tier_claimed", "tier_verified", "verified_on",
                 "software_version", "tags", "divergence"]
        adopters.append({k: entry[k] for k in order if k in entry})

    doc = {"standard": "scim-2.0",
           "standard_url": "https://github.com/api-commons/identity",
           "cohort": "reimplementation", "source_date": TODAY,
           "generated_by": "scripts/harvest-adopters.py", "adopters": adopters}
    (HERE / "adopters" / "scim-2.0.yml").write_text(
        "# SPDX-License-Identifier: CC-BY-NC-SA-4.0\n"
        "# Generated by scripts/harvest-adopters.py — do not hand-edit.\n"
        "# No entry is graded `tested`: S3 checks the signature before routing the operation,\n"
        "# so an anonymous caller cannot tell a supported operation from an unsupported one.\n"
        + yaml.dump(doc, Dumper=Dumper, sort_keys=False, width=100, allow_unicode=True))

    ops_rows = [o for o in profile["operations"] if o["tier"] in ("core", "extended")]
    dec = [a for a in adopters if a["evidence"] == "declared"]
    rows = [f"# Adopter matrix — {profile['title']}", "",
            "Generated by `scripts/harvest-adopters.py`. Do not hand-edit.", "",
            f"Measured {TODAY} against {len(dec)} providers that publish an OpenAPI containing "
            f"a SCIM path, out of {len(claimants)} that mention SCIM in the "
            "[API Evangelist](https://apis.io) catalog — the largest claim cohort of any "
            "standard in this programme, and under a quarter of it is checkable.", "",
            "**SCIM is ratified, so this table has a column the others do not.** RFC 7643 and "
            "RFC 7644 already say what a SCIM server is; what was missing is the measurement "
            "beside it. Where the RFC compels nothing, the table says so rather than implying "
            "a violation.", "",
            "There is no `tested` column and there cannot be one: every SCIM operation is "
            "authenticated, so there is no anonymous discriminator to probe with.", "",
            "## By operation", "",
            "| Operation | RFC | What the RFC says | Measured tier | Declaring | Share |",
            "| --- | --- | --- | --- | ---: | ---: |"]
    for o in ops_rows:
        rows.append(f"| `{o['operation']}` | RFC 7644 &sect;{o['rfc_section']} "
                    f"| {o['normative_force']} | {o['tier']} "
                    f"| {o['providers_declaring']} | {o['percent_of_cohort']}% |")
    tiers = Counter(a["tier_verified"] for a in dec)
    rows += ["", "## By provider", "",
             f"**Declares the whole core tier**: {tiers['core'] + tiers['extended']} of "
             f"{len(dec)}", "",
             ", ".join(sorted(a["name"] for a in dec if a["tier_verified"])) or "_none_", "",
             f"**Declares part of it**: {tiers[None]}", "",
             ", ".join(sorted(a["name"] for a in dec if not a["tier_verified"])) or "_none_", ""]
    (HERE / "adopters" / "scim-2.0-matrix.md").write_text("\n".join(rows))

    print(f"adopters:  {len(adopters)} entries (skipped {len(skipped)})")
    print(f"evidence:  declared {counts['declared']} · vendor-matrix {counts['vendor-matrix']} "
          f"· prose {counts['prose']}")
    print(f"tiers:     core {counts['core']} · extended {counts['extended']} · "
          f"part of core {counts['no_tier']}")


if __name__ == "__main__":
    main()
