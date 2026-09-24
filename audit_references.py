#!/usr/bin/env python3
"""Offline integrity audit for the delivered scholarly bibliography.

The command verifies BibTeX, the complete frozen metadata inventory, the exact
citation-key set, and a dated primary-record spot-check inventory.  Network
resolution is intentionally not part of reproduction: the spot checks record
what was manually rechecked against primary scholarly or publisher records on
2026-09-19.  The audit therefore establishes delivered-record consistency and
basic bibliographic completeness, not an independent literature review.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import urlparse

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
YEAR_RE = re.compile(r"^(19|20)\d{2}$")
PLACEHOLDERS = ("todo", "tbd", "example.com", "placeholder", "xxxx")
INVENTORY_FIELDS = [
    "key", "entry_type", "year", "title", "authors", "author_count",
    "container_title", "volume", "number", "pages", "article_number",
    "publisher", "identifier_kind", "identifier", "record_url",
    "verification_basis", "checked_on", "status",
]
SPOTCHECK_FIELDS = [
    "key", "checked_on", "official_record_url", "source_class",
    "matched_fields", "status", "note",
]
STABLE_URL_HOSTS = {
    "www.usenix.org",
    "usenix.org",
    "proceedings.mlsys.org",
    "dblp.org",
}


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\n", " ")).strip()


def parse_bibtex(text: str):
    entries = []
    i = 0
    while True:
        match = re.search(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text[i:], re.I)
        if not match:
            break
        entry_type, key = match.group(1).lower(), match.group(2)
        pos = i + match.end()
        depth = 1
        j = pos
        while j < len(text) and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        if depth:
            raise ValueError(f"unclosed entry {key}")
        body = text[pos:j - 1]
        fields = {}
        k = 0
        while k < len(body):
            while k < len(body) and (body[k].isspace() or body[k] == ","):
                k += 1
            field_match = re.match(r"([A-Za-z][\w-]*)\s*=\s*", body[k:])
            if not field_match:
                k += 1
                continue
            name = field_match.group(1).lower()
            k += field_match.end()
            if k < len(body) and body[k] == "{":
                field_depth = 1
                end = k + 1
                while end < len(body) and field_depth:
                    if body[end] == "{":
                        field_depth += 1
                    elif body[end] == "}":
                        field_depth -= 1
                    end += 1
                if field_depth:
                    raise ValueError(f"unclosed field {name} in {key}")
                value = body[k + 1:end - 1]
                k = end
            elif k < len(body) and body[k] == '"':
                end = k + 1
                while end < len(body) and not (
                    body[end] == '"' and body[end - 1] != "\\"
                ):
                    end += 1
                value = body[k + 1:end]
                k = end + 1
            else:
                end = k
                while end < len(body) and body[end] not in ",\n":
                    end += 1
                value = body[k:end].strip()
                k = end
            fields[name] = normalize(value)
        entries.append({"key": key, "entry_type": entry_type, "fields": fields})
        i = j
    return entries


def _read_csv(path: Path, expected_fields: list[str], errors: list[str], label: str):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        actual = reader.fieldnames or []
        if actual != expected_fields:
            errors.append(
                f"{label}: header mismatch: expected={expected_fields}, actual={actual}"
            )
        return list(reader)


def _parse_date(value: str, label: str, errors: list[str]):
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError:
        errors.append(f"{label}: invalid ISO date {value!r}")
        return None
    if parsed > dt.date.today():
        errors.append(f"{label}: future verification date {value}")
    return parsed


def _stable_url_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in STABLE_URL_HOSTS


def _entry_completeness(key: str, entry_type: str, fields: dict[str, str], errors: list[str]):
    for required in ("author", "title", "year"):
        if not fields.get(required):
            errors.append(f"{key}: missing {required}")
    year = fields.get("year", "")
    if year and not YEAR_RE.match(year):
        errors.append(f"{key}: malformed four-digit year {year!r}")
    elif year and int(year) > dt.date.today().year:
        errors.append(f"{key}: future publication year {year}")

    if entry_type == "article":
        for required in ("journal", "volume", "number"):
            if not fields.get(required):
                errors.append(f"{key}: article missing {required}")
        if not (fields.get("pages") or fields.get("articleno")):
            errors.append(f"{key}: article missing pages or articleno")
    elif entry_type == "inproceedings":
        if not fields.get("booktitle"):
            errors.append(f"{key}: inproceedings missing booktitle")
        # The official MLSys record for Tensat exposes no page range.
        if not fields.get("pages"):
            stable_url = fields.get("url", "")
            if (urlparse(stable_url).hostname or "").lower() != "proceedings.mlsys.org":
                errors.append(f"{key}: inproceedings missing pages")
    elif entry_type == "misc":
        if not (
            fields.get("howpublished")
            or fields.get("journal")
            or fields.get("booktitle")
        ):
            errors.append(f"{key}: misc entry missing publication container")
    else:
        errors.append(f"{key}: unsupported BibTeX entry type {entry_type}")


def audit(
    bibliography: Path,
    inventory: Path,
    citations: Path,
    spotchecks: Path | None = None,
):
    errors: list[str] = []
    entries = parse_bibtex(bibliography.read_text(encoding="utf-8"))
    bib = {entry["key"]: entry for entry in entries}
    if len(bib) != len(entries):
        errors.append("duplicate BibTeX key")

    rows = _read_csv(inventory, INVENTORY_FIELDS, errors, "inventory")
    inv = {row.get("key", ""): row for row in rows}
    if len(inv) != len(rows):
        errors.append("duplicate inventory key")

    cited = [
        value.strip()
        for value in citations.read_text(encoding="utf-8").splitlines()
        if value.strip()
    ]
    if len(set(cited)) != len(cited):
        errors.append("duplicate cited key")
    if set(bib) != set(inv):
        errors.append(
            "bibliography/inventory key mismatch: "
            f"bib-only={sorted(set(bib) - set(inv))}, "
            f"inventory-only={sorted(set(inv) - set(bib))}"
        )
    if set(bib) != set(cited):
        errors.append(
            "bibliography/citation key mismatch: "
            f"uncited={sorted(set(bib) - set(cited))}, "
            f"missing={sorted(set(cited) - set(bib))}"
        )

    identifiers: list[str] = []
    checked_dates: list[dt.date] = []
    for key, row in inv.items():
        if not key:
            errors.append("inventory: empty key")
            continue
        if row.get("status") != "verified-metadata":
            errors.append(f"{key}: inventory status must be verified-metadata")
        if not normalize(row.get("verification_basis", "")):
            errors.append(f"{key}: empty verification_basis")
        parsed_date = _parse_date(row.get("checked_on", ""), f"{key}: checked_on", errors)
        if parsed_date:
            checked_dates.append(parsed_date)
        if key not in bib:
            continue

        entry = bib[key]
        fields = entry["fields"]
        authors = fields.get("author", "")
        expected = {
            "entry_type": entry["entry_type"],
            "year": fields.get("year", ""),
            "title": fields.get("title", ""),
            "authors": authors,
            "author_count": str(
                len([part for part in authors.split(" and ") if part.strip()])
            ),
            "container_title": fields.get("journal")
            or fields.get("booktitle")
            or fields.get("howpublished", ""),
            "volume": fields.get("volume", ""),
            "number": fields.get("number", ""),
            "pages": fields.get("pages", ""),
            "article_number": fields.get("articleno", ""),
            "publisher": fields.get("publisher", ""),
            "identifier_kind": "doi" if fields.get("doi") else "stable-url",
            "identifier": fields.get("doi") or fields.get("url", ""),
            "record_url": (
                "https://doi.org/" + fields["doi"]
                if fields.get("doi")
                else fields.get("url", "")
            ),
        }
        for name, value in expected.items():
            if normalize(row.get(name, "")) != normalize(value):
                errors.append(f"{key}: {name} differs from frozen inventory")

        _entry_completeness(key, entry["entry_type"], fields, errors)
        if not fields.get("doi") and not fields.get("url"):
            errors.append(f"{key}: missing stable locator")
        lower = " ".join(fields.values()).lower()
        if any(token in lower for token in PLACEHOLDERS):
            errors.append(f"{key}: placeholder token")
        record_url = expected["record_url"]
        if not record_url.startswith("https://"):
            errors.append(f"{key}: non-HTTPS record URL")
        if fields.get("doi") and not DOI_RE.match(fields["doi"]):
            errors.append(f"{key}: malformed DOI")
        if not fields.get("doi") and record_url and not _stable_url_allowed(record_url):
            errors.append(f"{key}: stable URL host is outside the approved primary-record set")
        identifiers.append(expected["identifier"].lower())

    if len(identifiers) != len(set(identifiers)):
        errors.append("duplicate stable identifier")

    spotcheck_rows: list[dict[str, str]] = []
    spotcheck_dates: list[dt.date] = []
    if spotchecks is not None:
        spotcheck_rows = _read_csv(
            spotchecks, SPOTCHECK_FIELDS, errors, "primary-record spot checks"
        )
        spot_by_key = {row.get("key", ""): row for row in spotcheck_rows}
        if len(spot_by_key) != len(spotcheck_rows):
            errors.append("duplicate primary-record spot-check key")
        if not set(spot_by_key).issubset(bib):
            errors.append(
                "primary-record spot checks contain unknown keys: "
                f"{sorted(set(spot_by_key) - set(bib))}"
            )
        for key, row in spot_by_key.items():
            if row.get("status") != "verified-live-metadata":
                errors.append(f"{key}: spot-check status must be verified-live-metadata")
            parsed_date = _parse_date(
                row.get("checked_on", ""), f"{key}: spot-check checked_on", errors
            )
            if parsed_date:
                spotcheck_dates.append(parsed_date)
            if key in inv and normalize(row.get("official_record_url", "")) != normalize(
                inv[key].get("record_url", "")
            ):
                errors.append(f"{key}: spot-check URL differs from frozen inventory")
            url = row.get("official_record_url", "")
            if not url.startswith("https://"):
                errors.append(f"{key}: spot-check URL is not HTTPS")
            if not normalize(row.get("source_class", "")):
                errors.append(f"{key}: empty spot-check source_class")
            if not normalize(row.get("matched_fields", "")):
                errors.append(f"{key}: empty spot-check matched_fields")

    report = {
        "bibliography_entries": len(entries),
        "inventory_rows": len(rows),
        "cited_keys": len(cited),
        "doi_records": sum(bool(entry["fields"].get("doi")) for entry in entries),
        "stable_url_only_records": sum(
            not bool(entry["fields"].get("doi")) for entry in entries
        ),
        "verified_inventory_records": sum(
            row.get("status") == "verified-metadata" for row in rows
        ),
        "primary_record_spotchecks": len(spotcheck_rows),
        "latest_inventory_check": max(checked_dates).isoformat() if checked_dates else None,
        "latest_primary_record_spotcheck": (
            max(spotcheck_dates).isoformat() if spotcheck_dates else None
        ),
        "errors": errors,
        "passed": not errors,
        "interpretation": (
            "Offline consistency and completeness check against the delivered "
            "frozen metadata inventory plus a dated primary-record spot-check "
            "inventory. Reproduction does not resolve the network and this is "
            "not an independent literature review."
        ),
    }
    return report


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--bibliography", type=Path, default=root / "data/references.bib")
    parser.add_argument("--inventory", type=Path, default=root / "data/reference-audit.csv")
    parser.add_argument("--citations", type=Path, default=root / "data/cited-reference-keys.txt")
    parser.add_argument(
        "--spotchecks", type=Path, default=root / "data/reference-live-spot-check.csv"
    )
    parser.add_argument("--output", type=Path, default=root / "results/reference-audit.json")
    args = parser.parse_args()
    report = audit(args.bibliography, args.inventory, args.citations, args.spotchecks)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
