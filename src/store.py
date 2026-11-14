"""SQLite store: every job seen, its score, and whether it was already notified.

Dedupe rules ("never alert twice"):
  - same job id (source:board:native_id) -> already known
  - same fingerprint (company+title+location) already notified -> treat as notified
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import Job, ScoreResult, utcnow_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    source      TEXT, company TEXT, title TEXT, location TEXT, url TEXT,
    posted_at   TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    score       INTEGER,
    status      TEXT,           -- match | borderline | reject
    reasons     TEXT,
    llm_verdict TEXT,           -- NULL = not asked; 'yes: ...' / 'no: ...'
    notified    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_jobs_fp ON jobs(fingerprint);
CREATE TABLE IF NOT EXISTS runs (
    started_at TEXT PRIMARY KEY, finished_at TEXT, fetched INTEGER, new_matches INTEGER, errors TEXT
);
"""


class Store:
    def __init__(self, path: str | Path, in_memory_copy: bool = False):
        """in_memory_copy=True (used by --dry-run): load the DB into memory so nothing
        is ever written back to disk."""
        self.path = str(path)
        if in_memory_copy:
            self.db = sqlite3.connect(":memory:")
            if Path(self.path).exists():
                src = sqlite3.connect(self.path)
                src.backup(self.db)
                src.close()
        else:
            if self.path != ":memory:":
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def get(self, job_id: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    def already_notified(self, job: Job) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM jobs WHERE notified = 1 AND (id = ? OR fingerprint = ?) LIMIT 1",
            (job.id, job.fingerprint)).fetchone()
        return row is not None

    def upsert(self, job: Job, result: ScoreResult, llm_verdict: str | None = None) -> None:
        now = utcnow_iso()
        self.db.execute(
            """INSERT INTO jobs (id, fingerprint, source, company, title, location, url, posted_at,
                                 first_seen, last_seen, score, status, reasons, llm_verdict)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 title=excluded.title, location=excluded.location, url=excluded.url,
                 last_seen=excluded.last_seen, score=excluded.score, status=excluded.status,
                 reasons=excluded.reasons,
                 llm_verdict=COALESCE(excluded.llm_verdict, jobs.llm_verdict)""",
            (job.id, job.fingerprint, job.source, job.company, job.title, job.location, job.url,
             job.posted_at, job.first_seen, now, result.score, result.status,
             "; ".join(result.reasons), llm_verdict))

    def mark_notified(self, job_ids: list[str]) -> None:
        self.db.executemany("UPDATE jobs SET notified = 1 WHERE id = ?", [(i,) for i in job_ids])

    def current_matches(self, since: str) -> list[sqlite3.Row]:
        """Matches still listed (seen in the run that started at `since`)."""
        return self.db.execute(
            "SELECT * FROM jobs WHERE status = 'match' AND last_seen >= ? ORDER BY score DESC, first_seen DESC",
            (since,)).fetchall()

    def current_borderline(self, since: str) -> list[sqlite3.Row]:
        """Borderline jobs still listed in the latest run."""
        return self.db.execute(
            "SELECT * FROM jobs WHERE status = 'borderline' AND last_seen >= ? ORDER BY score DESC, first_seen DESC",
            (since,)).fetchall()

    def total_seen(self, since: str) -> int:
        row = self.db.execute("SELECT COUNT(*) FROM jobs WHERE last_seen >= ?", (since,)).fetchone()
        return int(row[0]) if row else 0

    def log_run(self, started: str, fetched: int, new_matches: int, errors: list[str]) -> None:
        self.db.execute("INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?)",
                        (started, utcnow_iso(), fetched, new_matches, "\n".join(errors)))

    def commit(self) -> None:
        self.db.commit()

    def close(self) -> None:
        self.db.close()
