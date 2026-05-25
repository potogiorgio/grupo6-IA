import argparse
import csv
import os
import warnings
from importlib.metadata import PackageNotFoundError, version
from itertools import combinations
from typing import Optional

os.environ.setdefault("PYTHONWARNINGS", "ignore:urllib3 v2 only supports OpenSSL")
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

try:
    from urllib3.exceptions import NotOpenSSLWarning

    warnings.filterwarnings("ignore", category=NotOpenSSLWarning)
except Exception:
    pass

from sklearn.metrics.pairwise import cosine_similarity


INPUT_CSV = "data/intermediate/papers_master.csv"
GOLD_CSV = "data/evaluation/similarity_gold.csv"
OUT_CSV = "outputs/semantic_similarity_relations_embeddings.csv"
REVIEW_CSV = "data/evaluation/similarity_manual_review.csv"
COMPARISON_CSV = "outputs/comparisons/similarity_model_comparison.csv"

DEFAULT_MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/all-mpnet-base-v2",
    "sentence-transformers/paraphrase-MiniLM-L6-v2",
]
SIMILARITY_METRIC = "cosine_similarity"
DEFAULT_TOP_K = 10
DEFAULT_SELECTED_MODEL = "sentence-transformers/all-mpnet-base-v2"
RELEVANT_LABELS = {"similar", "parcialmente similar"}


def read_papers(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            abstract = (row.get("abstract") or "").strip()
            if row.get("usable_for_similarity") == "yes" and abstract:
                rows.append({
                    "id": row["id"],
                    "title": (row.get("title") or "").strip(),
                    "text": abstract,
                })
        return rows


def pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def read_gold(path: str) -> dict[tuple[str, str], dict]:
    if not os.path.exists(path):
        return {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        gold = {}
        for row in reader:
            key = pair_key(row["query_paper"], row["relevant_paper"])
            gold[key] = row
        return gold


def load_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Falta instalar sentence-transformers. "
            "Instalar dependencias antes de ejecutar esta evaluacion semantica."
        ) from exc

    return SentenceTransformer


def compute_model_rows(papers: list[dict], model_name: str, top_k: int, local_files_only: bool) -> list[dict]:
    SentenceTransformer = load_sentence_transformer()
    model = SentenceTransformer(model_name, local_files_only=local_files_only)

    texts = [paper["text"] for paper in papers]
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    sim_matrix = cosine_similarity(embeddings)

    rows = []
    for i, j in combinations(range(len(papers)), 2):
        rows.append({
            "source_paper": papers[i]["id"],
            "target_paper": papers[j]["id"],
            "source_title": papers[i]["title"],
            "target_title": papers[j]["title"],
            "similarity_score": round(float(sim_matrix[i, j]), 4),
            "similarity_metric": SIMILARITY_METRIC,
            "representation_method": model_name,
        })

    rows = sorted(rows, key=lambda item: item["similarity_score"], reverse=True)
    return rows[:top_k]


def add_review_and_gold_fields(rows: list[dict], gold: dict[tuple[str, str], dict]) -> None:
    for row in rows:
        key = pair_key(row["source_paper"], row["target_paper"])
        gold_row = gold.get(key, {})
        row["in_gold"] = "yes" if key in gold else "no"
        row["gold_relation_type"] = gold_row.get("relation_type", "")
        row.setdefault("final_label", "")


def read_review_rows(path: str) -> dict[tuple[str, str, str], dict]:
    if not os.path.exists(path):
        return {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        reviews = {}
        for row in reader:
            model = row.get("model_name", "")
            source = row.get("source_paper", "")
            target = row.get("target_paper", "")
            if model and source and target:
                reviews[(model, *pair_key(source, target))] = row
        return reviews


def attach_manual_labels(rows: list[dict], reviews: dict[tuple[str, str, str], dict]) -> None:
    for row in rows:
        source, target = pair_key(row["source_paper"], row["target_paper"])
        review = reviews.get((row["model_name"], source, target), {})
        value = (review.get("final_label") or "").strip()
        if value:
            row["final_label"] = value


def precision_at_k(rows: list[dict], top_k: int) -> Optional[float]:
    judged = [row for row in rows[:top_k] if (row.get("final_label") or "").strip()]
    if len(judged) < min(top_k, len(rows)):
        return None

    relevant = sum(1 for row in rows[:top_k] if row["final_label"].strip().lower() in RELEVANT_LABELS)
    return relevant / min(top_k, len(rows))


def gold_precision_at_k(rows: list[dict], top_k: int) -> float:
    relevant = sum(1 for row in rows[:top_k] if row.get("in_gold") == "yes")
    return relevant / min(top_k, len(rows)) if rows else 0.0


def package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "pendiente de confirmar"


def write_csv(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = [
        "similarity_id",
        "model_name",
        "rank",
        "source_paper",
        "target_paper",
        "source_title",
        "target_title",
        "similarity_score",
        "similarity_metric",
        "representation_method",
        "selection_method",
        "in_gold",
        "gold_relation_type",
        "final_label",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def accepted_relation_rows(rows: list[dict], selected_model: str) -> list[dict]:
    rows = [row for row in rows if row.get("model_name") == selected_model]
    reviewed = [row for row in rows if (row.get("final_label") or "").strip()]
    if not reviewed:
        return rows

    return [
        row for row in reviewed
        if row["final_label"].strip().lower() in RELEVANT_LABELS
    ]


def write_comparison_csv(
    path: str,
    rows_by_model: dict[str, list[dict]],
    top_k: int,
    selected_model: str,
    local_files_only: bool,
) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fieldnames = [
        "selected",
        "model_name",
        "top_k",
        "reviewed_pairs",
        "manual_precision_at_k",
        "gold_positive_precision_at_k",
        "similarity_metric",
        "local_files_only",
        "sentence_transformers_version",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for model_name, rows in rows_by_model.items():
            manual_precision = precision_at_k(rows, top_k)
            reviewed = sum(1 for row in rows[:top_k] if (row.get("final_label") or "").strip())
            writer.writerow({
                "selected": "yes" if model_name == selected_model else "no",
                "model_name": model_name,
                "top_k": top_k,
                "reviewed_pairs": f"{reviewed}/{min(top_k, len(rows))}",
                "manual_precision_at_k": "" if manual_precision is None else f"{manual_precision:.4f}",
                "gold_positive_precision_at_k": f"{gold_precision_at_k(rows, top_k):.4f}",
                "similarity_metric": SIMILARITY_METRIC,
                "local_files_only": str(local_files_only).lower(),
                "sentence_transformers_version": package_version("sentence-transformers"),
            })


def print_summary(rows_by_model: dict[str, list[dict]], top_k: int) -> None:
    for model_name, rows in rows_by_model.items():
        manual_precision = precision_at_k(rows, top_k)
        reviewed = sum(1 for row in rows[:top_k] if (row.get("final_label") or "").strip())
        manual_text = "pendiente" if manual_precision is None else f"{manual_precision:.4f}"
        gold_precision = gold_precision_at_k(rows, top_k)
        print(
            f"{model_name}: reviewed={reviewed}/{min(top_k, len(rows))}, "
            f"manual_precision_at_k={manual_text}, "
            f"gold_positive_precision_at_k={gold_precision:.4f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalua similarity entre abstracts con sentence embeddings")
    parser.add_argument("--input", default=INPUT_CSV)
    parser.add_argument("--gold", default=GOLD_CSV)
    parser.add_argument("--output", default=OUT_CSV)
    parser.add_argument("--review", default=REVIEW_CSV)
    parser.add_argument("--comparison", default=COMPARISON_CSV)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--selected-model", default=DEFAULT_SELECTED_MODEL)
    parser.add_argument("--allow-download", action="store_true", help="Permite descargar/verificar modelos en Hugging Face")
    args = parser.parse_args()

    local_files_only = not args.allow_download
    if local_files_only:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    papers = read_papers(args.input)
    gold = read_gold(args.gold)
    manual_reviews = read_review_rows(args.review)

    all_rows = []
    rows_by_model = {}
    for model_name in args.models:
        rows = compute_model_rows(papers, model_name, args.top_k, local_files_only)
        for rank, row in enumerate(rows, start=1):
            row["model_name"] = model_name
            row["rank"] = rank
            row["selection_method"] = f"top_{args.top_k}"
            row["similarity_id"] = f"semantic_similarity_{len(all_rows) + rank:04d}"
        add_review_and_gold_fields(rows, gold)
        attach_manual_labels(rows, manual_reviews)
        rows_by_model[model_name] = rows
        all_rows.extend(rows)

    write_csv(args.output, accepted_relation_rows(all_rows, args.selected_model))
    write_csv(args.review, all_rows)
    write_comparison_csv(args.comparison, rows_by_model, args.top_k, args.selected_model, local_files_only)

    print(f"Guardado: {args.output}")
    print(f"Guardado: {args.review}")
    print(f"Guardado: {args.comparison}")
    print(f"Papers evaluados: {len(papers)}")
    print(f"Modelos evaluados: {len(args.models)}")
    print(f"Pares exportados: {len(all_rows)}")
    print_summary(rows_by_model, args.top_k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
