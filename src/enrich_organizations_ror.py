import argparse
import csv
import os
import time
from urllib.parse import urlencode

import requests


INPUT_CSV = "outputs/funding_entities.csv"
OUTPUT_CSV = "outputs/organization_ror_matches.csv"

ROR_API = "https://api.ror.org/v2/organizations"


def normalize_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


def read_organizations(path: str) -> list[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe {path}")

    organizations = set()

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            entity_type = normalize_text(row.get("entity_type")).upper()
            entity_text = normalize_text(row.get("entity_text"))

            if entity_type not in {"ORGANIZATION", "FUNDER", "ORG"}:
                continue

            if not entity_text:
                continue

            if len(entity_text) < 3:
                continue

            if "##" in entity_text:
                continue

            organizations.add(entity_text)

    return sorted(organizations, key=str.lower)


def extract_ror_name(record: dict) -> str:
    names = record.get("names") or []

    for item in names:
        if "ror_display" in item.get("types", []):
            return item.get("value", "")

    for item in names:
        if "label" in item.get("types", []):
            return item.get("value", "")

    return record.get("name", "")


def extract_country(record: dict) -> str:
    locations = record.get("locations") or []

    for location in locations:
        geonames = location.get("geonames_details") or {}
        country = geonames.get("country_name")
        if country:
            return country

    return ""


def query_ror(organization_name: str, timeout: int = 30) -> dict:
    params = urlencode({"affiliation": organization_name})
    url = f"{ROR_API}?{params}"

    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    data = response.json()
    items = data.get("items") or []

    if not items:
        return {
            "organization_name": organization_name,
            "matched": "no",
            "chosen": "no",
            "score": "",
            "ror_id": "",
            "ror_name": "",
            "country": "",
            "matching_type": "",
        }

    chosen_item = None

    for item in items:
        if item.get("chosen") is True:
            chosen_item = item
            break

    if chosen_item is None:
        best = items[0]
        organization = best.get("organization") or best

        return {
            "organization_name": organization_name,
            "matched": "no",
            "chosen": "no",
            "score": best.get("score", ""),
            "ror_id": organization.get("id", ""),
            "ror_name": extract_ror_name(organization),
            "country": extract_country(organization),
            "matching_type": best.get("matching_type", ""),
        }

    organization = chosen_item.get("organization") or chosen_item

    return {
        "organization_name": organization_name,
        "matched": "yes",
        "chosen": "yes",
        "score": chosen_item.get("score", ""),
        "ror_id": organization.get("id", ""),
        "ror_name": extract_ror_name(organization),
        "country": extract_country(organization),
        "matching_type": chosen_item.get("matching_type", ""),
    }


def write_rows(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

    fieldnames = [
        "organization_name",
        "matched",
        "chosen",
        "score",
        "ror_id",
        "ror_name",
        "country",
        "matching_type",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich extracted organizations with ROR identifiers.")
    parser.add_argument("--input", default=INPUT_CSV)
    parser.add_argument("--output", default=OUTPUT_CSV)
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    organizations = read_organizations(args.input)

    if args.limit > 0:
        organizations = organizations[: args.limit]

    print(f"Organizaciones únicas a consultar: {len(organizations)}")

    rows = []

    for index, organization in enumerate(organizations, start=1):
        print(f"[{index}/{len(organizations)}] {organization}")

        try:
            row = query_ror(organization)
        except Exception as exc:
            row = {
                "organization_name": organization,
                "matched": "error",
                "chosen": "error",
                "score": "",
                "ror_id": "",
                "ror_name": "",
                "country": "",
                "matching_type": str(exc),
            }

        rows.append(row)
        time.sleep(args.sleep)

    write_rows(args.output, rows)

    matched = sum(1 for row in rows if row["matched"] == "yes")

    print(f"Guardado: {args.output}")
    print(f"Matches ROR chosen:true: {matched}/{len(rows)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())