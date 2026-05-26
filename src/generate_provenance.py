import argparse
import json
import os
from datetime import datetime, timezone


OUTPUT_JSON = "outputs/provenance.json"
OUTPUT_TTL = "outputs/provenance.ttl"


def safe_id(text):
    return (
        text.replace("/", "_")
        .replace("\\", "_")
        .replace(".", "_")
        .replace("-", "_")
        .replace(" ", "_")
        .replace(":", "_")
        .replace("#", "_")
    )


def ttl_literal(text):
    text = "" if text is None else str(text)
    text = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    return f'"{text}"'


def entity(path, entity_type="File"):
    return {
        "id": path,
        "type": entity_type,
        "exists": os.path.exists(path),
    }


def build_provenance():
    generated_at = datetime.now(timezone.utc).isoformat()

    activities = [
        {
            "id": "download_pdfs",
            "label": "Download PDFs",
            "script": "src/download_pdfs.py",
            "inputs": ["data/papers.csv"],
            "outputs": ["data/pdfs/"],
            "models": [],
            "description": "Downloads the PDF files of the selected papers from the source URLs.",
        },
        {
            "id": "grobid_extraction",
            "label": "GROBID TEI extraction",
            "script": "src/run_grobid.py",
            "inputs": ["data/pdfs/"],
            "outputs": ["data/tei/"],
            "models": ["GROBID"],
            "description": "Extracts TEI XML files from scientific PDFs using GROBID.",
        },
        {
            "id": "master_csv_generation",
            "label": "Master CSV generation",
            "script": "src/extract_papers_master.py",
            "inputs": ["data/papers.csv", "data/tei/"],
            "outputs": ["data/intermediate/papers_master.csv"],
            "models": [],
            "description": "Builds the master CSV with metadata, titles, abstracts, authors and acknowledgements.",
        },
        {
            "id": "similarity_generation",
            "label": "Semantic similarity generation",
            "script": "src/generate_similarity.py",
            "inputs": ["data/intermediate/papers_master.csv"],
            "outputs": ["outputs/semantic_similarity_relations_embeddings.csv"],
            "models": ["sentence-transformers/all-mpnet-base-v2"],
            "description": "Computes semantic similarity between papers using abstract embeddings.",
        },
        {
            "id": "topic_modeling",
            "label": "Topic modeling",
            "script": "src/generate_topics.py",
            "inputs": ["data/intermediate/papers_master.csv"],
            "outputs": ["outputs/paper_topics.csv", "outputs/topics_info.csv"],
            "models": [
                "sentence-transformers/all-mpnet-base-v2",
                "BERTopic",
                "UMAP",
                "HDBSCAN",
            ],
            "description": "Assigns papers to topics using embeddings, dimensionality reduction and clustering.",
        },
        {
            "id": "ner_model_evaluation",
            "label": "NER model evaluation",
            "script": "evaluation/ner/evaluate_hf_ner_models.py",
            "inputs": [
                "data/intermediate/papers_master.csv",
                "data/evaluation/ner/ner_gold.csv",
            ],
            "outputs": ["data/evaluation/ner/ner_model_comparison.csv"],
            "models": [
                "dslim/bert-base-NER",
                "Jean-Baptiste/roberta-large-ner-english",
                "Davlan/bert-base-multilingual-cased-ner-hrl",
            ],
            "description": "Compares HuggingFace NER models against a manually annotated gold standard.",
        },
        {
            "id": "ner_funding_extraction",
            "label": "NER and funding extraction",
            "script": "src/funding.py",
            "inputs": [
                "data/intermediate/papers_master.csv",
                "data/evaluation/ner/ner_model_comparison.csv",
            ],
            "outputs": ["outputs/funding_entities.csv"],
            "models": [
                "dslim/bert-base-NER",
                "regular expressions for grant and project IDs",
                "context rules for funders",
            ],
            "description": "Extracts persons, organizations, funders, grant IDs and project IDs from acknowledgements.",
        },
        {
            "id": "ror_enrichment",
            "label": "ROR organization enrichment",
            "script": "src/enrich_organizations_ror.py",
            "inputs": [
                "outputs/funding_entities.csv"
            ],
            "outputs": [
                "outputs/organization_ror_matches.csv"
            ],
            "models": [
                "ROR API v2 affiliation matching"
            ],
            "description": "Matches extracted organizations against ROR to obtain persistent organization identifiers and country metadata.",
        },
        {
            "id": "kg_construction",
            "label": "Knowledge Graph construction",
            "script": "src/build_kg.py",
            "inputs": [
                "data/intermediate/papers_master.csv",
                "outputs/semantic_similarity_relations_embeddings.csv",
                "outputs/paper_topics.csv",
                "outputs/funding_entities.csv",
                "ontologia/ontology.ttl",
                "outputs/organization_ror_matches.csv",
            ],
            "outputs": ["outputs/kg.ttl"],
            "models": [],
            "description": "Builds the RDF Knowledge Graph by integrating metadata, authors, similarity, topics and funding entities.",
        },
        {
            "id": "kg_validation",
            "label": "Knowledge Graph validation",
            "script": "src/validate_kg.py",
            "inputs": ["outputs/kg.ttl", "queries/"],
            "outputs": ["validation report printed in terminal"],
            "models": [],
            "description": "Validates that the Turtle KG parses correctly and contains the expected entities and relations.",
        },
        {
            "id": "rocrate_generation",
            "label": "RO-Crate metadata generation",
            "script": "src/generate_rocrate.py",
            "inputs": [
                "data/",
                "src/",
                "outputs/",
                "ontologia/",
                "queries/",
                "README.md",
            ],
            "outputs": ["ro-crate-metadata.json"],
            "models": [],
            "description": "Generates RO-Crate metadata describing the research object and workflow.",
        },
    ]

    return {
        "generated_at": generated_at,
        "description": "Provenance metadata for the Grupo 6 IA publication analysis and Knowledge Graph construction pipeline.",
        "activities": activities,
    }


def write_json(path, provenance):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2, ensure_ascii=False)


def write_ttl(path, provenance):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines = [
        "@prefix kg: <https://w3id.org/grupo6-ia/resource/> .",
        "@prefix prov: <http://www.w3.org/ns/prov#> .",
        "@prefix dcterms: <http://purl.org/dc/terms/> .",
        "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
        "",
        "kg:provenance_record",
        "    a prov:Entity ;",
        '    dcterms:title "Grupo 6 IA provenance record" ;',
        f'    prov:generatedAtTime "{provenance["generated_at"]}"^^xsd:dateTime .',
        "",
    ]

    created_entities = set()

    for activity in provenance["activities"]:
        activity_uri = f"kg:activity_{safe_id(activity['id'])}"
        script_uri = f"kg:script_{safe_id(activity['script'])}"

        lines.extend(
            [
                f"{activity_uri}",
                "    a prov:Activity ;",
                f"    dcterms:title {ttl_literal(activity['label'])} ;",
                f"    dcterms:description {ttl_literal(activity['description'])} ;",
                f"    prov:wasAssociatedWith {script_uri} .",
                "",
            ]
        )

        if script_uri not in created_entities:
            created_entities.add(script_uri)
            lines.extend(
                [
                    f"{script_uri}",
                    "    a prov:SoftwareAgent ;",
                    f"    dcterms:identifier {ttl_literal(activity['script'])} .",
                    "",
                ]
            )

        for input_path in activity["inputs"]:
            input_uri = f"kg:input_{safe_id(input_path)}"

            if input_uri not in created_entities:
                created_entities.add(input_uri)
                lines.extend(
                    [
                        f"{input_uri}",
                        "    a prov:Entity ;",
                        f"    dcterms:identifier {ttl_literal(input_path)} .",
                        "",
                    ]
                )

            lines.extend(
                [
                    f"{activity_uri}",
                    f"    prov:used {input_uri} .",
                    "",
                ]
            )

        for model in activity["models"]:
            model_uri = f"kg:model_{safe_id(model)}"

            if model_uri not in created_entities:
                created_entities.add(model_uri)
                lines.extend(
                    [
                        f"{model_uri}",
                        "    a prov:Entity ;",
                        f"    dcterms:title {ttl_literal(model)} .",
                        "",
                    ]
                )

            lines.extend(
                [
                    f"{activity_uri}",
                    f"    prov:used {model_uri} .",
                    "",
                ]
            )

        for output_path in activity["outputs"]:
            output_uri = f"kg:output_{safe_id(output_path)}"

            if output_uri not in created_entities:
                created_entities.add(output_uri)
                lines.extend(
                    [
                        f"{output_uri}",
                        "    a prov:Entity ;",
                        f"    dcterms:identifier {ttl_literal(output_path)} ;",
                        f"    prov:wasGeneratedBy {activity_uri} .",
                        "",
                    ]
                )
            else:
                lines.extend(
                    [
                        f"{output_uri}",
                        f"    prov:wasGeneratedBy {activity_uri} .",
                        "",
                    ]
                )

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Generate provenance metadata for the project pipeline.")
    parser.add_argument("--json-output", default=OUTPUT_JSON)
    parser.add_argument("--ttl-output", default=OUTPUT_TTL)

    args = parser.parse_args()

    provenance = build_provenance()

    write_json(args.json_output, provenance)
    write_ttl(args.ttl_output, provenance)

    print(f"Guardado: {args.json_output}")
    print(f"Guardado: {args.ttl_output}")
    print(f"Actividades registradas: {len(provenance['activities'])}")

    for activity in provenance["activities"]:
        print(f"  - {activity['id']}: {activity['label']}")


if __name__ == "__main__":
    main()