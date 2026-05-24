import argparse
import csv
import hashlib
import os
import re
from datetime import date
from json import dumps


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


def add_triples(lines: list[str], subject: str, predicates: list[tuple[str, str]]) -> None:
    if not predicates:
        return

    lines.append(f"{subject}")
    for index, (predicate, obj) in enumerate(predicates):
        end = " ." if index == len(predicates) - 1 else " ;"
        lines.append(f"    {predicate} {obj}{end}")
    lines.append("")


def build_turtle(rows: list[dict]) -> str:
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

        add_triples(lines, paper_ref, predicates)

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
    args = parser.parse_args()

    rows = read_rows(args.input)
    turtle = build_turtle(rows)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(turtle)
        f.write("\n")

    author_count = sum(1 for line in turtle.splitlines() if "a onto:Person" in line)
    print(f"Guardado: {args.output}")
    print(f"Papers exportados: {len(rows)}")
    print(f"Personas exportadas: {author_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
