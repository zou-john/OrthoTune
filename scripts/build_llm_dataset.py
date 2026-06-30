"""build a dataset from orthotune.csv preserving pmid, title, full text, and limitations."""

import json
import pandas as pd

CSV_PATH = "data/orthotune.csv"
OUTPUT_PATH = "data/llm_dataset.json"


def main():
    # load only the columns we need
    df = pd.read_csv(CSV_PATH, usecols=["PMID", "Title", "Full Text", "Limitations"])

    total = len(df)

    # drop rows where full text is missing or blank
    df = df.dropna(subset=["Full Text"])
    df = df[df["Full Text"].str.strip() != ""]

    # normalize whitespace: replace non-breaking spaces and collapse runs of whitespace
    for col in ["Full Text", "Limitations"]:
        df[col] = df[col].str.replace(" ", " ", regex=False).str.split().str.join(" ")

    # count words by splitting on whitespace
    df["full_text_word_length"] = df["Full Text"].str.split().str.len()

    print(f"Total rows: {total}")
    print(f"Rows with Full Text: {len(df)}")

    # build list of records for json output
    records = [
        {
            "pmid": row["PMID"],
            "title": row["Title"],
            "full_text": row["Full Text"],
            "limitations": row["Limitations"],
            "full_text_word_length": row["full_text_word_length"],
        }
        for _, row in df.iterrows()
    ]

    with open(OUTPUT_PATH, "w") as f:
        json.dump(records, f, indent=2)

    print(f"Saved {len(records)} records to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
