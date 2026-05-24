import os
import numpy as np
import pandas as pd

from bertopic import BERTopic
from hdbscan import HDBSCAN
from umap import UMAP


INPUT_CSV = "data/intermediate/papers_master.csv"
OUTPUT_DIR = "data/intermediate"

PAPER_TOPICS_CSV = os.path.join(OUTPUT_DIR, "paper_topics.csv")
TOPICS_INFO_CSV = os.path.join(OUTPUT_DIR, "topics_info.csv")

TOPIC_THRESHOLD = 0.60
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df = pd.read_csv(INPUT_CSV)

    df_valid = df.dropna(subset=["abstract"]).copy()
    df_valid = df_valid[df_valid["abstract"].astype(str).str.strip() != ""]

    abstracts = df_valid["abstract"].astype(str).tolist()

    print(f"Usando {len(abstracts)} abstracts para topic modeling")

    if len(abstracts) == 0:
        raise ValueError("No hay abstracts válidos para topic modeling.")

    umap_model = UMAP(
        n_neighbors=5,
        n_components=2,
        min_dist=0.0,
        metric="cosine",
        random_state=42
    )

    hdbscan_model = HDBSCAN(
        min_cluster_size=3,
        min_samples=1,
        metric="euclidean",
        prediction_data=True
    )

    topic_model = BERTopic(
        embedding_model=EMBEDDING_MODEL,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        calculate_probabilities=True,
        verbose=True
    )

    topics, probs = topic_model.fit_transform(abstracts)

    topic_info = topic_model.get_topic_info()
    print(topic_info)

    df_valid["topic"] = topics

    if probs is not None:
        probs = np.array(probs)

        if probs.ndim == 1:
            df_valid["topic_probability"] = probs
        else:
            df_valid["topic_probability"] = probs.max(axis=1)
    else:
        df_valid["topic_probability"] = None

    df_valid["topic_threshold"] = TOPIC_THRESHOLD
    df_valid["belongs_to_topic"] = (
        (df_valid["topic"] != -1)
        & (df_valid["topic_probability"].fillna(0) >= TOPIC_THRESHOLD)
    )

    df_valid["topic_model"] = "BERTopic"
    df_valid["embedding_model"] = EMBEDDING_MODEL
    df_valid["topic_assignment_relation"] = [
        f"topic_assignment_{i+1:03d}" for i in range(len(df_valid))
    ]

    output_cols = [
        "topic_assignment_relation",
        "id",
        "title",
        "topic",
        "topic_probability",
        "topic_threshold",
        "belongs_to_topic",
        "topic_model",
        "embedding_model"
    ]

    df_valid[output_cols].to_csv(PAPER_TOPICS_CSV, index=False)
    topic_info.to_csv(TOPICS_INFO_CSV, index=False)

    print(f"\nGuardado: {PAPER_TOPICS_CSV}")
    print(f"Guardado: {TOPICS_INFO_CSV}")


if __name__ == "__main__":
    main()