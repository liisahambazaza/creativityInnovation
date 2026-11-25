"""Import artworks from open museum collections into ``data/works``.

    python -m kanjian.importers search npm 谿山行旅      find record numbers
    python -m kanjian.importers add npm 1195            import one work (or several)
    python -m kanjian.importers add met 45636
    python -m kanjian.importers add cma 1953.126
    python -m kanjian.importers refresh                 re-import every work already here

Importing never overwrites what this project wrote for a work (its ``editorial`` block:
the introduction, things to look for, image description and any corrections).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from kanjian.importers import cma, met, npm
from kanjian.importers.common import DATA_DIR, IMAGE_DIR, Fetcher, ImportFailed, save_image, write_work

SOURCES = {"npm": npm, "met": met, "cma": cma}


def _existing_editorial(source: str, ident: str, data_dir: Path) -> dict:
    for path in data_dir.glob(f"{source}-*.json"):
        work = json.loads(path.read_text(encoding="utf-8"))
        if _ident_of(work).split(":")[0] == ident.split(":")[0] or work["record"].get("id") == ident:
            return work.get("editorial") or {}
    return {}


def import_one(
    source: str, ident: str, *, fetcher: Fetcher, data_dir: Path = DATA_DIR, image_dir: Path = IMAGE_DIR
) -> Path:
    """Import one work. Its editorial ``image_choice`` can pick or crop the museum image:
    ``canvas`` and ``region`` (Taipei IIIF), ``crop`` [x, y, w, h] in percent (any museum),
    ``thumb_at`` (where a wide thumbnail is centred, in percent from the left),
    or ``keep: true`` to keep the image file already in the project."""
    choice = _existing_editorial(source, ident, data_dir).get("image_choice") or {}
    if source == "npm":
        record, raw = npm.fetch(fetcher, ident, choice)
    else:
        record, raw = SOURCES[source].fetch(fetcher, ident)
    if not choice.get("keep"):
        record["image"] = save_image(
            raw,
            record["id"],
            image_dir,
            fmt=record["format"],
            crop=choice.get("crop"),
            thumb_at=choice.get("thumb_at"),
        )
    return write_work(record, data_dir)


def _ident_of(work: dict) -> str:
    rec = work["record"]
    if work["museum"] == "npm":
        return f"{rec['id']}:{rec.get('dep', 'P')}"
    if work["museum"] == "cma":
        return rec.get("object_number") or rec["id"]
    return rec["id"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m kanjian.importers", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("search", help="search a collection")
    s.add_argument("source", choices=SOURCES)
    s.add_argument("query", nargs="+")
    a = sub.add_parser("add", help="import works by their number in the collection")
    a.add_argument("source", choices=SOURCES)
    a.add_argument("ids", nargs="+")
    sub.add_parser("refresh", help="re-import every work already in data/works")
    args = parser.parse_args(argv)

    fetcher = Fetcher()
    if args.command == "search":
        try:
            results = SOURCES[args.source].search(fetcher, " ".join(args.query))
        except ImportFailed as exc:
            print(f"Search failed: {exc}", file=sys.stderr)
            return 1
        for ident, title in results:
            print(f"{ident:<14} {title}")
        if not results:
            print("Nothing found.")
        return 0

    if args.command == "add":
        jobs = [(args.source, ident) for ident in args.ids]
    else:
        jobs = []
        for path in sorted(DATA_DIR.glob("*.json")):
            work = json.loads(path.read_text(encoding="utf-8"))
            jobs.append((work["museum"], _ident_of(work)))

    failed = 0
    for source, ident in jobs:
        try:
            path = import_one(source, ident, fetcher=fetcher)
            work = json.loads(path.read_text(encoding="utf-8"))
            title = work["title"]["en"] or work["title"]["zh"]
            print(f"  ok    {source} {ident:<12} → {path.name}  ({title})")
        except ImportFailed as exc:
            failed += 1
            print(f"  FAIL  {source} {ident:<12} {exc}", file=sys.stderr)
    print(f"\n{len(jobs) - failed} imported, {failed} failed.")
    return 1 if failed else 0
