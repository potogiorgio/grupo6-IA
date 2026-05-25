import argparse
import re


KG_TTL = "outputs/kg.ttl"


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def prefixed_subjects(text: str, rdf_type: str) -> set[str]:
    pattern = rf"^(kg:[A-Za-z0-9_]+)\n\s+a {re.escape(rdf_type)}\b"
    return set(re.findall(pattern, text, flags=re.MULTILINE))


def object_refs(text: str, predicate: str) -> list[str]:
    pattern = rf"{re.escape(predicate)} (kg:[A-Za-z0-9_]+)"
    return re.findall(pattern, text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validacion liviana del KG minimo sin motor SPARQL")
    parser.add_argument("--kg", default=KG_TTL, help="Archivo Turtle del KG")
    args = parser.parse_args()

    text = read_text(args.kg)

    require("@prefix kg:" in text, "Falta prefijo kg")
    require("@prefix onto:" in text, "Falta prefijo onto")
    require("kg:knowledge_graph" in text, "Falta metadata del dataset")

    papers = prefixed_subjects(text, "onto:Paper")
    people = prefixed_subjects(text, "onto:Person")
    author_refs = object_refs(text, "onto:hasAuthor")
    similarity_refs = object_refs(text, "onto:hasSimilarityRelation")
    topic_assignment_refs = object_refs(text, "onto:hasTopicAssignment")

    require(len(papers) > 0, "No hay recursos onto:Paper")
    require(len(people) > 0, "No hay recursos onto:Person")
    require(len(author_refs) > 0, "No hay relaciones onto:hasAuthor")

    missing_people = sorted(set(author_refs) - people)
    require(not missing_people, f"Hay autores referenciados sin onto:Person: {missing_people[:5]}")

    if similarity_refs:
        similarity_relations = prefixed_subjects(text, "onto:SimilarityRelation")
        missing_similarity = sorted(set(similarity_refs) - similarity_relations)
        require(
            not missing_similarity,
            f"Hay relaciones de similarity referenciadas sin onto:SimilarityRelation: {missing_similarity[:5]}",
        )
        require("onto:similarPaper " in text, "Hay similarity relations sin onto:similarPaper")
        require("onto:similarityScore " in text, "Hay similarity relations sin onto:similarityScore")

    if topic_assignment_refs:
        topic_assignments = prefixed_subjects(text, "onto:TopicAssignment")
        topics = prefixed_subjects(text, "onto:Topic")
        topic_refs = object_refs(text, "onto:assignedTopic")
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

    paper_blocks = re.findall(r"^(kg:paper_[A-Za-z0-9_]+)\n(.*?)(?=\nkg:|\Z)", text, flags=re.MULTILINE | re.DOTALL)
    without_title = [paper for paper, block in paper_blocks if "onto:title " not in block]
    without_author = [paper for paper, block in paper_blocks if "onto:hasAuthor " not in block]

    require(not without_title, f"Hay papers sin titulo: {without_title[:5]}")
    require(not without_author, f"Hay papers sin autor: {without_author[:5]}")

    print(f"KG validado: {args.kg}")
    print(f"Papers: {len(papers)}")
    print(f"Personas: {len(people)}")
    print(f"Relaciones hasAuthor: {len(author_refs)}")
    print(f"Relaciones de similarity: {len(similarity_refs)}")
    print(f"Asignaciones de topic: {len(topic_assignment_refs)}")
    print("Consultas SPARQL de referencia: queries/*.sparql")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
