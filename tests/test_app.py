"""The web pages and the JSON API, through Flask's test client."""

from __future__ import annotations

import json
import os
import re

import pytest

from app import _is_loopback, create_app, mark_chinese

ZH, EN = {"Accept-Language": "zh-CN"}, {"Accept-Language": "en-US"}


def html(response) -> str:
    return response.get_data(as_text=True)


# --- language --------------------------------------------------------------------


def test_home_defaults_to_chinese(client):
    page = html(client.get("/"))
    assert '<html lang="zh-CN"' in page
    assert "找到作品" in page


def test_browser_language_picks_english(client):
    page = html(client.get("/", headers=EN))
    assert '<html lang="en"' in page
    assert "Find a work" in page


def test_choosing_a_language_is_remembered(client):
    response = client.get("/?lang=en", headers=ZH)
    assert "Find a work" in html(response)
    assert "lang=en" in response.headers["Set-Cookie"]
    assert "Find a work" in html(client.get("/", headers=ZH))


def test_unknown_language_is_ignored(client):
    assert '<html lang="zh-CN"' in html(client.get("/?lang=fr"))


def test_language_switch_keeps_the_page(client):
    page = html(client.get("/w/02"))
    assert 'href="/w/02?lang=en"' in page


# --- home and finding a work --------------------------------------------------------


def test_home_lists_every_work(client):
    page = html(client.get("/", headers=EN))
    for code in ("01", "02", "03"):
        assert f'href="/w/{code}"' in page


@pytest.mark.parametrize("typed", ["1", "01", " 01 ", "No. 1"])
def test_label_number_opens_the_work(client, typed):
    response = client.get("/go", query_string={"code": typed})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/w/01")


def test_unknown_number_explains_and_keeps_what_was_typed(client):
    response = client.get("/go?code=99", headers=EN)
    page = html(response)
    assert response.status_code == 404
    assert "There is no work numbered 99" in page
    assert 'role="alert"' in page and 'aria-invalid="true"' in page
    assert 'value="99"' in page


def test_empty_number_asks_for_one(client):
    assert "Please enter the number" in html(client.get("/go?code=", headers=EN))


def test_typed_text_is_escaped(client):
    page = html(client.get("/go", query_string={"code": "<b>x"}, headers=EN))
    assert "<b>x" not in page


# --- the work page ----------------------------------------------------------------


def test_short_code_redirects_to_the_canonical_page(client):
    response = client.get("/w/1")
    assert response.status_code == 302 and response.headers["Location"].endswith("/w/01")


def test_unknown_work_is_a_friendly_404(client):
    response = client.get("/w/77", headers=EN)
    assert response.status_code == 404
    from kanjian.i18n import t

    assert f"<h1>{t('not_found_title', 'en')}</h1>" in html(response)
    assert t("back_to_list", "en") in html(response)


@pytest.mark.parametrize("code", ["01", "02", "03"])
def test_work_page_has_four_layers_and_every_statement(client, app, code):
    work = app.extensions["kanjian_corpus"].get().get(code)
    page = html(client.get(f"/w/{code}", headers=EN))
    assert len(re.findall(r'<section class="layer"', page)) == 4
    statements = sum(len(stop["segments"]) for layer in work["layers"] for stop in layer["stops"])
    assert page.count('class="seg seg--') == statements
    assert page.count("seg seg--verified") == work["stats"]["verified"]


def test_every_statement_is_labelled_in_text_not_only_colour(client):
    page = html(client.get("/w/01", headers=EN))
    assert page.count('class="tag tag--verified"') >= 1
    assert page.count('class="tag tag--inferred"') >= 1
    assert "AI description · not verified" in page


def test_verified_statements_link_to_their_source(client):
    page = html(client.get("/w/01", headers=EN))
    assert 'href="#source-1"' in page and 'id="source-1"' in page
    assert 'aria-label="Source 1:' in page


def test_handscroll_sections_are_counted_and_run_right_to_left(client):
    page = html(client.get("/w/01", headers=EN))
    assert "Section 1 of 5" in page and "Section 5 of 5" in page
    assert "5 sections, from right to left." in page


def test_chinese_inside_english_is_marked_for_screen_readers(client):
    page = html(client.get("/w/01", headers=EN))
    assert '<span lang="zh-CN">吴兴钱选舜举</span>' in page


def test_chinese_page_is_not_wrapped_in_spans(client):
    page = html(client.get("/w/01", headers=ZH))
    main = page.split('<main id="main"', 1)[1]
    assert '<span lang="zh-CN">' not in main.split('class="layers"', 1)[1].split('class="sources"', 1)[0]


def test_work_page_works_without_the_script(client):
    # The player starts hidden; the descriptions are plain text that needs no script to read.
    page = html(client.get("/w/03", headers=EN))
    assert 'id="player" aria-label="Audio guide controls" hidden' in page
    assert page.count('class="seg-text"') > 10


def test_image_has_size_and_alt_text(client):
    page = html(client.get("/w/02", headers=EN))
    img = re.search(r'<img class="viewer-image"[^>]*>', page).group(0)
    assert re.search(r'alt="[^"]{20,}"', img)
    assert re.search(r'width="\d+"', img) and re.search(r'height="\d+"', img)


def test_page_data_for_the_viewer_is_valid_json(client):
    page = html(client.get("/w/03", headers=EN))
    block = re.search(r'<script type="application/json" id="kj-work">(.*?)</script>', page, re.S).group(1)
    images = json.loads(block)["images"]
    assert set(images) == {"opening", "cart", "battle", "river", "signature"}
    strings = re.search(r'<script type="application/json" id="kj-strings">(.*?)</script>', page, re.S).group(1)
    assert json.loads(strings)["btn_play"] == "Play"


# --- other pages ---------------------------------------------------------------------


def test_corpus_page_shows_the_verified_share(client):
    page = html(client.get("/corpus", headers=EN))
    assert "<caption" in page and "15%" in page
    assert page.count("<tr>") == 1 + 3 + 1  # header, three works, total


def test_labels_page_has_a_qr_code_per_work(client, monkeypatch):
    monkeypatch.setenv("KANJIAN_PUBLIC_URL", "https://guide.example.org/")
    page = html(client.get("/labels", headers=EN))
    assert page.count("<svg") >= 3
    assert "https://guide.example.org/w/01" in page
    assert 'role="alert"' not in page  # no "only this computer" or "no QR library" warning


def test_labels_warn_when_only_this_computer_can_open_them(client, monkeypatch):
    monkeypatch.delenv("KANJIAN_PUBLIC_URL", raising=False)
    monkeypatch.setattr("app.lan_address", lambda: None)
    page = html(client.get("/labels", headers=EN))
    assert 'role="alert"' in page


def test_favicon(client):
    assert client.get("/favicon.ico").headers["Location"].endswith("/static/favicon.svg")
    assert client.get("/static/favicon.svg").status_code == 200


def test_security_headers(client):
    headers = client.get("/").headers
    assert "default-src 'self'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_no_inline_scripts_that_the_policy_would_block(client):
    for path in ("/", "/w/01", "/labels", "/corpus"):
        page = html(client.get(path))
        for tag in re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>", page):
            assert 'type="application/json"' in tag, (path, tag)
        assert not re.search(r"\son[a-z]+=", page), path


# --- JSON API ---------------------------------------------------------------------------


def test_api_lists_works(client):
    data = client.get("/api/works").get_json()
    assert data["target"] == 0.95
    assert [w["code"] for w in data["works"]] == ["01", "02", "03"]
    assert data["works"][0]["url"] == "/api/works/01"


def test_api_work_keeps_both_languages_and_sources(client):
    data = client.get("/api/works/1").get_json()
    assert data["code"] == "01" and set(data["title"]) == {"zh", "en"}
    segments = [s for layer in data["layers"] for stop in layer["stops"] for s in stop["segments"]]
    assert all(s["source"] == "met" for s in segments if s["status"] == "verified")
    assert all(s["source"] is None for s in segments if s["status"] == "inferred")
    assert data["images"]["main"]["url"].startswith("/static/")


def test_api_json_is_utf8_not_escaped(client):
    assert "王羲之" in client.get("/api/works/01").get_data(as_text=True)


def test_api_errors_are_json(client):
    assert client.get("/api/works/99").get_json() == {"error": "not found"}
    assert client.get("/api/nothing").get_json() == {"error": "not found"}


# --- the corpus reloads while the app runs --------------------------------------------------


def test_editing_a_data_file_shows_up_without_a_restart(corpus_dir, sample_work):
    data, static, write = corpus_dir
    path = write("work", sample_work)
    client = create_app(data, static).test_client()
    assert "Wang Xizhi Watching Geese" in html(client.get("/w/01", headers=EN))

    sample_work["title"]["en"] = "A Renamed Scroll"
    path.write_text(json.dumps(sample_work, ensure_ascii=False), encoding="utf-8")
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
    assert "A Renamed Scroll" in html(client.get("/w/01", headers=EN))


def test_a_broken_file_does_not_take_the_site_down(corpus_dir, sample_work):
    data, static, write = corpus_dir
    write("good", sample_work)
    (data / "bad.json").write_text("{", encoding="utf-8")
    client = create_app(data, static).test_client()
    assert client.get("/").status_code == 200
    assert client.get("/w/01").status_code == 200
    assert "JSON" in html(client.get("/corpus", headers=EN))


# --- helpers ------------------------------------------------------------------------------------


def test_mark_chinese_wraps_runs_and_escapes_the_rest():
    out = str(mark_chinese("It reads 吴兴钱选舜举: <Qian Xuan>."))
    assert out == 'It reads <span lang="zh-CN">吴兴钱选舜举</span>: &lt;Qian Xuan&gt;.'


def test_mark_chinese_keeps_chinese_punctuation_inside_a_run():
    out = str(mark_chinese("The line 昨风起西，又起东。 ends."))
    assert '<span lang="zh-CN">昨风起西，又起东。</span>' in out


def test_mark_chinese_leaves_plain_english_alone():
    assert str(mark_chinese("No Chinese here.")) == "No Chinese here."


@pytest.mark.parametrize(
    "host, expected",
    [("localhost", True), ("127.0.0.1", True), ("::1", True), ("192.168.1.5", False), ("example.org", False)],
)
def test_loopback_detection(host, expected):
    assert _is_loopback(host) is expected
