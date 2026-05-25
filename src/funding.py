import argparse
import csv
import os
import re
from typing import Dict, List


INPUT_CSV = "data/intermediate/papers_master.csv"
OUTPUT_CSV = "outputs/funding_entities.csv"


GRANT_PATTERNS = [
    r"\bgrant(?:s)?\s+(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-\/\.]{3,})",
    r"\bproject(?:s)?\s+(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-\/\.]{3,})",
    r"\bcontract(?:s)?\s+(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-\/\.]{3,})",
    r"\b([A-Z]{2,}[- ]?\d{3,}[-A-Z0-9]*)\b",
    r"\b(\d{4}[A-Z]?\/[A-Z0-9\-]+)\b",
]

FUNDER_KEYWORDS = [
    "funded by",
    "supported by",
    "financial support",
    "acknowledges support",
    "funding",
    "grant",
    "grants",
    "project",
    "programme",
    "program",
    "research council",
    "foundation",
    "agency",
    "ministry",
    "commission",
]

ORG_HINTS = [
    "University",
    "Institute",
    "Instituto",
    "Council",
    "Foundation",
    "Agency",
    "Ministry",
    "Commission",
    "Programme",
    "Program",
    "Observatory",
    "Laboratory",
    "Centre",
    "Center",
    "Department",
    "Consortium",
    "NASA",
    "ESA",
    "ERC",
    "NSF",
    "CNRS",
    "DFG",
]


def normalize_text(text: str) -> str:
    return " ".join((text or "").replace("\n", " ").split())


def context_window(text: str, start: int, end: int, window: int = 120) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    return text[left:right].strip()


def add_entity(
    rows: List[Dict],
    seen: set,
    paper_id: str,
    title: str,
    entity_text: str,
    entity_type: str,
    context: str,
    method: str,
    confidence: float,
):
    entity_text = normalize_text(entity_text)
    if not entity_text or len(entity_text) < 2:
        return

    key = (paper_id, entity_text.lower(), entity_type)
    if key in seen:
        return

    seen.add(key)
    rows.append({
        "paper_id": paper_id,
        "title": title,
        "entity_text": entity_text,
        "entity_type": entity_type,
        "normalized_name": entity_text.lower(),
        "grant_id": entity_text if entity_type in {"GRANT_ID", "PROJECT_ID"} else "",
        "context": context,
        "method": method,
        "confidence": f"{confidence:.2f}",
    })


def extract_grants(text: str, paper_id: str, title: str, rows: List[Dict], seen: set):
    for pattern in GRANT_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = match.group(1).strip(" ,.;:()[]")
            if len(value) < 4:
                continue

            entity_type = "GRANT_ID"
            if "project" in match.group(0).lower():
                entity_type = "PROJECT_ID"

            add_entity(
                rows,
                seen,
                paper_id,
                title,
                value,
                entity_type,
                context_window(text, match.start(), match.end()),
                "regex",
                0.85,
            )


def extract_possible_funders(text: str, paper_id: str, title: str, rows: List[Dict], seen: set):
    sentences = re.split(r"(?<=[.!?])\s+", text)

    for sentence in sentences:
        sentence_clean = normalize_text(sentence)
        lower = sentence_clean.lower()

        if not any(keyword in lower for keyword in FUNDER_KEYWORDS):
            continue

        for hint in ORG_HINTS:
            pattern = rf"\b([A-Z][A-Za-z&,\- ]{{2,80}}\s+{re.escape(hint)}(?:\s+[A-Z][A-Za-z&,\- ]{{2,50}})?)\b"
            for match in re.finditer(pattern, sentence_clean):
                org = match.group(1).strip(" ,.;:")
                add_entity(
                    rows,
                    seen,
                    paper_id,
                    title,
                    org,
                    "ORGANIZATION",
                    sentence_clean,
                    "rule_org_hint",
                    0.70,
                )

        acronyms = re.findall(r"\b[A-Z]{2,8}\b", sentence_clean)
        for acronym in acronyms:
            if acronym in {"NASA", "ESA", "ERC", "NSF", "CNRS", "DFG"}:
                add_entity(
                    rows,
                    seen,
                    paper_id,
                    title,
                    acronym,
                    "FUNDER",
                    sentence_clean,
                    "rule_acronym",
                    0.75,
                )


def read_papers(path: str) -> List[Dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_output(path: str, rows: List[Dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

    fieldnames = [
        "paper_id",
        "title",
        "entity_text",
        "entity_type",
        "normalized_name",
        "grant_id",
        "context",
        "method",
        "confidence",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrae entidades NER/funding desde acknowledgements")
    parser.add_argument("--input", default=INPUT_CSV)
    parser.add_argument("--output", default=OUTPUT_CSV)
    args = parser.parse_args()

    papers = read_papers(args.input)
    rows = []
    seen = set()

    for paper in papers:
        paper_id = paper.get("id", "").strip()
        title = paper.get("title", "").strip()
        acknowledgements = normalize_text(paper.get("acknowledgements", ""))

        usable_for_ner = paper.get("usable_for_ner", "").strip().lower()
        has_ack = paper.get("has_acknowledgements", "").strip().lower()

        if usable_for_ner not in {"yes", "true", "1"} and has_ack not in {"yes", "true", "1"}:
            continue

        if not acknowledgements:
            continue

        extract_grants(acknowledgements, paper_id, title, rows, seen)
        extract_possible_funders(acknowledgements, paper_id, title, rows, seen)

    write_output(args.output, rows)

    print(f"Guardado: {args.output}")
    print(f"Papers leídos: {len(papers)}")
    print(f"Entidades extraídas: {len(rows)}")

    counts = {}
    for row in rows:
        counts[row["entity_type"]] = counts.get(row["entity_type"], 0) + 1

    print("Entidades por tipo:")
    for entity_type, count in sorted(counts.items()):
        print(f"  {entity_type}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())