"""Optional job aggregator source (Jooble REST API - Israel portal il.jooble.org).

Why Jooble and why disabled by default:
- Adzuna does not cover Israel (`il` is not a supported country code).
- Careerjet v4 requires forwarding a real browser visitor's `user_ip`, `user_agent`, and
  `Referer` URL for publisher click-tracking, so it is not suitable for a personal script.
- Jooble has an Israel portal (`il.jooble.org`) and a simple JSON POST API, but requires a
  free API key requested for the Israel domain (`JOOBLE_API_KEY` env var) and enforces a
  request quota. Keep `enabled: false` in sources.yaml unless you set `JOOBLE_API_KEY`.

Docs: https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation
POST https://il.jooble.org/api/{api_key}
Body: {"keywords": "...", "location": "Israel", "page": "1"}
"""
from __future__ import annotations

import hashlib
import logging
import os

from .. import net
from ..models import Job
from ..normalize import clean_html, normalize_location

log = logging.getLogger(__name__)
API = "https://il.jooble.org/api/{key}"
DEFAULT_QUERIES = [
    "embedded software engineer",
    "firmware engineer",
    "real-time software engineer",
    "RTOS C++",
]


def fetch(entry: dict) -> list[Job]:
    key = os.environ.get(entry.get("api_key_env", "JOOBLE_API_KEY"))
    if not key:
        log.warning("Aggregator (%s) enabled but JOOBLE_API_KEY is not set; skipping", entry.get("name"))
        return []
    url = API.format(key=key)
    queries = entry.get("queries") or DEFAULT_QUERIES
    location = entry.get("location", "Israel")
    jobs, seen = [], set()
    for q in queries:
        net._wait()
        data = net.post_json(url, {"keywords": q, "location": location, "page": "1"})
        for j in data.get("jobs", []):
            jid = str(j.get("id") or hashlib.sha1((j.get("link") or "").encode()).hexdigest()[:12])
            if jid in seen:
                continue
            seen.add(jid)
            jobs.append(Job(
                id=f"aggregator:jooble:{jid}",
                source="aggregator",
                company=(j.get("company") or "Unknown").strip(),
                title=(j.get("title") or "").strip(),
                location=normalize_location(j.get("location") or location),
                url=j.get("link") or "",
                description=clean_html(j.get("snippet") or ""),
                posted_at=j.get("updated"),
            ))
    return jobs
