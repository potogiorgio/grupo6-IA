import os
import csv
from itertools import combinations

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

INPUT_CSV = "data/intermediate/papers_master.csv"
OUT_CSV = "data/intermediate/semantic_similarity_relations.csv"

TOP_K_PER_PAPER = 3

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def read_papers():
    papers = []

    with open(INPUT_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row.get("usable_for_similarity") == "yes":
                title = (row.get("title") or "").strip()
                abstract = (row.get("abstract") or "").strip()

                if abstract:
                    text = f"{title}. {abstract}"

                    papers.append({
                        "id": row["id"],
                        "title": title,
                        "text": text,
                    })

    return papers


def main():
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)

    papers = read_papers()

    if len(papers) < 2:
        raise SystemExit("Necesitas al menos 2 papers con abstract para calcular similitud.")

    texts = [p["text"] for p in papers]

    print(f"Cargando modelo: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print("Calculando embeddings...")
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    sim_matrix = cosine_similarity(embeddings)

    candidate_rows = []

    for i, j in combinations(range(len(papers)), 2):
        score = float(sim_matrix[i, j])

        candidate_rows.append({
            "source_paper": papers[i]["id"],
            "target_paper": papers[j]["id"],
            "similarity_score": round(score, 4),
            "similarity_metric": "cosine_similarity",
            "representation_method": MODEL_NAME,
        })

    selected = {}

    for paper in papers:
        paper_id = paper["id"]

        related = [
            r for r in candidate_rows
            if r["source_paper"] == paper_id or r["target_paper"] == paper_id
        ]

        related = sorted(
            related,
            key=lambda r: r["similarity_score"],
            reverse=True
        )[:TOP_K_PER_PAPER]

        for r in related:
            key = tuple(sorted([r["source_paper"], r["target_paper"]]))
            selected[key] = r

    rows = list(selected.values())
    rows = sorted(rows, key=lambda r: r["similarity_score"], reverse=True)

    for idx, row in enumerate(rows, start=1):
        row["similarity_id"] = f"semantic_similarity_{idx:04d}"

    fieldnames = [
        "similarity_id",
        "source_paper",
        "target_paper",
        "similarity_score",
        "similarity_metric",
        "representation_method",
    ]

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Guardado: {OUT_CSV}")
    print(f"Papers usados: {len(papers)}")
    print(f"Relaciones exportadas: {len(rows)}")

    print("\nTop 10 similitudes semánticas:")
    for row in rows[:10]:
        print(
            f"{row['source_paper']} - {row['target_paper']}: "
            f"{row['similarity_score']}"
        )


if __name__ == "__main__":
    main()