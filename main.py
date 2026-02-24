import json
import re
from pathlib import Path

from docling.document_converter import DocumentConverter
from datasets import Dataset

DATA_DIR = Path("data")
OUTPUT_JSON = Path("output.json")
DATASET_DIR = Path("medtune_dataset")

SECTION_PATTERNS = {
    "introduction": ["introduction", "background"],
    "methodology": ["method", "methodology", "materials and methods", "methods"],
    "results": ["results", "findings"],
    "limitations": ["limitations", "limitation"],
    "conclusion": ["conclusion", "conclusions", "concluding remarks"],
    "discussion": ["discussion"],
}


def match_section(heading: str) -> str | None:
    heading_lower = heading.lower().strip()
    for section, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            if pattern in heading_lower:
                return section
    return None


def extract_sections(markdown_text: str) -> dict:
    sections = {k: [] for k in SECTION_PATTERNS}
    current_section = None
    current_content = []

    for line in markdown_text.split("\n"):
        heading_match = re.match(r"^#{1,4}\s+(.+)$", line)
        if heading_match:
            if current_section and current_content:
                sections[current_section].append("\n".join(current_content).strip())
                current_content = []
            current_section = match_section(heading_match.group(1))
        elif current_section:
            current_content.append(line)

    if current_section and current_content:
        sections[current_section].append("\n".join(current_content).strip())

    return {k: "\n\n".join(v) for k, v in sections.items()}


def process_pdfs():
    converter = DocumentConverter()
    records = []

    for pdf_path in sorted(DATA_DIR.glob("*.pdf")):
        print(f"Processing {pdf_path.name}...")
        result = converter.convert(str(pdf_path))
        markdown_text = result.document.export_to_markdown()
        sections = extract_sections(markdown_text)

        record = {
            "link": "",  # populate with DOI/URL if available
            "pdf_path": str(pdf_path),
            **sections,
        }
        records.append(record)

        filled = [k for k, v in sections.items() if v]
        print(f"  -> sections found: {filled}")

    with open(OUTPUT_JSON, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nSaved {len(records)} records to {OUTPUT_JSON}")

    dataset = Dataset.from_list(records)
    dataset.save_to_disk(str(DATASET_DIR))
    print(f"HuggingFace dataset saved to {DATASET_DIR}/")
    print(dataset)

    return dataset


if __name__ == "__main__":
    process_pdfs()
