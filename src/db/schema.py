import sqlite3
from pathlib import Path

DB_PATH = "data/eval_table.db"


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS limitation_details (
            pmid              INTEGER NOT NULL,
            limitation_label  TEXT    NOT NULL CHECK(limitation_label IN ('A', 'B')),
            limitation_name   TEXT    NOT NULL,
            relevance         INTEGER NOT NULL CHECK(relevance BETWEEN 1 AND 5),
            critical_thinking INTEGER NOT NULL CHECK(critical_thinking BETWEEN 1 AND 5),
            publishable       TEXT    NOT NULL CHECK(publishable IN ('Y', 'N')),
            hallucination     TEXT    NOT NULL CHECK(hallucination IN ('Y', 'N'))
        );

        CREATE TABLE IF NOT EXISTS limitation_summary (
            pmid          INTEGER NOT NULL UNIQUE,
            ai_generated  TEXT    CHECK(ai_generated IN ('A', 'B')),
            publishable_a TEXT    NOT NULL CHECK(publishable_a IN ('Y', 'N')),
            publishable_b TEXT    NOT NULL CHECK(publishable_b IN ('Y', 'N'))
        );
    """)
    conn.commit()
