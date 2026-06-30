"""convert a judge output json file to a readable markdown file."""

import argparse
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="path to input judge json file")
    parser.add_argument("output", help="path to output markdown file")
    args = parser.parse_args()

    with open(args.input) as f:
        records = json.load(f)

    lines = []
    for i, record in enumerate(records):
        lines.append(f"## {record['title']}")
        lines.append(f"**PMID:** {record['pmid']} | **Author 1 is:** {record['author1_is']} | **Author 2 is:** {record['author2_is']}")
        lines.append("")
        lines.append(record["judge_output"])
        if i < len(records) - 1:
            lines.append("")
            lines.append("---")
            lines.append("")

    with open(args.output, "w") as f:
        f.write("\n".join(lines))

    print(f"saved {len(records)} entries to {args.output}")


if __name__ == "__main__":
    main()
