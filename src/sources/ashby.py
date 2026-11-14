"""Ashby public Job Posting API (no auth).

Docs: https://developers.ashbyhq.com/docs/public-job-posting-api
GET https://api.ashbyhq.com/posting-api/job-board/{job_board_name}
"""
from __future__ import annotations

from .. import net
from ..models import Job
from ..normalize import clean_html, normalize_location

API = "https://api.ashbyhq.com/posting-api/job-board/{board}"


def fetch(entry: dict) -> list[Job]:
    board = entry["board"]
    data = net.get_json(API.format(board=board))
    jobs = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location") or ""]
        locs += [s.get("location") or "" for s in j.get("secondaryLocations") or []]
        country = (((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry")) or ""
        location = " / ".join(dict.fromkeys(l for l in locs if l))
        if country and country.lower() not in location.lower():
            location = f"{location}, {country}" if location else country
        jobs.append(Job(
            id=f"ashby:{board}:{j['id']}",
            source="ashby",
            company=entry["name"],
            title=(j.get("title") or "").strip(),
            location=normalize_location(location),
            url=j.get("jobUrl", ""),
            description=j.get("descriptionPlain") or clean_html(j.get("descriptionHtml")),
            posted_at=j.get("publishedAt"),
            remote=bool(j.get("isRemote")) or (j.get("workplaceType") or "").lower() == "remote",
        ))
    return jobs
