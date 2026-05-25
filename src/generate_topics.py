import argparse
import csv
import os
import warnings
from collections import Counter

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/grupo6_matplotlib")
os.environ.setdefault("PYTHONWARNINGS", "ignore:urllib3 v2 only supports OpenSSL")
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

try:
    from urllib3.exceptions import NotOpenSSLWarning

    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except Exception:
    pass

import numpy as np
from bertopic import BERTopic
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP


INPUT_CSV = "data/intermediate/papers_master.csv"
PAPER_TOPICS_CSV = "outputs/paper_topics.csv"
TOPICS_INFO_CSV = "outputs/topics_info.csv"

RANDOM_STATE = 42
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
CONFIG_ID = "bertopic_reduced_k6"
TARGET_TOPICS = 6
TOP_WORDS = 10

BER_TOPIC_CONFIG = {
    "n_neighbors": 3,
    "n_components": 2,
    "min_cluster_size": 2,
    "min_samples": 1,
}


def read_papers(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        papers = []
        for row in reader:
            abstract = (row.get("abstract") or "").strip()
            if row.get("usable_for_topic_modeling") == "yes" and abstract:
                papers.append({
                    "id": row["id"],
                    "title": (row.get("title") or "").strip(),
                    "abstract": abstract,
                })
        return papers


def labels_from_words(words_by_topic: dict[int, list[str]]) -> dict[int, str]:
    labels = {}
    for topic_id, words in words_by_topic.items():
        labels[topic_id] = " / ".join(words[:3]) if words else f"topic {topic_id}"
    return labels


def confidence_scores(probs, topics: list[int]) -> list[float]:
    if probs is None:
        return [1.0 if topic != -1 else 0.0 for topic in topics]

    probs = np.array(probs)
    if probs.ndim == 1:
        return [float(value) for value in probs]

    return [0.0 if topic == -1 else float(np.max(probs[index])) for index, topic in enumerate(topics)]


def build_topic_model() -> BERTopic:
    umap_model = UMAP(
        n_neighbors=BER_TOPIC_CONFIG["n_neighbors"],
        n_components=BER_TOPIC_CONFIG["n_components"],
        min_dist=0.0,
        metric="cosine",
        random_state=RANDOM_STATE,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=BER_TOPIC_CONFIG["min_cluster_size"],
        min_samples=BER_TOPIC_CONFIG["min_samples"],
        metric="euclidean",
        prediction_data=True,
    )
    vectorizer_model = CountVectorizer(stop_words="english", min_df=1, ngram_range=(1, 2))
    return BERTopic(
        embedding_model=None,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        nr_topics=TARGET_TOPICS,
        calculate_probabilities=True,
        verbose=False,
    )


def generate_topics(papers: list[dict], local_files_only: bool) -> dict:
    docs = [paper["abstract"] for paper in papers]
    embedding_model = SentenceTransformer(EMBEDDING_MODEL, local_files_only=local_files_only)
    embeddings = embedding_model.encode(docs, normalize_embeddings=True, show_progress_bar=False)

    topic_model = build_topic_model()
    topics, probs = topic_model.fit_transform(docs, embeddings)
    assigned_topics = [int(topic) for topic in topics]
    topic_ids = sorted(topic_id for topic_id in set(assigned_topics) if topic_id != -1)
    words_by_topic = {
        topic_id: [word for word, _ in (topic_model.get_topic(topic_id) or [])[:TOP_WORDS]]
        for topic_id in topic_ids
    }
    return {
        "assigned_topics": assigned_topics,
        "confidences": confidence_scores(probs, assigned_topics),
        "topic_ids": topic_ids,
        "topic_words": words_by_topic,
        "topic_labels": labels_from_words(words_by_topic),
        "topic_sizes": Counter(assigned_topics),
        "outliers": Counter(assigned_topics).get(-1, 0),
    }


def write_topics_info(path: str, result: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = [
        "topic_id",
        "topic_label",
        "top_words",
        "size",
        "model_name",
        "config_id",
        "embedding_model",
        "target_topics",
        "outliers",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for topic_id in result["topic_ids"]:
            writer.writerow({
                "topic_id": topic_id,
                "topic_label": result["topic_labels"][topic_id],
                "top_words": "; ".join(result["topic_words"][topic_id]),
                "size": result["topic_sizes"].get(topic_id, 0),
                "model_name": "BERTopic",
                "config_id": CONFIG_ID,
                "embedding_model": EMBEDDING_MODEL,
                "target_topics": TARGET_TOPICS,
                "outliers": result["outliers"],
            })


def write_paper_topics(path: str, papers: list[dict], result: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = [
        "topic_assignment_id",
        "paper_id",
        "title",
        "topic_id",
        "topic_score",
        "topic_label",
        "topic_model",
        "config_id",
        "embedding_model",
        "is_outlier",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for index, paper in enumerate(papers):
            topic_id = result["assigned_topics"][index]
            is_outlier = topic_id == -1
            writer.writerow({
                "topic_assignment_id": f"topic_assignment_{index + 1:03d}",
                "paper_id": paper["id"],
                "title": paper["title"],
                "topic_id": topic_id,
                "topic_score": f"{float(result['confidences'][index]):.4f}",
                "topic_label": "outlier" if is_outlier else result["topic_labels"].get(topic_id, f"topic {topic_id}"),
                "topic_model": "BERTopic",
                "config_id": CONFIG_ID,
                "embedding_model": EMBEDDING_MODEL,
                "is_outlier": "yes" if is_outlier else "no",
            })


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera topics finales para el KG")
    parser.add_argument("--input", default=INPUT_CSV)
    parser.add_argument("--paper-topics", default=PAPER_TOPICS_CSV)
    parser.add_argument("--topics-info", default=TOPICS_INFO_CSV)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()

    local_files_only = not args.allow_download
    if local_files_only:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    papers = read_papers(args.input)
    if not papers:
        raise ValueError("No hay abstracts validos para topic modeling")

    result = generate_topics(papers, local_files_only)
    write_topics_info(args.topics_info, result)
    write_paper_topics(args.paper_topics, papers, result)

    print(f"Guardado: {args.paper_topics}")
    print(f"Guardado: {args.topics_info}")
    print(f"Papers evaluados: {len(papers)}")
    print(f"Topics exportados: {len(result['topic_ids'])}")
    print(f"Outliers: {result['outliers']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
