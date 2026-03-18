"""Inspect a CSV file and print it as a table."""

import pandas as pd

CSV_PATH = "data/ortho_v1.csv"


def main():
    df = pd.read_csv(CSV_PATH)
    print(f"Shape: {df.shape[0]} rows x {df.shape[1]} cols\n")

    for col in df.columns:
        print(f"{'='*60}")
        print(f"Column: {col}")
        print(f"{'='*60}")
        for entry in df[col].head(1):
            print(f"  {str(entry)[:100]}")
        print()


if __name__ == "__main__":
    main()
