"""The Metropolitan Museum of Art: Open Access API (CC0). No key needed.

https://metmuseum.github.io/ — records carry catalogue data but no label text.
"""

from __future__ import annotations

import urllib.parse

from kanjian import periods
from kanjian.importers.common import Fetcher, ImportFailed, clean, format_from_en, pair, today

API = "https://collectionapi.metmuseum.org/public/collection/v1"
ASIAN_ART = 6
CATEGORY = {"paintings": "painting", "calligraphy": "calligraphy"}


def build_record(obj: dict) -> dict:
    if not obj.get("isPublicDomain"):
        raise ImportFailed("this Met object is not Open Access (public domain), so its image cannot be reused")
    if not obj.get("primaryImage"):
        raise ImportFailed("this Met object has no Open Access image")
    classification = (obj.get("classification") or "").lower()
    period = periods.period_from_en(" ".join(filter(None, [obj.get("period"), obj.get("dynasty")])))
    bio = obj.get("artistDisplayBio") or ""
    dims = (obj.get("dimensions") or "").replace("\r\n", "\n")
    return {
        "id": f"met-{obj['objectID']}",
        "museum": "met",
        "record": {
            "id": str(obj["objectID"]),
            "object_number": obj.get("accessionNumber", ""),
            "url": obj.get("objectURL") or f"https://www.metmuseum.org/art/collection/search/{obj['objectID']}",
            "accessed": today(),
        },
        "category": next((v for k, v in CATEGORY.items() if k in classification), "other"),
        "format": format_from_en(obj.get("medium", "")),
        "period": period,
        "year": obj.get("objectBeginDate") or periods.start_year(period),
        "title": pair("", clean(obj.get("title"))),
        "artist": pair("", clean(obj.get("artistDisplayName")) + (f" ({bio})" if bio else "")),
        "date": pair("", clean(obj.get("objectDate"))),
        "medium": pair("", clean(obj.get("medium"))),
        "dimensions": pair("", "; ".join(line.strip() for line in dims.splitlines() if line.strip())),
        "museum_text": pair(),
        "credit_line": pair("", clean(obj.get("creditLine"))),
    }


def fetch(fetcher: Fetcher, ident: str) -> tuple[dict, bytes]:
    """``ident`` is the Met object ID, the number at the end of a collection page URL."""
    if not ident.isdigit():
        raise ImportFailed(f"'{ident}' is not a Met object ID (the number in /art/collection/search/<number>)")
    obj = fetcher.json(f"{API}/objects/{ident}")
    if not obj or "objectID" not in obj:
        raise ImportFailed(f"the Met has no object {ident}")
    record = build_record(obj)
    raw = fetcher.bytes(obj["primaryImage"], timeout=300)
    return record, raw


def search(fetcher: Fetcher, query: str, limit: int = 12) -> list[tuple[str, str]]:
    params = urllib.parse.urlencode({"q": query, "hasImages": "true", "departmentId": ASIAN_ART})
    ids = (fetcher.json(f"{API}/search?{params}") or {}).get("objectIDs") or []
    results = []
    for object_id in ids[: limit * 3]:
        obj = fetcher.json(f"{API}/objects/{object_id}")
        if obj.get("isPublicDomain") and "China" in (obj.get("culture") or ""):
            results.append((str(object_id), f"{obj.get('title')} · {obj.get('artistDisplayName') or '—'}"))
        if len(results) >= limit:
            break
    return results
