import pandas as pd


INPUT = "data/evaluation/ner_manual_review.csv"
OUTPUT = "data/evaluation/ner_manual_review.csv"


answers = [
    "no",
    "yes",
    "yes",
    "yes",
    "yes",
    "yes",
    "yes",
    "yes",
    "yes",
    "yes",

    "yes",
    "no",
    "yes",
    "yes",
    "no",
    "yes",
    "yes",
    "no",
    "yes",
    "no",

    "yes",
    "yes",
    "no",
    "no",
    "no",
    "yes",
    "no",
    "no",
    "no",
    "yes",

    "no",
    "no",
    "no",
    "yes",
    "yes",
]


notes = [
    "Mentioned as data/source provider, not clearly as funder",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",

    "",
    "Ambiguous or incomplete grant identifier",
    "",
    "",
    "Invalid grant identifier, contains extra word",
    "",
    "",
    "Organization detected as grant identifier",
    "",
    "Common word, not a grant identifier",

    "",
    "",
    "Entity span too long or mixed with other information",
    "Entity span too long; should be only the organization name",
    "Entity span too long; sentence fragment instead of organization",
    "",
    "Entity span too long; sentence fragment instead of organization",
    "Entity span too long; contains project and organization mixed",
    "Entity span too generic/incomplete",
    "",

    "Common word, not a project identifier",
    "Common word, not a project identifier",
    "Common word, not a project identifier",
    "",
    "",
]


def main():
    df = pd.read_csv(INPUT)

    if len(df) != len(answers):
        raise ValueError(
            f"El CSV tiene {len(df)} filas, pero hay {len(answers)} respuestas. "
            "Regenera la muestra con create_ner_review_sample.py usando random_state=42."
        )

    df["is_correct"] = answers
    df["review_notes"] = notes

    df.to_csv(OUTPUT, index=False, encoding="utf-8")

    print(f"Guardado: {OUTPUT}")
    print(df["is_correct"].value_counts().to_string())


if __name__ == "__main__":
    main()