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
FUNDING_CSV = "outputs/funding_entities.csv"

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


def resource_id(prefix: str, value: str) -> str:
    slug = local_name(value, prefix)
    digest = hashlib.sha1(value.strip().lower().encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{slug}_{digest}"


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


def read_topic_rows(path: Optional[str]) -> list[dict]:
    if not path:
        return []

    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe {path}")

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {
            "topic_assignment_id",
            "paper_id",
            "topic_id",
            "topic_score",
            "topic_label",
            "topic_model",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Faltan columnas en {path}: {sorted(missing)}")
        return list(reader)


def read_funding_rows(path: Optional[str]) -> list[dict]:
    if not path:
        return []

    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe {path}")

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {
            "paper_id",
            "entity_text",
            "entity_type",
            "normalized_name",
            "grant_id",
            "context",
            "method",
            "confidence",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Faltan columnas en {path}: {sorted(missing)}")
        return list(reader)
    
def read_ror_rows(path: Optional[str]) -> dict[str, dict]:
        if not path:
            return {}

        if not os.path.exists(path):
            raise FileNotFoundError(f"No existe {path}")

        matches = {}

        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            required = {
                "organization_name",
                "matched",
                "chosen",
                "ror_id",
                "ror_name",
                "country",
            }
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Faltan columnas en {path}: {sorted(missing)}")

            for row in reader:
                name = (row.get("organization_name") or "").strip().lower()
                matched = (row.get("matched") or "").strip().lower()
                chosen = (row.get("chosen") or "").strip().lower()
                ror_id = (row.get("ror_id") or "").strip()

                if not name:
                    continue

                if matched == "yes" and chosen == "yes" and ror_id:
                    matches[name] = row

        return matches


def add_triples(lines: list[str], subject: str, predicates: list[tuple[str, str]]) -> None:
    if not predicates:
        return

    lines.append(f"{subject}")
    for index, (predicate, obj) in enumerate(predicates):
        end = " ." if index == len(predicates) - 1 else " ;"
        lines.append(f"    {predicate} {obj}{end}")
    lines.append("")


def build_turtle(
    rows: list[dict],
    similarity_rows: Optional[list[dict]] = None,
    topic_rows: Optional[list[dict]] = None,
    funding_rows: Optional[list[dict]] = None,
    ror_matches: Optional[dict[str, dict]] = None,
) -> str:
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
    acknowledged_people = {}
    organizations = {}
    projects = {}

    similarity_rows = similarity_rows or []
    topic_rows = topic_rows or []
    funding_rows = funding_rows or []
    ror_matches = ror_matches or {}

    similarity_by_source = {}
    topics_by_paper = {}
    funding_by_paper = {}

    paper_ids = {local_name(row.get("id", ""), "paper") for row in rows}

    for row in similarity_rows:
        source = local_name(row.get("source_paper", ""), "")
        if source in paper_ids:
            similarity_by_source.setdefault(source, []).append(row)

    for row in topic_rows:
        paper_id = local_name(row.get("paper_id", ""), "")
        if paper_id in paper_ids:
            topics_by_paper.setdefault(paper_id, []).append(row)

    for row in funding_rows:
        paper_id = local_name(row.get("paper_id", ""), "")
        if paper_id in paper_ids:
            funding_by_paper.setdefault(paper_id, []).append(row)

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

        for topic_row in topics_by_paper.get(paper_id, []):
            assignment_id = local_name(topic_row.get("topic_assignment_id", ""), "topic_assignment")
            predicates.append(("onto:hasTopicAssignment", f"kg:{assignment_id}"))

        for funding_row in funding_by_paper.get(paper_id, []):
            entity_text = (funding_row.get("entity_text") or "").strip()
            entity_type = (funding_row.get("entity_type") or "").strip().upper()

            if not entity_text:
                continue

            if entity_type == "PERSON":
                    pid = resource_id("person_ack", entity_text)
                    acknowledged_people.setdefault(
                        pid,
                        {
                            "name": entity_text,
                            "type": entity_type,
                            "context": funding_row.get("context", ""),
                            "method": funding_row.get("method", ""),
                            "confidence": funding_row.get("confidence", ""),
                        },
                    )
                    predicates.append(("onto:acknowledgesPerson", f"kg:{pid}"))

            elif entity_type in {"FUNDER", "ORGANIZATION", "ORG"}:
                    org_id = resource_id("org", entity_text)
                    ror_match = ror_matches.get(entity_text.strip().lower(), {})
                    organizations.setdefault(
                        org_id,
                        {
                            "name": entity_text,
                            "type": entity_type,
                            "context": funding_row.get("context", ""),
                            "method": funding_row.get("method", ""),
                            "confidence": funding_row.get("confidence", ""),
                            "ror_id": ror_match.get("ror_id", ""),
                            "ror_name": ror_match.get("ror_name", ""),
                            "country": ror_match.get("country", ""),
                        },
                    )
                    predicates.append(("onto:acknowledgesOrganization", f"kg:{org_id}"))

            elif entity_type in {"GRANT_ID", "PROJECT_ID"}:
                    project_id = resource_id("project", entity_text)
                    projects.setdefault(
                        project_id,
                        {
                            "name": entity_text,
                            "funding_id": funding_row.get("grant_id") or entity_text,
                            "type": entity_type,
                            "context": funding_row.get("context", ""),
                            "method": funding_row.get("method", ""),
                            "confidence": funding_row.get("confidence", ""),
                        },
                    )
                    predicates.append(("onto:fundedBy", f"kg:{project_id}"))

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

    topic_entities = {}

    for row in topic_rows:
        paper_id = local_name(row.get("paper_id", ""), "")
        if paper_id not in paper_ids:
            continue

        assignment_id = local_name(row.get("topic_assignment_id", ""), "topic_assignment")
        topic_model = local_name(row.get("topic_model", ""), "topic_model")
        topic_id = local_name(row.get("topic_id", ""), "topic")
        topic_ref = f"kg:topic_{topic_model}_{topic_id}"
        topic_entities[topic_ref] = row.get("topic_label", "")

        predicates = [
            ("a", "onto:TopicAssignment"),
            ("onto:assignedTopic", topic_ref),
            ("onto:topicScore", literal(row.get("topic_score", ""), "xsd:float")),
        ]

        details = []
        for field in ("topic_model", "config_id", "embedding_model", "is_outlier", "n_topics", "vectorizer"):
            value = (row.get(field) or "").strip()
            if value:
                details.append(f"{field}={value}")

        if details:
            predicates.append(("dcterms:description", literal("; ".join(details))))

        add_triples(lines, f"kg:{assignment_id}", predicates)

    for topic_ref, label in sorted(topic_entities.items()):
        add_triples(
            lines,
            topic_ref,
            [
                ("a", "onto:Topic"),
                ("onto:topicName", literal(label)),
                ("onto:topicLabel", literal(label)),
            ],
        )

    for pid, name in sorted(people.items()):
        add_triples(
            lines,
            f"kg:{pid}",
            [
                ("a", "onto:Person"),
                ("onto:personName", literal(name)),
            ],
        )
    for pid, data in sorted(acknowledged_people.items()):
        predicates = [
            ("a", "onto:Person"),
            ("onto:personName", literal(data["name"])),
        ]

        if data.get("type"):
            predicates.append(("onto:entityType", literal(data["type"])))

        if data.get("method"):
            predicates.append(("onto:extractionMethod", literal(data["method"])))

        if data.get("confidence"):
            predicates.append(("onto:confidenceScore", literal(data["confidence"], "xsd:float")))

        if data.get("context"):
            predicates.append(("dcterms:description", literal(data["context"])))

        add_triples(lines, f"kg:{pid}", predicates)

    for org_id, data in sorted(organizations.items()):
        predicates = [
            ("a", "onto:Organization"),
            ("onto:organizationName", literal(data["name"])),
        ]
        if data.get("ror_id"):
            predicates.append(("onto:rorID", literal(data["ror_id"])))

        if data.get("ror_name"):
            predicates.append(("dcterms:alternative", literal(data["ror_name"])))

        if data.get("country"):
             predicates.append(("onto:country", literal(data["country"])))

        if data.get("type"):
            predicates.append(("onto:entityType", literal(data["type"])))

        if data.get("method"):
            predicates.append(("onto:extractionMethod", literal(data["method"])))

        if data.get("confidence"):
            predicates.append(("onto:confidenceScore", literal(data["confidence"], "xsd:float")))

        if data.get("context"):
            predicates.append(("dcterms:description", literal(data["context"])))

        add_triples(lines, f"kg:{org_id}", predicates)

    for project_id, data in sorted(projects.items()):
        predicates = [
            ("a", "onto:Project"),
            ("onto:projectName", literal(data["name"])),
            ("onto:fundingID", literal(data["funding_id"])),
        ]

        if data.get("type"):
            predicates.append(("onto:entityType", literal(data["type"])))

        if data.get("method"):
            predicates.append(("onto:extractionMethod", literal(data["method"])))

        if data.get("confidence"):
            predicates.append(("onto:confidenceScore", literal(data["confidence"], "xsd:float")))

        if data.get("context"):
            predicates.append(("dcterms:description", literal(data["context"])))

        add_triples(lines, f"kg:{project_id}", predicates)

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera un RDF/KG minimo desde papers_master.csv")
    parser.add_argument("--input", default=INPUT_CSV, help="CSV maestro de entrada")
    parser.add_argument("--output", default=OUTPUT_TTL, help="Archivo Turtle de salida")
    parser.add_argument("--similarity", default=None, help="CSV opcional con relaciones de similarity evaluadas")
    parser.add_argument("--topics", default=None, help="CSV opcional con asignaciones de topics evaluadas")
    parser.add_argument("--funding", default=None, help="CSV opcional con entidades NER/funding")
    parser.add_argument("--ror", default=None, help="CSV opcional con matches ROR de organizaciones")
    args = parser.parse_args()

    rows = read_rows(args.input)
    similarity_rows = read_similarity_rows(args.similarity)
    topic_rows = read_topic_rows(args.topics)
    funding_rows = read_funding_rows(args.funding)
    ror_matches = read_ror_rows(args.ror)

    turtle = build_turtle(rows, similarity_rows, topic_rows, funding_rows, ror_matches)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(turtle)
        f.write("\n")

    person_count = sum(1 for line in turtle.splitlines() if "a onto:Person" in line)
    organization_count = sum(1 for line in turtle.splitlines() if "a onto:Organization" in line)
    project_count = sum(1 for line in turtle.splitlines() if "a onto:Project" in line)

    print(f"Guardado: {args.output}")
    print(f"Papers exportados: {len(rows)}")
    print(f"Personas exportadas: {person_count}")
    print(f"Organizaciones exportadas: {organization_count}")
    print(f"Proyectos exportados: {project_count}")
    print(f"Relaciones de similarity integradas: {len(similarity_rows)}")
    print(f"Asignaciones de topic integradas: {len(topic_rows)}")
    print(f"Entidades NER/funding integradas: {len(funding_rows)}")
    print(f"Organizaciones enriquecidas con ROR: {len(ror_matches)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())