"""Loading and checking the collection in data/works."""

from __future__ import annotations

import json

import pytest

from kanjian import periods
from kanjian.museums import MUSEUMS, credit
from kanjian.works import CATEGORIES, FORMATS, LANGS, load_collection, main_cli
from tests.conftest import DATA, STATIC

# --- the real collection ---------------------------------------------------------


@pytest.fixture(scope="module")
def collection():
    return load_collection(DATA, STATIC)


def test_the_real_collection_loads_without_errors(collection):
    assert collection.errors == []
    assert len(collection.works) >= 13


def test_every_museum_is_represented(collection):
    assert {w["museum"] for w in collection.works} == set(MUSEUMS)


@pytest.mark.parametrize("path", sorted(DATA.glob("*.json")), ids=lambda p: p.stem)
def test_every_work_is_complete(collection, path):
    work = collection.get(path.stem)
    assert work is not None, f"{path.name} did not load"
    assert work["category"] in CATEGORIES and work["format"] in FORMATS
    assert work["period"] in periods.PERIODS
    assert isinstance(work["year"], int), "a year is needed to place the work in time"
    assert work["intro"], "no introduction"
    assert work["checked"]["on"], "the editorial text has not been checked against sources"
    for lang in LANGS:
        assert work["title"][lang], f"no {lang} title"
        assert work["alt"][lang], f"no {lang} image description"
        for statement in [*work["intro"], *work["look_for"], *work["views"]]:
            assert statement[lang], f"a statement has no {lang} text"
            assert statement["sources"], f"a statement cites no source: {statement['en'][:60]}"
    for view in work["views"]:
        assert view["who"]["en"] and view["who"]["zh"], "a view must say whose it is"
    for source in work["sources"]:
        assert source["key"] in ("museum", "image") or source["url"].startswith("https://")
    assert work["record"]["url"].startswith("https://")
    assert (STATIC / work["image"]["src"]).is_file() and (STATIC / work["image"]["thumb"]).is_file()


def test_editorial_text_is_marked_as_an_ai_draft():
    for path in DATA.glob("*.json"):
        editorial = json.loads(path.read_text(encoding="utf-8"))["editorial"]
        assert editorial.get("status") == "ai_draft", f"{path.name}: say who wrote the editorial text"


def test_works_are_in_time_order(collection):
    years = [w["sort_year"] for w in collection.works]
    assert years == sorted(years)


def test_eras_group_works_oldest_first(collection):
    eras = [era for era, _ in collection.by_era()]
    assert eras == [e for e in periods.ERAS if e in eras]
    assert eras[0] == "tang"


def test_filter_by_category(collection):
    for _, works in collection.by_era("calligraphy"):
        assert all(w["category"] == "calligraphy" for w in works)


def test_neighbours(collection):
    first, second = collection.works[0], collection.works[1]
    assert collection.neighbours(first["id"]) == (None, second)
    assert collection.neighbours(second["id"])[0] == first


# --- rules, on broken copies -------------------------------------------------------


def load_one(collection_dir, work):
    data, static, write = collection_dir
    write(work)
    return load_collection(data, static)


def test_overrides_replace_museum_fields(collection_dir, sample_work):
    sample_work["editorial"]["overrides"] = {"title": {"en": "A corrected title"}, "year": 1001}
    work = load_one(collection_dir, sample_work).works[0]
    assert work["title"] == {"zh": "谿山行旅圖", "en": "A corrected title"}
    assert work["year"] == 1001


def test_file_name_must_match_id(collection_dir, sample_work):
    data, static, write = collection_dir
    write(sample_work, name="something-else")
    collection = load_collection(data, static)
    assert collection.works == []
    assert "should match the file name" in str(collection.errors[0])


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda w: w.update(museum="louvre"), "unknown museum"),
        (lambda w: w["record"].pop("url"), "record.url"),
        (lambda w: w.update(title={"zh": "", "en": ""}), "no title"),
        (lambda w: w["image"].update(src="img/works/missing.jpg"), "image file"),
    ],
)
def test_broken_files_are_reported_and_skipped(collection_dir, sample_work, change, message):
    change(sample_work)
    collection = load_one(collection_dir, sample_work)
    assert collection.works == []
    assert message in str(collection.errors[0])


def test_missing_editorial_text_is_only_a_warning(collection_dir, sample_work):
    sample_work["editorial"] = {}
    collection = load_one(collection_dir, sample_work)
    assert len(collection.works) == 1
    assert collection.errors == []
    assert any("no introduction" in str(p) for p in collection.problems)


def test_unknown_values_fall_back_with_a_warning(collection_dir, sample_work):
    sample_work.update(category="sculpture", format="scroll-ish", period="martian")
    sample_work["editorial"]["overrides"] = {}
    work = load_one(collection_dir, sample_work).works[0]
    assert (work["category"], work["format"], work["period"], work["era"]) == ("other", "other", None, "other")


def test_unreadable_json_is_reported(collection_dir):
    data, static, _ = collection_dir
    (data / "bad.json").write_text("{not json", encoding="utf-8")
    assert "cannot be read" in str(load_collection(data, static).errors[0])


def test_command_line_check_passes_on_the_real_collection(capsys):
    assert main_cli(["--data", str(DATA), "--static", str(STATIC)]) == 0
    assert "Collection check passed." in capsys.readouterr().out


# --- dynasties and credit lines ----------------------------------------------------


@pytest.mark.parametrize(
    "title, key", [("宋范寬谿山行旅圖", "song"), ("北宋蘇東坡書", "northern_song"), ("唐懷素", "tang"), ("倪瓚", None)]
)
def test_period_from_npm_title(title, key):
    assert periods.period_from_zh_prefix(title) == key


@pytest.mark.parametrize(
    "text, key",
    [
        ("Yuan dynasty (1271–1368)", "yuan"),
        ("China, Northern Song dynasty (960–1127)", "northern_song"),
        ("Southern Song dynasty", "southern_song"),
        ("Edo period", None),
    ],
)
def test_period_from_english(text, key):
    assert periods.period_from_en(text) == key


def test_npm_credit_line_follows_the_museums_form():
    title = {"zh": "谿山行旅圖", "en": "Travelers Among Mountains and Streams"}
    assert credit("npm", "zh", title) == "谿山行旅圖 國立故宮博物院，臺北，CC BY 4.0 @ www.npm.gov.tw"
    assert (
        credit("npm", "en", title)
        == "Travelers Among Mountains and Streams The National Palace Museum, Taipei, CC BY 4.0 @ www.npm.gov.tw"
    )


# --- the source rules ----------------------------------------------------------------


def statement(en="A claim.", sources=("museum",)):
    return {"zh": "一句话。", "en": en, "sources": list(sources)}


def with_editorial(sample_work, **editorial):
    sample_work["editorial"] = {"checked": {"on": "2026-11-24"}, "alt": {"zh": "图", "en": "Image"}, **editorial}
    return sample_work


def test_a_statement_without_a_source_fails_the_check(collection_dir, sample_work):
    collection = load_one(collection_dir, with_editorial(sample_work, intro=[statement(sources=())]))
    assert any("cites no source" in str(p) and p.level == "error" for p in collection.problems)
    assert len(collection.works) == 1, "the work is still shown; the check fails"


def test_citing_a_source_that_is_not_listed_fails(collection_dir, sample_work):
    collection = load_one(collection_dir, with_editorial(sample_work, look_for=[statement(sources=("nowhere",))]))
    assert any("unknown source(s) nowhere" in str(p) for p in collection.errors)


def test_unchecked_editorial_text_fails(collection_dir, sample_work):
    sample_work = with_editorial(sample_work, intro=[statement()])
    sample_work["editorial"].pop("checked")
    assert any("not been checked" in str(p) for p in load_one(collection_dir, sample_work).errors)


def test_a_source_needs_a_kind_and_a_link(collection_dir, sample_work):
    sources = {"x": {"kind": "rumour", "title": "Hearsay", "url": "http://example.com"}}
    collection = load_one(
        collection_dir, with_editorial(sample_work, intro=[statement(sources=("x",))], sources=sources)
    )
    messages = " ".join(str(p) for p in collection.errors)
    assert "kind 'rumour'" in messages and "https:// link" in messages


def test_an_inscription_needs_no_link(collection_dir, sample_work):
    sources = {"colophon": {"kind": "inscription", "title": "Colophon by Dong Qichang"}}
    collection = load_one(
        collection_dir, with_editorial(sample_work, intro=[statement(sources=("colophon",))], sources=sources)
    )
    assert collection.errors == []


def test_a_view_must_name_someone(collection_dir, sample_work):
    collection = load_one(collection_dir, with_editorial(sample_work, views=[statement()]))
    assert any("does not say whose view" in str(p) for p in collection.errors)


def test_sources_are_numbered_in_reading_order(collection_dir, sample_work):
    sources = {
        "a": {"kind": "encyclopedia", "title": "A", "url": "https://a.example"},
        "b": {"kind": "scholarship", "title": "B", "url": "https://b.example"},
    }
    editorial = {
        "intro": [statement(sources=("b",)), statement(sources=("museum", "b"))],
        "look_for": [statement(sources=("a", "image"))],
        "sources": sources,
    }
    work = load_one(collection_dir, with_editorial(sample_work, **editorial)).works[0]
    assert [s["key"] for s in work["sources"]] == ["b", "museum", "a", "image"]
    assert work["source_numbers"] == {"b": 1, "museum": 2, "a": 3, "image": 4}


def test_an_unused_source_is_a_warning(collection_dir, sample_work):
    sources = {"spare": {"kind": "encyclopedia", "title": "Spare", "url": "https://spare.example"}}
    collection = load_one(collection_dir, with_editorial(sample_work, intro=[statement()], sources=sources))
    assert collection.errors == []
    assert any("nothing cites it" in str(p) for p in collection.problems)


def test_the_first_format_of_introduction_still_loads_but_fails_the_check(collection_dir, sample_work):
    collection = load_one(collection_dir, with_editorial(sample_work, intro={"zh": "旧", "en": "Old"}))
    assert collection.works[0]["intro"][0]["en"] == "Old"
    assert any("cites no source" in str(p) for p in collection.errors)
