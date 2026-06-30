"""convert a limitations json file to a readable markdown file."""

import argparse
import json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="path to input json file")
    parser.add_argument("output", help="path to output markdown file")
    args = parser.parse_args()

    with open(args.input) as f:
        records = json.load(f)

    lines = []
    for i, record in enumerate(records):
        lines.append(f"## {record['title']}")
        lines.append(f"**PMID:** {record['pmid']}")
        lines.append("")
        lines.append(record["limitations"])
        if i < len(records) - 1:
            lines.append("")
            lines.append("---")
            lines.append("")

    with open(args.output, "w") as f:
        f.write("\n".join(lines))

    print(f"saved {len(records)} entries to {args.output}")


if __name__ == "__main__":
    main()
