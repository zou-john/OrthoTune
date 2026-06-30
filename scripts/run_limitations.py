"""run the limitations prompt over llm_dataset.json and save results."""

import argparse
import json
import os

from dotenv import load_dotenv

from src.core.llm import create_llm
from src.core.prompt import build_limitations_prompt

load_dotenv()

INPUT_PATH = "data/llm_dataset.json"
OUTPUT_PATH = "data/limitations_output.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=["openai", "claude"], default="openai", help="which llm to use")
    parser.add_argument("--n", type=int, default=None, help="run only the first n records (omit to run all)")
    parser.add_argument("--end", action="store_true", help="append END confirmation to prompt to verify full text was read")
    parser.add_argument("--output", default=OUTPUT_PATH, help="output file path")
    parser.add_argument("--resume", action="store_true", help="skip records already present in the output file")
    args = parser.parse_args()

    with open(INPUT_PATH) as f:
        records = json.load(f)

    if args.n:
        records = records[: args.n]
        print(f"running first {args.n} records")
    else:
        print(f"running all {len(records)} records")

    if args.model == "claude":
        llm = create_llm("claude-sonnet-4-5-20250929", api_key=os.getenv("ANTHROPIC_API_KEY"))
    else:
        llm = create_llm("gpt-4.1", api_key=os.getenv("OPENAI_API_KEY"))
    print(f"using model: {llm.model}")

    # load existing results for resume support
    results = []
    done_pmids: set = set()
    if args.resume and os.path.exists(args.output):
        with open(args.output) as f:
            results = json.load(f)
        done_pmids = {r["pmid"] for r in results}
        print(f"resuming — {len(done_pmids)} records already done, {len(records) - len(done_pmids)} remaining")

    for i, record in enumerate(records):
        if record["pmid"] in done_pmids:
            continue

        prompt = build_limitations_prompt(
            title=record["title"],
            full_text=record["full_text"],
        )
        if args.end:
            prompt += "\n\nAfter your response, output only the word END on its own line to confirm you read the full text."
        response = llm.complete(prompt)

        if args.end and hasattr(llm, "last_usage"):
            u = llm.last_usage
            # claude-sonnet-4-5: 200k limit, gpt-4.1: 1m limit
            limit = 200000 if args.model == "claude" else 1000000
            pt = u["prompt_tokens"] if isinstance(u, dict) else u.prompt_tokens
            ct = u["completion_tokens"] if isinstance(u, dict) else u.completion_tokens
            tt = u["total_tokens"] if isinstance(u, dict) else u.total_tokens
            print(f"tokens — prompt: {pt}, completion: {ct}, total: {tt} / {limit}")

        print(f"[{i+1}/{len(records)}] [{record['pmid']}] {record['title']}")
        print(response)
        print()

        results.append({
            "pmid": record["pmid"],
            "title": record["title"],
            "limitations": response,
        })

        # save incrementally so progress survives interruptions
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)

    print(f"saved {len(results)} results to {args.output}")


if __name__ == "__main__":
    main()
