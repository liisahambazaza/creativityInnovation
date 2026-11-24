"""Load and check the collection: one JSON file per work in ``data/works``.

A work file has two kinds of content, kept apart on purpose:

* **museum data**: title, artist, period, medium, dimensions, the museum's own text and
  the image, written by the importers (``python -m kanjian.importers``) from open data;
* **editorial**: what this project adds: a short introduction, things to look for and
  what historians and critics have said, every statement citing its sources (drafted
  with AI help, checked against those sources, not yet reviewed by a curator, and
  labelled that way on the page); an image description, image choices, and
  ``overrides`` that correct or translate museum fields. Importing never touches it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from kanjian import periods
from kanjian.museums import MUSEUMS

LANGS = ("zh", "en")
CATEGORIES = ("painting", "calligraphy", "other")
FORMATS = ("handscroll", "hanging_scroll", "album_leaf", "album", "fan", "other")
TEXT_FIELDS = ("title", "artist", "date", "medium", "dimensions", "museum_text", "credit_line")
# Where a statement's support comes from. "museum" and "image" need no entry in the work's
# source list: they are the work's own museum record and the image shown on its page.
SOURCE_KINDS = ("museum", "inscription", "scholarship", "museum_essay", "encyclopedia", "image")
BUILT_IN_SOURCES = ("museum", "image")


@dataclass(frozen=True)
class Problem:
    """Something wrong with a work file. ``error`` fails the checks; ``warning`` does not."""

    work: str
    message: str
    level: str = "error"

    def __str__(self) -> str:
        return f"[{self.level}] {self.work}: {self.message}"


class Collection:
    def __init__(self, works: list[dict], problems: list[Problem]):
        self.works = sorted(works, key=lambda w: (w["sort_year"], w["id"]))
        self.problems = problems
        self._by_id = {w["id"]: w for w in self.works}

    def get(self, work_id: str) -> dict | None:
        return self._by_id.get(work_id)

    @property
    def errors(self) -> list[Problem]:
        return [p for p in self.problems if p.level == "error"]

    def neighbours(self, work_id: str) -> tuple[dict | None, dict | None]:
        ids = [w["id"] for w in self.works]
        i = ids.index(work_id)
        return (self.works[i - 1] if i > 0 else None, self.works[i + 1] if i + 1 < len(ids) else None)

    def by_era(self, category: str | None = None) -> list[tuple[str, list[dict]]]:
        groups = []
        for era in periods.ERAS:
            works = [w for w in self.works if w["era"] == era and (not category or w["category"] == category)]
            if works:
                groups.append((era, works))
        return groups


def _pair(value) -> dict:
    value = value if isinstance(value, dict) else {}
    return {lang: str(value.get(lang) or "").strip() for lang in LANGS}


def load_work(raw: dict, name: str, static_dir: Path, problems: list[Problem]) -> dict | None:
    def problem(message: str, level: str = "error") -> None:
        problems.append(Problem(name, message, level))

    if raw.get("id") != name:
        problem(f"its id ({raw.get('id')!r}) should match the file name ({name!r})")
        return None
    museum = raw.get("museum")
    if museum not in MUSEUMS:
        problem(f"unknown museum {museum!r} (known: {', '.join(MUSEUMS)})")
        return None
    record = raw.get("record") or {}
    if not record.get("url"):
        problem("no link to the museum's record (record.url)")
        return None

    editorial = raw.get("editorial") or {}
    overrides = editorial.get("overrides") or {}
    work: dict = {"id": name, "museum": museum, "record": record}
    for field in TEXT_FIELDS:
        value = _pair(raw.get(field))
        for lang, text in _pair(overrides.get(field)).items():
            if text:
                value[lang] = text
        work[field] = value
    if not (work["title"]["zh"] or work["title"]["en"]):
        problem("no title in either language")
        return None

    work["category"] = overrides.get("category") or raw.get("category")
    if work["category"] not in CATEGORIES:
        problem(f"category {work['category']!r} should be one of {', '.join(CATEGORIES)}", "warning")
        work["category"] = "other"
    work["format"] = overrides.get("format") or raw.get("format")
    if work["format"] not in FORMATS:
        problem(f"format {work['format']!r} should be one of {', '.join(FORMATS)}", "warning")
        work["format"] = "other"
    work["period"] = overrides.get("period") or raw.get("period")
    if work["period"] and work["period"] not in periods.PERIODS:
        problem(f"unknown period {work['period']!r}", "warning")
        work["period"] = None
    work["era"] = periods.era_of(work["period"])
    year = overrides.get("year", raw.get("year"))
    work["year"] = year if isinstance(year, int) else None
    work["sort_year"] = work["year"] or periods.start_year(work["period"]) or 9999

    image = raw.get("image") or {}
    for key in ("src", "thumb"):
        if not image.get(key) or not (Path(static_dir) / image[key]).is_file():
            problem(f"image file {image.get(key)!r} is missing; import the work again")
            return None
    work["image"] = {
        "src": image["src"],
        "thumb": image["thumb"],
        "width": int(image.get("width") or 0),
        "height": int(image.get("height") or 0),
        "note": str((editorial.get("image_choice") or {}).get("note") or ""),
    }

    work["alt"] = _pair(editorial.get("alt"))
    for lang in LANGS:
        if not work["alt"][lang]:
            problem(f"no image description (alt) in {lang} yet", "warning")
    if not any(work["museum_text"].values()):
        problem("the museum record has no description text", "warning")
    _load_editorial_text(work, editorial, problem)
    return work


def _statement(raw, where: str, sources: dict, problem) -> dict | None:
    """One sentence of editorial text with the sources that support it.

    The rule this enforces: nothing we write is shown without saying where it comes from.
    A statement with no source, or citing a source that is not listed, fails the check.
    """
    if not isinstance(raw, dict):
        return None
    text = _pair(raw)
    if not any(text.values()):
        return None
    for lang in LANGS:
        if not text[lang]:
            problem(f"{where} has no {lang} text", "warning")
    cited = [str(s) for s in raw.get("sources") or []]
    if not cited:
        problem(f"{where} cites no source: check it against a reliable source, or remove it")
    unknown = [s for s in cited if s not in sources and s not in BUILT_IN_SOURCES]
    if unknown:
        problem(f"{where} cites unknown source(s) {', '.join(unknown)}")
    return {**text, "sources": [s for s in cited if s not in unknown]}


def _load_editorial_text(work: dict, editorial: dict, problem) -> None:
    sources: dict[str, dict] = {}
    for key, raw in (editorial.get("sources") or {}).items():
        raw = raw or {}
        kind = raw.get("kind")
        if kind not in SOURCE_KINDS:
            problem(f"source {key!r} has kind {kind!r}; use one of {', '.join(SOURCE_KINDS)}")
        if not raw.get("title"):
            problem(f"source {key!r} has no title")
        if kind != "inscription" and not str(raw.get("url", "")).startswith("https://"):
            problem(f"source {key!r} needs an https:// link so readers can check it")
        sources[key] = {
            "key": key,
            "kind": kind or "museum_essay",
            "title": str(raw.get("title") or key),
            "author": str(raw.get("author") or ""),
            "publisher": str(raw.get("publisher") or ""),
            "url": str(raw.get("url") or ""),
            "accessed": str(raw.get("accessed") or ""),
        }

    intro = editorial.get("intro")
    if isinstance(intro, dict):  # the first format: one paragraph, no sources
        intro = [intro]
    work["intro"] = [
        s
        for i, raw in enumerate(intro or [])
        if (s := _statement(raw, f"introduction sentence {i + 1}", sources, problem))
    ]
    work["look_for"] = [
        s
        for i, raw in enumerate(editorial.get("look_for") or [])
        if (s := _statement(raw, f"'look closer' item {i + 1}", sources, problem))
    ]
    views = []
    for i, raw in enumerate(editorial.get("views") or []):
        view = _statement(raw, f"view {i + 1}", sources, problem)
        if view is None:
            continue
        view["who"] = _pair(raw.get("who"))
        view["about"] = _pair(raw.get("about"))
        view["quote"] = _pair(raw.get("quote"))
        if not any(view["who"].values()):
            problem(f"view {i + 1} does not say whose view it is")
        views.append(view)
    work["views"] = views

    # Number the sources in the order a reader meets them on the page.
    order: list[str] = []
    for statement in [*work["intro"], *work["look_for"], *work["views"]]:
        for key in statement["sources"]:
            if key not in order:
                order.append(key)
    numbered = []
    for n, key in enumerate(order, start=1):
        entry = sources.get(key) or {"key": key, "kind": key}
        numbered.append({**entry, "n": n})
    work["sources"] = numbered
    work["source_numbers"] = {entry["key"]: entry["n"] for entry in numbered}
    for key in sources:
        if key not in order:
            problem(f"source {key!r} is listed but nothing cites it", "warning")

    checked = editorial.get("checked") or {}
    work["checked"] = {"on": str(checked.get("on") or ""), "note": _pair(checked.get("note"))}
    if (work["intro"] or work["look_for"] or work["views"]) and not work["checked"]["on"]:
        problem("the editorial text has not been checked against its sources yet (editorial.checked.on)")
    for lang in LANGS:
        if not any(s[lang] for s in work["intro"]):
            problem(f"no introduction in {lang} yet", "warning")


def load_collection(data_dir: Path, static_dir: Path) -> Collection:
    works, problems = [], []
    for path in sorted(Path(data_dir).glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(Problem(path.stem, f"cannot be read as JSON ({exc})"))
            continue
        work = load_work(raw, path.stem, Path(static_dir), problems)
        if work:
            works.append(work)
    return Collection(works, problems)


# --- command line: `python -m kanjian.works` ------------------------------------------


def main_cli(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Check the collection in data/works.")
    parser.add_argument("--data", default="data/works")
    parser.add_argument("--static", default="static")
    args = parser.parse_args(argv)

    collection = load_collection(Path(args.data), Path(args.static))
    print(
        f"{'Work':<13}{'Museum':<6}{'Period':<15}{'Title':<40}{'Intro':<7}{'Look':<5}{'Views':<6}{'Srcs':<5}Museum text"
    )
    for w in collection.works:
        langs = "+".join(lang for lang in LANGS if w["museum_text"][lang]) or "none"
        intro = "+".join(lang for lang in LANGS if any(st[lang] for st in w["intro"])) or "none"
        title = (w["title"]["en"] or w["title"]["zh"])[:38]
        print(
            f"{w['id']:<13}{w['museum']:<6}{str(w['period']):<15}{title:<40}{intro:<7}"
            f"{len(w['look_for']):<5}{len(w['views']):<6}{len(w['sources']):<5}{langs}"
        )
    print(f"\n{len(collection.works)} works.")
    for item in collection.problems:
        print(item)
    if collection.errors or not collection.works:
        print("\nCollection check FAILED.")
        return 1
    print("\nCollection check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
