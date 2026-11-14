"""Clean HTML descriptions and standardize locations."""
from __future__ import annotations

import html
import re

_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"</?(p|div|br|li|ul|ol|h[1-6]|tr)[^>]*>", re.I)
_WS = re.compile(r"[ \t\r\f\v]+")


def clean_html(text: str | None) -> str:
    """HTML (possibly entity-escaped, as Greenhouse returns it) -> plain text."""
    if not text:
        return ""
    s = html.unescape(text)          # Greenhouse double-escapes: &lt;p&gt; -> <p>
    s = _BLOCK.sub("\n", s)
    s = _TAG.sub(" ", s)
    s = html.unescape(s)
    s = _WS.sub(" ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return re.sub(r"\n{2,}", "\n", s).strip()


# Common spellings -> canonical city name. Extend freely.
_CITY_ALIASES = {
    "tlv": "Tel Aviv",
    "tel-aviv": "Tel Aviv",
    "tel aviv-yafo": "Tel Aviv",
    "tel aviv yafo": "Tel Aviv",
    "תל אביב-יפו": "Tel Aviv",   # longer alias first
    "תל אביב": "Tel Aviv",
    "herzliya pituach": "Herzliya",
    "herzelia": "Herzliya",
    "hertzliya": "Herzliya",
    "petach tikva": "Petah Tikva",
    "petah tiqva": "Petah Tikva",
    "petach tikvah": "Petah Tikva",
    "raanana": "Ra'anana",
    "ra’anana": "Ra'anana",
    "yokneam": "Yokneam",
    "yoqneam": "Yokneam",
    "yokne'am": "Yokneam",
    "rishon lezion": "Rishon LeZion",
    "rishon le zion": "Rishon LeZion",
    "modiin": "Modi'in",
    "beer sheva": "Be'er Sheva",
    "beersheba": "Be'er Sheva",
}


def normalize_location(loc: str | None) -> str:
    """Collapse whitespace and map known aliases, keeping the rest of the string."""
    if not loc:
        return ""
    s = _WS.sub(" ", loc.replace("\n", " ")).strip()
    low = s.lower()
    for alias, canon in _CITY_ALIASES.items():
        if alias in low:
            s = re.sub(re.escape(alias), canon, s, flags=re.I)
            low = s.lower()
    return s
