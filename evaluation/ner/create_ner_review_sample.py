import argparse
import os

import pandas as pd


DEFAULT_INPUT = "outputs/funding_entities.csv"
DEFAULT_OUTPUT = "data/evaluation/ner_manual_review.csv"


def create_stratified_sample(df: pd.DataFrame, per_type: int, random_state: int) -> pd.DataFrame:
    samples = []

    for entity_type in sorted(df["entity_type"].dropna().unique()):
        group = df[df["entity_type"] == entity_type]
        n = min(len(group), per_type)

        if n > 0:
            samples.append(group.sample(n=n, random_state=random_state))

    if not samples:
        return pd.DataFrame(columns=df.columns)

    return pd.concat(samples, ignore_index=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crea una muestra para revisión manual de NER/funding."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--per-type", type=int, default=10)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    if not os.path.exists(args.input):
        raise FileNotFoundError(f"No existe el fichero de entrada: {args.input}")

    df = pd.read_csv(args.input)

    required_columns = {
        "paper_id",
        "entity_text",
        "entity_type",
        "method",
        "confidence",
        "context",
    }

    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en {args.input}: {sorted(missing)}")

    sample = create_stratified_sample(df, args.per_type, args.random_state)

    sample["is_correct"] = ""
    sample["corrected_entity_text"] = ""
    sample["corrected_entity_type"] = ""
    sample["review_notes"] = ""

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    sample.to_csv(args.output, index=False)

    print(f"Guardado: {args.output}")
    print(f"Entidades seleccionadas: {len(sample)}")
    print()

    if "entity_type" in sample.columns and not sample.empty:
        print(sample["entity_type"].value_counts().to_string())
    else:
        print("No se han seleccionado entidades.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())