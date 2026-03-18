"""Run the limitations prompt over llm_dataset.json and save results."""

import json
import os

from dotenv import load_dotenv

from src.core.llm import create_llm
from src.core.prompt import build_limitations_prompt

load_dotenv()

INPUT_PATH = "data/llm_dataset.json"
OUTPUT_PATH = "data/limitations_output.json"


def main():
    with open(INPUT_PATH) as f:
        records = json.load(f)

    llm = create_llm("gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))
    results = []

    for record in records:
        prompt = build_limitations_prompt(
            title=record["title"],
            full_text=record["full_text"],
        )
        response = llm.complete(prompt)

        print(f"[{record['key']}] {record['title']}")
        print(response)
        print()

        results.append({
            "key": record["key"],
            "title": record["title"],
            "limitations": response,
        })

    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Saved {len(results)} results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
