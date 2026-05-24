import argparse
import csv
import hashlib
import os
import re
from datetime import date
from json import dumps
from typing import Optional


INPUT_CSV = "data/intermediate/papers_master.csv"
OUTPUT_TTL = "outputs/kg.ttl"

ONTOLOGY_NS = "https://w3id.org/grupo6-ia/ontology#"
RESOURCE_NS = "https://w3id.org/grupo6-ia/resource/"


def literal(value: str, datatype: str = None, lang: str = None) -> str:
    text = "" if value is None else str(value)
    escaped = dumps(text, ensure_ascii=True)
    if lang:
        return f"{escaped}@{lang}"
    if datatype:
        return f"{escaped}^^{datatype}"
    return escaped


def local_name(value: str, fallback: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or fallback


def person_id(name: str) -> str:
    slug = local_name(name, "person")
    digest = hashlib.sha1(name.strip().lower().encode("utf-8")).hexdigest()[:8]
    return f"person_{slug}_{digest}"


def split_authors(authors: str) -> list[str]:
    names = []
    seen = set()

    for raw in (authors or "").split(";"):
        name = " ".join(raw.split())
        key = name.lower()
        if name and key not in seen:
            names.append(name)
            seen.add(key)

    return names


def read_rows(path: str) -> list[dict]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe {path}")

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"id", "title", "doi", "openaire_url", "abstract", "authors"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Faltan columnas en {path}: {sorted(missing)}")
        return list(reader)


def read_similarity_rows(path: Optional[str]) -> list[dict]:
    if not path:
        return []

    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe {path}")

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {
            "similarity_id",
            "source_paper",
            "target_paper",
            "similarity_score",
            "similarity_metric",
            "representation_method",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Faltan columnas en {path}: {sorted(missing)}")
        return list(reader)


def add_triples(lines: list[str], subject: str, predicates: list[tuple[str, str]]) -> None:
    if not predicates:
        return

    lines.append(f"{subject}")
    for index, (predicate, obj) in enumerate(predicates):
        end = " ." if index == len(predicates) - 1 else " ;"
        lines.append(f"    {predicate} {obj}{end}")
    lines.append("")


def build_turtle(rows: list[dict], similarity_rows: Optional[list[dict]] = None) -> str:
    lines = [
        "@prefix kg: <https://w3id.org/grupo6-ia/resource/> .",
        "@prefix onto: <https://w3id.org/grupo6-ia/ontology#> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        "kg:knowledge_graph",
        "    a dcterms:Dataset ;",
        f"    dcterms:title {literal('Knowledge Graph de publicaciones sobre galaxias', lang='es')} ;",
        f"    dcterms:created {literal(date.today().isoformat(), 'xsd:date')} ;",
        f"    dcterms:source {literal(INPUT_CSV)} ;",
        f"    dcterms:conformsTo <{ONTOLOGY_NS[:-1]}> .",
        "",
    ]

    people = {}
    similarity_rows = similarity_rows or []
    similarity_by_source = {}
    paper_ids = {local_name(row.get("id", ""), "paper") for row in rows}

    for row in similarity_rows:
        source = local_name(row.get("source_paper", ""), "")
        if source in paper_ids:
            similarity_by_source.setdefault(source, []).append(row)

    for row in rows:
        paper_id = local_name(row.get("id", ""), "paper")
        paper_ref = f"kg:{paper_id}"
        authors = split_authors(row.get("authors", ""))

        predicates = [
            ("a", "onto:Paper"),
            ("onto:title", literal(row.get("title", ""))),
        ]

        if row.get("abstract"):
            predicates.append(("onto:abstract", literal(row["abstract"])))

        if row.get("doi"):
            predicates.append(("onto:doi", literal(row["doi"])))

        if row.get("openaire_url"):
            predicates.append(("onto:openAireID", literal(row["openaire_url"])))

        for author in authors:
            pid = person_id(author)
            people.setdefault(pid, author)
            predicates.append(("onto:hasAuthor", f"kg:{pid}"))

        for sim_row in similarity_by_source.get(paper_id, []):
            sim_id = local_name(sim_row.get("similarity_id", ""), "similarity")
            predicates.append(("onto:hasSimilarityRelation", f"kg:{sim_id}"))

        add_triples(lines, paper_ref, predicates)

    for row in similarity_rows:
        sim_id = local_name(row.get("similarity_id", ""), "similarity")
        target_id = local_name(row.get("target_paper", ""), "")
        source_id = local_name(row.get("source_paper", ""), "")

        if source_id not in paper_ids or target_id not in paper_ids:
            continue

        predicates = [
            ("a", "onto:SimilarityRelation"),
            ("onto:similarPaper", f"kg:{target_id}"),
            ("onto:similarityScore", literal(row.get("similarity_score", ""), "xsd:float")),
            ("onto:similarityMetric", literal(row.get("similarity_metric", ""))),
        ]

        details = []
        representation = (row.get("representation_method") or "").strip()
        threshold = (row.get("similarity_threshold") or "").strip()
        selection_method = (row.get("selection_method") or "").strip()
        rank = (row.get("rank") or "").strip()
        if representation:
            details.append(f"representation_method={representation}")
        if threshold:
            details.append(f"similarity_threshold={threshold}")
        if selection_method:
            details.append(f"selection_method={selection_method}")
        if rank:
            details.append(f"rank={rank}")
        if details:
            predicates.append(("dcterms:description", literal("; ".join(details))))

        add_triples(lines, f"kg:{sim_id}", predicates)

    for pid, name in sorted(people.items()):
        add_triples(
            lines,
            f"kg:{pid}",
            [
                ("a", "onto:Person"),
                ("onto:personName", literal(name)),
            ],
        )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera un RDF/KG minimo desde papers_master.csv")
    parser.add_argument("--input", default=INPUT_CSV, help="CSV maestro de entrada")
    parser.add_argument("--output", default=OUTPUT_TTL, help="Archivo Turtle de salida")
    parser.add_argument("--similarity", default=None, help="CSV opcional con relaciones de similarity evaluadas")
    args = parser.parse_args()

    rows = read_rows(args.input)
    similarity_rows = read_similarity_rows(args.similarity)
    turtle = build_turtle(rows, similarity_rows)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(turtle)
        f.write("\n")

    author_count = sum(1 for line in turtle.splitlines() if "a onto:Person" in line)
    print(f"Guardado: {args.output}")
    print(f"Papers exportados: {len(rows)}")
    print(f"Personas exportadas: {author_count}")
    print(f"Relaciones de similarity integradas: {len(similarity_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
