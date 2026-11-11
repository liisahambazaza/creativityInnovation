"""The app in a real browser: accessibility, phone layout, and the audio player.

Uses the Google Chrome installed on this computer (no extra download). If it
cannot be started, these tests are skipped rather than failed; the checks
script says so, and CI installs a browser so they always run there.
"""

from __future__ import annotations

import json
import threading

import pytest
from werkzeug.serving import make_server

from tests.conftest import ROOT

pytestmark = pytest.mark.browser
AXE = ROOT / "tests" / "vendor" / "axe.min.js"
PAGES = ["/", "/w/01", "/w/02", "/w/03", "/labels", "/corpus", "/w/99"]

# A stand-in for the browser's voice: records what would be said and finishes each line quickly.
FAKE_SPEECH = """
(() => {
  window.__spoken = [];
  class Utterance { constructor(text) { this.text = text; this.lang = ''; this.pitch = 1; this.rate = 1; } }
  const synth = {
    speaking: false,
    getVoices: () => window.__voices || [],
    addEventListener: () => {},
    cancel: () => { synth._queue = []; },
    _queue: [],
    speak(u) {
      if (u.text.trim()) window.__spoken.push({ text: u.text, lang: u.lang, pitch: u.pitch, voice: u.voice ? u.voice.name : null });
      setTimeout(() => { u.onstart && u.onstart(); setTimeout(() => u.onend && u.onend(), 5); }, 5);
    },
  };
  Object.defineProperty(window, 'speechSynthesis', { value: synth, configurable: true });
  window.SpeechSynthesisUtterance = Utterance;
})();
"""


def prefs_script(**values) -> str:
    return f"localStorage.setItem('kanjian.prefs', {json.dumps(json.dumps(values))});"


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


def open_work(page, base_url, code):
    page.goto(f"{base_url}/w/{code}")
    page.wait_for_selector("html[data-player=ready]")


# --- accessibility and layout ----------------------------------------------------------


@pytest.mark.parametrize("lang", ["zh", "en"])
@pytest.mark.parametrize("path", PAGES)
def test_no_accessibility_violations(make_page, base_url, path, lang):
    page = make_page(lang)
    page.goto(f"{base_url}{path}")
    page.add_script_tag(path=str(AXE))
    result = page.evaluate("axe.run(document, { resultTypes: ['violations'] })")
    problems = [f"{v['id']} ({v['impact']}): {v['help']} — {len(v['nodes'])} element(s)" for v in result["violations"]]
    assert problems == [], "\n".join(problems)
    assert page.errors == []


@pytest.mark.parametrize("width", [320, 390, 1280])
@pytest.mark.parametrize("path", ["/", "/w/01", "/w/03", "/labels", "/corpus"])
def test_no_sideways_scrolling(make_page, base_url, path, width):
    page = make_page("en", width=width)
    page.goto(f"{base_url}{path}")
    overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 0, f"{path} is {overflow}px wider than a {width}px screen"


def test_largest_text_size_still_fits_a_phone(make_page, base_url):
    page = make_page("zh", width=320, init=[prefs_script(text="xlarge")])
    open_work(page, base_url, "01")
    assert page.get_attribute("html", "data-text") == "xlarge"
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_reads_fully_without_javascript(make_page, base_url):
    page = make_page("en", script=False)
    page.goto(f"{base_url}/w/01")
    assert page.locator("#player").is_hidden()
    assert page.locator(".seg").count() == 53
    assert all(page.locator(".layer-body").nth(i).is_visible() for i in range(4))


# --- the player with the built-in voice off (a screen-reader user) ---------------------------


def test_next_and_back_move_focus_through_the_parts(make_page, base_url):
    page = make_page("en", init=[prefs_script(voice="off")])
    open_work(page, base_url, "01")
    assert page.text_content("#player-status") == "Press Next to read part by part."

    page.click("#btn-next")  # layer 1 has one part, so this opens layer 2, section 1
    assert page.evaluate("document.activeElement.closest('.stop').id") == "stop-2-1"
    assert page.text_content("#player-status") == "Layer 2: Composition · Section 1 of 5"
    assert page.get_attribute("#layer-2 .layer-toggle", "aria-expanded") == "true"

    page.click("#btn-next")
    assert page.evaluate("document.activeElement.closest('.stop').id") == "stop-2-2"
    page.click("#btn-prev")
    assert page.evaluate("document.activeElement.closest('.stop').id") == "stop-2-1"
    assert page.errors == []


def test_viewer_pans_right_to_left_along_the_handscroll(make_page, base_url):
    page = make_page("en", init=[prefs_script(voice="off")])
    open_work(page, base_url, "01")
    offsets = []
    for _ in range(5):
        page.click("#btn-next")
        transform = page.get_attribute(".viewer-image", "style")
        offsets.append(float(transform.split("translate(")[1].split("px")[0]))
    # moving left along the scroll means the image slides right
    assert offsets == sorted(offsets), offsets


def test_layer_headings_open_and_close(make_page, base_url):
    page = make_page("en", init=[prefs_script(voice="off")])
    open_work(page, base_url, "02")
    toggle = page.locator("#layer-3 .layer-toggle")
    assert toggle.get_attribute("aria-expanded") == "false" and page.locator("#layer-3-body").is_hidden()
    toggle.click()
    assert toggle.get_attribute("aria-expanded") == "true" and page.locator("#layer-3-body").is_visible()
    toggle.click()
    assert page.locator("#layer-3-body").is_hidden()


def test_another_calligraphy_image_is_shown_per_passage(make_page, base_url):
    page = make_page("en", init=[prefs_script(voice="off")])
    open_work(page, base_url, "03")
    page.click("#layer-3 .layer-toggle")  # opening the brushwork layer selects its first passage
    seen = []
    for index, stop in enumerate(page.locator("#layer-3 [data-stop]").all()):
        if index:
            page.click("#btn-next")
        assert "is-current" in stop.get_attribute("class").split()
        seen.append(page.get_attribute(".viewer-image", "src").rsplit("/", 1)[-1])
    assert len(set(seen)) >= 2, seen


# --- the player with the built-in voice on (stand-in voice) -----------------------------------


def play_until(page, done_js, timeout=10_000):
    page.click("#btn-play")
    page.wait_for_function(done_js, timeout=timeout)
    return page.evaluate("window.__spoken")


def test_play_announces_the_layer_and_marks_each_kind_of_statement(make_page, base_url):
    page = make_page("en", init=[FAKE_SPEECH, prefs_script(voice="on")])
    open_work(page, base_url, "01")
    spoken = play_until(
        page, "document.querySelector('#player').dataset.state === 'paused' && window.__spoken.length > 3"
    )
    texts = [s["text"] for s in spoken]
    assert texts[0].startswith("Layer 1 of 4: Orientation.")
    assert "Verified." in texts and "AI description, not verified." in texts
    # AI descriptions are spoken lower, so the difference can be heard
    pitches = {s["pitch"] for s in spoken if s["text"] == "AI description, not verified."}
    assert pitches == {0.85}
    # ends the layer by saying what comes next, then waits for the listener
    assert texts[-1] == "End of Orientation. Press Next to go deeper: Composition, scroll traversal."
    assert page.evaluate("document.querySelector('.stop.is-current').id") == "stop-1-1"
    assert page.errors == []


def test_handscroll_plays_section_after_section_and_stops_at_the_layer_end(make_page, base_url):
    page = make_page("en", init=[FAKE_SPEECH, prefs_script(voice="on", auto=True)])
    open_work(page, base_url, "01")
    page.click("#btn-next")  # to layer 2: the traversal
    page.wait_for_function("window.__spoken.length > 0")
    page.wait_for_function(
        "document.querySelector('#player').dataset.state === 'paused' && "
        "document.querySelector('.stop.is-current').id === 'stop-2-5'",
        timeout=15_000,
    )
    texts = [s["text"] for s in page.evaluate("window.__spoken")]
    for n in range(1, 6):
        assert f"Section {n} of 5." in texts
    assert page.evaluate("document.querySelector('.stop.is-current').id") == "stop-2-5"


def test_chinese_inside_english_gets_a_mandarin_voice(make_page, base_url):
    page = make_page("en", init=[FAKE_SPEECH, prefs_script(voice="on", auto=True)])
    open_work(page, base_url, "01")
    page.click("#btn-next")
    page.wait_for_function("window.__spoken.some(s => s.lang === 'zh-CN')", timeout=15_000)
    zh = [s for s in page.evaluate("window.__spoken") if s["lang"] == "zh-CN"]
    assert all(any("一" <= ch <= "鿿" for ch in s["text"]) for s in zh)


VOICES_WITH_AVA = """
window.__voices = [
  { name: 'Samantha', lang: 'en-US', localService: true },
  { name: 'Ava', lang: 'en-US', localService: true },
  { name: 'Ava (Premium)', lang: 'en-US', localService: true },
  { name: 'Avani', lang: 'en-IN', localService: true },
  { name: 'Tingting', lang: 'zh-CN', localService: true },
];
"""


def test_english_prefers_the_best_installed_ava_voice(make_page, base_url):
    page = make_page("en", init=[VOICES_WITH_AVA, FAKE_SPEECH, prefs_script(voice="on", auto=True)])
    open_work(page, base_url, "01")
    page.click("#btn-next")
    page.wait_for_function("window.__spoken.some(s => s.lang === 'zh-CN')", timeout=15_000)
    spoken = page.evaluate("window.__spoken")
    assert {s["voice"] for s in spoken if s["lang"] == "en-US"} == {"Ava (Premium)"}
    assert {s["voice"] for s in spoken if s["lang"] == "zh-CN"} == {"Tingting"}


def test_verified_only_skips_ai_descriptions(make_page, base_url):
    page = make_page("en", init=[FAKE_SPEECH, prefs_script(voice="on", verifiedOnly=True)])
    open_work(page, base_url, "01")
    spoken = play_until(
        page, "document.querySelector('#player').dataset.state === 'paused' && window.__spoken.length > 2"
    )
    texts = [s["text"] for s in spoken]
    assert "AI description, not verified." not in texts
    assert "Verified." in texts
    assert page.get_attribute("html", "data-verified-only") == ""


def test_settings_are_saved_on_the_device(make_page, base_url):
    page = make_page("en")
    open_work(page, base_url, "02")
    page.click("#settings summary")
    page.check("input[name=text][value=large]")
    page.check("input[name=voice][value=off]")
    assert page.get_attribute("html", "data-text") == "large"
    page.reload()
    page.wait_for_selector("html[data-player=ready]")
    assert page.get_attribute("html", "data-text") == "large"
    assert page.is_checked("input[name=voice][value=off]")
    assert page.text_content("#player-status") == "Press Next to read part by part."


def test_speech_that_never_starts_is_reported_not_hung(make_page, base_url):
    # Some phones have no voice installed: speak() is accepted but nothing ever happens.
    silent = FAKE_SPEECH.replace(
        "setTimeout(() => { u.onstart && u.onstart(); setTimeout(() => u.onend && u.onend(), 5); }, 5);", ""
    )
    page = make_page("en", init=[silent, prefs_script(voice="on")])
    open_work(page, base_url, "01")
    page.click("#btn-play")
    page.wait_for_selector("#player-notice:not([hidden])", timeout=12_000)
    assert page.get_attribute("#player", "data-state") == "paused"
