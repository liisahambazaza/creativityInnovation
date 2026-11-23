"""The museum importers, run offline against saved copies of real museum responses."""

from __future__ import annotations

import io
import json

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from kanjian.importers import _ident_of, cma, import_one, met, npm  # noqa: E402
from kanjian.importers.common import (  # noqa: E402
    ImportFailed,
    clean,
    fit_size,
    format_from_en,
    limits_for,
    save_image,
    write_work,
)
from kanjian.works import load_collection  # noqa: E402
from tests.conftest import FIXTURES  # noqa: E402


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def fixture_json(name: str):
    return json.loads(fixture_text(name))


def jpeg(width: int, height: int, colour=(120, 90, 60)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), colour).save(buffer, "JPEG")
    return buffer.getvalue()


class FakeFetcher:
    """Answers from a dict of URL → bytes/str/object, and records what was asked for."""

    def __init__(self, answers: dict):
        self.answers = answers
        self.asked: list[str] = []

    def _find(self, url):
        self.asked.append(url)
        for prefix, answer in self.answers.items():
            if url.startswith(prefix):
                return answer(url) if callable(answer) else answer
        raise ImportFailed(f"unexpected URL {url}")

    def bytes(self, url, **_):
        answer = self._find(url)
        return answer.encode() if isinstance(answer, str) else answer

    def text(self, url, **_):
        return self._find(url)

    def json(self, url, **_):
        answer = self._find(url)
        return json.loads(answer) if isinstance(answer, (str, bytes)) else answer


# --- text helpers --------------------------------------------------------------------


def test_clean_strips_tags_and_keeps_paragraphs():
    assert clean("<p>One&nbsp; <i>two</i></p><p>Three</p>") == "One two\n\nThree"
    assert clean(None) == ""


@pytest.mark.parametrize(
    "medium, fmt",
    [
        ("Handscroll; ink on paper", "handscroll"),
        ("hanging scroll; ink on paper", "hanging_scroll"),
        ("Album leaf; ink on silk", "album_leaf"),
        ("Folding fan", "fan"),
        ("Bronze", "other"),
    ],
)
def test_format_from_medium(medium, fmt):
    assert format_from_en(medium) == fmt


def test_fit_size_keeps_shape_and_never_enlarges():
    assert fit_size(1000, 500) == (1000, 500)
    w, h = fit_size(6000, 3000)
    assert w * h <= 3_000_000 and abs(w / h - 2) < 0.01
    w, h = fit_size(30000, 1000, **limits_for("handscroll"))
    assert w <= 20000 and h >= 600


# --- Taipei --------------------------------------------------------------------------


def test_npm_record_page_is_read_into_a_work():
    record = npm.build_record("1195", "P", fixture_text("npm-detail-1195.html"))
    assert record["id"] == "npm-1195"
    assert record["title"] == {"zh": "谿山行旅圖", "en": "Travelers Among Mountains and Streams"}
    assert record["artist"] == {"zh": "范寬", "en": "Fan Kuan"}
    assert (record["category"], record["format"], record["period"]) == ("painting", "hanging_scroll", "song")
    assert record["medium"] == {"zh": "絹", "en": "silk"}
    assert record["dimensions"]["en"] == "Image 206.3 × 103.3 cm"
    assert record["record"]["object_number"] == "故畫000826N000000000"
    assert record["museum_text"]["zh"].startswith("范寬向來被視為山水成立期的大師")
    assert "(20061206)" not in record["museum_text"]["zh"]
    assert record["museum_text"]["en"].startswith("Fan K'uan has long been considered")


def test_npm_page_without_a_title_is_refused():
    with pytest.raises(ImportFailed, match="no title"):
        npm.build_record("1", "P", "<html></html>")


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("宋范寬谿山行旅圖　軸\n\nTravelers", ("宋范寬谿山行旅圖", "軸", "Travelers")),
        ("唐懷素自敘帖 卷", ("唐懷素自敘帖", "卷", "")),
    ],
)
def test_npm_title_split(raw, expected):
    assert npm.split_title(raw) == expected


def test_npm_search_results():
    assert npm.parse_search(fixture_text("npm-search.html")) == [
        ("14901:P", "唐懷素自敘帖 卷"),
        ("14890:P", "唐懷素自敘帖 卷"),
    ]


def test_npm_canvas_choice_prefers_a_whole_stitched_scroll():
    manifest = fixture_json("npm-manifest-1195.json")
    first = manifest["sequences"][0]["canvases"][0]
    assert npm.choose_canvas(manifest)[0] == first["label"]
    stitched = json.loads(json.dumps(first))
    stitched["label"] = "K2A000826N000000000AAA"
    manifest["sequences"][0]["canvases"].append(stitched)
    assert npm.choose_canvas(manifest)[0].endswith("AAA")
    assert npm.choose_canvas(manifest, "PAB")[0].endswith("PAB")
    with pytest.raises(ImportFailed, match="no image labelled"):
        npm.choose_canvas(manifest, "ZZZ")


def test_npm_region_box():
    assert npm._region_box("full", 1000, 500) == (0, 0, 1000, 500)
    assert npm._region_box("pct:10,0,50,100", 1000, 500) == (100, 0, 500, 500)
    with pytest.raises(ImportFailed):
        npm._region_box("square", 1000, 500)


def test_npm_large_images_are_fetched_in_strips_and_joined():
    service = "https://iiif.example/iiif/2/K2A"
    info = {"width": 30000, "height": 1000, "maxArea": 2_000_000}

    def strip(url):
        size = url.split("/")[-3]  # .../{region}/{w},{h}/0/default.jpg
        w, h = (int(v) for v in size.split(","))
        return jpeg(w, h)

    fetcher = FakeFetcher({service + "/info.json": info, service + "/": strip})
    raw = npm.iiif_image(fetcher, service, max_area=6_000_000, max_side=20000)
    image = Image.open(io.BytesIO(raw))
    assert image.size == fit_size(30000, 1000, max_area=6_000_000, max_side=20000)
    strips = [u for u in fetcher.asked if u.endswith("default.jpg")]
    assert len(strips) == 3  # 6 megapixels in requests of at most 2


def test_npm_fetch_uses_the_editorial_image_choice():
    page = fixture_text("npm-detail-1195.html")
    manifest = fixture_json("npm-manifest-1195.json")
    service = manifest["sequences"][0]["canvases"][1]["images"][0]["resource"]["service"]["@id"]
    fetcher = FakeFetcher(
        {
            npm.SITE + "/opendata/Pub/Detail/": page,
            npm.SITE + "/opendata/Integrate/GetJson": manifest,
            service + "/info.json": {"width": 2000, "height": 1000},
            service + "/": jpeg(10, 10),
        }
    )
    record, _raw = npm.fetch(fetcher, "1195", {"canvas": "PAB", "region": "pct:0,0,100,50"})
    assert record["record"]["image"].endswith("PAB")
    assert any("/0,0,2000,500/" in url for url in fetcher.asked)


def test_npm_rejects_a_bad_record_number():
    with pytest.raises(ImportFailed, match="not a record number"):
        npm.fetch(FakeFetcher({}), "abc")


# --- the Met and Cleveland -------------------------------------------------------------


def test_met_record():
    record = met.build_record(fixture_json("met-45636.json"))
    assert record["id"] == "met-45636"
    assert record["title"]["en"] == "Woods and Valleys of Mount Yu"
    assert record["artist"]["en"] == "Ni Zan (Chinese, 1306–1374)"
    assert (record["category"], record["format"], record["period"]) == ("painting", "hanging_scroll", "yuan")
    assert record["year"] == 1372


def test_met_refuses_objects_that_are_not_open_access():
    obj = fixture_json("met-45636.json")
    obj["isPublicDomain"] = False
    with pytest.raises(ImportFailed, match="not Open Access"):
        met.build_record(obj)


def test_cleveland_record():
    record = cma.build_record(fixture_json("cma-1953.126.json")["data"])
    assert record["title"] == {"zh": "溪山無盡", "en": "Streams and Mountains without End"}
    assert record["format"] == "handscroll"
    assert record["museum_text"]["en"].startswith("Streams and Mountains without End")
    assert record.pop("_image").startswith("https://")


def test_cleveland_refuses_works_that_are_not_cc0():
    data = fixture_json("cma-1953.126.json")["data"]
    data["share_license_status"] = "Copyrighted"
    with pytest.raises(ImportFailed, match="not CC0"):
        cma.build_record(data)


# --- images and work files -----------------------------------------------------------


def test_save_image_writes_a_main_image_and_thumbnail(tmp_path):
    image_dir = tmp_path / "static" / "img" / "works"
    saved = save_image(jpeg(4000, 3000), "test-1", image_dir)
    assert saved["src"] == "img/works/test-1.jpg" and saved["thumb"] == "img/works/test-1-thumb.jpg"
    assert saved["width"] * saved["height"] <= 3_000_000
    assert Image.open(image_dir / "test-1-thumb.jpg").size[1] == 420


def test_handscroll_thumbnail_shows_the_right_hand_end(tmp_path):
    image = Image.new("RGB", (6000, 300), (255, 255, 255))
    image.paste((200, 0, 0), (5000, 0, 6000, 300))  # the start of the scroll is red
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    image_dir = tmp_path / "static" / "img" / "works"
    save_image(buffer.getvalue(), "scroll", image_dir, fmt="handscroll")
    thumb = Image.open(image_dir / "scroll-thumb.jpg")
    assert thumb.size[0] == thumb.size[1] * 3
    assert thumb.getpixel((thumb.size[0] - 5, 10))[0] > 150 and thumb.getpixel((thumb.size[0] - 5, 10))[1] < 80


def test_save_image_crops(tmp_path):
    saved = save_image(jpeg(1000, 1000), "c", tmp_path / "static" / "img" / "works", crop=(0, 0, 50, 100))
    assert (saved["width"], saved["height"]) == (500, 1000)


def test_unreadable_image_is_refused(tmp_path):
    with pytest.raises(ImportFailed, match="could not be read"):
        save_image(b"not an image", "x", tmp_path)


def test_write_work_keeps_editorial_text(tmp_path, sample_work):
    sample_work["editorial"]["intro"]["en"] = "Written by us."
    write_work(json.loads(json.dumps(sample_work)), tmp_path)
    fresh = {k: v for k, v in sample_work.items() if k != "editorial"}
    fresh["title"] = {"zh": "新", "en": "New"}
    path = write_work(fresh, tmp_path)
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["title"]["en"] == "New"
    assert saved["editorial"]["intro"]["en"] == "Written by us."


def test_import_one_end_to_end(tmp_path):
    """A Met import, from fake downloads to a work the site can load."""
    obj = fixture_json("met-45636.json")
    fetcher = FakeFetcher({met.API + "/objects/45636": obj, obj["primaryImage"]: jpeg(800, 1600)})
    data, image_dir = tmp_path / "works", tmp_path / "static" / "img" / "works"
    path = import_one("met", "45636", fetcher=fetcher, data_dir=data, image_dir=image_dir)
    work = json.loads(path.read_text(encoding="utf-8"))
    assert _ident_of(work) == "45636"
    assert work["editorial"]["intro"] == {"zh": "", "en": ""}
    collection = load_collection(data, tmp_path / "static")
    assert [w["id"] for w in collection.works] == ["met-45636"]
    assert collection.errors == []


def test_import_one_can_keep_an_existing_image(tmp_path):
    obj = fixture_json("met-45636.json")
    data, image_dir = tmp_path / "works", tmp_path / "static" / "img" / "works"
    fetcher = FakeFetcher({met.API + "/objects/45636": obj, obj["primaryImage"]: jpeg(800, 1600)})
    path = import_one("met", "45636", fetcher=fetcher, data_dir=data, image_dir=image_dir)
    work = json.loads(path.read_text(encoding="utf-8"))
    work["editorial"]["image_choice"] = {"keep": True}
    work["image"]["width"] = 12345  # a marker that must survive
    path.write_text(json.dumps(work), encoding="utf-8")
    import_one("met", "45636", fetcher=fetcher, data_dir=data, image_dir=image_dir)
    assert json.loads(path.read_text(encoding="utf-8"))["image"]["width"] == 12345
