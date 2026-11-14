"""Polite HTTP: fixed User-Agent, delay between requests, ETag/Last-Modified cache."""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path

log = logging.getLogger(__name__)

USER_AGENT = "personal-job-tracker/0.1 (personal, non-commercial job alerts)"
DELAY_SECONDS = 1.5
TIMEOUT = 30
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "http_cache"

_last_request = 0.0


def _wait() -> None:
    global _last_request
    gap = time.monotonic() - _last_request
    if gap < DELAY_SECONDS:
        time.sleep(DELAY_SECONDS - gap)
    _last_request = time.monotonic()


def _cache_path(url: str) -> Path:
    return CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest() + ".json")


def get_json(url: str, headers: dict | None = None):
    """GET url and parse JSON. Uses conditional requests when we have a cached copy."""
    cache_file = _cache_path(url)
    cached = None
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cached = None

    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json",
                   "Accept-Encoding": "gzip"}
    if headers:
        req_headers.update(headers)
    if cached:
        if cached.get("etag"):
            req_headers["If-None-Match"] = cached["etag"]
        if cached.get("last_modified"):
            req_headers["If-Modified-Since"] = cached["last_modified"]

    _wait()
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            body = raw.decode("utf-8")
            etag, last_mod = resp.headers.get("ETag"), resp.headers.get("Last-Modified")
    except urllib.error.HTTPError as e:
        if e.code == 304 and cached:
            log.debug("304 Not Modified (cache hit): %s", url)
            return json.loads(cached["body"])
        raise

    data = json.loads(body)
    if etag or last_mod:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({"etag": etag, "last_modified": last_mod, "body": body}),
                              encoding="utf-8")
    return data


def get_text(url: str, headers: dict | None = None) -> str:
    """Polite GET returning decoded UTF-8 text (with 1.5s rate limit)."""
    req_headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"}
    if headers:
        req_headers.update(headers)
    _wait()
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "ignore")


def post_json(url: str, payload: dict, headers: dict | None = None):
    """POST JSON, return parsed JSON response (no cache, no delay for non-scraping calls)."""
    req_headers = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=req_headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))
