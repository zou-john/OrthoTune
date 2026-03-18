"""Build a dataset from ortho_v1.csv preserving Key, Title, and Full Text."""

import json
import pandas as pd

CSV_PATH = "data/ortho_v1.csv"
OUTPUT_PATH = "data/llm_dataset.json"
MAX_ROWS = 50


def main():
    df = pd.read_csv(CSV_PATH, usecols=["Key", "Title", "Full Text"])

    total = len(df)
    df = df.dropna(subset=["Full Text"])
    df = df[df["Full Text"].str.strip() != ""]
    df = df.head(MAX_ROWS)

    print(f"Total rows: {total}")
    print(f"Rows with Full Text: {len(df)}")

    records = [
        {"key": row["Key"], "title": row["Title"], "full_text": row["Full Text"]}
        for _, row in df.iterrows()
    ]

    with open(OUTPUT_PATH, "w") as f:
        json.dump(records, f, indent=2)

    print(f"Saved {len(records)} records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
