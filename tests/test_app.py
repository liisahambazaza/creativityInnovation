"""The web pages and the JSON API, through Flask's test client."""

from __future__ import annotations

import pytest

from app import LEGACY_CODES, create_app, mark_chinese
from tests.conftest import DATA

ZH, EN = {"Accept-Language": "zh-CN"}, {"Accept-Language": "en-US"}
WORK_IDS = sorted(p.stem for p in DATA.glob("*.json"))


def html(response) -> str:
    return response.get_data(as_text=True)


# --- language --------------------------------------------------------------------


def test_home_defaults_to_chinese(client):
    page = html(client.get("/"))
    assert '<html lang="zh-CN"' in page
    assert "中国书画入门" in page


def test_browser_language_picks_english(client):
    page = html(client.get("/", headers=EN))
    assert '<html lang="en"' in page
    assert "An introduction to Chinese painting and calligraphy" in page


def test_choosing_a_language_is_remembered(client):
    response = client.get("/?lang=en", headers=ZH)
    assert "lang=en" in response.headers["Set-Cookie"]
    assert '<html lang="en"' in html(client.get("/", headers=ZH))


def test_language_links_keep_the_page(client):
    page = html(client.get("/w/npm-1195?lang=en"))
    assert 'href="/w/npm-1195?lang=zh"' in page


# --- gallery -----------------------------------------------------------------------


def test_gallery_lists_every_work_grouped_by_dynasty(client):
    page = html(client.get("/?lang=en"))
    for work_id in WORK_IDS:
        assert f'href="/w/{work_id}"' in page
    assert page.index('id="era-tang"') < page.index('id="era-song"') < page.index('id="era-yuan"')
    assert "13 works" in page or f"{len(WORK_IDS)} works" in page


def test_gallery_filter_shows_only_that_category(client):
    page = html(client.get("/?category=calligraphy&lang=en"))
    assert 'href="/w/npm-14901"' in page  # Huaisu
    assert 'href="/w/npm-1195"' not in page  # Fan Kuan, a painting
    assert 'aria-current="true">Calligraphy' in page


def test_unknown_filter_shows_everything(client):
    assert html(client.get("/?category=sculpture")).count('class="card') >= len(WORK_IDS)


# --- work pages ------------------------------------------------------------------


@pytest.mark.parametrize("work_id", WORK_IDS)
@pytest.mark.parametrize("headers", [ZH, EN], ids=["zh", "en"])
def test_every_work_page_renders(client, work_id, headers):
    response = client.get(f"/w/{work_id}", headers=headers)
    assert response.status_code == 200
    page = html(response)
    assert 'class="viewer' in page and 'class="badge"' in page
    assert 'class="details"' in page


def test_work_page_shows_intro_museum_text_and_credit(client):
    page = html(client.get("/w/npm-1195?lang=en"))
    assert "AI-drafted · not reviewed" in page
    assert "A single mountain fills most of this tall silk scroll" in page
    assert "Fan K&#39;uan has long been considered" in page
    assert (
        "Travelers Among Mountains and Streams The National Palace Museum, Taipei, CC BY 4.0 @ www.npm.gov.tw" in page
    )
    assert 'href="https://digitalarchive.npm.gov.tw/opendata/Pub/Detail/1195?dep=P"' in page


def test_chinese_inside_english_is_marked(client):
    page = html(client.get("/w/npm-1195?lang=en"))
    assert '<span lang="zh">范寬</span>' in page


def test_text_only_in_the_other_language_is_marked_with_its_language(client):
    # The Met gives no Chinese title for Ni Zan's painting; ours is an override,
    # but the Cleveland museum text exists only in English.
    page = html(client.get("/w/cma-130361?lang=zh"))
    assert "馆方只提供英文说明。" in page
    assert '<p><span lang="en">' in page


def test_record_without_museum_text_says_so(client):
    page = html(client.get("/w/met-45636?lang=en"))
    assert "The museum&#39;s record has no descriptive text" in page


def test_handscroll_page_is_a_scroll_viewer(client):
    assert 'data-scroll-start="right"' in html(client.get("/w/npm-1194"))
    assert 'data-scroll-start="right"' not in html(client.get("/w/npm-1195"))


def test_image_choice_note_is_shown(client):
    assert "The painting only" in html(client.get("/w/npm-909?lang=en"))


def test_previous_and_next_links(client):
    page = html(client.get("/w/npm-14901?lang=en"))  # the oldest work: no previous
    assert 'rel="next"' in page and 'rel="prev"' not in page


@pytest.mark.parametrize("code, work_id", sorted(LEGACY_CODES.items()))
def test_old_label_numbers_redirect(client, code, work_id):
    response = client.get(f"/w/{code}")
    assert response.status_code == 301
    assert response.headers["Location"].endswith(f"/w/{work_id}")


def test_unknown_work_is_a_friendly_404(client):
    response = client.get("/w/nope?lang=en")
    assert response.status_code == 404
    assert "Page not found" in html(response)


def test_about_page_explains_sources_and_beijing(client):
    page = html(client.get("/about?lang=en"))
    assert "CC BY 4.0" in page and "CC0" in page
    assert "Palace Museum in Beijing" in page


# --- security headers --------------------------------------------------------------


def test_pages_send_security_headers(client):
    response = client.get("/")
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"


# --- JSON ------------------------------------------------------------------------


def test_api_lists_works(client):
    data = client.get("/api/works").get_json()
    assert [w["id"] for w in data["works"]] and {w["id"] for w in data["works"]} == set(WORK_IDS)
    assert data["works"][0]["thumbnail"].startswith("/static/img/works/")


def test_api_work_has_everything_and_says_what_is_ai_drafted(client):
    data = client.get("/api/works/npm-47").get_json()
    assert data["license"] == "CC BY 4.0"
    assert data["credit"]["en"].endswith("CC BY 4.0 @ www.npm.gov.tw")
    assert data["editorial"]["status"] == "ai_draft_not_reviewed"
    assert data["museum_text"]["zh"]


def test_api_unknown_work(client):
    response = client.get("/api/works/nope")
    assert response.status_code == 404
    assert response.get_json() == {"error": "not found"}


# --- helpers -----------------------------------------------------------------------


def test_mark_chinese():
    assert str(mark_chinese("The poem 行到水窮處 ends")) == 'The poem <span lang="zh">行到水窮處</span> ends'
    assert str(mark_chinese("<b>")) == "&lt;b&gt;"


def test_edited_files_are_picked_up_without_a_restart(collection_dir, sample_work):
    data, static, write = collection_dir
    application = create_app(data_dir=data, static_dir=static)
    client = application.test_client()
    assert client.get("/w/npm-1195").status_code == 404
    write(sample_work)
    assert client.get("/w/npm-1195").status_code == 200
