"""Shared by the museum importers: polite downloads, images, and writing work files."""

from __future__ import annotations

import datetime as _dt
import html
import io
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "works"
IMAGE_DIR = ROOT / "static" / "img" / "works"

USER_AGENT = "Kanjian-prototype/0.2 (educational open-data importer)"
PAUSE_SECONDS = 1.0  # between requests to the same museum
MAX_AREA = 3_000_000  # pixels kept for the main image: plenty for a laptop screen
MAX_SIDE = 9000
# Handscrolls are long and thin (up to 30:1): keep enough height to read them unrolled.
HANDSCROLL_AREA = 12_000_000
HANDSCROLL_SIDE = 20000
THUMB_SHORT_SIDE = 420
THUMB_MAX_RATIO = 3  # gallery thumbnails are cropped to at most 3:1

# Fields the importers never touch: written by people (or drafted for them) in this project.
EDITORIAL_KEY = "editorial"


class ImportFailed(Exception):
    """A record could not be imported; the message says why, in plain words."""


def _tls_context() -> ssl.SSLContext:
    """Verified HTTPS. Python from python.org on macOS ships without root certificates,
    so use certifi's bundle when it is installed (it is, with the dev requirements)."""
    try:
        import certifi
    except ImportError:  # pragma: no cover
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


class Fetcher:
    """Fetches URLs with a clear user agent and a pause between requests to one host."""

    def __init__(self, pause: float = PAUSE_SECONDS):
        self.pause = pause
        self._last: dict[str, float] = {}
        self._tls = _tls_context()

    def _wait(self, url: str) -> None:
        host = urllib.parse.urlsplit(url).netloc
        since = time.monotonic() - self._last.get(host, 0.0)
        if since < self.pause:
            time.sleep(self.pause - since)
        self._last[host] = time.monotonic()

    def bytes(self, url: str, *, data: bytes | None = None, headers: dict | None = None, timeout: int = 90) -> bytes:
        self._wait(url)
        request = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=self._tls) as response:  # noqa: S310 - museum URLs only
                return response.read()
        except OSError as exc:
            raise ImportFailed(f"could not download {url} ({exc})") from exc

    def text(self, url: str, **kwargs) -> str:
        return self.bytes(url, **kwargs).decode("utf-8", errors="replace")

    def json(self, url: str, **kwargs):
        try:
            return json.loads(self.bytes(url, **kwargs))
        except ValueError as exc:
            raise ImportFailed(f"{url} did not return JSON") from exc


# --- text helpers -------------------------------------------------------------------------


def clean(text: str | None) -> str:
    """Strip tags, decode entities and tidy whitespace (keeping paragraph breaks)."""
    if not text:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    lines = [re.sub(r"[ \t 　]+", " ", line).strip() for line in text.splitlines()]
    out, blank = [], False
    for line in lines:
        if line:
            if blank and out:
                out.append("")
            out.append(line)
            blank = False
        else:
            blank = True
    return "\n".join(out).strip()


def pair(zh: str = "", en: str = "") -> dict:
    return {"zh": (zh or "").strip(), "en": (en or "").strip()}


FORMAT_WORDS = (  # (English phrase in a medium line, format)
    ("handscroll", "handscroll"),
    ("hanging scroll", "hanging_scroll"),
    ("album leaf", "album_leaf"),
    ("album", "album"),
    ("fan", "fan"),
)


def format_from_en(medium: str) -> str:
    low = (medium or "").lower()
    for word, fmt in FORMAT_WORDS:
        if word in low:
            return fmt
    return "other"


def today() -> str:
    return _dt.date.today().isoformat()


# --- images -----------------------------------------------------------------------------


def fit_size(width: int, height: int, max_area: int = MAX_AREA, max_side: int = MAX_SIDE) -> tuple[int, int]:
    """Largest size with the same shape that fits the area and side limits (never enlarges)."""
    scale = min(1.0, (max_area / (width * height)) ** 0.5, max_side / max(width, height))
    return max(1, int(width * scale)), max(1, int(height * scale))  # round down: stay within the limits


def limits_for(fmt: str) -> dict:
    if fmt == "handscroll":
        return {"max_area": HANDSCROLL_AREA, "max_side": HANDSCROLL_SIDE}
    return {"max_area": MAX_AREA, "max_side": MAX_SIDE}


def save_image(
    raw: bytes,
    work_id: str,
    image_dir: Path = IMAGE_DIR,
    *,
    fmt: str = "other",
    crop: tuple | None = None,
    thumb_at: float | None = None,
) -> dict:
    """Save the main image and a gallery thumbnail; return their paths and sizes.

    A handscroll is read from right to left, so its thumbnail shows the right-hand end.
    ``crop`` is an optional (x, y, w, h) box in percent, to trim mounting or colour charts.
    ``thumb_at`` centres a wide image's thumbnail on that point (percent from the left),
    for a scroll whose right-hand end is only mounting.
    """
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - only without the dev requirements
        raise ImportFailed("Pillow is needed to import images: run `make setup`") from exc

    Image.MAX_IMAGE_PIXELS = 400_000_000  # museum masters are large; they are trusted sources
    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
    except Exception as exc:  # noqa: BLE001 - any decoding problem means the same thing
        raise ImportFailed("the image could not be read") from exc
    image = image.convert("RGB")
    if crop:
        x, y, w, h = crop
        W, H = image.size
        image = image.crop((round(W * x / 100), round(H * y / 100), round(W * (x + w) / 100), round(H * (y + h) / 100)))
    image_dir.mkdir(parents=True, exist_ok=True)

    target = fit_size(*image.size, **limits_for(fmt))
    main = image.resize(target, Image.LANCZOS) if target != image.size else image
    main_path = image_dir / f"{work_id}.jpg"
    # baseline (not progressive) JPEG: some phones decode very large progressive files at low quality
    main.save(main_path, "JPEG", quality=84, optimize=True)

    w, h = main.size
    scale = THUMB_SHORT_SIDE / min(w, h)
    thumb = main.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS) if scale < 1 else main
    tw, th = thumb.size
    if tw > th * THUMB_MAX_RATIO:
        keep = th * THUMB_MAX_RATIO
        if thumb_at is not None:
            left = min(max(tw * thumb_at / 100 - keep / 2, 0), tw - keep)
        else:
            left = tw - keep if fmt == "handscroll" else (tw - keep) // 2
        thumb = thumb.crop((left, 0, left + keep, th))
    elif th > tw * THUMB_MAX_RATIO:
        keep = tw * THUMB_MAX_RATIO
        thumb = thumb.crop((0, 0, tw, keep))  # top of a tall scroll: where the eye starts
    thumb_path = image_dir / f"{work_id}-thumb.jpg"
    thumb.save(thumb_path, "JPEG", quality=80, optimize=True, progressive=True)

    rel = image_dir.relative_to(image_dir.parents[1]).as_posix()  # img/works
    return {
        "src": f"{rel}/{main_path.name}",
        "width": w,
        "height": h,
        "thumb": f"{rel}/{thumb_path.name}",
    }


# --- work files -----------------------------------------------------------------------


def work_path(work_id: str, data_dir: Path = DATA_DIR) -> Path:
    return data_dir / f"{work_id}.json"


def write_work(record: dict, data_dir: Path = DATA_DIR) -> Path:
    """Write a work file, keeping whatever this project wrote for it before."""
    path = work_path(record["id"], data_dir)
    if path.exists():
        old = json.loads(path.read_text(encoding="utf-8"))
        if old.get(EDITORIAL_KEY):
            record[EDITORIAL_KEY] = old[EDITORIAL_KEY]
        if "image" not in record and "image" in old:
            record["image"] = old["image"]
    record.setdefault(
        EDITORIAL_KEY,
        {"intro": [], "look_for": [], "views": [], "sources": {}, "alt": pair(), "overrides": {}, "status": "ai_draft"},
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
