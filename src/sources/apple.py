"""Apple Careers public SSR JSON (jobs.apple.com).

Fetches Israel job listings via https://jobs.apple.com/en-il/search?location=israel-ISR&key=...
and enriches candidate postings with full descriptions from /en-il/details/{id}.
"""
from __future__ import annotations

import json
import re
import urllib.parse

from .. import net
from ..models import Job
from ..normalize import clean_html, normalize_location

_HYDRATION = re.compile(r"window\.__staticRouterHydrationData\s*=\s*JSON\.parse\((\".*?\")\);", re.S)
DEFAULT_KEYS = ["embedded", "firmware", "real-time", "C++"]
_SKIP_DETAIL = (
    "intern", "student", "junior", "graduate", "manager", "director", "vp", "head of",
    "principal", "staff", "mechanical", "analog", "asic", "physical design", "layout",
    "devops", "sales", "recruiter", "designer",
)
_WANT_DETAIL = (
    "embedded", "firmware", "fw", "real-time", "real time", "real - time", "realtime",
    "rtos", "kernel", "driver", "bsp", "c++", "low level", "low-level", "linux",
    "software", "system", "silicon", "validation", "soc", "dsp", "wireless",
    "network", "robotics", "autonomous", "middleware", "platform", "hal", "sdk",
)


def _load_hydration(url: str) -> dict:
    html = net.get_text(url)
    m = _HYDRATION.search(html)
    if not m:
        return {}
    return json.loads(json.loads(m.group(1))).get("loaderData", {})


def fetch(entry: dict) -> list[Job]:
    location = entry.get("location", "israel-ISR")
    keys = entry.get("queries") or DEFAULT_KEYS
    raw_items: dict[str, dict] = {}
    for k in keys:
        q = urllib.parse.quote(k)
        url = f"https://jobs.apple.com/en-il/search?location={location}&key={q}"
        data = (_load_hydration(url).get("search") or {}).get("searchResults") or []
        for item in data:
            jid = str(item.get("id") or "")
            if jid and jid not in raw_items:
                raw_items[jid] = item

    jobs: list[Job] = []
    for jid, item in raw_items.items():
        title = (item.get("postingTitle") or "").strip()
        locs = [l.get("name") or "" for l in (item.get("locations") or [])]
        loc_str = ", ".join(dict.fromkeys([l for l in locs if l] + ["Israel"]))
        summary = clean_html(item.get("jobSummary") or "")
        low_t = title.lower()
        if any(w in low_t for w in _WANT_DETAIL) and not any(b in low_t for b in _SKIP_DETAIL):
            try:
                jd = ((_load_hydration(f"https://jobs.apple.com/en-il/details/{jid}")
                       .get("jobDetails") or {}).get("jobsData") or {})
                parts = [
                    jd.get("jobSummary"),
                    jd.get("description"),
                    jd.get("minimumQualifications"),
                    jd.get("preferredQualifications"),
                ]
                full = "\n".join(clean_html(p) for p in parts if p)
                if full:
                    summary = full
            except Exception:  # noqa: BLE001
                pass
        jobs.append(Job(
            id=f"apple:israel:{jid}",
            source="apple",
            company=entry.get("name", "Apple"),
            title=title,
            location=normalize_location(loc_str),
            url=f"https://jobs.apple.com/en-il/details/{jid}",
            description=summary,
            posted_at=item.get("postDateInGMT") or item.get("postingDate"),
            remote=bool(item.get("homeOffice")),
        ))
    return jobs
