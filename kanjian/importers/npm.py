"""National Palace Museum, Taipei: open-data records and IIIF images.

Records come from the museum's open-data site (https://digitalarchive.npm.gov.tw/opendata),
images from its IIIF image server. Mid-resolution images and the site's text are CC BY 4.0;
the credit line is in ``kanjian.museums``. The site's image-download buttons sit behind a
CAPTCHA, which this importer never touches: it uses the IIIF service the museum publishes.
"""

from __future__ import annotations

import io
import json
import re

from kanjian import periods
from kanjian.importers.common import Fetcher, ImportFailed, clean, fit_size, limits_for, pair, today

SITE = "https://digitalarchive.npm.gov.tw"
DETAIL = SITE + "/opendata/Pub/Detail/{id}?dep={dep}&mode=full"
MANIFEST = SITE + "/opendata/Integrate/GetJson?cid={id}&dept={dep}&imageName="
SEARCH = SITE + "/opendata/Pub/Search"
IIIF_MAX_AREA = 6_000_000  # the open-data tier is about 6 megapixels

CATEGORY = {"繪畫": "painting", "法書": "calligraphy", "法帖": "calligraphy", "書畫": "painting"}
FORMAT_SUFFIX = (
    ("冊頁", "album_leaf"),
    ("摺扇", "fan"),
    ("扇面", "fan"),
    ("軸", "hanging_scroll"),
    ("卷", "handscroll"),
    ("冊", "album"),
)
MATERIAL_EN = {
    "絹": "silk",
    "紙": "paper",
    "綾": "damask silk",
    "金箋": "gold-flecked paper",
    "灑金箋": "gold-flecked paper",
}
# Parts of a mounted scroll, as the record names them.
PART_EN = {
    "本幅": "Image",
    "全卷": "Whole scroll",
    "詩塘": "Poem panel",
    "引首": "Frontispiece",
    "拖尾": "Colophons",
    "隔水": "Mounting strip",
    "前隔水": "Front mounting strip",
    "後隔水": "Back mounting strip",
    "隔水一": "Mounting strip 1",
    "隔水二": "Mounting strip 2",
    "隔水三": "Mounting strip 3",
}


# --- reading the record page ----------------------------------------------------------------


def _pane(page: str, n: int) -> str:
    start = page.find(f'id="details-{n}"')
    if start < 0:
        return ""
    end = page.find('class="tab-pane', start + 10)
    return page[start : end if end > 0 else len(page)]


def _rows(fragment: str) -> list[list[str]]:
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", fragment, flags=re.S):
        cells = [clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
        if cells:
            rows.append(cells)
    return rows


def parse_detail(page: str) -> dict:
    """The parts of a record page this project uses, as plain strings."""
    basics = {row[0]: row[1] for row in _rows(_pane(page, 1)) if len(row) >= 2}
    if "品名" not in basics:
        raise ImportFailed("the record page has no title (品名); the museum may have changed its site")

    # Tabs are found by their name, since a record shows only the tabs it has data for.
    tabs = dict(re.findall(r'data-bs-target="#details-(\d+)"[^>]*><span>([^<]+)</span>', page))
    by_name = {name: int(n) for n, name in tabs.items()}

    def table(name: str) -> list[list[str]]:
        return _rows(_pane(page, by_name[name]))[1:] if name in by_name else []

    zh_texts, en_texts = [], []
    for row in table("參考資料"):
        if len(row) >= 2 and row[1]:
            if row[0] == "內容簡介":
                zh_texts.append(row[1])
            elif row[0].lower() == "description":
                en_texts.append(row[1])
    return {
        "basics": basics,
        "sizes": [r for r in table("典藏尺寸") if len(r) >= 2],
        "materials": [r for r in table("質地") if len(r) >= 2],
        "zh_texts": zh_texts,
        "en_texts": en_texts,
    }


def _strip_date_stamp(text: str) -> str:
    return re.sub(r"\s*\(\d{8}\)\s*$", "", text).strip()


def split_title(raw: str) -> tuple[str, str, str]:
    """'宋范寬谿山行旅圖　軸\\nTravelers Among…' → ('宋范寬谿山行旅圖', '軸', 'Travelers Among…')."""
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    zh_line = lines[0] if lines else ""
    en = " ".join(lines[1:])
    parts = re.split(r"[　 ]+", zh_line, maxsplit=1)
    return parts[0], (parts[1] if len(parts) > 1 else ""), en


def build_record(record_id: str, dep: str, page: str) -> dict:
    data = parse_detail(page)
    basics = data["basics"]
    full_zh, suffix, title_en = split_title(basics["品名"])

    artist_zh, _, artist_en = (basics.get("作者") or "").partition(",")
    period = periods.period_from_zh_prefix(full_zh)
    title_zh = full_zh
    if period:
        title_zh = title_zh[len(periods.PERIODS[period][0]) :]
    if artist_zh and title_zh.startswith(artist_zh.strip()):
        title_zh = title_zh[len(artist_zh.strip()) :]
    fmt = next((f for word, f in FORMAT_SUFFIX if suffix.startswith(word)), "other")

    zh_sizes = [f"{part} {size.replace('x', ' × ')} 公分" for part, size in data["sizes"]]
    en_sizes = [f"{PART_EN.get(part, part)} {size.replace('x', ' × ')} cm" for part, size in data["sizes"]]
    zh_mats = [f"{part}：{mat}" if part != "本幅" else mat for part, mat in data["materials"]]
    en_mats = [MATERIAL_EN.get(mat, "") for part, mat in data["materials"] if part == "本幅"]

    museum_zh = _strip_date_stamp(data["zh_texts"][-1]) if data["zh_texts"] else ""
    museum_en = _strip_date_stamp(data["en_texts"][-1]) if data["en_texts"] else ""

    return {
        "id": f"npm-{record_id}",
        "museum": "npm",
        "record": {
            "id": record_id,
            "dep": dep,
            "object_number": basics.get("文物統一編號", ""),
            "url": DETAIL.format(id=record_id, dep=dep).replace("&mode=full", ""),
            "accessed": today(),
        },
        "category": CATEGORY.get(basics.get("分類", ""), "other"),
        "format": fmt,
        "period": period,
        "year": periods.start_year(period),
        "title": pair(title_zh.strip(), title_en),
        "artist": pair(artist_zh, artist_en),
        "date": pair(),
        "medium": pair("；".join(zh_mats), ", ".join(m for m in en_mats if m)),
        "dimensions": pair("；".join(zh_sizes), "; ".join(en_sizes)),
        "museum_text": pair(museum_zh, museum_en),
    }


def choose_canvas(manifest: dict, label: str | None = None) -> tuple[str, str]:
    """(canvas label, IIIF image service) for the image to show.

    Handscrolls are photographed in sections; when the museum also publishes the whole
    scroll stitched together, its label ends in 'AAA', and that is the one to use.
    Otherwise the first canvas is normally the whole work. ``label`` picks one by hand.
    """
    try:
        canvases = manifest["sequences"][0]["canvases"]
        pairs = [(c["label"], c["images"][0]["resource"]["service"]["@id"]) for c in canvases]
    except (KeyError, IndexError, TypeError) as exc:
        raise ImportFailed("the museum's IIIF manifest lists no image for this record") from exc
    if not pairs:
        raise ImportFailed("the museum's IIIF manifest lists no image for this record")
    if label:
        for name, service in pairs:
            if name == label or name.endswith(label):
                return name, service
        raise ImportFailed(f"no image labelled {label} in this record ({len(pairs)} images)")
    for name, service in pairs:
        if name.endswith("AAA"):
            return name, service
    return pairs[0]


def _region_box(region: str, width: int, height: int) -> tuple[int, int, int, int]:
    """'full' or 'pct:x,y,w,h' → a pixel box (x, y, w, h) of the full-size image."""
    if region in ("", "full"):
        return 0, 0, width, height
    if not region.startswith("pct:"):
        raise ImportFailed(f"image region '{region}' should be 'full' or 'pct:x,y,w,h'")
    x, y, w, h = (float(v) for v in region[4:].split(","))
    box = (round(width * x / 100), round(height * y / 100), round(width * w / 100), round(height * h / 100))
    return box[0], box[1], min(box[2], width - box[0]), min(box[3], height - box[1])


def iiif_image(
    fetcher: Fetcher, service: str, *, region: str = "full", max_area: int = 3_000_000, max_side: int = 9000
) -> bytes:
    """The image at a size fitting the limits. The server caps each request at about six
    megapixels, so a larger image (a long handscroll) is fetched in strips and joined."""
    from PIL import Image  # imported here so the website itself never needs Pillow

    base = service.rstrip("/")
    info = fetcher.json(base + "/info.json")
    per_request = min(IIIF_MAX_AREA, int(info.get("maxArea") or IIIF_MAX_AREA))
    bx, by, bw, bh = _region_box(region, int(info["width"]), int(info["height"]))
    out_w, out_h = fit_size(bw, bh, max_area=max_area, max_side=max_side)
    strips = max(1, -(-out_w * out_h // per_request))  # ceiling division
    canvas = Image.new("RGB", (out_w, out_h), "white")
    x_out = 0
    for i in range(strips):
        # split the output width evenly, and the source region in the same proportion
        next_out = round(out_w * (i + 1) / strips)
        sx0 = bx + round(bw * x_out / out_w)
        sx1 = bx + round(bw * next_out / out_w)
        size = f"{next_out - x_out},{out_h}"
        raw = fetcher.bytes(f"{base}/{sx0},{by},{sx1 - sx0},{bh}/{size}/0/default.jpg", timeout=180)
        strip = Image.open(io.BytesIO(raw)).convert("RGB")
        canvas.paste(
            strip.resize((next_out - x_out, out_h)) if strip.size != (next_out - x_out, out_h) else strip, (x_out, 0)
        )
        x_out = next_out
    buffer = io.BytesIO()
    canvas.save(buffer, "PNG")  # lossless hand-over; save_image writes the final JPEG
    return buffer.getvalue()


# --- public interface ------------------------------------------------------------------


def fetch(fetcher: Fetcher, ident: str, choice: dict | None = None) -> tuple[dict, bytes]:
    """``ident`` is the record number from the open-data site, e.g. '1195' or '1195:P'.

    ``choice`` (from the work's editorial block) can pick an image by its ``canvas`` label
    and crop it with an IIIF ``region`` such as 'pct:0,0,100,89'.
    """
    choice = choice or {}
    record_id, _, dep = ident.partition(":")
    dep = (dep or "P").upper()
    if not record_id.isdigit():
        raise ImportFailed(f"'{ident}' is not a record number (use the number in /Pub/Detail/<number>)")
    page = fetcher.text(DETAIL.format(id=record_id, dep=dep))
    manifest = fetcher.json(MANIFEST.format(id=record_id, dep=dep))
    record = build_record(record_id, dep, page)
    label, service = choose_canvas(manifest, choice.get("canvas"))
    record["record"]["image"] = label
    raw = iiif_image(fetcher, service, region=choice.get("region", "full"), **limits_for(record["format"]))
    return record, raw


def search(fetcher: Fetcher, query: str) -> list[tuple[str, str]]:
    """(ident, title) pairs for the first page of results."""
    body = {
        "RegisterType": None,
        "IndexYear": None,
        "WestBeginYear": 0,
        "WestEndYear": 0,
        "YearDisplay": None,
        "SearchContent": query,
        "RegisterTypeEng": None,
        "PageInfo": {"PageIndex": 1, "PageSize": 15, "PageCount": 0},
    }
    page = fetcher.text(
        SEARCH, data=json.dumps(body).encode(), headers={"Content-Type": "application/json; charset=utf-8"}
    )
    return parse_search(page)


def parse_search(page: str) -> list[tuple[str, str]]:
    """Each result card: <a onclick="Detail('1195', 'P')"> … <div class="card-title">title</div>."""
    results: dict[str, str] = {}
    pattern = r"Detail\('(\d+)',\s*'([A-Z])'\).*?class=\"card-title\"[^>]*>(.*?)</div>"
    for record_id, dep, title in re.findall(pattern, page, flags=re.S):
        results.setdefault(f"{record_id}:{dep}", clean(title).replace("\n", " "))
    return list(results.items())
