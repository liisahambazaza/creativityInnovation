"""Load and check the collection: one JSON file per work in ``data/works``.

A work file has two kinds of content, kept apart on purpose:

* **museum data**: title, artist, period, medium, dimensions, the museum's own text and
  the image, written by the importers (``python -m kanjian.importers``) from open data;
* **editorial**: what this project adds: a short introduction and things to look for
  (drafted with AI help and not yet reviewed by a curator, and labelled that way on the
  page), an image description, image choices, and ``overrides`` that correct or translate
  museum fields. Importing again never touches it.
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

    work["intro"] = _pair(editorial.get("intro"))
    work["look_for"] = [_pair(item) for item in editorial.get("look_for") or [] if any(_pair(item).values())]
    work["alt"] = _pair(editorial.get("alt"))
    for lang in LANGS:
        if not work["intro"][lang]:
            problem(f"no introduction in {lang} yet", "warning")
        if not work["alt"][lang]:
            problem(f"no image description (alt) in {lang} yet", "warning")
    if not any(work["museum_text"].values()):
        problem("the museum record has no description text", "warning")
    return work


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
    print(f"{'Work':<13}{'Museum':<6}{'Period':<15}{'Title':<44}{'Intro':<7}{'Look':<6}Museum text")
    for w in collection.works:
        langs = "+".join(lang for lang in LANGS if w["museum_text"][lang]) or "none"
        intro = "+".join(lang for lang in LANGS if w["intro"][lang]) or "none"
        title = (w["title"]["en"] or w["title"]["zh"])[:42]
        print(f"{w['id']:<13}{w['museum']:<6}{str(w['period']):<15}{title:<44}{intro:<7}{len(w['look_for']):<6}{langs}")
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
