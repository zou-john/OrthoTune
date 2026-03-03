#!/usr/bin/env python3
"""
Orthopedic Surgery Open-Access PDF Database Builder
Searches Semantic Scholar for 2025 orthopedic articles, saves metadata
to SQLite, and downloads the PDFs.

Requirements:
    pip install requests tqdm

Usage:
    python ortho_pdf_database.py
    python ortho_pdf_database.py --max-papers 500 --year 2024-2025
    python ortho_pdf_database.py --query "knee arthroplasty" --max-papers 100
    python ortho_pdf_database.py --api-key YOUR_KEY
    python ortho_pdf_database.py --no-download   # index metadata only

Free API key: https://www.semanticscholar.org/product/api
(raises rate limit from 1 req/s → 10 req/s — highly recommended)
"""

import sys, time, sqlite3, argparse, logging, requests
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    class tqdm:
        def __init__(self, iterable=None, **kw):
            self._it = iter(iterable) if iterable is not None else iter([])
        def __iter__(self): return self
        def __next__(self): return next(self._it)
        def update(self, n=1): pass
        def close(self): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass

# ── Configuration ──────────────────────────────────────────────────────────

DEFAULT_QUERIES = [
    "orthopedic surgery outcomes",
    "orthopaedic surgery complications",
    "total knee arthroplasty",
    "total hip arthroplasty",
    "spinal fusion surgery",
    "fracture fixation internal",
    "rotator cuff repair",
    "anterior cruciate ligament reconstruction",
    "bone fracture surgical treatment",
    "joint replacement implant",
    "shoulder arthroplasty",
    "ankle fracture fixation",
    "tibial plateau fracture surgery",
    "lumbar spine surgery",
    "cervical spine surgery",
]

OUTPUT_DIR = Path("ortho_database")
PDF_DIR    = OUTPUT_DIR / "pdfs"
DB_PATH    = OUTPUT_DIR / "articles.db"
LOG_PATH   = OUTPUT_DIR / "download.log"

S2_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = (
    "paperId,title,authors,year,publicationDate,"
    "openAccessPdf,abstract,externalIds,venue,"
    "citationCount,isOpenAccess,publicationTypes"
)
REQUEST_DELAY  = 1.1
DOWNLOAD_DELAY = 0.5

# ── Logging ────────────────────────────────────────────────────────────────

def setup_logging():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(
        level=logging.INFO, format=fmt,
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(LOG_PATH)])
    return logging.getLogger(__name__)

logger = logging.getLogger(__name__)

# ── Database ───────────────────────────────────────────────────────────────

def init_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            paper_id         TEXT PRIMARY KEY,
            title            TEXT NOT NULL,
            authors          TEXT,
            year             INTEGER,
            publication_date TEXT,
            venue            TEXT,
            publication_type TEXT,
            abstract         TEXT,
            doi              TEXT,
            pdf_url          TEXT,
            pdf_filename     TEXT,
            pdf_downloaded   INTEGER DEFAULT 0,
            citation_count   INTEGER,
            is_open_access   INTEGER DEFAULT 0,
            search_query     TEXT,
            added_at         TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS search_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT, year_range TEXT,
            total_found INTEGER, fetched INTEGER,
            run_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_year ON articles(year);
        CREATE INDEX IF NOT EXISTS idx_doi  ON articles(doi);
        CREATE INDEX IF NOT EXISTS idx_dl   ON articles(pdf_downloaded);
    """)
    conn.commit()
    return conn

def upsert_article(conn, paper, query):
    authors   = "; ".join(a.get("name","") for a in (paper.get("authors") or []))
    ext       = paper.get("externalIds") or {}
    doi       = ext.get("DOI") or ext.get("doi")
    pdf_url   = (paper.get("openAccessPdf") or {}).get("url")
    pub_types = ", ".join(paper.get("publicationTypes") or [])
    dl_status = 0 if pdf_url else 2
    conn.execute("""
        INSERT INTO articles
            (paper_id,title,authors,year,publication_date,venue,
             publication_type,abstract,doi,pdf_url,
             is_open_access,citation_count,search_query,pdf_downloaded)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(paper_id) DO UPDATE SET
            pdf_url=COALESCE(excluded.pdf_url,pdf_url),
            citation_count=excluded.citation_count,
            is_open_access=excluded.is_open_access
    """, (paper["paperId"], paper.get("title") or "", authors,
          paper.get("year"), paper.get("publicationDate"),
          paper.get("venue") or "", pub_types,
          paper.get("abstract") or "", doi, pdf_url,
          int(bool(paper.get("isOpenAccess"))),
          paper.get("citationCount") or 0, query, dl_status))
    conn.commit()

# ── Semantic Scholar API ───────────────────────────────────────────────────

def search_papers(query, year_range, max_papers, api_key=None):
    headers = {"User-Agent": "OrthoDBBuilder/1.0"}
    if api_key:
        headers["x-api-key"] = api_key
    results, offset = [], 0
    pbar = tqdm(desc="  " + query[:52], unit=" papers", leave=False)
    while len(results) < max_papers:
        batch = min(100, max_papers - len(results))
        params = {"query": query, "fields": S2_FIELDS, "limit": batch,
                  "offset": offset, "year": year_range, "openAccessPdf": ""}
        try:
            resp = requests.get(S2_SEARCH_URL, params=params,
                                headers=headers, timeout=30)
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                logger.warning("Rate-limited — sleeping %d s", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("API error for '%s': %s", query, exc)
            break
        page = data.get("data") or []
        if not page:
            break
        oa = [p for p in page if (p.get("openAccessPdf") or {}).get("url")]
        results.extend(oa)
        pbar.update(len(oa))
        offset += len(page)
        if offset >= (data.get("total") or 0):
            break
        time.sleep(REQUEST_DELAY)
    pbar.close()
    return results

# ── PDF Download ───────────────────────────────────────────────────────────

def safe_filename(paper_id, title):
    clean = "".join(c if c.isalnum() or c in " _-" else "_" for c in (title or ""))
    return f"{paper_id[:8]}_{'_'.join(clean.split())[:80]}.pdf"

def download_pdf(url, dest, timeout=60):
    try:
        resp = requests.get(url, timeout=timeout, stream=True,
                            headers={"User-Agent": "OrthoDBBuilder/1.0"},
                            allow_redirects=True)
        resp.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(8192):
                fh.write(chunk)
        with open(dest, "rb") as fh:
            if fh.read(4) != b"%PDF":
                dest.unlink(missing_ok=True)
                return False
        return True
    except Exception as exc:
        logger.debug("Download failed [%s]: %s", url, exc)
        if dest.exists():
            dest.unlink(missing_ok=True)
        return False

def download_all_pdfs(conn, pdf_dir):
    rows = conn.execute("""
        SELECT paper_id, title, pdf_url FROM articles
        WHERE pdf_downloaded=0 AND pdf_url IS NOT NULL
    """).fetchall()
    if not rows:
        logger.info("No pending PDFs.")
        return
    logger.info("Downloading %d PDFs ...", len(rows))
    ok = fail = skip = 0
    for row in tqdm(rows, desc="Downloading PDFs", unit=" PDF"):
        fname = safe_filename(row["paper_id"], row["title"])
        dest  = pdf_dir / fname
        if dest.exists():
            conn.execute("UPDATE articles SET pdf_downloaded=1, pdf_filename=? WHERE paper_id=?",
                         (fname, row["paper_id"]))
            conn.commit(); skip += 1; continue
        if download_pdf(row["pdf_url"], dest):
            conn.execute("UPDATE articles SET pdf_downloaded=1, pdf_filename=? WHERE paper_id=?",
                         (fname, row["paper_id"]))
            ok += 1
        else:
            conn.execute("UPDATE articles SET pdf_downloaded=-1 WHERE paper_id=?",
                         (row["paper_id"],))
            fail += 1
        conn.commit()
        time.sleep(DOWNLOAD_DELAY)
    logger.info("Done — saved: %d  existed: %d  failed: %d", ok, skip, fail)

# ── Summary ────────────────────────────────────────────────────────────────

def print_summary(conn):
    def q(sql): return conn.execute(sql).fetchone()[0]
    print("\n" + "="*62)
    print("  ORTHOPEDIC SURGERY DATABASE  —  SUMMARY")
    print("="*62)
    print(f"  Articles indexed          : {q('SELECT COUNT(*) FROM articles'):>7,}")
    print(f"  PDFs successfully saved   : {q(\"SELECT COUNT(*) FROM articles WHERE pdf_downloaded=1\"):>7,}")
    print(f"  Download failures         : {q(\"SELECT COUNT(*) FROM articles WHERE pdf_downloaded=-1\"):>7,}")
    print(f"  Pending downloads         : {q(\"SELECT COUNT(*) FROM articles WHERE pdf_downloaded=0\"):>7,}")
    print(f"  No PDF URL available      : {q('SELECT COUNT(*) FROM articles WHERE pdf_url IS NULL'):>7,}")
    print(f"\n  Database  : {DB_PATH.resolve()}")
    print(f"  PDF dir   : {PDF_DIR.resolve()}")
    print("="*62)
    top = conn.execute("""
        SELECT title, year, citation_count FROM articles
        WHERE pdf_downloaded=1 ORDER BY citation_count DESC LIMIT 5
    """).fetchall()
    if top:
        print("\n  Top downloaded articles by citation count:")
        for i, r in enumerate(top, 1):
            print(f"  {i}. [{r['citation_count']:,} cit., {r['year']}]  {r['title'][:60]}")
    print()

# ── Main ───────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="Build an open-access orthopedic surgery PDF database via Semantic Scholar.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--query",       type=str, default=None)
    p.add_argument("--max-papers",  type=int, default=200)
    p.add_argument("--year",        type=str, default="2025-2025")
    p.add_argument("--api-key",     type=str, default=None)
    p.add_argument("--no-download", action="store_true")
    p.add_argument("--output-dir",  type=str, default=None)
    return p.parse_args()

def main():
    args = parse_args()
    global OUTPUT_DIR, PDF_DIR, DB_PATH, LOG_PATH
    if args.output_dir:
        OUTPUT_DIR = Path(args.output_dir)
        PDF_DIR    = OUTPUT_DIR / "pdfs"
        DB_PATH    = OUTPUT_DIR / "articles.db"
        LOG_PATH   = OUTPUT_DIR / "download.log"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    global logger
    logger = setup_logging()
    logger.info("Starting | year=%s | max_per_query=%d", args.year, args.max_papers)

    conn    = init_db(DB_PATH)
    queries = [args.query] if args.query else DEFAULT_QUERIES

    logger.info("PHASE 1 — Indexing articles")
    for i, query in enumerate(queries, 1):
        logger.info("[%d/%d] %s", i, len(queries), query)
        papers = search_papers(query, args.year, args.max_papers, args.api_key)
        logger.info("       %d papers found", len(papers))
        for paper in papers:
            upsert_article(conn, paper, query)
        conn.execute("INSERT INTO search_log (query,year_range,total_found,fetched) VALUES (?,?,?,?)",
                     (query, args.year, len(papers), len(papers)))
        conn.commit()
        time.sleep(REQUEST_DELAY)

    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    logger.info("Phase 1 complete — %d unique articles", total)

    if not args.no_download:
        logger.info("PHASE 2 — Downloading PDFs")
        download_all_pdfs(conn, PDF_DIR)
    else:
        logger.info("Skipping PDF downloads (--no-download)")

    print_summary(conn)
    conn.close()

if __name__ == "__main__":
    main()