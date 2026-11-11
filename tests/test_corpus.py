"""The grounding corpus: the real data files, and the rules that protect them."""

from __future__ import annotations

import pytest

from kanjian.corpus import LAYER_KEYS, image_size, load_corpus, main_cli, normalise_code
from tests.conftest import DATA, STATIC

# --- the real data files ---------------------------------------------------------


@pytest.fixture(scope="module")
def corpus():
    return load_corpus(DATA, STATIC)


def test_every_data_file_loads_without_errors(corpus):
    files = sorted(p.stem for p in DATA.glob("*.json"))
    assert [w["file"] for w in corpus.works] == files
    assert corpus.errors == [], "\n".join(map(str, corpus.errors))


def test_no_warnings_in_shipped_data(corpus):
    assert corpus.problems == [], "\n".join(map(str, corpus.problems))


def test_pilot_covers_the_core_formats(corpus):
    formats = {w["format"] for w in corpus.works}
    assert {"handscroll", "hanging_scroll", "calligraphy"} <= formats


def test_codes_are_unique_two_digit_numbers(corpus):
    codes = [w["code"] for w in corpus.works]
    assert len(codes) == len(set(codes))
    assert all(len(c) >= 2 and c.isdigit() for c in codes)


def test_every_work_has_all_four_layers_in_order(corpus):
    for work in corpus.works:
        assert [layer["key"] for layer in work["layers"]] == list(LAYER_KEYS), work["id"]


def test_every_verified_statement_cites_a_listed_source(corpus):
    for work in corpus.works:
        listed = {s["id"] for s in work["sources"]}
        for layer in work["layers"]:
            for stop in layer["stops"]:
                for seg in stop["segments"]:
                    if seg["status"] == "verified":
                        assert seg["source"] and seg["source"]["id"] in listed


def test_every_statement_exists_in_both_languages(corpus):
    for work in corpus.works:
        for layer in work["layers"]:
            for stop in layer["stops"]:
                for seg in stop["segments"]:
                    assert seg["text"]["zh"].strip() and seg["text"]["en"].strip()


def test_handscroll_has_a_right_to_left_traversal(corpus):
    for work in (w for w in corpus.works if w["format"] == "handscroll"):
        traversal = next(layer for layer in work["layers"] if layer["mode"] == "traversal")
        rights = [stop["region"][2] for stop in traversal["stops"]]
        assert len(rights) >= 3
        assert rights == sorted(rights, reverse=True)


def test_calligraphy_has_a_brushwork_layer(corpus):
    for work in (w for w in corpus.works if w["format"] == "calligraphy"):
        assert any(layer["mode"] == "brushwork" for layer in work["layers"])


def test_every_work_has_a_provenance_layer(corpus):
    for work in corpus.works:
        assert work["layers"][3]["mode"] == "provenance"


def test_chinese_text_contains_chinese(corpus):
    for work in corpus.works:
        for layer in work["layers"]:
            for stop in layer["stops"]:
                for seg in stop["segments"]:
                    assert any("一" <= ch <= "鿿" for ch in seg["text"]["zh"]), seg["text"]["zh"]


def test_image_sizes_are_read_from_the_files(corpus):
    for work in corpus.works:
        for image in work["images"].values():
            assert image["width"] > 100 and image["height"] > 100


def test_shipped_images_are_reasonably_small():
    for path in (STATIC / "img").rglob("*.jpg"):
        assert path.stat().st_size < 1_000_000, f"{path.name} is over 1 MB; phones in a gallery may be on slow data"


# --- the rules, on broken copies of a real file -------------------------------------


def load_one(corpus_dir, work):
    data, static, write = corpus_dir
    write("work", work)
    return load_corpus(data, static)


def first_segment(work):
    return work["layers"][0]["stops"][0]["segments"][0]


def test_verified_without_source_is_downgraded_and_reported(corpus_dir, sample_work):
    seg = first_segment(sample_work)
    assert seg["status"] == "verified"
    del seg["source"]
    corpus = load_one(corpus_dir, sample_work)
    served = corpus.works[0]["layers"][0]["stops"][0]["segments"][0]
    assert served["status"] == "inferred"
    assert any("cites no known source" in p.message for p in corpus.errors)


def test_verified_with_unknown_source_is_downgraded(corpus_dir, sample_work):
    first_segment(sample_work)["source"] = "made-up"
    corpus = load_one(corpus_dir, sample_work)
    assert corpus.works[0]["layers"][0]["stops"][0]["segments"][0]["status"] == "inferred"
    assert corpus.errors


def test_inferred_with_a_source_is_a_warning(corpus_dir, sample_work):
    seg = sample_work["layers"][0]["stops"][0]["segments"][1]
    assert seg["status"] == "inferred"
    seg["source"] = "met"
    corpus = load_one(corpus_dir, sample_work)
    assert not corpus.errors
    assert any(p.level == "warning" for p in corpus.problems)
    assert corpus.works[0]["layers"][0]["stops"][0]["segments"][1]["source"] is None


@pytest.mark.parametrize(
    "breakage, message",
    [
        (lambda w: w.pop("code"), "'code'"),
        (lambda w: w.update(format="fresco"), "'format'"),
        (lambda w: w["title"].pop("en"), "'en' text"),
        (lambda w: w["layers"].pop(), "four"),
        (lambda w: w["layers"].reverse(), "four"),
        (lambda w: w["layers"][1].update(mode="brushwork"), "cannot use mode"),
        (lambda w: w["layers"][0]["stops"][0].update(region=[0.5, 0, 0.2, 1]), "region"),
        (lambda w: w["layers"][0]["stops"][0].update(image="nope"), "unknown image"),
        (lambda w: w["images"]["main"].update(src="img/works/missing.jpg"), "no file"),
        (lambda w: w["images"]["main"].update(src="../app.py"), "no file"),
        (lambda w: first_segment(w).update(status="probably"), "'status'"),
        (lambda w: w["layers"][1]["stops"][0].pop("label"), "needs a 'label'"),
        (lambda w: w["layers"][0]["stops"][0].update(segments=[]), "at least one segment"),
    ],
)
def test_broken_files_are_rejected_with_a_clear_message(corpus_dir, sample_work, breakage, message):
    breakage(sample_work)
    corpus = load_one(corpus_dir, sample_work)
    assert corpus.works == []
    assert any(message in p.message for p in corpus.errors), [str(p) for p in corpus.problems]


def test_traversal_running_left_to_right_is_flagged(corpus_dir, sample_work):
    sample_work["layers"][1]["stops"].reverse()
    corpus = load_one(corpus_dir, sample_work)
    assert any("right to left" in p.message for p in corpus.problems)


def test_invalid_json_is_reported_not_crashed(corpus_dir):
    data, static, _ = corpus_dir
    (data / "bad.json").write_text("{ not json", encoding="utf-8")
    corpus = load_corpus(data, static)
    assert corpus.works == [] and "JSON" in corpus.errors[0].message


def test_duplicate_codes_keep_only_the_first(corpus_dir, sample_work):
    data, static, write = corpus_dir
    write("a", sample_work)
    second = dict(sample_work, id="another-id")
    write("b", second)
    corpus = load_corpus(data, static)
    assert [w["file"] for w in corpus.works] == ["a"]
    assert any("already used" in p.message for p in corpus.errors)


def test_stats_count_verified_share(corpus_dir, sample_work):
    corpus = load_one(corpus_dir, sample_work)
    stats = corpus.works[0]["stats"]
    assert stats["verified"] + stats["inferred"] == stats["segments"]
    assert stats["share"] == pytest.approx(stats["verified"] / stats["segments"])
    assert stats["meets_target"] is False


def test_fully_verified_work_meets_target(corpus_dir, sample_work):
    for layer in sample_work["layers"]:
        for stop in layer["stops"]:
            for seg in stop["segments"]:
                seg.update(status="verified", source="met")
    corpus = load_one(corpus_dir, sample_work)
    assert corpus.works[0]["stats"]["meets_target"] is True


@pytest.mark.parametrize(
    "raw, expected",
    [("1", "01"), ("01", "01"), (" 3 ", "03"), ("No. 12", "12"), ("", ""), ("abc", ""), ("12345", "")],
)
def test_label_numbers_are_normalised(raw, expected):
    assert normalise_code(raw) == expected


def test_image_size_reads_jpeg_and_png(tmp_path):
    assert image_size(STATIC / "img" / "works" / "geese.jpg") == (3600, 901)
    png = tmp_path / "x.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (7).to_bytes(4, "big") + (5).to_bytes(4, "big"))
    assert image_size(png) == (7, 5)
    bad = tmp_path / "x.gif"
    bad.write_bytes(b"GIF89a")
    with pytest.raises(ValueError):
        image_size(bad)


# --- the command-line audit ------------------------------------------------------------


def test_audit_passes_on_shipped_data(capsys):
    assert main_cli(["--data", str(DATA), "--static", str(STATIC)]) == 0
    assert "Corpus audit passed" in capsys.readouterr().out


def test_audit_strict_fails_below_target(capsys):
    assert main_cli(["--data", str(DATA), "--static", str(STATIC), "--strict"]) == 1


def test_audit_fails_on_errors(corpus_dir, sample_work, capsys):
    data, static, write = corpus_dir
    del first_segment(sample_work)["source"]
    write("work", sample_work)
    assert main_cli(["--data", str(data), "--static", str(static)]) == 1
    assert "FAILED" in capsys.readouterr().out
