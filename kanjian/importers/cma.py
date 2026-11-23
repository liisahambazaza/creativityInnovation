"""The Cleveland Museum of Art: Open Access API (CC0). No key needed.

https://openaccess-api.clevelandart.org/ — records include the museum's own description.
"""

from __future__ import annotations

import urllib.parse

from kanjian import periods
from kanjian.importers.common import Fetcher, ImportFailed, clean, format_from_en, pair, today

API = "https://openaccess-api.clevelandart.org/api/artworks"
CATEGORY = {"painting": "painting", "calligraphy": "calligraphy"}


def build_record(art: dict) -> dict:
    if art.get("share_license_status") != "CC0":
        raise ImportFailed("this Cleveland object is not CC0, so its image cannot be reused")
    images = art.get("images") or {}
    best = images.get("print") or images.get("web") or {}
    if not best.get("url"):
        raise ImportFailed("this Cleveland object has no Open Access image")
    creator = (art.get("creators") or [{}])[0].get("description") or ""
    culture = " ".join(art.get("culture") or [])
    period = periods.period_from_en(culture)
    texts = [clean(art.get("description")), clean(art.get("did_you_know"))]
    return {
        "id": f"cma-{art['id']}",
        "museum": "cma",
        "record": {
            "id": str(art["id"]),
            "object_number": art.get("accession_number", ""),
            "url": art.get("url") or f"https://clevelandart.org/art/{art.get('accession_number')}",
            "accessed": today(),
        },
        "category": CATEGORY.get((art.get("type") or "").lower(), "other"),
        "format": format_from_en(art.get("technique", "")),
        "period": period,
        "year": art.get("creation_date_earliest") or periods.start_year(period),
        "title": pair(clean(art.get("title_in_original_language")), clean(art.get("title"))),
        "artist": pair("", clean(creator)),
        "date": pair("", clean(art.get("creation_date"))),
        "medium": pair("", clean(art.get("technique"))),
        "dimensions": pair("", clean(art.get("measurements")).replace("\n", "; ")),
        "museum_text": pair("", "\n\n".join(t for t in texts if t)),
        "credit_line": pair("", clean(art.get("creditline"))),
        "_image": best["url"],
    }


def fetch(fetcher: Fetcher, ident: str) -> tuple[dict, bytes]:
    """``ident`` is the Cleveland accession number (e.g. 1953.126) or its record ID."""
    data = (fetcher.json(f"{API}/{urllib.parse.quote(ident)}") or {}).get("data")
    if not data:
        raise ImportFailed(f"Cleveland has no artwork '{ident}'")
    record = build_record(data)
    raw = fetcher.bytes(record.pop("_image"), timeout=300)
    return record, raw


def search(fetcher: Fetcher, query: str, limit: int = 15) -> list[tuple[str, str]]:
    params = urllib.parse.urlencode({"q": query, "department": "Chinese Art", "cc0": 1, "has_image": 1, "limit": limit})
    found = (fetcher.json(f"{API}/?{params}") or {}).get("data") or []
    return [
        (
            a.get("accession_number", str(a["id"])),
            f"{a.get('title')} {a.get('title_in_original_language') or ''} · {a.get('type')}".strip(),
        )
        for a in found
    ]
