import argparse
import os

import pandas as pd


DEFAULT_INPUT = "data/evaluation/ner_manual_review.csv"
DEFAULT_OUTPUT = "data/evaluation/ner_evaluation_summary.csv"


def normalize_answer(value: str) -> str:
    return str(value).strip().lower()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evalúa manualmente la calidad de las entidades NER/funding revisadas."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"No existe el fichero de revisión: {args.input}")

    df = pd.read_csv(args.input, encoding="cp1252")

    if "is_correct" not in df.columns:
        raise ValueError("El CSV debe tener la columna 'is_correct'.")

    reviewed = df[df["is_correct"].fillna("").astype(str).str.strip() != ""].copy()

    if reviewed.empty:
        raise ValueError(
            "No hay entidades revisadas. Rellena la columna 'is_correct' con yes/no."
        )

    reviewed["is_correct_norm"] = reviewed["is_correct"].apply(normalize_answer)

    valid_values = {"yes", "no"}
    invalid = reviewed[~reviewed["is_correct_norm"].isin(valid_values)]

    if not invalid.empty:
        print("Valores inválidos en is_correct. Usa solo yes/no:")
        print(invalid[["paper_id", "entity_text", "entity_type", "is_correct"]])
        raise ValueError("Hay valores inválidos en la revisión manual.")

    total_reviewed = len(reviewed)
    correct = int((reviewed["is_correct_norm"] == "yes").sum())
    incorrect = int((reviewed["is_correct_norm"] == "no").sum())

    estimated_precision = correct / total_reviewed if total_reviewed else 0.0

    rows = []

    rows.append({
        "entity_type": "ALL",
        "reviewed_entities": total_reviewed,
        "correct_entities": correct,
        "incorrect_entities": incorrect,
        "estimated_precision": round(estimated_precision, 4),
    })

    for entity_type, group in reviewed.groupby("entity_type"):
        group_total = len(group)
        group_correct = int((group["is_correct_norm"] == "yes").sum())
        group_incorrect = int((group["is_correct_norm"] == "no").sum())
        group_precision = group_correct / group_total if group_total else 0.0

        rows.append({
            "entity_type": entity_type,
            "reviewed_entities": group_total,
            "correct_entities": group_correct,
            "incorrect_entities": group_incorrect,
            "estimated_precision": round(group_precision, 4),
        })

    summary = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    summary.to_csv(args.output, index=False)

    print(summary.to_string(index=False))
    print()
    print(f"Guardado: {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())