"""Relevance scoring driven entirely by config/profile.yaml.

Order:
  1. Hard filters (reject): bad seniority words, non-software title words, experience
     level, years required (>= reject_min_years, or Senior with > senior_max_years),
     location not in Israel / not remote-open-to-Israel.
  2. Score = title weights (capped) + skill weights in description (capped)
             + location bonus - title penalties - senior-with-unknown-years penalty.
  3. status: match (>= thresholds.match AND title has a real role keyword),
             borderline (>= thresholds.borderline), else reject.
"""
from __future__ import annotations

import re

from .models import Job, ScoreResult


def _pattern(kw: str) -> re.Pattern:
    """Whole-word match for Latin keywords; substring for Hebrew (prefix letters attach)."""
    kw = kw.lower().strip()
    left = r"(?<!\w)" if kw[0].isascii() and kw[0].isalnum() else ""
    right = r"(?!\w)" if kw[-1].isascii() and kw[-1].isalnum() else ""
    return re.compile(left + re.escape(kw) + right, re.IGNORECASE)


def _compile_list(words) -> list[tuple[str, re.Pattern]]:
    return [(w, _pattern(w)) for w in (words or [])]


def _compile_weights(d) -> list[tuple[str, int, re.Pattern]]:
    return [(k, int(v), _pattern(k)) for k, v in (d or {}).items()]


def _first_hit(text: str, pats) -> str | None:
    for word, pat in pats:
        if pat.search(text):
            return word
    return None


# "5+ years", "3-5 years", "at least 4 years", "minimum of 8 yrs"
_EN_YEARS = re.compile(
    r"(at least|minimum(?: of)?|min\.?|over)?\s*(\d{1,2})\s*(\+|plus)?\s*"
    r"(?:(?:-|–|to)\s*\d{1,2}\s*\+?\s*)?(?:years?|yrs?)\b(?=(.{0,60}))",
    re.IGNORECASE | re.DOTALL)
# "5 שנות ניסיון", "3+ שנים", "ניסיון של 4 שנים לפחות"
_HE_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:(?:-|–)\s*\d{1,2}\s*\+?\s*)?(?:שנות|שנים|שנ['\"]?)")
_EXP_CONTEXT = re.compile(r"experience|exp\b|hands[- ]on|background|industry", re.IGNORECASE)
MAX_PLAUSIBLE_YEARS = 15   # ignore "25 years of innovation" style company boilerplate


def required_years(text: str) -> int | None:
    """Strongest (largest) minimum-years requirement found in the text, or None."""
    found = []
    for m in _EN_YEARS.finditer(text or ""):
        qualifier, n, plus, after = m.group(1), int(m.group(2)), m.group(3), m.group(4)
        if n > MAX_PLAUSIBLE_YEARS:
            continue
        if qualifier or plus or _EXP_CONTEXT.search(after or ""):
            found.append(n)
    for m in _HE_YEARS.finditer(text or ""):
        n = int(m.group(1))
        window = (text or "")[max(0, m.start() - 40): m.end() + 40]
        if n <= MAX_PLAUSIBLE_YEARS and "ניסיון" in window:
            found.append(n)
    return max(found) if found else None


_EXP_LEVEL = re.compile(r"experience level:\s*([^\n]+)", re.IGNORECASE)
_MID_LEVEL = re.compile(r"\b(mid[- ]?level|intermediate)\b|ביניים", re.IGNORECASE)
_NON_WORD = re.compile(r"[\W_]+")


class Scorer:
    def __init__(self, profile: dict):
        self.p = profile
        sen, title, loc = profile["seniority"], profile["title"], profile["location"]
        self.reject_title = _compile_list(sen["reject_title_words"]) + _compile_list(title["reject_words"])
        self.reject_levels = [s.lower() for s in sen.get("reject_experience_levels", [])]
        self.senior = _compile_list(sen["senior_title_words"])
        self.title_kw = _compile_weights(title["keywords"])
        self.generic_kw = _compile_weights(title.get("generic_keywords"))
        self.title_pen = _compile_weights(title.get("penalty_words"))
        self.skills = _compile_weights(profile["skills"]["keywords"])
        self.tiers = [(t["name"], int(t["bonus"]), _compile_list(t["places"])) for t in loc["tiers"]]
        self.notify_tiers = set(loc.get("notify_tiers") or [])
        self.israel = _compile_list(loc["israel_words"])
        self.remote = _compile_list(loc["remote_words"])
        self.remote_ok = _compile_list(loc["remote_ok_regions"])

    def in_notify_region(self, job: Job) -> bool:
        """True if Telegram notifications should be sent for this job's location."""
        if not self.notify_tiers:
            return True
        loc = job.location or ""
        for name, _, places in self.tiers:
            if name in self.notify_tiers and _first_hit(loc, places):
                return True
        return False

    # ---------------------------------------------------------------- location
    def location(self, job: Job) -> tuple[int | None, str]:
        """(bonus, label). bonus None => location not acceptable."""
        loc = job.location or ""
        for name, bonus, places in self.tiers:
            if _first_hit(loc, places):
                return bonus, name
        if _first_hit(loc, self.israel):
            return int(self.p["location"]["israel_generic_bonus"]), "israel"
        is_remote = job.remote or _first_hit(loc, self.remote) is not None
        if is_remote:
            if _first_hit(loc, self.remote_ok):
                return int(self.p["location"]["remote_bonus"]), "remote"
            leftover = loc
            for _, pat in self.remote:
                leftover = pat.sub("", leftover)
            if not _NON_WORD.sub("", leftover):   # just "Remote", region unspecified
                return 0, "remote (region not stated)"
        return None, f"location '{loc or 'unknown'}' not in Israel/remote"

    # ---------------------------------------------------------------- main
    def score(self, job: Job) -> ScoreResult:
        sen, th = self.p["seniority"], self.p["thresholds"]
        title = job.title or ""

        def reject(why: str) -> ScoreResult:
            return ScoreResult(0, "reject", [why])

        if hit := _first_hit(title, self.reject_title):
            if not (hit in ("junior", "jr", "ג'וניור") and _MID_LEVEL.search(title)):
                return reject(f"title contains '{hit}'")

        m = _EXP_LEVEL.search(job.description or "")
        if m and m.group(1).strip().lower() in self.reject_levels:
            if not _MID_LEVEL.search(title):
                return reject(f"experience level '{m.group(1).strip()}'")

        loc_bonus, loc_label = self.location(job)
        if loc_bonus is None:
            return reject(loc_label)

        years = required_years(job.description)
        is_senior = _first_hit(title, self.senior) is not None
        if years is not None and years >= int(sen["reject_min_years"]):
            return reject(f"requires {years}+ years")
        if is_senior and years is not None and years > int(sen["senior_max_years"]):
            return reject(f"Senior requiring {years} years (> {sen['senior_max_years']})")

        reasons = []
        role_hits = [(k, w) for k, w, p in self.title_kw if p.search(title)]
        generic_hits = [(k, w) for k, w, p in self.generic_kw if p.search(title)]
        title_score = min(sum(w for _, w in role_hits + generic_hits), int(self.p["title"]["cap"]))
        if role_hits or generic_hits:
            reasons.append("title: " + ", ".join(k for k, _ in role_hits + generic_hits))

        text = job.description or ""
        skill_hits = [(k, w) for k, w, p in self.skills if p.search(text)]
        skill_score = min(sum(w for _, w in skill_hits), int(self.p["skills"]["cap"]))
        if skill_hits:
            reasons.append("skills: " + ", ".join(k for k, _ in skill_hits))

        penalty = sum(w for _, w, p in self.title_pen if p.search(title))
        if penalty:
            reasons.append(f"title penalty -{penalty}")
        if is_senior and years is None:
            penalty += int(sen["senior_unknown_years_penalty"])
            reasons.append("senior, years not stated")
        if years is not None:
            reasons.append(f"{years} yrs required")
        reasons.append(f"location: {loc_label} (+{loc_bonus})")

        score = title_score + skill_score + loc_bonus - penalty
        if score >= int(th["match"]) and role_hits:
            status = "match"
        elif score >= int(th["borderline"]):
            status = "borderline"
        else:
            status = "reject"
        return ScoreResult(score, status, reasons)
