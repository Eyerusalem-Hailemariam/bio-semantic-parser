"""Layer 7 step 2 — SQLite triple store deduplication with PLN confidence revision."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


# Legacy / staging path (used by Layer 7 during paper processing)
_DB_PATH      = Path("data/triple_store.db")

# Format-specific permanent stores
_DB_NEO4J     = Path("data/triple_store_neo4j.db")
_DB_METTA     = Path("data/triple_store_metta.db")


def db_path_for_format(fmt: str) -> Path:
    """Return the permanent DB path for the given format ('neo4j' or 'metta')."""
    if fmt == "neo4j":
        return _DB_NEO4J
    if fmt == "metta":
        return _DB_METTA
    return _DB_PATH   # fallback / legacy


def _get_conn() -> sqlite3.Connection:
    import os as _os
    path = Path(_os.getenv("TRIPLE_STORE_PATH", str(_DB_PATH)))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS triples (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id       TEXT    NOT NULL,
            subject_name     TEXT    NOT NULL,
            subject_type     TEXT    NOT NULL,
            relation         TEXT    NOT NULL,
            object_id        TEXT    NOT NULL,
            object_name      TEXT    NOT NULL,
            object_type      TEXT    NOT NULL,
            negated          INTEGER NOT NULL DEFAULT 0,
            confidence       REAL    NOT NULL,
            source_papers    TEXT    NOT NULL,
            species          TEXT,
            tissue           TEXT,
            condition        TEXT,
            effect_size      TEXT,
            reasoning        TEXT,
            is_contradiction INTEGER DEFAULT 0,
            flagged_for_review INTEGER DEFAULT 0,
            review_reason    TEXT,
            created_at       TEXT    NOT NULL,
            updated_at       TEXT    NOT NULL,
            UNIQUE(subject_id, relation, object_id, negated)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_triple_key
        ON triples(subject_id, relation, object_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_subject ON triples(subject_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_object  ON triples(object_id)
    """)
    conn.commit()


def deduplicate(record: dict) -> dict:
    """
    Check and insert/update one normalised relation record.

    Returns record with added fields:
        is_duplicate   bool  — True if triple already existed
        triple_id      int   — SQLite row ID (existing or new)
    """
    now  = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    _ensure_schema(conn)

    subject_id = record.get("subject_id", "")
    relation   = record.get("relation",   "")
    object_id  = record.get("object_id",  "")
    negated    = 1 if record.get("negated") else 0
    doc_id     = record.get("document_id", "unknown")
    confidence = float(record.get("confidence", 0.0))

    # ── Normalize doc_id to canonical paper ID ────────────────────────────────
    # The DOI extractor may replace the PDF hash with a DOI during Layer 7.
    # Multiple runs of the same paper then produce different doc_ids
    # (hash, DOI, dataset DOI) which would inflate N in PLN confidence.
    # Fix: for PDF papers, always use the SHA256 hash as the canonical source ID.
    # The hash is recoverable from the staging DB filename (set in TRIPLE_STORE_PATH).
    import os as _os, re as _re
    _staging = _os.getenv("TRIPLE_STORE_PATH", "")
    if _staging:
        _m = _re.search(r'([0-9a-f]{64})', Path(_staging).name)
        if _m:
            _canonical_hash = _m.group(1)
            # If the incoming doc_id is a DOI (not a hash), use the canonical hash.
            # This ensures all runs of the same PDF paper use the same source ID.
            if doc_id != _canonical_hash and not _re.match(r'^[0-9a-f]{64}$', doc_id):
                doc_id = _canonical_hash

    existing = conn.execute(
        "SELECT id, confidence, source_papers FROM triples "
        "WHERE subject_id=? AND relation=? AND object_id=? AND negated=?",
        (subject_id, relation, object_id, negated),
    ).fetchone()

    if existing:
        # PLN Revision Rule — Truth_Revision from trueagi-io/PeTTa lib_pln.metta
        # Confidence = N/(N+1) where N = number of INDEPENDENT PAPERS (Truth_w2c).
        # doc_id is normalized above so the same paper never inflates N.
        sources = json.loads(existing["source_papers"])
        if doc_id not in sources:
            sources.append(doc_id)
        n_total  = len(sources)
        new_conf = round(n_total / (n_total + 1), 4)   # Truth_w2c(n_total)
        conn.execute(
            "UPDATE triples SET confidence=?, source_papers=?, updated_at=? WHERE id=?",
            (new_conf, json.dumps(sources), now, existing["id"]),
        )
        conn.commit()
        conn.close()
        return {**record, "is_duplicate": True,  "triple_id": existing["id"]}

    cursor = conn.execute("""
        INSERT INTO triples
            (subject_id, subject_name, subject_type,
             relation,
             object_id, object_name, object_type,
             negated, confidence, source_papers,
             species, tissue, condition, effect_size, reasoning,
             is_contradiction, flagged_for_review, review_reason,
             created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        subject_id, record.get("subject_name",""), record.get("subject_type",""),
        relation,
        object_id,  record.get("object_name",""),  record.get("object_type",""),
        negated, confidence, json.dumps([doc_id]),
        record.get("species",""), record.get("tissue",""),
        record.get("condition",""), record.get("effect_size",""),
        record.get("reasoning",""),
        1 if record.get("is_contradiction") else 0,
        1 if record.get("flagged_for_review") else 0,
        record.get("review_reason",""),
        now, now,
    ))
    conn.commit()
    triple_id = cursor.lastrowid
    conn.close()
    return {**record, "is_duplicate": False, "triple_id": triple_id}


def get_all_triples() -> list:
    """Return all triples from the store (for export to CSV / MeTTa)."""
    conn = _get_conn()
    _ensure_schema(conn)
    rows = conn.execute("SELECT * FROM triples").fetchall()
    conn.close()
    return [dict(row) for row in rows]

