import argparse
import csv
import os
import warnings
from itertools import combinations

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
REVIEW_CSV = "data/evaluation/similarity_manual_review.csv"
OUTPUT_CSV = "outputs/semantic_similarity_relations_embeddings.csv"

SELECTED_MODEL = "sentence-transformers/all-mpnet-base-v2"
SIMILARITY_METRIC = "cosine_similarity"
TOP_K = 20
RELEVANT_LABELS = {"similar", "parcialmente similar"}


def read_papers(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        papers = []
        for row in reader:
            abstract = (row.get("abstract") or "").strip()
            if row.get("usable_for_similarity") == "yes" and abstract:
                papers.append({
                    "id": row["id"],
                    "title": (row.get("title") or "").strip(),
                    "text": abstract,
                })
        return papers


def pair_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def read_review_labels(path: str, selected_model: str) -> dict[tuple[str, str], str]:
    if not os.path.exists(path):
        return {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        labels = {}
        for row in reader:
            if row.get("model_name") != selected_model:
                continue
            label = (row.get("final_label") or "").strip()
            if not label:
                continue
            labels[pair_key(row.get("source_paper", ""), row.get("target_paper", ""))] = label
        return labels


def read_gold(path: str) -> dict[tuple[str, str], dict]:
    if not os.path.exists(path):
        return {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        gold = {}
        for row in reader:
            gold[pair_key(row.get("query_paper", ""), row.get("relevant_paper", ""))] = row
        return gold


def compute_similarity_rows(
    papers: list[dict],
    model_name: str,
    top_k: int,
    local_files_only: bool,
) -> list[dict]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Falta instalar sentence-transformers") from exc

    model = SentenceTransformer(model_name, local_files_only=local_files_only)
    embeddings = model.encode(
        [paper["text"] for paper in papers],
        normalize_embeddings=True,
        show_progress_bar=False,
    )
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

    rows.sort(key=lambda row: row["similarity_score"], reverse=True)
    return rows[:top_k]


def final_rows(
    rows: list[dict],
    review_labels: dict[tuple[str, str], str],
    gold: dict[tuple[str, str], dict],
    top_k: int,
) -> list[dict]:
    reviewed = bool(review_labels)
    accepted = []
    for rank, row in enumerate(rows, start=1):
        key = pair_key(row["source_paper"], row["target_paper"])
        label = review_labels.get(key, "")
        if reviewed and label.lower() not in RELEVANT_LABELS:
            continue
        gold_row = gold.get(key, {})

        output_row = {
            "similarity_id": f"semantic_similarity_{len(accepted) + 1:04d}",
            "model_name": SELECTED_MODEL,
            "rank": rank,
            **row,
            "selection_method": f"top_{top_k}",
            "in_gold": "yes" if key in gold else "no",
            "gold_relation_type": gold_row.get("relation_type", ""),
            "final_label": label,
        }
        accepted.append(output_row)
    return accepted


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera relaciones finales de similarity para el KG")
    parser.add_argument("--input", default=INPUT_CSV)
    parser.add_argument("--gold", default=GOLD_CSV)
    parser.add_argument("--review", default=REVIEW_CSV)
    parser.add_argument("--output", default=OUTPUT_CSV)
    parser.add_argument("--model", default=SELECTED_MODEL)
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()

    local_files_only = not args.allow_download
    if local_files_only:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    papers = read_papers(args.input)
    rows = compute_similarity_rows(papers, args.model, args.top_k, local_files_only)
    review_labels = read_review_labels(args.review, args.model)
    gold = read_gold(args.gold)
    accepted = final_rows(rows, review_labels, gold, args.top_k)
    write_csv(args.output, accepted)

    print(f"Guardado: {args.output}")
    print(f"Papers evaluados: {len(papers)}")
    print(f"Relaciones exportadas: {len(accepted)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
