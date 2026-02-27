import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from docling.document_converter import DocumentConverter
from datasets import Dataset

load_dotenv()

# ==========================
# CONFIGURATION
# ==========================
DATA_DIR = Path("data")
OUTPUT_JSON = Path("output.json")
DATASET_DIR = Path("medtune_dataset")
SECTION_KEYS = ["without_limitations", "limitations"]

# ==========================
# SETUP OPENAI CLIENT
# ==========================
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("Please set OPENAI_API_KEY in your .env file!")

client = OpenAI(api_key=api_key)

# ==========================
# CLEAN TEXT
# ==========================
def clean_text(text: str) -> str:
    # Remove references section and everything after it
    text = re.sub(
        r'\n+#{0,4}\s*(?:references?|bibliography)\s*\n.*',
        '',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # Remove bracketed citations like [1], [1,2], [1-3]
    text = re.sub(r'\[\d+(?:[,\-]\d+)*\]', '', text)
    # Remove superscript-style inline citations like "word 1,2 ." or "word 5-8 ."
    text = re.sub(r'(?<=[a-zA-Z\)]) \d{1,3}(?:[,\-]\d{1,3})* (?=[a-zA-Z\(.,;:])', ' ', text)
    return text.strip()


# ==========================
# HARDCODED SPLIT ON FIRST "LIMITATION" OCCURRENCE
# ==========================
def extract_sections_hardcoded(text: str) -> dict:
    match = re.search(r'limitation', text, flags=re.IGNORECASE)
    if match:
        # Walk back to the start of the paragraph containing the match
        para_start = text.rfind('\n\n', 0, match.start())
        split_pos = para_start + 2 if para_start != -1 else 0
        without = text[:split_pos].strip()
        limitations = text[split_pos:].strip()
    else:
        without = text.strip()
        limitations = ""
    return {"without_limitations": without, "limitations": limitations}


# ==========================
# FUNCTION TO EXTRACT SECTIONS
# ==========================
def extract_sections_llm(text: str) -> dict:
    prompt = (
        "Split this medical research paper into two parts. "
        "Return ONLY a JSON object with exactly these two keys:\n"
        "- \"without_limitations\": the full paper text verbatim, excluding any limitations content\n"
        "- \"limitations\": all limitations text verbatim, including any that appear inline in paragraphs (not just under a Limitations heading)\n"
        'Use an empty string "" if no limitations are found.'
        "\n\nPaper:\n" + text
    )

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    print(content)
    try:
        sections = json.loads(content)
    except json.JSONDecodeError:
        print("  WARNING: failed to parse LLM response as JSON, returning empty sections")
        sections = {k: "" for k in SECTION_KEYS}

    # Ensure all keys exist
    for key in SECTION_KEYS:
        sections.setdefault(key, "")

    return sections

# ==========================
# PROCESS PDF FILES
# ==========================
def process_pdfs():
    converter = DocumentConverter()
    records = []

    for pdf_path in sorted(DATA_DIR.glob("*.pdf")):
        print(f"Processing {pdf_path.name}...")
        result = converter.convert(str(pdf_path))
        text = result.document.export_to_markdown()
        cleaned = clean_text(text)
        # llm_sections = extract_sections_llm(cleaned)
        hardcoded_sections = extract_sections_hardcoded(cleaned)

        record = {
            "link": "",
            "pdf_path": str(pdf_path),
            "cleaned": cleaned,
            # NOTE: LLM
            # "llm_without_limitations": llm_sections["without_limitations"],
            # "llm_limitations": llm_sections["limitations"],
            "hc_without_limitations": hardcoded_sections["without_limitations"],
            "hc_limitations": hardcoded_sections["limitations"],
        }
        records.append(record)
        # NOTE: LLM
        # print(f"  -> llm_limitations found: {bool(llm_sections['limitations'])}")
        print(f"  -> hc_limitations found:  {bool(hardcoded_sections['limitations'])}")

    # Save as JSON
    with open(OUTPUT_JSON, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nSaved {len(records)} records to {OUTPUT_JSON}")

    # Save as HuggingFace dataset
    dataset = Dataset.from_list(records)
    dataset.save_to_disk(str(DATASET_DIR))
    print(f"HuggingFace dataset saved to {DATASET_DIR}/")
    print(dataset)

    return dataset

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    process_pdfs()