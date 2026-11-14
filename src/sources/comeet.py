"""Comeet Careers API 2.0 (used by many Israeli companies).

Docs: https://developers.comeet.com/reference/careers-api-overview
GET https://www.comeet.co/careers-api/2.0/company/{company_uid}/positions?token={token}&details=true

Comeet requires a company uid + token. These are published by each company for its
public careers site (visible in the company's public Comeet careers page). Put them in
sources.yaml as `uid:` and `token:`.
"""
from __future__ import annotations

import urllib.parse

from .. import net
from ..models import Job
from ..normalize import clean_html, normalize_location

API = "https://www.comeet.co/careers-api/2.0/company/{uid}/positions?token={token}&details=true"
COUNTRY = {"IL": "Israel"}


def fetch(entry: dict) -> list[Job]:
    uid, token = entry["uid"], entry["token"]
    data = net.get_json(API.format(uid=urllib.parse.quote(uid), token=urllib.parse.quote(token)))
    jobs = []
    for p in data:
        if p.get("is_internal"):
            continue
        loc = p.get("location") or {}
        country = COUNTRY.get(loc.get("country") or "", loc.get("country") or "")
        location = ", ".join(x for x in dict.fromkeys(
            [loc.get("name"), loc.get("city"), country]) if x)
        details = sorted(p.get("details") or [], key=lambda d: int(d.get("order") or 0))
        description = "\n".join(f"{d.get('name', '')}\n{clean_html(d.get('value'))}" for d in details)
        workplace = (p.get("workplace_type") or "").lower()
        jobs.append(Job(
            id=f"comeet:{uid}:{p['uid']}",
            source="comeet",
            company=entry["name"],
            title=(p.get("name") or "").strip(),
            location=normalize_location(location),
            url=p.get("url_active_page") or p.get("url_comeet_hosted_page") or "",
            # experience_level (e.g. "Entry-level", "Senior") helps the seniority filter
            description=(f"Experience level: {p['experience_level']}\n" if p.get("experience_level") else "")
                        + description,
            posted_at=p.get("time_updated"),
            remote=bool(loc.get("is_remote")) or workplace == "remote",
        ))
    return jobs
