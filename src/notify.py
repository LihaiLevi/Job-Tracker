"""Telegram sender. Needs env vars TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.

API: https://core.telegram.org/bots/api#sendmessage
"""
from __future__ import annotations

import html
import logging
import os
import time

from . import net
from .models import Job, ScoreResult

log = logging.getLogger(__name__)
MAX_LEN = 4000          # Telegram limit is 4096 chars per message


def format_job(job: Job, result: ScoreResult) -> str:
    e = html.escape
    return (f"<b>{e(job.title)}</b>\n"
            f"🏢 {e(job.company)} · 📍 {e(job.location or '?')}\n"
            f"⭐ {result.score} — {e('; '.join(result.reasons[:3]))}\n"
            f"<a href=\"{e(job.url, quote=True)}\">Open posting</a>")


def batch_messages(blocks: list[str]) -> list[str]:
    messages, cur = [], ""
    for b in blocks:
        if cur and len(cur) + len(b) + 2 > MAX_LEN:
            messages.append(cur)
            cur = ""
        cur = f"{cur}\n\n{b}" if cur else b
    if cur:
        messages.append(cur)
    return messages


def send(items: list[tuple[Job, ScoreResult]]) -> bool:
    """Send all items. Returns True on success (so the caller can mark them notified)."""
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        log.warning("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set; skipping notifications")
        return False
    header = f"🔔 {len(items)} new job match{'es' if len(items) != 1 else ''}"
    messages = batch_messages([header] + [format_job(j, r) for j, r in items])
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for text in messages:
        resp = net.post_json(url, {"chat_id": chat, "text": text, "parse_mode": "HTML",
                                   "link_preview_options": {"is_disabled": True}})
        if not resp.get("ok"):
            raise RuntimeError(f"Telegram error: {resp}")
        time.sleep(1)   # stay well under Telegram's per-chat rate limit
    return True
