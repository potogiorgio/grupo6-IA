import argparse
import re
from collections import Counter
from rdflib import Graph


KG_TTL = "outputs/kg.ttl"
PROVENANCE_TTL = "outputs/provenance.ttl"


BAD_URI_PATTERNS = [
    "project_that",
    "project_with",
    "project_built",
    "project_agreement",
    "project_from",
    "project_the",
    "project_and",
]


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_turtle(path: str) -> int:
    g = Graph()
    g.parse(path, format="turtle")
    return len(g)


def prefixed_subjects(text: str, rdf_type: str) -> set[str]:
    pattern = rf"^(kg:[A-Za-z0-9_]+)\n\s+a {re.escape(rdf_type)}\b"
    return set(re.findall(pattern, text, flags=re.MULTILINE))


def object_refs(text: str, predicate: str) -> list[str]:
    pattern = rf"{re.escape(predicate)} (kg:[A-Za-z0-9_]+)"
    return re.findall(pattern, text)


def literal_values(text: str, predicate: str) -> list[str]:
    pattern = rf"{re.escape(predicate)} \"(.*?)\""
    return re.findall(pattern, text, flags=re.DOTALL)


def find_bad_uris(text: str) -> list[str]:
    bad = []

    for pattern in BAD_URI_PATTERNS:
        matches = re.findall(rf"kg:[A-Za-z0-9_]*{re.escape(pattern)}[A-Za-z0-9_]*", text, flags=re.IGNORECASE)
        bad.extend(matches)

    return sorted(set(bad))


def find_empty_or_suspicious_uris(text: str) -> list[str]:
    suspicious = []

    # Detecta prefijos kg: realmente vacíos, por ejemplo:
    # kg: ;
    # kg: .
    # kg: ,
    suspicious.extend(re.findall(r"\bkg:\s*[.;,]", text))

    # Detecta recursos kg: con caracteres claramente problemáticos.
    # En Turtle es normal que después de kg:algo venga un salto de línea,
    # así que NO marcamos espacios o saltos de línea como error.
    suspicious.extend(re.findall(r"kg:[A-Za-z0-9_]*[\"'<>{}]", text))

    return sorted(set(suspicious))


def duplicated_resources(resources: set[str]) -> dict[str, int]:
    counts = Counter(resources)
    return {resource: count for resource, count in counts.items() if count > 1}


def validate_kg(kg_path: str) -> bool:
    print(f"\nValidando KG: {kg_path}")

    triples = validate_turtle(kg_path)
    text = read_text(kg_path)

    print(f"TTL parseado correctamente: {triples} triples")

    require("@prefix kg:" in text, "Falta prefijo kg")
    require("@prefix onto:" in text, "Falta prefijo onto")
    require("kg:knowledge_graph" in text, "Falta metadata del dataset")

    papers = prefixed_subjects(text, "onto:Paper")
    people = prefixed_subjects(text, "onto:Person")
    organizations = prefixed_subjects(text, "onto:Organization")
    projects = prefixed_subjects(text, "onto:Project")
    similarity_relations = prefixed_subjects(text, "onto:SimilarityRelation")
    topic_assignments = prefixed_subjects(text, "onto:TopicAssignment")
    topics = prefixed_subjects(text, "onto:Topic")
    galaxies = prefixed_subjects(text, "onto:Galaxy")
    evidences = prefixed_subjects(text, "onto:GalaxyStudyEvidence")

    author_refs = object_refs(text, "onto:hasAuthor")
    person_ack_refs = object_refs(text, "onto:acknowledgesPerson")
    org_ack_refs = object_refs(text, "onto:acknowledgesOrganization")
    funding_refs = object_refs(text, "onto:fundedBy")
    similarity_refs = object_refs(text, "onto:hasSimilarityRelation")
    topic_assignment_refs = object_refs(text, "onto:hasTopicAssignment")
    topic_refs = object_refs(text, "onto:assignedTopic")
    galaxy_refs = object_refs(text, "onto:studiesGalaxy")
    evidence_refs = object_refs(text, "onto:hasGalaxyStudyEvidence")

    funding_ids = literal_values(text, "onto:fundingID")

    require(len(papers) > 0, "No hay recursos onto:Paper")
    # require(len(people) > 0, "No hay recursos onto:Person")
    # require(len(author_refs) > 0, "No hay relaciones onto:hasAuthor")

    # missing_people = sorted(set(author_refs) - people)
    # require(not missing_people, f"Hay autores referenciados sin onto:Person: {missing_people[:5]}")

    if person_ack_refs:
        missing_ack_people = sorted(set(person_ack_refs) - people)
        require(
            not missing_ack_people,
            f"Hay personas reconocidas sin onto:Person: {missing_ack_people[:5]}",
        )

    if org_ack_refs:
        missing_orgs = sorted(set(org_ack_refs) - organizations)
        require(
            not missing_orgs,
            f"Hay organizaciones reconocidas sin onto:Organization: {missing_orgs[:5]}",
        )

    if funding_refs:
        missing_projects = sorted(set(funding_refs) - projects)
        require(
            not missing_projects,
            f"Hay proyectos/grants referenciados sin onto:Project: {missing_projects[:5]}",
        )

    if similarity_refs:
        missing_similarity = sorted(set(similarity_refs) - similarity_relations)
        require(
            not missing_similarity,
            f"Hay relaciones de similarity referenciadas sin onto:SimilarityRelation: {missing_similarity[:5]}",
        )
        require("onto:similarPaper " in text, "Hay similarity relations sin onto:similarPaper")
        require("onto:similarityScore " in text, "Hay similarity relations sin onto:similarityScore")

    if topic_assignment_refs:
        missing_assignments = sorted(set(topic_assignment_refs) - topic_assignments)
        missing_topics = sorted(set(topic_refs) - topics)

        require(
            not missing_assignments,
            f"Hay asignaciones de topic referenciadas sin onto:TopicAssignment: {missing_assignments[:5]}",
        )
        require(
            not missing_topics,
            f"Hay topics referenciados sin onto:Topic: {missing_topics[:5]}",
        )
        require("onto:topicScore " in text, "Hay topic assignments sin onto:topicScore")

    paper_blocks = re.findall(
        r"^(kg:paper_[A-Za-z0-9_]+)\n(.*?)(?=\nkg:|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )

    without_title = [paper for paper, block in paper_blocks if "onto:title " not in block]
    # without_author = [paper for paper, block in paper_blocks if "onto:hasAuthor " not in block]

    require(not without_title, f"Hay papers sin titulo: {without_title[:5]}")
    # require(not without_author, f"Hay papers sin autor: {without_author[:5]}")

    bad_uris = find_bad_uris(text)
    require(not bad_uris, f"Hay URIs con falsos positivos antiguos: {bad_uris[:10]}")

    suspicious_uris = find_empty_or_suspicious_uris(text)
    require(not suspicious_uris, f"Hay URIs sospechosas o vacías: {suspicious_uris[:10]}")

    duplicated_papers = duplicated_resources(papers)
    duplicated_people = duplicated_resources(people)
    duplicated_organizations = duplicated_resources(organizations)
    duplicated_projects = duplicated_resources(projects)

    require(not duplicated_papers, f"Hay papers duplicados: {list(duplicated_papers.items())[:5]}")
    require(not duplicated_people, f"Hay personas duplicadas: {list(duplicated_people.items())[:5]}")
    require(not duplicated_organizations, f"Hay organizaciones duplicadas: {list(duplicated_organizations.items())[:5]}")
    require(not duplicated_projects, f"Hay proyectos duplicados: {list(duplicated_projects.items())[:5]}")

    print("\nEntidades:")
    print(f"  Papers: {len(papers)}")
    print(f"  Personas: {len(people)}")
    print(f"  Organizaciones: {len(organizations)}")
    print(f"  Proyectos/grants: {len(projects)}")
    print(f"  Topics: {len(topics)}")
    print(f"  Asignaciones de topic: {len(topic_assignments)}")
    print(f"  Relaciones de similarity: {len(similarity_relations)}")
    print(f"  Galaxias: {len(galaxies)}")
    print(f"  Evidencias de galaxias: {len(evidences)}")

    print("\nRelaciones:")
    print(f"  hasAuthor: {len(author_refs)}")
    print(f"  acknowledgesPerson: {len(person_ack_refs)}")
    print(f"  acknowledgesOrganization: {len(org_ack_refs)}")
    print(f"  fundedBy: {len(funding_refs)}")
    print(f"  hasSimilarityRelation: {len(similarity_refs)}")
    print(f"  hasTopicAssignment: {len(topic_assignment_refs)}")
    print(f"  studiesGalaxy: {len(galaxy_refs)}")
    print(f"  hasGalaxyStudyEvidence: {len(evidence_refs)}")
    print(f"  fundingID: {len(funding_ids)}")

    if len(organizations) == 0:
        print("AVISO: No se han encontrado organizaciones NER/funding.")

    if len(projects) == 0:
        print("AVISO: No se han encontrado proyectos/grants.")

    if len(org_ack_refs) == 0:
        print("AVISO: No hay relaciones onto:acknowledgesOrganization.")

    if len(funding_refs) == 0:
        print("AVISO: No hay relaciones onto:fundedBy.")

    print("\nResultado KG: OK")
    return True


def validate_provenance(provenance_path: str) -> bool:
    print(f"\nValidando provenance: {provenance_path}")

    triples = validate_turtle(provenance_path)
    text = read_text(provenance_path)

    print(f"TTL parseado correctamente: {triples} triples")

    require("@prefix prov:" in text, "Falta prefijo prov")
    require("prov:Activity" in text, "No hay actividades prov:Activity")
    require("prov:Entity" in text, "No hay entidades prov:Entity")
    require("prov:SoftwareAgent" in text, "No hay scripts prov:SoftwareAgent")
    require("prov:used" in text, "No hay relaciones prov:used")
    require("prov:wasGeneratedBy" in text, "No hay relaciones prov:wasGeneratedBy")

    activities = len(re.findall(r"\n\s+a prov:Activity", text))
    entities = len(re.findall(r"\n\s+a prov:Entity", text))
    software_agents = len(re.findall(r"\n\s+a prov:SoftwareAgent", text))
    used_relations = text.count("prov:used")
    generated_relations = text.count("prov:wasGeneratedBy")

    require(activities >= 5, "Hay muy pocas actividades PROV registradas")
    require(used_relations > 0, "No se han registrado inputs/modelos usados")
    require(generated_relations > 0, "No se han registrado outputs generados")

    expected_terms = [
        "GROBID",
        "sentence-transformers/all-mpnet-base-v2",
        "BERTopic",
        "dslim/bert-base-NER",
        "src/funding.py",
        "src/build_kg.py",
        "outputs/kg.ttl",
    ]

    missing_terms = [term for term in expected_terms if term not in text]
    require(not missing_terms, f"Faltan elementos esperados en provenance: {missing_terms}")

    print("\nProvenance:")
    print(f"  Actividades: {activities}")
    print(f"  Entidades: {entities}")
    print(f"  Software agents: {software_agents}")
    print(f"  Relaciones used: {used_relations}")
    print(f"  Relaciones wasGeneratedBy: {generated_relations}")

    print("\nResultado provenance: OK")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Validacion del KG final y provenance")
    parser.add_argument("--kg", default=KG_TTL, help="Archivo Turtle del KG")
    parser.add_argument("--provenance", default=PROVENANCE_TTL, help="Archivo Turtle de provenance")
    parser.add_argument("--skip-provenance", action="store_true", help="Validar solo el KG")

    args = parser.parse_args()

    validate_kg(args.kg)

    if not args.skip_provenance:
        validate_provenance(args.provenance)

    print("\nResumen final:")
    print("  KG: OK")

    if not args.skip_provenance:
        print("  Provenance: OK")

    print("\nValidacion completada correctamente.")
    print("Consultas SPARQL de referencia: queries/*.sparql")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())