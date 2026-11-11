"""Load and validate the grounding corpus.

Each artwork is one JSON file in ``data/works/``. A work has four description
layers (orientation, composition, material, context); a layer is a list of
stops; a stop is a list of short segments, each written in Chinese and English.

The rule this module exists to enforce: a segment is only ever served as
*verified* if it cites a source listed in the same file. A segment that claims
to be verified without one is served as unverified and reported as a problem,
because a confidently wrong description is worse than silence.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path

LANGS = ("zh", "en")
FORMATS = ("handscroll", "hanging_scroll", "calligraphy", "contemporary")
LAYER_KEYS = ("orientation", "composition", "material", "context")
# Format-specific ways of delivering a layer.
LAYER_MODES = {
    "composition": ("traversal", "reading_path"),
    "material": ("brushwork",),
    "context": ("provenance",),
}
STATUSES = ("verified", "inferred")
SOURCE_KINDS = ("catalogue", "wall_label", "audio_guide", "curator_interview", "publication")
CATALOGUE_KEYS = ("artist", "period", "date", "medium", "dimensions", "collection", "credit", "accession")

# Project success target: share of claims that can be checked against a source.
VERIFIED_TARGET = 0.95


@dataclass(frozen=True)
class Problem:
    """Something wrong with a data file. ``error`` fails the checks; ``warning`` does not."""

    work: str
    where: str
    message: str
    level: str = "error"

    def __str__(self) -> str:
        return f"[{self.level}] {self.work}: {self.where}: {self.message}"


class _Invalid(Exception):
    """Raised when a file is too broken to serve at all."""


def image_size(path: Path) -> tuple[int, int]:
    """Return (width, height) of a JPEG or PNG without needing an imaging library."""
    with path.open("rb") as f:
        head = f.read(24)
        if head.startswith(b"\x89PNG\r\n\x1a\n"):
            width, height = struct.unpack(">II", head[16:24])
            return width, height
        if head[:2] != b"\xff\xd8":
            raise ValueError(f"{path.name} is not a JPEG or PNG")
        f.seek(2)
        while True:
            byte = f.read(1)
            if not byte:
                break
            if byte != b"\xff":
                continue
            marker = f.read(1)
            while marker == b"\xff":  # fill bytes before a marker
                marker = f.read(1)
            if not marker:
                break
            code = marker[0]
            if code == 0x00 or code == 0x01 or 0xD0 <= code <= 0xD9:
                continue  # markers without a length field
            (length,) = struct.unpack(">H", f.read(2))
            if 0xC0 <= code <= 0xCF and code not in (0xC4, 0xC8, 0xCC):
                f.read(1)  # sample precision
                height, width = struct.unpack(">HH", f.read(4))
                return width, height
            f.seek(length - 2, 1)
    raise ValueError(f"could not read the size of {path.name}")


class Corpus:
    """All works that loaded, plus every problem found while loading."""

    def __init__(self, works: list[dict], problems: list[Problem]):
        self.works = sorted(works, key=lambda w: w["code"])
        self.problems = problems
        self._by_code = {w["code"]: w for w in self.works}

    def get(self, code: str) -> dict | None:
        return self._by_code.get(normalise_code(code))

    @property
    def errors(self) -> list[Problem]:
        return [p for p in self.problems if p.level == "error"]

    @property
    def totals(self) -> dict:
        segments = sum(w["stats"]["segments"] for w in self.works)
        verified = sum(w["stats"]["verified"] for w in self.works)
        return {
            "works": len(self.works),
            "segments": segments,
            "verified": verified,
            "share": (verified / segments) if segments else 0.0,
            "target": VERIFIED_TARGET,
        }


def normalise_code(raw: str) -> str:
    """Label numbers are two digits: a visitor typing '1' means work '01'."""
    digits = "".join(ch for ch in str(raw).strip() if ch.isdigit())
    if not digits or len(digits) > 4:
        return ""
    return digits.zfill(2)


def load_corpus(data_dir: Path, static_dir: Path) -> Corpus:
    works: list[dict] = []
    problems: list[Problem] = []
    for path in sorted(Path(data_dir).glob("*.json")):
        name = path.stem
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(Problem(name, path.name, f"cannot be read as JSON ({exc})"))
            continue
        try:
            works.append(_load_work(name, raw, Path(static_dir), problems))
        except _Invalid as exc:
            problems.append(Problem(name, path.name, f"not loaded: {exc}"))

    seen: dict[str, str] = {}
    unique: list[dict] = []
    for work in works:
        for key in ("code", "id"):
            marker = f"{key}:{work[key]}"
            if marker in seen:
                problems.append(
                    Problem(work["file"], key, f"'{work[key]}' is already used by {seen[marker]}; work skipped")
                )
                break
            seen[marker] = work["file"]
        else:
            unique.append(work)
    return Corpus(unique, problems)


# --- validation of a single file ------------------------------------------------


def _text(value, where: str) -> dict:
    """A piece of text must exist in both languages."""
    if not isinstance(value, dict):
        raise _Invalid(f"{where} must give text as {{'zh': …, 'en': …}}")
    out = {}
    for lang in LANGS:
        text = value.get(lang)
        if not isinstance(text, str) or not text.strip():
            raise _Invalid(f"{where} is missing its '{lang}' text")
        out[lang] = " ".join(text.split())
    return out


def _load_work(name: str, raw, static_dir: Path, problems: list[Problem]) -> dict:
    if not isinstance(raw, dict):
        raise _Invalid("the file must contain one JSON object")

    def problem(where: str, message: str, level: str = "error") -> None:
        problems.append(Problem(name, where, message, level))

    work_id = raw.get("id")
    if not isinstance(work_id, str) or not work_id.strip():
        raise _Invalid("'id' is required")
    code = normalise_code(raw.get("code", ""))
    if not code:
        raise _Invalid("'code' must be the number printed on the label, e.g. \"01\"")
    if raw.get("format") not in FORMATS:
        raise _Invalid(f"'format' must be one of {', '.join(FORMATS)}")

    work = {
        "file": name,
        "id": work_id.strip(),
        "code": code,
        "format": raw["format"],
        "title": _text(raw.get("title"), "title"),
        "artist": _text(raw.get("artist"), "artist"),
        "date": _text(raw.get("date"), "date"),
    }

    # Sources: what a verified segment is allowed to cite.
    sources: dict[str, dict] = {}
    for index, item in enumerate(raw.get("sources") or [], start=1):
        where = f"sources[{index}]"
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise _Invalid(f"{where} needs an 'id'")
        if item["id"] in sources:
            raise _Invalid(f"{where} repeats the id '{item['id']}'")
        if item.get("kind") not in SOURCE_KINDS:
            raise _Invalid(f"{where} 'kind' must be one of {', '.join(SOURCE_KINDS)}")
        url = item.get("url")
        if url is not None and not (isinstance(url, str) and url.startswith(("https://", "http://"))):
            raise _Invalid(f"{where} 'url' must be a web address")
        sources[item["id"]] = {
            "id": item["id"],
            "n": index,
            "kind": item["kind"],
            "title": _text(item.get("title"), f"{where}.title"),
            "note": _text(item["note"], f"{where}.note") if item.get("note") else None,
            "url": url,
            "accessed": item.get("accessed"),
            "license": item.get("license"),
        }
    work["sources"] = list(sources.values())

    # Images: the files must exist; their size is read from the file itself.
    images: dict[str, dict] = {}
    for key, item in (raw.get("images") or {}).items():
        where = f"images.{key}"
        if not isinstance(item, dict) or not isinstance(item.get("src"), str):
            raise _Invalid(f"{where} needs a 'src'")
        file = static_dir / item["src"]
        if ".." in Path(item["src"]).parts or not file.is_file():
            raise _Invalid(f"{where}: no file at static/{item['src']}")
        try:
            width, height = image_size(file)
        except (ValueError, struct.error) as exc:
            raise _Invalid(f"{where}: {exc}") from exc
        images[key] = {
            "key": key,
            "src": item["src"],
            "width": width,
            "height": height,
            "alt": _text(item.get("alt"), f"{where}.alt"),
            "credit": _text(item["credit"], f"{where}.credit") if item.get("credit") else None,
        }
    work["images"] = images
    default_image = next(iter(images), None)

    # Catalogue facts, all drawn from one cited record.
    catalogue = raw.get("catalogue")
    work["catalogue"] = None
    if catalogue is not None:
        if not isinstance(catalogue, dict):
            raise _Invalid("'catalogue' must be an object")
        source = sources.get(catalogue.get("source"))
        if source is None:
            problem("catalogue", "cites no known source, so its facts are shown as unverified")
        fields = []
        for index, item in enumerate(catalogue.get("fields") or [], start=1):
            where = f"catalogue.fields[{index}]"
            if not isinstance(item, dict) or item.get("key") not in CATALOGUE_KEYS:
                raise _Invalid(f"{where} 'key' must be one of {', '.join(CATALOGUE_KEYS)}")
            fields.append({"key": item["key"], "value": _text(item, where)})
        work["catalogue"] = {"source": source, "fields": fields}

    # The four layers, always in the same order.
    layers_raw = raw.get("layers")
    if not isinstance(layers_raw, list) or [
        layer.get("key") if isinstance(layer, dict) else None for layer in layers_raw
    ] != list(LAYER_KEYS):
        raise _Invalid(f"'layers' must be exactly these four, in order: {', '.join(LAYER_KEYS)}")

    layers = []
    total = verified = 0
    for layer_n, layer_raw in enumerate(layers_raw, start=1):
        key = layer_raw["key"]
        mode = layer_raw.get("mode")
        if mode is not None and mode not in LAYER_MODES.get(key, ()):
            raise _Invalid(f"layer '{key}' cannot use mode '{mode}'")
        stops_raw = layer_raw.get("stops")
        if not isinstance(stops_raw, list) or not stops_raw:
            raise _Invalid(f"layer '{key}' needs at least one stop")
        stops = []
        for stop_n, stop_raw in enumerate(stops_raw, start=1):
            where = f"{key}.stops[{stop_n}]"
            if not isinstance(stop_raw, dict):
                raise _Invalid(f"{where} must be an object")
            image_key = stop_raw.get("image", default_image)
            if image_key is not None and image_key not in images:
                raise _Invalid(f"{where} points to an unknown image '{image_key}'")
            region = stop_raw.get("region")
            if region is not None:
                ok = (
                    isinstance(region, list)
                    and len(region) == 4
                    and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in region)
                    and 0 <= region[0] < region[2] <= 1
                    and 0 <= region[1] < region[3] <= 1
                )
                if not ok:
                    raise _Invalid(f"{where} 'region' must be [left, top, right, bottom] as fractions between 0 and 1")
                if image_key is None:
                    raise _Invalid(f"{where} has a region but the work has no image")
            segments_raw = stop_raw.get("segments")
            if not isinstance(segments_raw, list) or not segments_raw:
                raise _Invalid(f"{where} needs at least one segment")
            segments = []
            for seg_n, seg_raw in enumerate(segments_raw, start=1):
                seg_where = f"{where}.segments[{seg_n}]"
                if not isinstance(seg_raw, dict):
                    raise _Invalid(f"{seg_where} must be an object")
                status = seg_raw.get("status")
                if status not in STATUSES:
                    raise _Invalid(f"{seg_where} 'status' must be 'verified' or 'inferred'")
                source = sources.get(seg_raw.get("source"))
                if status == "verified" and source is None:
                    # The grounding rule. Serve it as unverified and make the checks fail.
                    problem(seg_where, "claims to be verified but cites no known source; served as unverified")
                    status = "inferred"
                elif status == "inferred" and seg_raw.get("source"):
                    problem(
                        seg_where,
                        "cites a source but is marked 'inferred'; mark it verified or drop the source",
                        "warning",
                    )
                    source = None
                segments.append({"text": _text(seg_raw, seg_where), "status": status, "source": source})
                total += 1
                verified += status == "verified"
            stops.append(
                {
                    "n": stop_n,
                    "label": _text(stop_raw["label"], f"{where}.label") if stop_raw.get("label") else None,
                    "image": image_key,
                    "region": region,
                    "segments": segments,
                }
            )
        if len(stops) > 1 and any(stop["label"] is None for stop in stops):
            raise _Invalid(f"layer '{key}' has several stops, so each one needs a 'label'")
        if mode == "traversal":
            # A handscroll is unrolled from right to left, so its sections must run that way too.
            for earlier, later in zip(stops, stops[1:], strict=False):
                if (
                    earlier["region"]
                    and later["region"]
                    and earlier["image"] == later["image"]
                    and later["region"][2] > earlier["region"][2]
                ):
                    problem(
                        f"{key}.stops[{later['n']}]",
                        "lies to the right of the section before it; a traversal runs from right to left",
                        "warning",
                    )
        layers.append({"n": layer_n, "key": key, "mode": mode, "stops": stops})

    work["layers"] = layers
    work["stats"] = {
        "segments": total,
        "verified": verified,
        "inferred": total - verified,
        "share": (verified / total) if total else 0.0,
        "sources": len(sources),
        "meets_target": total > 0 and verified / total >= VERIFIED_TARGET,
    }
    if not sources:
        problem("sources", "no sources yet: nothing in this work can be verified", "warning")
    return work


# --- command line: `python -m kanjian.corpus` -------------------------------------


def main_cli(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Audit the Kànjiàn corpus.")
    parser.add_argument("--data", default="data/works", help="folder of work files")
    parser.add_argument("--static", default="static", help="folder holding the images")
    parser.add_argument(
        "--strict",
        action="store_true",
        help=f"also fail if any work is below the {VERIFIED_TARGET:.0%} verified target",
    )
    args = parser.parse_args(argv)

    corpus = load_corpus(Path(args.data), Path(args.static))
    print(f"{'No.':<5}{'Work':<34}{'Format':<16}{'Segments':>9}{'Verified':>10}{'Share':>8}  Target")
    for work in corpus.works:
        stats = work["stats"]
        print(
            f"{work['code']:<5}{work['title']['en'][:32]:<34}{work['format']:<16}"
            f"{stats['segments']:>9}{stats['verified']:>10}{stats['share']:>8.0%}  "
            f"{'met' if stats['meets_target'] else 'below'}"
        )
    totals = corpus.totals
    print(
        f"\n{totals['works']} works, {totals['segments']} segments, "
        f"{totals['share']:.0%} verified (target {VERIFIED_TARGET:.0%})."
    )
    for item in corpus.problems:
        print(item)

    failed = bool(corpus.errors) or not corpus.works
    if args.strict and any(not w["stats"]["meets_target"] for w in corpus.works):
        failed = True
    if failed:
        print("\nCorpus audit FAILED.")
        return 1
    print("\nCorpus audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
