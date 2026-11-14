"""Workday public career site JSON endpoint (`/wday/cxs/{tenant}/{site}/jobs`).

Used by NVIDIA Israel, Intel Israel, Qualcomm Israel, etc.
"""
from __future__ import annotations

from .. import net
from ..models import Job
from ..normalize import clean_html, normalize_location

DEFAULT_QUERIES = ["embedded Israel", "firmware Israel", "RTOS Israel"]
_SKIP_DETAIL = (
    "intern", "student", "junior", "graduate", "manager", "director", "vp", "head of",
    "principal", "staff", "architect", "mechanical", "analog", "asic", "physical design",
    "layout", "devops", "sales",
)
_WANT_DETAIL = (
    "embedded", "firmware", "fw", "real-time", "real time", "real - time", "realtime",
    "rtos", "kernel", "driver", "bsp", "c++", "low level", "low-level", "linux",
    "software", "system", "silicon", "validation", "soc", "dsp", "wireless",
    "network", "rdma", "switch", "pcie", "phy", "serdes", "robotics", "autonomous",
    "middleware", "platform", "hal", "sdk", "bootloader",
)


def fetch(entry: dict) -> list[Job]:
    host = entry["host"]          # e.g. nvidia.wd5.myworkdayjobs.com
    tenant = entry["tenant"]      # e.g. nvidia
    site = entry["site"]          # e.g. NVIDIAExternalCareerSite
    base = f"https://{host}/wday/cxs/{tenant}/{site}"
    queries = entry.get("queries") or DEFAULT_QUERIES

    postings: dict[str, dict] = {}
    for q in queries:
        net._wait()
        data = net.post_json(
            f"{base}/jobs",
            {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": q},
            headers={"Accept": "application/json"},
        )
        for p in data.get("jobPostings") or []:
            path = p.get("externalPath") or ""
            if path and path not in postings:
                postings[path] = p

    jobs: list[Job] = []
    for path, p in postings.items():
        title = (p.get("title") or "").strip()
        low_t = title.lower()
        detail = {}
        # Only fetch full detail JSON for candidate titles (saves dozens of 1.5s requests)
        if any(w in low_t for w in _WANT_DETAIL) and not any(b in low_t for b in _SKIP_DETAIL):
            try:
                detail = (net.get_json(f"{base}{path}") or {}).get("jobPostingInfo") or {}
            except Exception:  # noqa: BLE001
                detail = {}
        loc_hint = detail.get("location") or p.get("locationsText") or ""
        if not loc_hint or "location" in loc_hint.lower():
            # Infer Israel city from externalPath like /job/Israel-Tel-Aviv/...
            if "/job/israel" in path.lower():
                loc_hint = path.split("/")[2].replace("-", " ")
        locs = [loc_hint] + (detail.get("additionalLocations") or [])
        location = " / ".join(dict.fromkeys(l for l in locs if l))
        req_id = detail.get("jobReqId") or (p.get("bulletFields") or [path])[0]
        jobs.append(Job(
            id=f"workday:{tenant}:{req_id}",
            source="workday",
            company=entry["name"],
            title=(detail.get("title") or title).strip(),
            location=normalize_location(location),
            url=detail.get("externalUrl") or f"https://{host}/en-US/{site}{path}",
            description=clean_html(detail.get("jobDescription") or ""),
            posted_at=detail.get("startDate") or p.get("postedOn"),
        ))
    return jobs
