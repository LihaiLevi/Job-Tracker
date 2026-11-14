"""Optional Gemini second opinion for *borderline* jobs only.

Enabled when GEMINI_API_KEY is set. Model via GEMINI_MODEL (default gemini-flash-latest).
API: https://ai.google.dev/api/generate-content
"""
from __future__ import annotations

import json
import logging
import os

from . import net
from .models import Job

log = logging.getLogger(__name__)
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROFILE = """Candidate: Embedded Software Engineer, 4+ years, Tel Aviv, Israel.
Skills: C, C++ (primary), C#, Python, Java, Assembly. RTOS (VxWorks, uC/OS, Embedded Linux),
real-time systems, avionics, UAV ground control stations, mission/safety-critical software,
TCP/IP, UDP, DO-178C. Wants: embedded / real-time / firmware / embedded Linux / low-level
systems software / avionics / RTOS-BSP-driver roles, mid-level (3-6 years; "Senior" only if
<= 6 years required). Location: Israel or fully remote open to Israel."""


def enabled() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def judge(job: Job) -> str:
    """Return 'yes: <reason>' or 'no: <reason>'. Raises on API errors."""
    prompt = (f"{PROFILE}\n\nJob posting:\nTitle: {job.title}\nCompany: {job.company}\n"
              f"Location: {job.location}\nDescription:\n{job.description[:6000]}\n\n"
              "Is this job a good fit for the candidate? Answer as JSON: "
              '{"relevant": true|false, "reason": "<max 15 words>"}')
    model = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
    resp = net.post_json(
        API.format(model=model),
        {"contents": [{"parts": [{"text": prompt}]}],
         "generationConfig": {"responseMimeType": "application/json", "temperature": 0}},
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    text = resp["candidates"][0]["content"]["parts"][0]["text"]
    data = json.loads(text)
    return f"{'yes' if data.get('relevant') else 'no'}: {data.get('reason', '')}"
