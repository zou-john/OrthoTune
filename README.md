# OrthoTune

A tool that reads orthopedic research papers from a spreadsheet and uses AI to summarize their limitations.

## One-Time Setup

Open your Terminal (Mac: press `Cmd + Space`, type "Terminal", hit Enter) and run these commands one at a time:

**1. Go to the project folder**
```bash
cd path/to/OrthoTune
```

**2. Create a virtual environment (an isolated space for the project)**
```bash
python -m venv .venv
```

**3. Activate it**
```bash
source .venv/bin/activate
```
> You'll see `(.venv)` appear at the start of your terminal line — that means it's working.

**4. Install the project and its dependencies**
```bash
pip install -e .
```

**5. Add your API key**

Create a file called `.env` in the project folder and paste this inside:
```
OPENAI_API_KEY="your-api-key-here"
```
Replace `your-api-key-here` with your actual key.

---

## Step 1 — Extract Data from the Spreadsheet

This reads `data/ortho_v1.csv` and pulls out the key, title, and full text of each paper. It saves the result to `data/llm_dataset.json`.

```bash
python scripts/build_llm_dataset.py
```

---

## Step 2 — Run AI Analysis

This sends each paper to the AI and asks it to summarize the limitations. Results are saved to `data/limitations_output.json`.

```bash
python scripts/run_limitations.py
```

---

## Where Are My Results?

After Step 2 finishes, open `data/limitations_output.json`. Each entry contains:
- `key` — the paper's ID
- `title` — the paper's title
- `limitations` — the AI-generated limitations summary
