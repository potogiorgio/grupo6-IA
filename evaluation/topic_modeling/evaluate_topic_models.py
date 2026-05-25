import argparse
import csv
import os
import warnings
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from typing import Optional

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
from gensim.corpora import Dictionary
from gensim.models import CoherenceModel
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP


INPUT_CSV = "data/intermediate/papers_master.csv"
PAPER_TOPICS_CSV = "outputs/paper_topics.csv"
TOPICS_INFO_CSV = "outputs/topics_info.csv"
REVIEW_CSV = "data/evaluation/topic_modeling_review.csv"
COMPARISON_CSV = "outputs/comparisons/topic_modeling_comparison.csv"

RANDOM_STATE = 42
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
TOP_WORDS = 10
TOPIC_COUNTS = [5, 6, 7]
COHERENCE_METRICS = ["c_v", "c_npmi", "u_mass"]

BER_TOPIC_BASE_CONFIG = {
    "n_neighbors": 3,
    "n_components": 2,
    "min_cluster_size": 2,
    "min_samples": 1,
}


def package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "pendiente"


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


def tokenize(text: str) -> list[str]:
    tokens = CountVectorizer(stop_words="english").build_analyzer()(text)
    return [token for token in tokens if len(token) > 2]


def coherence_scores(topics_words: list[list[str]], tokenized_docs: list[list[str]]) -> dict[str, float]:
    dictionary = Dictionary(tokenized_docs)
    corpus = [dictionary.doc2bow(text) for text in tokenized_docs]
    scores = {}
    for metric in COHERENCE_METRICS:
        kwargs = {
            "topics": topics_words,
            "texts": tokenized_docs,
            "dictionary": dictionary,
            "coherence": metric,
        }
        if metric == "u_mass":
            kwargs["corpus"] = corpus
        model = CoherenceModel(**kwargs)
        scores[metric] = float(model.get_coherence())
    return scores


def topic_diversity(topics_words: list[list[str]]) -> float:
    words = [word for topic in topics_words for word in topic]
    return len(set(words)) / len(words) if words else 0.0


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

    scores = []
    for index, topic in enumerate(topics):
        scores.append(0.0 if topic == -1 else float(np.max(probs[index])))
    return scores


def result_dict(
    config_id: str,
    model_name: str,
    target_topics: int,
    assigned_topics: list[int],
    confidences: list[float],
    words_by_topic: dict[int, list[str]],
    tokenized_docs: list[list[str]],
    embedding_model: str = "",
    perplexity: Optional[float] = None,
) -> dict:
    counts = Counter(assigned_topics)
    outliers = counts.get(-1, 0)
    topic_ids = sorted(topic_id for topic_id in words_by_topic if topic_id != -1)
    coherence_input = [words_by_topic[topic_id] for topic_id in topic_ids if words_by_topic[topic_id]]
    coherences = coherence_scores(coherence_input, tokenized_docs) if coherence_input else {
        metric: 0.0 for metric in COHERENCE_METRICS
    }

    return {
        "config_id": config_id,
        "model_name": model_name,
        "target_topics": target_topics,
        "embedding_model": embedding_model,
        "assigned_topics": assigned_topics,
        "confidences": confidences,
        "topic_ids": topic_ids,
        "topic_words": words_by_topic,
        "topic_labels": labels_from_words(words_by_topic),
        "topic_sizes": counts,
        "outliers": outliers,
        "outlier_ratio": outliers / len(assigned_topics),
        "n_topics": len(topic_ids),
        "topic_diversity": topic_diversity(coherence_input),
        "mean_confidence": float(np.mean(confidences)) if confidences else 0.0,
        "perplexity": perplexity,
        **coherences,
    }


def evaluate_bertopic(papers: list[dict], embeddings: np.ndarray, target_topics: int) -> dict:
    docs = [paper["abstract"] for paper in papers]
    tokenized_docs = [tokenize(doc) for doc in docs]
    config = BER_TOPIC_BASE_CONFIG
    umap_model = UMAP(
        n_neighbors=config["n_neighbors"],
        n_components=config["n_components"],
        min_dist=0.0,
        metric="cosine",
        random_state=RANDOM_STATE,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=config["min_cluster_size"],
        min_samples=config["min_samples"],
        metric="euclidean",
        prediction_data=True,
    )
    vectorizer_model = CountVectorizer(stop_words="english", min_df=1, ngram_range=(1, 2))
    model = BERTopic(
        embedding_model=None,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        nr_topics=target_topics,
        calculate_probabilities=True,
        verbose=False,
    )
    topics, probs = model.fit_transform(docs, embeddings)
    assigned_topics = [int(topic) for topic in topics]
    topic_ids = sorted(topic_id for topic_id in set(assigned_topics) if topic_id != -1)
    words_by_topic = {
        topic_id: [word for word, _ in (model.get_topic(topic_id) or [])[:TOP_WORDS]]
        for topic_id in topic_ids
    }

    return result_dict(
        config_id=f"bertopic_reduced_k{target_topics}",
        model_name="BERTopic",
        target_topics=target_topics,
        assigned_topics=assigned_topics,
        confidences=confidence_scores(probs, assigned_topics),
        words_by_topic=words_by_topic,
        tokenized_docs=tokenized_docs,
        embedding_model=EMBEDDING_MODEL,
    )


def evaluate_lda(papers: list[dict], target_topics: int) -> dict:
    docs = [paper["abstract"] for paper in papers]
    tokenized_docs = [tokenize(doc) for doc in docs]
    vectorizer = CountVectorizer(stop_words="english", min_df=1, ngram_range=(1, 2))
    doc_term_matrix = vectorizer.fit_transform(docs)
    lda = LatentDirichletAllocation(
        n_components=target_topics,
        random_state=RANDOM_STATE,
        learning_method="batch",
        max_iter=50,
    )
    doc_topic = lda.fit_transform(doc_term_matrix)
    feature_names = np.array(vectorizer.get_feature_names_out())
    assigned_topics = [int(topic_id) for topic_id in np.argmax(doc_topic, axis=1)]
    confidences = [float(score) for score in np.max(doc_topic, axis=1)]
    words_by_topic = {
        topic_id: feature_names[np.argsort(component)[::-1][:TOP_WORDS]].tolist()
        for topic_id, component in enumerate(lda.components_)
    }

    return result_dict(
        config_id=f"lda_count_k{target_topics}",
        model_name="LDA",
        target_topics=target_topics,
        assigned_topics=assigned_topics,
        confidences=confidences,
        words_by_topic=words_by_topic,
        tokenized_docs=tokenized_docs,
        perplexity=float(lda.perplexity(doc_term_matrix)),
    )


def select_best(results: list[dict]) -> dict:
    candidates = [result for result in results if result["n_topics"] > 1]
    return max(
        candidates or results,
        key=lambda result: (
            round(result["c_v"], 6),
            round(result["c_npmi"], 6),
            round(result["topic_diversity"], 6),
            -result["outlier_ratio"],
        ),
    )


def distribution_text(result: dict) -> str:
    return ", ".join(f"{topic}:{size}" for topic, size in sorted(result["topic_sizes"].items()))


def write_comparison(path: str, results: list[dict], best: dict, n_papers: int) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = [
        "selected",
        "model_name",
        "config_id",
        "embedding_model",
        "papers",
        "target_topics",
        "topics",
        "outliers",
        "c_v",
        "c_npmi",
        "u_mass",
        "perplexity",
        "topic_diversity",
        "mean_confidence",
        "distribution",
        "bertopic_version",
        "gensim_version",
        "random_state",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({
                "selected": "yes" if result["config_id"] == best["config_id"] else "no",
                "model_name": result["model_name"],
                "config_id": result["config_id"],
                "embedding_model": result["embedding_model"],
                "papers": n_papers,
                "target_topics": result["target_topics"],
                "topics": result["n_topics"],
                "outliers": result["outliers"],
                "c_v": f"{result['c_v']:.4f}",
                "c_npmi": f"{result['c_npmi']:.4f}",
                "u_mass": f"{result['u_mass']:.4f}",
                "perplexity": "" if result["perplexity"] is None else f"{result['perplexity']:.4f}",
                "topic_diversity": f"{result['topic_diversity']:.4f}",
                "mean_confidence": f"{result['mean_confidence']:.4f}",
                "distribution": distribution_text(result),
                "bertopic_version": package_version("bertopic"),
                "gensim_version": package_version("gensim"),
                "random_state": RANDOM_STATE,
            })


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
        "c_v",
        "c_npmi",
        "u_mass",
        "perplexity",
        "topic_diversity",
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
                "model_name": result["model_name"],
                "config_id": result["config_id"],
                "embedding_model": result["embedding_model"],
                "target_topics": result["target_topics"],
                "c_v": f"{result['c_v']:.4f}",
                "c_npmi": f"{result['c_npmi']:.4f}",
                "u_mass": f"{result['u_mass']:.4f}",
                "perplexity": "" if result["perplexity"] is None else f"{result['perplexity']:.4f}",
                "topic_diversity": f"{result['topic_diversity']:.4f}",
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
                "topic_model": result["model_name"],
                "config_id": result["config_id"],
                "embedding_model": result["embedding_model"],
                "is_outlier": "yes" if is_outlier else "no",
            })


def read_existing_human_labels(path: str) -> dict[tuple[str, str], str]:
    if not os.path.exists(path):
        return {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        labels = {}
        for row in reader:
            label = (row.get("human_interpretability_label") or "").strip()
            if not label:
                continue
            key = (row.get("config_id", ""), row.get("topic_id", ""))
            labels[key] = label
        return labels


def write_review(path: str, results: list[dict], papers: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing_labels = read_existing_human_labels(path)
    fieldnames = [
        "config_id",
        "model_name",
        "topic_id",
        "topic_label",
        "top_words",
        "size",
        "assigned_paper_ids",
        "assigned_paper_titles",
        "human_interpretability_label",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            for topic_id in result["topic_ids"]:
                assigned = [
                    paper
                    for index, paper in enumerate(papers)
                    if result["assigned_topics"][index] == topic_id
                ]
                writer.writerow({
                    "config_id": result["config_id"],
                    "model_name": result["model_name"],
                    "topic_id": topic_id,
                    "topic_label": result["topic_labels"][topic_id],
                    "top_words": "; ".join(result["topic_words"][topic_id]),
                    "size": result["topic_sizes"].get(topic_id, 0),
                    "assigned_paper_ids": "; ".join(paper["id"] for paper in assigned),
                    "assigned_paper_titles": " | ".join(paper["title"] for paper in assigned),
                    "human_interpretability_label": existing_labels.get((result["config_id"], str(topic_id)), ""),
                })


def main() -> int:
    parser = argparse.ArgumentParser(description="Compara BERTopic y LDA sobre abstracts")
    parser.add_argument("--input", default=INPUT_CSV)
    parser.add_argument("--paper-topics", default=PAPER_TOPICS_CSV)
    parser.add_argument("--topics-info", default=TOPICS_INFO_CSV)
    parser.add_argument("--review", default=REVIEW_CSV)
    parser.add_argument("--comparison", default=COMPARISON_CSV)
    parser.add_argument("--allow-download", action="store_true", help="Permite descargar/verificar modelos en Hugging Face")
    args = parser.parse_args()

    if not args.allow_download:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    papers = read_papers(args.input)
    if not papers:
        raise ValueError("No hay abstracts validos para topic modeling")

    docs = [paper["abstract"] for paper in papers]
    embedding_model = SentenceTransformer(EMBEDDING_MODEL, local_files_only=not args.allow_download)
    embeddings = embedding_model.encode(docs, normalize_embeddings=True, show_progress_bar=False)

    results = [
        *[evaluate_bertopic(papers, embeddings, topic_count) for topic_count in TOPIC_COUNTS],
        *[evaluate_lda(papers, topic_count) for topic_count in TOPIC_COUNTS],
    ]
    best = select_best(results)

    write_topics_info(args.topics_info, best)
    write_paper_topics(args.paper_topics, papers, best)
    write_review(args.review, results, papers)
    write_comparison(args.comparison, results, best, len(papers))

    print(f"Guardado: {args.paper_topics}")
    print(f"Guardado: {args.topics_info}")
    print(f"Guardado: {args.review}")
    print(f"Guardado: {args.comparison}")
    print(f"Configuracion elegida: {best['config_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
