"""Orchestrates one run: fetch all sources -> score -> dedupe -> notify -> dashboard.

    python -m src.main             # normal run
    python -m src.main --dry-run   # print matches; no Telegram, no DB writes, no dashboard
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

from . import dashboard, llm, notify
from .models import Job, ScoreResult, utcnow_iso
from .scoring import Scorer
from .sources import FETCHERS
from .store import Store

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("tracker")


def load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_all(sources: list[dict], only: str | None) -> tuple[list[Job], list[str]]:
    """Each source fails independently: errors are logged and collected, never raised."""
    jobs, errors = [], []
    for entry in sources:
        name = entry.get("name", "?")
        if entry.get("enabled", True) is False or (only and only.lower() != name.lower()):
            continue
        try:
            fetcher = FETCHERS[entry["ats"]]
            got = fetcher(entry)
            log.info("%-22s %-10s %4d jobs", name, entry["ats"], len(got))
            jobs.extend(got)
        except Exception as e:  # noqa: BLE001 - one broken source must not stop the run
            msg = f"{name} ({entry.get('ats')}): {type(e).__name__}: {e}"
            log.error("source failed: %s", msg)
            errors.append(msg)
    return jobs, errors


def evaluate(jobs: list[Job], scorer: Scorer, store: Store,
             llm_budget: int) -> list[tuple[Job, ScoreResult]]:
    """Score every job, ask Gemini about borderline ones, persist. Returns matches."""
    matches, seen_ids = [], set()
    for job in jobs:
        if job.id in seen_ids:
            continue
        seen_ids.add(job.id)
        result = scorer.score(job)
        verdict = None
        if result.status == "borderline":
            prev = store.get(job.id)
            verdict = prev["llm_verdict"] if prev else None
            if verdict is None and llm.enabled() and llm_budget > 0:
                llm_budget -= 1
                try:
                    verdict = llm.judge(job)
                except Exception as e:  # noqa: BLE001
                    log.warning("Gemini failed for %s: %s", job.id, e)
            if verdict and verdict.startswith("yes"):
                result = ScoreResult(result.score, "match", result.reasons + [f"gemini {verdict}"])
        store.upsert(job, result, verdict)
        if result.status == "match":
            matches.append((job, result))
    return matches


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Personal embedded-jobs tracker")
    ap.add_argument("--dry-run", action="store_true",
                    help="print matches without notifying or saving anything")
    ap.add_argument("--only", help="run a single company from sources.yaml (by name)")
    ap.add_argument("--db", default=str(ROOT / "data" / "jobs.db"))
    ap.add_argument("--llm-max", type=int, default=30, help="max Gemini calls per run")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    handlers = [logging.StreamHandler(sys.stdout)]
    if not args.dry_run:
        (ROOT / "data").mkdir(exist_ok=True)
        handlers.append(logging.FileHandler(ROOT / "data" / "tracker.log", encoding="utf-8"))
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s", handlers=handlers)

    profile = load_yaml(ROOT / "config" / "profile.yaml")
    sources = load_yaml(ROOT / "config" / "sources.yaml").get("sources", [])
    started = utcnow_iso()
    store = Store(args.db, in_memory_copy=args.dry_run)

    jobs, errors = fetch_all(sources, args.only)
    scorer = Scorer(profile)
    matches = evaluate(jobs, scorer, store, args.llm_max)
    new, new_fps = [], set()
    for j, r in matches:
        if j.fingerprint not in new_fps and not store.already_notified(j):
            new.append((j, r))
            new_fps.add(j.fingerprint)
    new_ids = {j.id for j, _ in new}
    notify_new = [(j, r) for j, r in new if scorer.in_notify_region(j)]
    log.info("fetched %d jobs, %d matches, %d new (%d in notify region), %d source errors",
             len(jobs), len(matches), len(new), len(notify_new), len(errors))

    if args.dry_run:
        for j, r in sorted(matches, key=lambda x: -x[1].score):
            flag = "NEW" if j.id in new_ids else "   "
            print(f"{flag} [{r.score:3d}] {j.company} | {j.title} | {j.location}\n"
                  f"          {j.url}\n          {'; '.join(r.reasons)}")
        store.close()
        return 0

    if notify_new:
        try:
            if notify.send(notify_new):
                store.mark_notified([j.id for j, _ in notify_new])
        except Exception as e:  # noqa: BLE001 - keep the run going; retried next run
            log.error("Telegram failed (will retry next run): %s", e)
            errors.append(f"telegram: {e}")

    dashboard.write(
        ROOT / "docs" / "index.html",
        store.current_matches(started),
        new_ids,
        borderline=store.current_borderline(started),
        total_scanned=store.total_seen(started),
    )
    store.log_run(started, len(jobs), len(new), errors)
    store.commit()
    store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
