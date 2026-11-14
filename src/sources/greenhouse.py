"""Greenhouse Job Board API (public, no auth).

Docs: https://developers.greenhouse.io/job-board.html
GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
"""
from __future__ import annotations

from .. import net
from ..models import Job
from ..normalize import clean_html, normalize_location

API = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"


def fetch(entry: dict) -> list[Job]:
    board = entry["board"]
    data = net.get_json(API.format(board=board))
    jobs = []
    for j in data.get("jobs", []):
        locs = [(j.get("location") or {}).get("name", "")]
        locs += [o.get("location") or o.get("name") or "" for o in j.get("offices") or []]
        location = " / ".join(dict.fromkeys(l for l in locs if l))  # dedupe, keep order
        jobs.append(Job(
            id=f"greenhouse:{board}:{j['id']}",
            source="greenhouse",
            company=entry["name"],
            title=j.get("title", "").strip(),
            location=normalize_location(location),
            url=j.get("absolute_url", ""),
            description=clean_html(j.get("content")),
            posted_at=j.get("first_published") or j.get("updated_at"),
        ))
    return jobs
