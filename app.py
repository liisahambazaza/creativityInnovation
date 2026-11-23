"""Kànjiàn prototype web app: an introduction to Chinese painting and calligraphy.

Run it with ``make run`` (this computer only) or ``make phone`` (also reachable
from phones on the same Wi-Fi), or directly: ``python app.py [--lan] [--port N]``.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import re
import socket
from pathlib import Path

from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for
from markupsafe import Markup, escape

from kanjian import i18n, periods
from kanjian.museums import MUSEUMS, credit
from kanjian.works import CATEGORIES, LANGS, Collection, load_collection

ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8000
# Addresses of the first prototype, kept working for old links and printed labels.
LEGACY_CODES = {"01": "met-40081", "02": "met-45636", "03": "met-39919"}
# Wider than this (width ÷ height), an image is shown as a scroll you move along.
SCROLL_RATIO = 2.4

# A run of Chinese characters, allowing Chinese punctuation inside it.
_HAN = "⺀-⿟々-〇㐀-䶿一-鿿豈-﫿"
_HAN_PUNCT = "、-〃〈-】〔-〟！-／：-＠［-｀｛-･‘’“”—…·"
_HAN_RUN = re.compile(f"[{_HAN}]+(?:[{_HAN_PUNCT}]+[{_HAN}]+)*[。！？]?")


def mark_chinese(text: str) -> Markup:
    """Wrap Chinese inside English text in ``<span lang="zh">``, so browsers pick a
    Chinese font for it and the read-aloud voice switches to Mandarin."""
    out, last = [], 0
    for match in _HAN_RUN.finditer(text):
        out.append(escape(text[last : match.start()]))
        out.append(Markup('<span lang="zh">%s</span>') % match.group(0))
        last = match.end()
    out.append(escape(text[last:]))
    return Markup("").join(out)


class CollectionCache:
    """Reload the collection whenever a work file is added, removed or edited."""

    def __init__(self, data_dir: Path, static_dir: Path, logger):
        self.data_dir, self.static_dir, self.logger = Path(data_dir), Path(static_dir), logger
        self._stamp = None
        self._collection: Collection | None = None

    def get(self) -> Collection:
        stamp = tuple(sorted((p.name, p.stat().st_mtime_ns) for p in self.data_dir.glob("*.json")))
        if self._collection is None or stamp != self._stamp:
            self._collection = load_collection(self.data_dir, self.static_dir)
            self._stamp = stamp
            for problem in self._collection.errors:
                self.logger.warning("collection %s", problem)
        return self._collection


def lan_address() -> str | None:
    """Best guess at this computer's address on the local network."""
    candidates: list[str] = []
    for target in ("192.168.0.1", "10.0.0.1", "172.16.0.1", "8.8.8.8"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((target, 9))  # UDP: picks a route, sends nothing
                candidates.append(sock.getsockname()[0])
        except OSError:
            continue
    try:
        candidates += [info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
    except OSError:
        pass
    private = [
        c
        for c in dict.fromkeys(candidates)
        if ipaddress.ip_address(c).is_private and not ipaddress.ip_address(c).is_loopback
    ]
    private.sort(key=lambda c: (not c.startswith("192.168."), not c.startswith("10.")))
    return private[0] if private else None


def create_app(data_dir: Path | None = None, static_dir: Path | None = None) -> Flask:
    static_dir = Path(static_dir or ROOT / "static")
    app = Flask(__name__, static_folder=str(static_dir), template_folder=str(ROOT / "templates"))
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.json.ensure_ascii = False
    cache = CollectionCache(Path(data_dir or ROOT / "data" / "works"), static_dir, app.logger)
    app.extensions["kanjian_collection"] = cache

    # --- language ---------------------------------------------------------------

    @app.before_request
    def pick_language():
        asked = request.args.get("lang")
        if asked in LANGS:
            g.lang, g.lang_chosen = asked, True
        elif request.cookies.get("lang") in LANGS:
            g.lang, g.lang_chosen = request.cookies["lang"], False
        else:
            g.lang = request.accept_languages.best_match(LANGS, default="zh")
            g.lang_chosen = False

    @app.after_request
    def finish(response):
        if g.get("lang_chosen"):
            response.set_cookie("lang", g.lang, max_age=365 * 24 * 3600, samesite="Lax")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; object-src 'none'; "
            "base-uri 'self'; form-action 'self'; frame-ancestors 'none'",
        )
        return response

    def t(key: str, **values) -> str:
        return i18n.t(key, g.lang, **values)

    def lang_url(target: str) -> str:
        args = {k: v for k, v in request.args.items() if k != "lang"}
        if request.endpoint and request.endpoint != "static":
            return url_for(request.endpoint, **(request.view_args or {}), **args, lang=target)
        return url_for("home", lang=target)

    def show(field: dict | None) -> Markup:
        """A two-language field in the visitor's language. If only the other language
        exists, show that, marked with its language so it is read and rendered right."""
        field = field or {}
        text, lang = field.get(g.lang, ""), g.lang
        if not text:
            lang = "en" if g.lang == "zh" else "zh"
            text = field.get(lang, "")
        if not text:
            return Markup("")
        body = mark_chinese(text) if lang == "en" else escape(text)
        if lang != g.lang:
            return Markup('<span lang="%s">%s</span>') % (lang, body)
        return body

    def paragraphs(field: dict | None) -> list[Markup]:
        field = field or {}
        text = field.get(g.lang) or field.get("en" if g.lang == "zh" else "zh") or ""
        lang = g.lang if field.get(g.lang) else ("en" if g.lang == "zh" else "zh")
        return [show({lang: p}) for p in text.split("\n") if p.strip()]

    @app.context_processor
    def template_globals():
        return {
            "lang": g.lang,
            "html_lang": "zh-CN" if g.lang == "zh" else "en",
            "t": t,
            "lang_url": lang_url,
            "show": show,
            "paragraphs": paragraphs,
            "js_strings": i18n.js_strings(g.lang),
        }

    @app.template_filter("cjk")
    def cjk_filter(text: str) -> Markup:
        return mark_chinese(text) if g.lang == "en" else escape(text)

    # --- what a work page needs -------------------------------------------------------

    def present(work: dict) -> dict:
        museum = MUSEUMS[work["museum"]]
        image = work["image"]
        ratio = image["width"] / image["height"] if image["height"] else 1
        museum_text = work["museum_text"]
        if museum_text[g.lang]:
            museum_note = ""
        elif museum_text["zh"] or museum_text["en"]:
            museum_note = t("museum_text_only_zh") if museum_text["zh"] else t("museum_text_only_en")
        else:
            museum_note = t("museum_text_none")
        details = [
            ("cat_artist", show(work["artist"]) or t("unknown_artist")),
            ("cat_period", periods.label(work["period"], g.lang)),
            ("cat_date", show(work["date"])),
            ("cat_format", t("format_" + work["format"])),
            ("cat_medium", show(work["medium"])),
            ("cat_dimensions", show(work["dimensions"])),
            ("cat_museum", museum["name"][g.lang]),
            ("cat_object_number", work["record"].get("object_number", "")),
            ("cat_credit_line", show(work["credit_line"])),
        ]
        previous, following = cache.get().neighbours(work["id"])
        return {
            "museum": museum,
            "credit": credit(work["museum"], g.lang, work["title"]),
            "scroll": ratio >= SCROLL_RATIO,
            "image_url": url_for("static", filename=image["src"]),
            "museum_note": museum_note,
            "details": [(key, value) for key, value in details if value],
            "previous": previous,
            "next": following,
        }

    # --- pages -------------------------------------------------------------------

    @app.get("/")
    def home():
        category = request.args.get("category")
        if category not in CATEGORIES:
            category = None
        collection = cache.get()
        return render_template(
            "index.html",
            groups=collection.by_era(category),
            category=category,
            total=len(collection.works),
            museums=MUSEUMS,
        )

    @app.get("/w/<work_id>")
    def work(work_id: str):
        if work_id in LEGACY_CODES:
            return redirect(url_for("work", work_id=LEGACY_CODES[work_id]), 301)
        found = cache.get().get(work_id)
        if found is None:
            abort(404)
        return render_template("work.html", work=found, view=present(found))

    @app.get("/about")
    def about():
        return render_template("about.html")

    # --- JSON --------------------------------------------------------------------------

    def work_json(work: dict, full: bool = False) -> dict:
        data = {
            "id": work["id"],
            "museum": work["museum"],
            "category": work["category"],
            "format": work["format"],
            "period": work["period"],
            "year": work["year"],
            "title": work["title"],
            "artist": work["artist"],
            "image": url_for("static", filename=work["image"]["src"]),
            "thumbnail": url_for("static", filename=work["image"]["thumb"]),
            "url": url_for("work", work_id=work["id"]),
            "api": url_for("api_work", work_id=work["id"]),
        }
        if full:
            data.update(
                {
                    field: work[field]
                    for field in ("date", "medium", "dimensions", "museum_text", "credit_line", "record")
                }
            )
            data["credit"] = {lang: credit(work["museum"], lang, work["title"]) for lang in LANGS}
            data["license"] = MUSEUMS[work["museum"]]["license"]
            data["editorial"] = {
                "status": "ai_draft_not_reviewed",
                "intro": work["intro"],
                "look_for": work["look_for"],
                "alt": work["alt"],
            }
        return data

    @app.get("/api/works")
    def api_works():
        return jsonify({"works": [work_json(w) for w in cache.get().works]})

    @app.get("/api/works/<work_id>")
    def api_work(work_id: str):
        found = cache.get().get(work_id)
        if found is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(work_json(found, full=True))

    @app.get("/favicon.ico")
    def favicon():
        return redirect(url_for("static", filename="favicon.svg"))

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "not found"}), 404
        return render_template("404.html"), 404

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Kànjiàn prototype.")
    parser.add_argument("--lan", action="store_true", help="also accept connections from phones on the same network")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)))
    args = parser.parse_args()

    app = create_app()
    collection = app.extensions["kanjian_collection"].get()
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        museums = sorted({w["museum"] for w in collection.works})
        print(f"\nKànjiàn: {len(collection.works)} works from {', '.join(museums)}.")
        print(f"  On this computer:  http://127.0.0.1:{args.port}")
        if args.lan:
            address = lan_address()
            if address:
                print(f"  On a phone (same Wi-Fi):  http://{address}:{args.port}")
            else:
                print("  No local network address found.")
        print()
    data_files = [str(p) for p in (ROOT / "data" / "works").glob("*.json")]
    app.run(
        host="0.0.0.0" if args.lan else "127.0.0.1",
        port=args.port,
        debug=False,
        use_reloader=True,
        extra_files=data_files,
    )


if __name__ == "__main__":
    main()
