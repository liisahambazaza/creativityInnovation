"""The app in a real browser: page quality checks, phone layout, the handscroll viewer
and read-aloud.

Uses the Google Chrome installed on this computer (no extra download). If it
cannot be started, these tests are skipped rather than failed; the checks
script says so, and CI installs a browser so they always run there.
"""

from __future__ import annotations

import threading

import pytest
from werkzeug.serving import make_server

from tests.conftest import ROOT

pytestmark = pytest.mark.browser
AXE = ROOT / "tests" / "vendor" / "axe.min.js"
PAGES = ["/", "/?category=calligraphy", "/about", "/w/npm-1195", "/w/npm-1194", "/w/cma-136951", "/w/nope"]

# A stand-in for the browser's voice: offers some voices, records what would be said,
# and finishes each line quickly.
FAKE_SPEECH = """
(() => {
  window.__spoken = [];
  const voices = [
    { name: 'Eddy (Chinese (China mainland))', lang: 'zh-CN', localService: true },
    { name: 'Tingting', lang: 'zh-CN', localService: true },
    { name: 'Samantha', lang: 'en-US', localService: true },
    { name: 'Ava (Premium)', lang: 'en-US', localService: true },
  ];
  class Utterance { constructor(text) { this.text = text; this.lang = ''; } }
  const synth = {
    getVoices: () => voices,
    addEventListener: () => {},
    cancel: () => {},
    speak(u) {
      window.__spoken.push({ text: u.text, lang: u.lang, voice: u.voice ? u.voice.name : null });
      setTimeout(() => { u.onstart && u.onstart(); setTimeout(() => u.onend && u.onend(), 5); }, 5);
    },
  };
  Object.defineProperty(window, 'speechSynthesis', { value: synth, configurable: true });
  window.SpeechSynthesisUtterance = Utterance;
})();
"""

SCROLL_LEFT_OF_END = (
    "(() => { const f = document.querySelector('.viewer-frame');"
    " return f.scrollWidth - f.clientWidth - f.scrollLeft; })()"
)


@pytest.fixture(scope="module")
def base_url():
    from app import create_app

    server = make_server("127.0.0.1", 0, create_app(), threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as p:
        launched = None
        for options in ({"channel": "chrome"}, {}):
            try:
                launched = p.chromium.launch(headless=True, **options)
                break
            except Exception:  # noqa: BLE001 - try the next way of finding a browser
                continue
        if launched is None:
            pytest.skip("no Chrome or Chromium available for browser tests")
        yield launched
        launched.close()


@pytest.fixture
def make_page(browser):
    contexts = []

    def make(lang="en", width=390, script=True, init: list[str] | None = None):
        ctx = browser.new_context(
            viewport={"width": width, "height": 844},
            locale="en-US" if lang == "en" else "zh-CN",
            java_script_enabled=script,
            bypass_csp=True,  # only so axe can be injected; the app itself never needs it
        )
        contexts.append(ctx)
        page = ctx.new_page()
        page.errors = []
        page.on("pageerror", lambda exc: page.errors.append(str(exc)))
        # Broken files (images, scripts, styles) count as errors; a page's own 404 status does not.
        page.on(
            "console",
            lambda msg: (
                msg.type == "error"
                and not msg.text.startswith("Failed to load resource")
                and page.errors.append(msg.text)
            ),
        )
        page.on(
            "response",
            lambda r: (
                r.status >= 400 and r.request.resource_type != "document" and page.errors.append(f"{r.status} {r.url}")
            ),
        )
        for item in init or []:
            page.add_init_script(item)
        return page

    yield make
    for ctx in contexts:
        ctx.close()


# --- page quality and layout ---------------------------------------------------------


@pytest.mark.parametrize("lang", ["zh", "en"])
@pytest.mark.parametrize("path", PAGES)
def test_pages_pass_the_axe_checker_and_load_cleanly(make_page, base_url, path, lang):
    page = make_page(lang)
    page.goto(f"{base_url}{path}")
    page.add_script_tag(path=str(AXE))
    result = page.evaluate("axe.run(document, { resultTypes: ['violations'] })")
    problems = [f"{v['id']} ({v['impact']}): {v['help']} — {len(v['nodes'])} element(s)" for v in result["violations"]]
    assert problems == [], "\n".join(problems)
    assert page.errors == []


@pytest.mark.parametrize("width", [320, 390, 1280])
@pytest.mark.parametrize("path", ["/", "/about", "/w/npm-1195", "/w/npm-1194", "/w/npm-909"])
def test_no_sideways_page_scrolling(make_page, base_url, path, width):
    page = make_page("en", width=width)
    page.goto(f"{base_url}{path}")
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 0, f"{path} is {overflow}px wider than a {width}px screen"


def test_every_gallery_image_loads(make_page, base_url):
    page = make_page("en", width=1280)
    page.goto(f"{base_url}/")
    page.evaluate("Promise.all([...document.images].map(i => { i.loading = 'eager'; return i.decode(); }))")
    broken = page.evaluate("[...document.images].filter(i => !i.naturalWidth).map(i => i.src)")
    assert broken == []
    assert page.errors == []


# --- handscroll viewer -------------------------------------------------------------


def test_handscroll_opens_at_its_right_hand_end_and_moves_with_arrow_keys(make_page, base_url):
    page = make_page("en", width=1000)
    page.goto(f"{base_url}/w/npm-1194")
    page.wait_for_function(
        "(() => { const f = document.querySelector('.viewer-frame');"
        " return f.scrollWidth > f.clientWidth && f.scrollLeft > 0; })()"
    )
    assert page.evaluate(SCROLL_LEFT_OF_END) <= 2
    page.locator(".viewer-frame").focus()
    page.keyboard.press("ArrowLeft")
    page.wait_for_function(f"{SCROLL_LEFT_OF_END} > 50")


def test_work_page_reads_fully_without_javascript(make_page, base_url):
    page = make_page("en", script=False)
    page.goto(f"{base_url}/w/npm-1195")
    assert page.locator(".read-aloud").is_hidden()
    assert page.locator(".look-for li").count() == 4
    assert page.locator(".museum-text").is_visible()


# --- read aloud ----------------------------------------------------------------------


def read_aloud(page):
    page.click("#btn-read")
    page.wait_for_function(
        "document.getElementById('btn-read').getAttribute('aria-pressed') === 'false' && window.__spoken.length > 3",
        timeout=10_000,
    )
    return page.evaluate("window.__spoken")


def test_read_aloud_uses_ava_for_english_and_mandarin_for_chinese_inside_it(make_page, base_url):
    page = make_page("en", init=[FAKE_SPEECH])
    page.goto(f"{base_url}/w/npm-1195")
    spoken = read_aloud(page)
    assert spoken[0]["text"] == "Travelers Among Mountains and Streams"
    assert {s["voice"] for s in spoken if s["lang"].startswith("en")} == {"Ava (Premium)"}
    assert [s["text"] for s in spoken if s["lang"].startswith("zh")] == ["范寬"]
    assert {s["voice"] for s in spoken if s["lang"].startswith("zh")} == {"Tingting"}
    assert page.errors == []


def test_read_aloud_in_chinese_prefers_tingting(make_page, base_url):
    page = make_page("zh", init=[FAKE_SPEECH])
    page.goto(f"{base_url}/w/npm-47")
    spoken = read_aloud(page)
    assert {s["voice"] for s in spoken} == {"Tingting"}
    assert any("早春" in s["text"] for s in spoken)


def test_read_aloud_can_be_stopped(make_page, base_url):
    page = make_page("en", init=[FAKE_SPEECH])
    page.goto(f"{base_url}/w/npm-1195")
    page.click("#btn-read")
    assert page.get_attribute("#btn-read", "aria-pressed") == "true"
    page.click("#btn-read")
    assert page.get_attribute("#btn-read", "aria-pressed") == "false"
    assert page.locator(".is-reading").count() == 0


def test_browser_without_speech_says_so(make_page, base_url):
    no_speech = "delete window.speechSynthesis; window.SpeechSynthesisUtterance = undefined;"
    page = make_page("en", init=[no_speech])
    page.goto(f"{base_url}/w/npm-1195")
    page.click("#btn-read")
    assert "cannot read aloud" in page.inner_text("#read-status")
