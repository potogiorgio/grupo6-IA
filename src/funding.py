import argparse
import csv
import os
import re
from typing import Dict, List

from transformers import pipeline


INPUT_CSV = "data/intermediate/papers_master.csv"
OUTPUT_CSV = "outputs/funding_entities.csv"

HF_MODEL = "dslim/bert-base-NER"


GRANT_PATTERNS = [
    r"\bgrant(?:s)?\s+(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-\/\.]{3,})",
    r"\bproject(?:s)?\s+(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-\/\.]{3,})",
    r"\bcontract(?:s)?\s+(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-\/\.]{3,})",
    r"\baward\s+([A-Z0-9][A-Z0-9\-\/\.]{3,})",
    r"\b([A-Z]{2,}[- ]?\d{3,}[-A-Z0-9]*)\b",
    r"\b(\d{4}[A-Z]?\/[A-Z0-9\-]+)\b",
]


FUNDER_KEYWORDS = [
    "funded by",
    "supported by",
    "financial support",
    "acknowledges support",
    "acknowledge support",
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


FUNDER_ACRONYMS = {
    "NASA",
    "ESA",
    "ERC",
    "NSF",
    "CNRS",
    "DFG",
    "INFN",
    "CNPQ",
    "FONDECYT",
    "ARC",
}


BAD_ENTITIES = {
    "that",
    "with",
    "from",
    "built",
    "agreement",
    "and",
    "or",
    "the",
    "grant",
    "grants",
    "project",
    "projects",
    "award",
    "support",
    "supported",
    "funding",
    "contract",
    "research",
    "work",
    "data",
}


def normalize_text(text: str) -> str:
    return " ".join((text or "").replace("\n", " ").split()).strip()


def normalize_name(text: str) -> str:
    return normalize_text(text).lower()


def context_window(text: str, start: int, end: int, window: int = 120) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    return text[left:right].strip()


def is_bad_entity(entity_text: str, entity_type: str) -> bool:
    text = normalize_text(entity_text)
    lower = text.lower()
    entity_type = (entity_type or "").upper()

    if not text:
        return True

    if lower in BAD_ENTITIES:
        return True

    if len(text) < 2:
        return True

    if entity_type in {"GRANT_ID", "PROJECT_ID"}:
        if len(text) < 4:
            return True

        # Un grant/proyecto normalmente tiene números o guiones.
        # Esto evita falsos positivos como "that", "with", "built".
        if not any(char.isdigit() for char in text) and "-" not in text:
            return True

    return False


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
    entity_type = normalize_text(entity_type).upper()

    if is_bad_entity(entity_text, entity_type):
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
        "normalized_name": normalize_name(entity_text),
        "grant_id": entity_text if entity_type in {"GRANT_ID", "PROJECT_ID"} else "",
        "context": context,
        "method": method,
        "confidence": f"{float(confidence):.2f}",
    })


def extract_grants(text: str, paper_id: str, title: str, rows: List[Dict], seen: set):
    for pattern in GRANT_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = match.group(1).strip(" ,.;:()[]")
            entity_type = "PROJECT_ID" if "project" in match.group(0).lower() else "GRANT_ID"

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


def map_hf_label(label: str) -> str | None:
    label = (label or "").upper()

    if "PER" in label:
        return "PERSON"

    if "ORG" in label:
        return "ORGANIZATION"

    return None


def split_text(text: str, chunk_size: int = 1200) -> list[str]:
    text = normalize_text(text)
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= chunk_size:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks


def extract_hf_entities(
    text: str,
    paper_id: str,
    title: str,
    rows: List[Dict],
    seen: set,
    ner_pipeline,
):
    for chunk in split_text(text):
        if not chunk:
            continue

        entities = ner_pipeline(chunk)

        for entity in entities:
            entity_text = normalize_text(entity.get("word", ""))
            label = entity.get("entity_group") or entity.get("entity") or ""
            score = float(entity.get("score", 0.0))
            mapped_type = map_hf_label(label)

            if not mapped_type:
                continue

            start = entity.get("start")
            end = entity.get("end")

            if isinstance(start, int) and isinstance(end, int):
                context = context_window(chunk, start, end)
            else:
                context = chunk

            add_entity(
                rows,
                seen,
                paper_id,
                title,
                entity_text,
                mapped_type,
                context,
                HF_MODEL,
                score,
            )


def extract_contextual_funders(
    text: str,
    paper_id: str,
    title: str,
    rows: List[Dict],
    seen: set,
):
    sentences = re.split(r"(?<=[.!?])\s+", text)

    for sentence in sentences:
        sentence_clean = normalize_text(sentence)
        lower = sentence_clean.lower()

        if not any(keyword in lower for keyword in FUNDER_KEYWORDS):
            continue

        # Acrónimos típicos de financiadores
        acronyms = re.findall(r"\b[A-Z]{2,10}\b", sentence_clean)
        for acronym in acronyms:
            if acronym.upper() in FUNDER_ACRONYMS:
                add_entity(
                    rows,
                    seen,
                    paper_id,
                    title,
                    acronym,
                    "FUNDER",
                    sentence_clean,
                    "context_rule_acronym",
                    0.75,
                )

        # Patrones sencillos para organizaciones financiadoras después de supported/funded/by/from
        patterns = [
            r"(?:supported by|funded by|financial support from|provided by|through)\s+(?:the\s+)?([A-Z][A-Za-z&,\- ]{3,120})",
            r"([A-Z][A-Za-z&,\- ]{3,120}\s+(?:Foundation|Council|Agency|Ministry|Commission|Programme|Program))",
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, sentence_clean):
                org = match.group(1).strip(" ,.;:()[]")

                # Evitar frases larguísimas.
                if len(org.split()) > 12:
                    continue

                add_entity(
                    rows,
                    seen,
                    paper_id,
                    title,
                    org,
                    "FUNDER",
                    sentence_clean,
                    "context_rule_funder",
                    0.70,
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
    parser = argparse.ArgumentParser(
        description="Extrae entidades NER/funding desde acknowledgements usando HuggingFace + regex"
    )
    parser.add_argument("--input", default=INPUT_CSV)
    parser.add_argument("--output", default=OUTPUT_CSV)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()

    if not args.allow_download:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    ner_pipeline = pipeline(
        "token-classification",
        model=HF_MODEL,
        aggregation_strategy="simple",
    )

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

        extract_hf_entities(acknowledgements, paper_id, title, rows, seen, ner_pipeline)
        extract_grants(acknowledgements, paper_id, title, rows, seen)
        extract_contextual_funders(acknowledgements, paper_id, title, rows, seen)

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