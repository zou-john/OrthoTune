"""Evaluate study limitations via Claude tool-use and populate eval_table.db."""

import argparse
import json
import os
import random
import sqlite3

from dotenv import load_dotenv

from src.core.llm import create_llm
from src.core.prompt import EVAL_SYSTEM_PROMPT, build_eval_prompt
from src.db.schema import DB_PATH, init_db

load_dotenv()

DATASET_PATH = "data/llm_dataset.json"
AI_LIMITATIONS_PATH = "data/limitations_output_gpt_41_477.json"

TOOLS = [
    {
        "name": "insert_limitation_detail",
        "description": "Record a single named sub-limitation with evaluation scores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pmid": {
                    "type": "integer",
                    "description": "PubMed ID of the study",
                },
                "limitation_label": {
                    "type": "string",
                    "enum": ["A", "B"],
                    "description": "Which limitations section this sub-limitation belongs to",
                },
                "limitation_name": {
                    "type": "string",
                    "description": "Short descriptive name (e.g. 'Short follow-up', 'No control group')",
                },
                "relevance": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Relevance to the study's methods/results (1=irrelevant, 5=highly relevant)",
                },
                "critical_thinking": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Level of critical thinking (1=superficial, 5=deeply insightful)",
                },
                "publishable": {
                    "type": "string",
                    "enum": ["Y", "N"],
                    "description": "Would you accept this limitation in a peer-reviewed journal?",
                },
                "hallucination": {
                    "type": "string",
                    "enum": ["Y", "N"],
                    "description": "Does this limitation contain factually incorrect or hallucinated information?",
                },
            },
            "required": [
                "pmid",
                "limitation_label",
                "limitation_name",
                "relevance",
                "critical_thinking",
                "publishable",
                "hallucination",
            ],
        },
    },
    {
        "name": "insert_limitation_summary",
        "description": (
            "Record the final publishability verdict for each section. "
            "Call this exactly once per study, after all insert_limitation_detail calls."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pmid": {
                    "type": "integer",
                    "description": "PubMed ID of the study",
                },
                "publishable_a": {
                    "type": "string",
                    "enum": ["Y", "N"],
                    "description": "Is Limitation A of sufficient quality to publish in a peer-reviewed journal?",
                },
                "publishable_b": {
                    "type": "string",
                    "enum": ["Y", "N"],
                    "description": "Is Limitation B of sufficient quality to publish in a peer-reviewed journal?",
                },
            },
            "required": ["pmid", "publishable_a", "publishable_b"],
        },
    },
]


def make_tool_handler(conn: sqlite3.Connection):
    def handler(name: str, inputs: dict) -> str:
        if name == "insert_limitation_detail":
            conn.execute(
                """INSERT INTO limitation_details
                   (pmid, limitation_label, limitation_name, relevance, critical_thinking, publishable, hallucination)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    inputs["pmid"],
                    inputs["limitation_label"],
                    inputs["limitation_name"],
                    inputs["relevance"],
                    inputs["critical_thinking"],
                    inputs["publishable"],
                    inputs["hallucination"],
                ),
            )
            conn.commit()
            return f"ok: {inputs['limitation_label']} — {inputs['limitation_name']}"

        if name == "insert_limitation_summary":
            try:
                conn.execute(
                    """INSERT INTO limitation_summary (pmid, publishable_a, publishable_b)
                       VALUES (?, ?, ?)""",
                    (inputs["pmid"], inputs["publishable_a"], inputs["publishable_b"]),
                )
                conn.commit()
                return f"ok: summary for pmid={inputs['pmid']}"
            except sqlite3.IntegrityError:
                return f"skipped: summary for pmid={inputs['pmid']} already exists"

        return f"error: unknown tool {name}"

    return handler


def evaluate_record(llm, conn, pmid, full_text, published_lims, ai_lims):
    conn.execute("DELETE FROM limitation_details WHERE pmid = ?", (pmid,))
    conn.execute("DELETE FROM limitation_summary WHERE pmid = ?", (pmid,))
    conn.commit()

    if random.random() < 0.5:
        lim_a, lim_b = published_lims, ai_lims
        a_is = "published"
    else:
        lim_a, lim_b = ai_lims, published_lims
        a_is = "ai"

    messages = [
        {
            "role": "user",
            "content": build_eval_prompt(
                full_text=full_text,
                lim_a=lim_a,
                lim_b=lim_b,
                pmid=pmid,
            ),
        }
    ]

    llm.run_with_tools(
        messages=messages,
        tools=TOOLS,
        tool_handler=make_tool_handler(conn),
        system=EVAL_SYSTEM_PROMPT,
        max_tokens=8192,
    )

    return a_is


def main():
    parser = argparse.ArgumentParser(description="Evaluate study limitations into eval_table.db")
    parser.add_argument("--model", default="gemini-3.1-pro-preview", help="model to use for evaluation")
    parser.add_argument("--ai_output", default=AI_LIMITATIONS_PATH, help="path to ai-generated limitations json")
    parser.add_argument("--n", type=int, default=None, help="number of records to run (default: all)")
    parser.add_argument("--db", default=DB_PATH, help="SQLite database path")
    # - --resume — skips PMIDs already in limitation_summary (don't re-evaluate)
    # - no --resume — deletes existing rows for every PMID before re-evaluating, so both tables always get fresh data
    parser.add_argument("--resume", action="store_true", help="skip PMIDs already in limitation_summary")
    args = parser.parse_args()

    with open(DATASET_PATH) as f:
        dataset = {r["pmid"]: r for r in json.load(f)}

    with open(args.ai_output) as f:
        ai_records = {r["pmid"]: r for r in json.load(f)}

    pmids = [p for p in ai_records if p in dataset and dataset[p].get("limitations")]
    if args.n:
        pmids = pmids[: args.n]

    conn = init_db(args.db)
    if args.model.startswith("gemini-"):
        api_key = os.getenv("GEMINI_API_KEY")
    elif args.model.startswith("claude-"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
    else:
        api_key = os.getenv("OPENAI_API_KEY")
    llm = create_llm(args.model, api_key=api_key)

    print(f"model : {llm.model}")
    print(f"db    : {args.db}")
    print(f"total : {len(pmids)} records")

    done_pmids: set = set()
    if args.resume:
        rows = conn.execute("SELECT pmid FROM limitation_summary").fetchall()
        done_pmids = {r["pmid"] for r in rows}
        print(f"resume: {len(done_pmids)} already done, {len(pmids) - len(done_pmids)} remaining")

    for i, pmid in enumerate(pmids):
        if pmid in done_pmids:
            continue

        record = dataset[pmid]
        ai_record = ai_records[pmid]

        print(f"[{i + 1}/{len(pmids)}] pmid={pmid} — {record['title'][:80]}")

        a_is = evaluate_record(
            llm=llm,
            conn=conn,
            pmid=pmid,
            full_text=record["full_text"],
            published_lims=record["limitations"],
            ai_lims=ai_record["limitations"],
        )

        ai_label = "A" if a_is == "ai" else "B"
        conn.execute(
            "UPDATE limitation_summary SET ai_generated = ? WHERE pmid = ?",
            (ai_label, pmid),
        )
        conn.commit()
        print(f"  done — AI was label {ai_label}")

    conn.close()
    print("complete")


if __name__ == "__main__":
    main()
