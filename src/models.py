"""Common Job object returned by every source."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Job:
    id: str                 # globally unique: "<source>:<board>:<native id>"
    source: str             # greenhouse | lever | ashby | comeet | aggregator name
    company: str
    title: str
    location: str
    url: str
    description: str = ""   # plain text (normalize.clean_html is applied by sources)
    posted_at: str | None = None
    first_seen: str = field(default_factory=utcnow_iso)
    remote: bool = False    # true when the source explicitly flags the job as remote

    @property
    def fingerprint(self) -> str:
        """Same company + title + location => same job, even if re-posted with a new id.

        Used so a re-posted job (new ATS id) is never alerted twice.
        """
        def norm(s: str) -> str:
            return re.sub(r"[^a-z0-9\u0590-\u05ff]+", " ", (s or "").lower()).strip()

        key = "|".join((norm(self.company), norm(self.title), norm(self.location)))
        return hashlib.sha1(key.encode("utf-8")).hexdigest()


@dataclass
class ScoreResult:
    score: int
    status: str             # "match" | "borderline" | "reject"
    reasons: list[str]
