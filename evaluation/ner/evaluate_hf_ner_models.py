import argparse
import os
import re
from collections import defaultdict

import pandas as pd
from transformers import pipeline


PAPERS_CSV = "data/intermediate/papers_master.csv"
GOLD_CSV = "data/evaluation/ner_gold.csv"
OUTPUT_CSV = "data/evaluation/ner/ner_model_comparison.csv"

MODELS = [
    "Jean-Baptiste/roberta-large-ner-english",
    "dslim/bert-base-NER",
    "Davlan/bert-base-multilingual-cased-ner-hrl",
]

GRANT_PATTERNS = [
    r"\bgrant(?:s)?\s+(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-\/\.]{3,})",
    r"\bproject(?:s)?\s+(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-\/\.]{3,})",
    r"\bcontract(?:s)?\s+(?:no\.?|number)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-\/\.]{3,})",
    r"\baward\s+([A-Z0-9][A-Z0-9\-\/\.]{3,})",
    r"\b([A-Z]{2,}[- ]?\d{3,}[-A-Z0-9]*)\b",
    r"\b(\d{4}[A-Z]?\/[A-Z0-9\-]+)\b",
]

BAD_ENTITIES = {
    "that",
    "with",
    "from",
    "built",
    "agreement",
    "and",
    "or",
    "the",
    "grant",
    "grants",
    "project",
    "projects",
    "award",
    "support",
    "supported",
    "funding",
    "contract",
}


def normalize_text(text: str) -> str:
    return " ".join(str(text or "").replace("\n", " ").split()).strip()


def normalize_key(text: str) -> str:
    text = normalize_text(text).lower()
    text = text.replace(".", "")
    text = text.replace(",", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def map_hf_label(label: str) -> str | None:
    label = label.upper()

    if "PER" in label:
        return "PERSON"

    if "ORG" in label:
        return "ORGANIZATION"

    return None


def is_bad_grant(value: str) -> bool:
    value = normalize_text(value)
    lower = value.lower()

    if not value:
        return True

    if lower in BAD_ENTITIES:
        return True

    if len(value) < 4:
        return True

    if not any(char.isdigit() for char in value) and "-" not in value:
        return True

    return False


def extract_regex_grants(text: str) -> set[tuple[str, str]]:
    predictions = set()

    for pattern in GRANT_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            value = match.group(1).strip(" ,.;:()[]")
            if is_bad_grant(value):
                continue

            entity_type = "PROJECT_ID" if "project" in match.group(0).lower() else "GRANT_ID"
            predictions.add((normalize_key(value), entity_type))

    return predictions


def load_papers(path: str, selected_ids: set[str]) -> dict[str, str]:
    df = pd.read_csv(path)
    result = {}

    for _, row in df.iterrows():
        paper_id = str(row.get("id", "")).strip()
        if paper_id in selected_ids:
            result[paper_id] = normalize_text(row.get("acknowledgements", ""))

    return result


def load_gold(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    required = {"paper_id", "entity_text", "entity_type"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en {path}: {sorted(missing)}")

    df["paper_id"] = df["paper_id"].astype(str).str.strip()
    df["entity_text_norm"] = df["entity_text"].apply(normalize_key)
    df["entity_type"] = df["entity_type"].astype(str).str.strip().str.upper()

    return df


def predict_with_model(model_name: str, papers: dict[str, str], allow_download: bool) -> set[tuple[str, str, str]]:
    if not allow_download:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    ner = pipeline(
        "token-classification",
        model=model_name,
        aggregation_strategy="simple",
    )

    predictions = set()

    for paper_id, text in papers.items():
        if not text:
            continue

        # Los modelos BERT suelen tener límite de longitud. Cortamos para evitar errores.
        chunks = [text[i:i + 1200] for i in range(0, len(text), 1200)]

        for chunk in chunks:
            for entity in ner(chunk):
                entity_text = normalize_text(entity.get("word", ""))
                entity_label = entity.get("entity_group") or entity.get("entity") or ""
                mapped_type = map_hf_label(entity_label)

                if not mapped_type:
                    continue

                if not entity_text or len(entity_text) < 2:
                    continue

                predictions.add((paper_id, normalize_key(entity_text), mapped_type))

        for entity_text_norm, entity_type in extract_regex_grants(text):
            predictions.add((paper_id, entity_text_norm, entity_type))

    return predictions


def compute_metrics(
    gold: set[tuple[str, str, str]],
    pred: set[tuple[str, str, str]],
    entity_types: list[str],
) -> list[dict]:
    rows = []

    for entity_type in ["ALL"] + entity_types:
        if entity_type == "ALL":
            gold_subset = gold
            pred_subset = pred
        else:
            gold_subset = {x for x in gold if x[2] == entity_type}
            pred_subset = {x for x in pred if x[2] == entity_type}

        tp = len(gold_subset & pred_subset)
        fp = len(pred_subset - gold_subset)
        fn = len(gold_subset - pred_subset)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

        rows.append({
            "entity_type": entity_type,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        })

    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Compara modelos HuggingFace NER sobre ner_gold.csv")
    parser.add_argument("--papers", default=PAPERS_CSV)
    parser.add_argument("--gold", default=GOLD_CSV)
    parser.add_argument("--output", default=OUTPUT_CSV)
    parser.add_argument("--allow-download", action="store_true")
    args = parser.parse_args()

    gold_df = load_gold(args.gold)
    selected_ids = set(gold_df["paper_id"])
    papers = load_papers(args.papers, selected_ids)

    gold_set = {
        (row.paper_id, row.entity_text_norm, row.entity_type)
        for row in gold_df.itertuples(index=False)
    }

    entity_types = sorted(gold_df["entity_type"].unique())

    all_rows = []

    for model_name in MODELS:
        print(f"Evaluando modelo: {model_name}")
        predictions = predict_with_model(model_name, papers, args.allow_download)

        metric_rows = compute_metrics(gold_set, predictions, entity_types)

        for row in metric_rows:
            row["model"] = model_name
            all_rows.append(row)

    output_df = pd.DataFrame(all_rows)
    output_df = output_df[
        [
            "model",
            "entity_type",
            "true_positives",
            "false_positives",
            "false_negatives",
            "precision",
            "recall",
            "f1",
        ]
    ]

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    output_df.to_csv(args.output, index=False)

    print()
    print(output_df.to_string(index=False))
    print()
    print(f"Guardado: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())