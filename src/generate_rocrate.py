import argparse
import json
import os
from datetime import date


OUTPUT = "ro-crate-metadata.json"


def file_entity(path, name=None, description=None, encoding_format=None):
    entity = {
        "@id": path,
        "@type": "File",
        "name": name or os.path.basename(path),
    }

    if description:
        entity["description"] = description

    if encoding_format:
        entity["encodingFormat"] = encoding_format

    if os.path.exists(path):
        entity["contentSize"] = os.path.getsize(path)

    return entity


def directory_entity(path, name=None, description=None):
    return {
        "@id": path if path.endswith("/") else path + "/",
        "@type": "Dataset",
        "name": name or os.path.basename(path),
        "description": description or "",
    }


def software_entity(path, description):
    return {
        "@id": path,
        "@type": "SoftwareSourceCode",
        "name": os.path.basename(path),
        "description": description,
        "programmingLanguage": "Python",
        "encodingFormat": "text/x-python",
    }


def build_rocrate():
    today = date.today().isoformat()

    graph = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            "about": {"@id": "./"},
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "name": "Grupo 6 IA - Knowledge Graph of Astrophysics of Galaxies publications",
            "description": (
                "Research Object describing a reproducible pipeline for analysing 30 scientific "
                "papers about Astrophysics of Galaxies. The workflow extracts metadata and "
                "acknowledgements with GROBID, computes semantic similarity and topic modeling "
                "from abstracts, extracts NER/funding entities from acknowledgements using "
                "HuggingFace models and rules, and builds an RDF Knowledge Graph."
            ),
            "datePublished": today,
            "license": {"@id": "LICENSE"},
            "author": [
                {"@id": "#grupo-6"}
            ],
            "hasPart": [
                {"@id": "data/papers.csv"},
                {"@id": "data/intermediate/papers_master.csv"},
                {"@id": "data/evaluation/ner/ner_gold.csv"},
                {"@id": "data/evaluation/ner/ner_model_comparison.csv"},
                {"@id": "ontologia/ontology.ttl"},
                {"@id": "outputs/kg.ttl"},
                {"@id": "outputs/semantic_similarity_relations_embeddings.csv"},
                {"@id": "outputs/paper_topics.csv"},
                {"@id": "outputs/topics_info.csv"},
                {"@id": "outputs/funding_entities.csv"},
                {"@id": "outputs/provenance.json"},
                {"@id": "outputs/provenance.ttl"},
                {"@id": "queries/"},
                {"@id": "src/"},
                {"@id": "evaluation/"},
                {"@id": "requirements.txt"},
                {"@id": "Dockerfile"},
                {"@id": "docker-compose.yml"},
                {"@id": "README.md"},
            ],
            "mentions": [
                {"@id": "#workflow"},
                {"@id": "#model-all-mpnet-base-v2"},
                {"@id": "#model-dslim-bert-base-ner"},
                {"@id": "#grobid"},
                {"@id": "#bertopic"},
            ],
        },
        {
            "@id": "#grupo-6",
            "@type": "Organization",
            "name": "Grupo 6 IA",
        },
        {
            "@id": "#grupo-6",
            "@type": "Organization",
            "name": "Grupo 6 IA",
        },
        {
            "@id": "LICENSE",
            "@type": "CreativeWork",
            "name": "Project license",
        },
        {
            "@id": "#workflow",
            "@type": "ComputationalWorkflow",
            "name": "Publication analysis and KG construction workflow",
            "description": (
                "Pipeline that downloads papers, processes PDFs with GROBID, extracts a master CSV, "
                "computes semantic similarity, performs topic modeling, extracts NER/funding entities, "
                "builds the RDF Knowledge Graph and validates the final KG."
            ),
            "step": [
                {"@id": "#step-download-pdfs"},
                {"@id": "#step-grobid"},
                {"@id": "#step-master-csv"},
                {"@id": "#step-similarity"},
                {"@id": "#step-topics"},
                {"@id": "#step-ner-funding"},
                {"@id": "#step-build-kg"},
                {"@id": "#step-validate-kg"},
            ],
        },
        {
            "@id": "#step-download-pdfs",
            "@type": "HowToStep",
            "name": "Download PDFs",
            "description": "Download paper PDFs from the metadata CSV.",
            "instrument": {"@id": "src/download_pdfs.py"},
            "workExample": "python src/download_pdfs.py",
        },
        {
            "@id": "#step-grobid",
            "@type": "HowToStep",
            "name": "Run GROBID",
            "description": "Extract TEI XML files from downloaded PDFs.",
            "instrument": {"@id": "src/run_grobid.py"},
            "workExample": "docker compose up -d grobid && python src/run_grobid.py --limit 0",
        },
        {
            "@id": "#step-master-csv",
            "@type": "HowToStep",
            "name": "Generate master CSV",
            "description": "Create papers_master.csv with extracted metadata, abstracts and acknowledgements.",
            "instrument": {"@id": "src/extract_papers_master.py"},
            "workExample": "python src/extract_papers_master.py",
        },
        {
            "@id": "#step-similarity",
            "@type": "HowToStep",
            "name": "Generate semantic similarity",
            "description": "Compute abstract similarity using HuggingFace sentence embeddings.",
            "instrument": {"@id": "src/generate_similarity.py"},
            "workExample": "python src/generate_similarity.py --allow-download",
        },
        {
            "@id": "#step-topics",
            "@type": "HowToStep",
            "name": "Generate topics",
            "description": "Generate topic assignments using BERTopic and sentence embeddings.",
            "instrument": {"@id": "src/generate_topics.py"},
            "workExample": "python src/generate_topics.py --allow-download",
        },
        {
            "@id": "#step-ner-funding",
            "@type": "HowToStep",
            "name": "Extract NER/funding entities",
            "description": (
                "Extract persons, organizations, funders, grants and project identifiers "
                "from acknowledgements using the selected HuggingFace NER model and regex rules."
            ),
            "instrument": {"@id": "src/funding.py"},
            "workExample": "python src/funding.py --allow-download",
        },
        {
            "@id": "#step-build-kg",
            "@type": "HowToStep",
            "name": "Build RDF Knowledge Graph",
            "description": "Integrate papers, authors, topics, similarity and funding entities into RDF.",
            "instrument": {"@id": "src/build_kg.py"},
            "workExample": (
                "python src/build_kg.py "
                "--similarity outputs/semantic_similarity_relations_embeddings.csv "
                "--topics outputs/paper_topics.csv "
                "--funding outputs/funding_entities.csv"
            ),
        },
        {
            "@id": "#step-validate-kg",
            "@type": "HowToStep",
            "name": "Validate KG",
            "description": "Validate that the final Turtle file parses correctly and contains expected entities.",
            "instrument": {"@id": "src/validate_kg.py"},
            "workExample": "python src/validate_kg.py",
        },
        {
            "@id": "#grobid",
            "@type": "SoftwareApplication",
            "name": "GROBID",
            "description": "Tool used to extract structured TEI XML from scientific PDFs.",
        },
        {
            "@id": "#model-all-mpnet-base-v2",
            "@type": "SoftwareApplication",
            "name": "sentence-transformers/all-mpnet-base-v2",
            "description": "HuggingFace/Sentence Transformers model used to compute abstract embeddings.",
        },
        {
            "@id": "#model-dslim-bert-base-ner",
            "@type": "SoftwareApplication",
            "name": "dslim/bert-base-NER",
            "description": "Selected HuggingFace NER model used for acknowledgements entity extraction.",
        },
        {
            "@id": "#bertopic",
            "@type": "SoftwareApplication",
            "name": "BERTopic",
            "description": "Topic modeling library used to group papers by themes.",
        },
    ]

    graph.extend([
        directory_entity("src", "Source code", "Python scripts implementing the pipeline."),
        directory_entity("evaluation", "Evaluation scripts", "Scripts used to evaluate similarity, topics and NER models."),
        directory_entity("queries", "SPARQL queries", "Reference SPARQL queries for the generated RDF Knowledge Graph."),
        directory_entity("outputs", "Generated outputs", "Generated CSV and RDF outputs of the pipeline."),
        directory_entity("data/evaluation/ner", "NER evaluation data", "Gold standard and model comparison files for NER evaluation."),
    ])

    graph.extend([
        file_entity("data/papers.csv", "Paper metadata", "Initial metadata file with selected papers.", "text/csv"),
        file_entity(
            "data/intermediate/papers_master.csv",
            "Master papers CSV",
            "CSV containing extracted metadata, abstracts and acknowledgements.",
            "text/csv",
        ),
        file_entity(
            "data/evaluation/ner/ner_gold.csv",
            "NER gold standard",
            "Manually annotated gold standard used to evaluate HuggingFace NER models.",
            "text/csv",
        ),
        file_entity(
            "data/evaluation/ner/ner_model_comparison.csv",
            "NER model comparison",
            "Precision, recall and F1 comparison of the tested HuggingFace NER models.",
            "text/csv",
        ),
        file_entity(
            "ontologia/ontology.ttl",
            "Ontology",
            "RDF/OWL ontology defining the classes and properties of the KG.",
            "text/turtle",
        ),
        file_entity(
            "outputs/kg.ttl",
            "RDF Knowledge Graph",
            "Final RDF Knowledge Graph in Turtle format.",
            "text/turtle",
        ),
        file_entity(
            "outputs/semantic_similarity_relations_embeddings.csv",
            "Semantic similarity output",
            "CSV containing semantic similarity relations between papers.",
            "text/csv",
        ),
        file_entity(
            "outputs/paper_topics.csv",
            "Paper topic assignments",
            "CSV containing paper-to-topic assignments.",
            "text/csv",
        ),
        file_entity(
            "outputs/topics_info.csv",
            "Topics information",
            "CSV containing topic labels and top words.",
            "text/csv",
        ),
        file_entity(
            "outputs/funding_entities.csv",
            "Funding and NER entities",
            "CSV containing extracted entities from acknowledgements.",
            "text/csv",
        ),
        file_entity(
            "outputs/provenance.json",
            "Provenance JSON",
            "JSON provenance record describing scripts, inputs, outputs and models used in the workflow.",
            "application/json",
        ),
        file_entity(
            "outputs/provenance.ttl",
            "Provenance RDF",
            "RDF/PROV-O provenance record describing scripts, inputs, outputs and models used in the workflow.",
            "text/turtle",
        ),
        file_entity("requirements.txt", "Python requirements", "Python dependencies required by the pipeline.", "text/plain"),
        file_entity("Dockerfile", "Dockerfile", "Docker image definition.", "text/plain"),
        file_entity("docker-compose.yml", "Docker Compose configuration", "Docker Compose services, including GROBID.", "text/yaml"),
        file_entity("README.md", "README", "Documentation and reproducibility instructions.", "text/markdown"),
    ])

    scripts = [
        ("src/download_pdfs.py", "Downloads PDFs for the selected papers."),
        ("src/run_grobid.py", "Runs GROBID over the downloaded PDFs."),
        ("src/extract_papers_master.py", "Builds the master CSV from TEI XML files."),
        ("src/generate_similarity.py", "Generates semantic similarity relations."),
        ("src/generate_topics.py", "Generates topic modeling outputs."),
        ("src/funding.py", "Extracts NER/funding entities from acknowledgements."),
        ("src/build_kg.py", "Builds the RDF Knowledge Graph."),
        ("src/validate_kg.py", "Validates the final RDF Knowledge Graph."),
        ("src/generate_rocrate.py", "Generates this RO-Crate metadata file."),
        ("src/generate_provenance.py", "Generates JSON and RDF provenance metadata for the pipeline."),
        ("evaluation/ner/evaluate_hf_ner_models.py", "Compares HuggingFace NER models on the gold standard."),
    ]

    for path, description in scripts:
        graph.append(software_entity(path, description))

    return {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": graph,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate RO-Crate metadata for the project.")
    parser.add_argument("--output", default=OUTPUT)
    args = parser.parse_args()

    crate = build_rocrate()

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(crate, f, indent=2, ensure_ascii=False)

    print(f"Guardado: {args.output}")
    print(f"Entidades en RO-Crate: {len(crate['@graph'])}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())