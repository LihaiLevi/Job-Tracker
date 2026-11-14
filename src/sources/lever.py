"""Lever Postings API (public, no auth).

Docs: https://github.com/lever/postings-api
GET https://api.lever.co/v0/postings/{company}?mode=json
EU accounts: https://api.eu.lever.co/v0/postings/{company}?mode=json  (set `region: eu`)
"""
from __future__ import annotations

from datetime import datetime, timezone

from .. import net
from ..models import Job
from ..normalize import clean_html, normalize_location

API = {"global": "https://api.lever.co/v0/postings/{board}?mode=json",
       "eu": "https://api.eu.lever.co/v0/postings/{board}?mode=json"}
COUNTRY = {"IL": "Israel"}


def fetch(entry: dict) -> list[Job]:
    board = entry["board"]
    data = net.get_json(API[entry.get("region", "global")].format(board=board))
    jobs = []
    for p in data:
        cats = p.get("categories") or {}
        locs = cats.get("allLocations") or [cats.get("location", "")]
        location = " / ".join(l for l in locs if l)
        country = COUNTRY.get(p.get("country") or "", p.get("country") or "")
        if country and country.lower() not in location.lower():
            location = f"{location}, {country}" if location else country
        parts = [p.get("descriptionPlain") or clean_html(p.get("description"))]
        for lst in p.get("lists") or []:
            parts.append(f"{lst.get('text', '')}\n{clean_html(lst.get('content'))}")
        parts.append(p.get("additionalPlain") or clean_html(p.get("additional")))
        created = p.get("createdAt")
        jobs.append(Job(
            id=f"lever:{board}:{p['id']}",
            source="lever",
            company=entry["name"],
            title=(p.get("text") or "").strip(),
            location=normalize_location(location),
            url=p.get("hostedUrl", ""),
            description="\n".join(x for x in parts if x).strip(),
            posted_at=(datetime.fromtimestamp(created / 1000, timezone.utc).isoformat()
                       if isinstance(created, (int, float)) else None),
            remote=(p.get("workplaceType") or "").lower() == "remote",
        ))
    return jobs
