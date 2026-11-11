"""Kànjiàn prototype web app.

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
from urllib.parse import urlsplit

from flask import Flask, abort, g, jsonify, redirect, render_template, request, url_for
from markupsafe import Markup, escape

from kanjian import i18n
from kanjian.corpus import LANGS, VERIFIED_TARGET, Corpus, load_corpus

ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8000
# Layer modes whose parts have their own name when counted ("Section 2 of 5").
COUNTED_MODES = ("traversal", "reading_path", "brushwork")

# A run of Chinese characters, allowing Chinese punctuation inside it.
_HAN = "⺀-⿟々-〇㐀-䶿一-鿿豈-﫿"
_HAN_PUNCT = "、-〃〈-】〔-〟！-／：-＠［-｀｛-･‘’“”—…·"
_HAN_RUN = re.compile(f"[{_HAN}]+(?:[{_HAN_PUNCT}]+[{_HAN}]+)*[。！？]?")


def mark_chinese(text: str) -> Markup:
    """Wrap Chinese inside English text in ``<span lang="zh-CN">``.

    Screen readers then switch voice for it, and the built-in voice reads those
    spans with a Mandarin voice instead of skipping them.
    """
    out, last = [], 0
    for match in _HAN_RUN.finditer(text):
        out.append(escape(text[last : match.start()]))
        out.append(Markup('<span lang="zh-CN">%s</span>') % match.group(0))
        last = match.end()
    out.append(escape(text[last:]))
    return Markup("").join(out)


class CorpusCache:
    """Reload the corpus whenever a data file is added, removed or edited."""

    def __init__(self, data_dir: Path, static_dir: Path, logger):
        self.data_dir, self.static_dir, self.logger = Path(data_dir), Path(static_dir), logger
        self._stamp = None
        self._corpus: Corpus | None = None

    def get(self) -> Corpus:
        stamp = tuple(sorted((p.name, p.stat().st_mtime_ns) for p in self.data_dir.glob("*.json")))
        if self._corpus is None or stamp != self._stamp:
            self._corpus = load_corpus(self.data_dir, self.static_dir)
            self._stamp = stamp
            for problem in self._corpus.problems:
                self.logger.warning("corpus %s", problem)
        return self._corpus


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


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def create_app(data_dir: Path | None = None, static_dir: Path | None = None) -> Flask:
    static_dir = Path(static_dir or ROOT / "static")
    app = Flask(__name__, static_folder=str(static_dir), template_folder=str(ROOT / "templates"))
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.json.ensure_ascii = False
    cache = CorpusCache(Path(data_dir or ROOT / "data" / "works"), static_dir, app.logger)
    app.extensions["kanjian_corpus"] = cache

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

    @app.context_processor
    def template_globals():
        return {
            "lang": g.lang,
            "html_lang": "zh-CN" if g.lang == "zh" else "en",
            "t": t,
            "lang_url": lang_url,
            "js_strings": i18n.js_strings(g.lang),
        }

    @app.template_filter("cjk")
    def cjk_filter(text: str) -> Markup:
        return mark_chinese(text) if g.lang == "en" else escape(text)

    # --- what the work page needs, in the visitor's language ------------------------

    def layer_title(layer: dict, spoken: bool = False) -> str:
        title = t(f"layer_{layer['key']}")
        if layer["mode"]:
            joiner = "，" if spoken and g.lang == "zh" else ", " if spoken else " · "
            title = f"{title}{joiner}{t('mode_' + layer['mode'])}"
        return title

    def present(work: dict) -> dict:
        layers = []
        for index, layer in enumerate(work["layers"]):
            total = len(layer["stops"])
            # how the parts of this layer are counted aloud: sections, stops, passages or parts
            unit = layer["mode"] if layer["mode"] in COUNTED_MODES else "default"
            announce = t("say_layer", n=layer["n"], title=layer_title(layer, spoken=True))
            if total > 1:
                announce += " " + t(f"say_count_{unit}", total=total)
            if index + 1 < len(work["layers"]):
                ending = t(
                    "say_layer_end",
                    title=t(f"layer_{layer['key']}"),
                    next=layer_title(work["layers"][index + 1], spoken=True),
                )
            else:
                ending = t("say_work_end")
            layers.append(
                {
                    "n": layer["n"],
                    "key": layer["key"],
                    "title": layer_title(layer),
                    "status": t("layer_status", n=layer["n"], title=t(f"layer_{layer['key']}")),
                    "announce": announce,
                    "ending": ending,
                    "stops": [
                        {
                            "n": stop["n"],
                            "label": stop["label"][g.lang] if stop["label"] else None,
                            "position": t(f"pos_{unit}", n=stop["n"], total=total) if total > 1 else None,
                            "image": stop["image"],
                            "region": stop["region"],
                            "segments": stop["segments"],
                        }
                        for stop in layer["stops"]
                    ],
                }
            )
        images = {
            key: {
                "src": url_for("static", filename=image["src"]),
                "width": image["width"],
                "height": image["height"],
                "alt": image["alt"][g.lang],
                "credit": image["credit"][g.lang] if image["credit"] else "",
            }
            for key, image in work["images"].items()
        }
        credits = list(dict.fromkeys(image["credit"] for image in images.values() if image["credit"]))
        return {
            "layers": layers,
            "images": images,
            "first_image": next(iter(images.values()), None),
            "credits": credits,
        }

    # --- pages ----------------------------------------------------------------------

    @app.get("/")
    def home():
        return render_template("index.html", works=cache.get().works, error=None, entered="")

    @app.get("/go")
    def go():
        entered = request.args.get("code", "").strip()[:12]
        work = cache.get().get(entered)
        if work:
            return redirect(url_for("work", code=work["code"]))
        error = t("code_error", code=entered) if entered else t("code_empty")
        return render_template("index.html", works=cache.get().works, error=error, entered=entered), 404

    @app.get("/w/<code>")
    def work(code: str):
        found = cache.get().get(code)
        if found is None:
            abort(404)
        if code != found["code"]:
            return redirect(url_for("work", code=found["code"]))
        return render_template("work.html", work=found, view=present(found))

    @app.get("/labels")
    def labels():
        configured = os.environ.get("KANJIAN_PUBLIC_URL", "").strip().rstrip("/")
        base = configured or request.host_url.rstrip("/")
        parts = urlsplit(base)
        if not configured and _is_loopback(parts.hostname or ""):
            address = lan_address()
            if address:
                port = f":{parts.port}" if parts.port else ""
                base = f"{parts.scheme}://{address}{port}"
        try:
            import segno
        except ImportError:  # the page still lists the addresses
            segno = None
        cards = []
        for item in cache.get().works:
            link = f"{base}{url_for('work', code=item['code'])}"
            svg = None
            if segno:
                svg = Markup(segno.make(link, error="m").svg_inline(scale=5, border=3, dark="#000", light="#fff"))
            cards.append({"work": item, "url": link, "svg": svg})
        return render_template(
            "labels.html",
            cards=cards,
            base=base,
            local_only=_is_loopback(urlsplit(base).hostname or ""),
            has_qr=segno is not None,
        )

    @app.get("/corpus")
    def corpus_status():
        corpus = cache.get()
        return render_template("corpus.html", corpus=corpus, totals=corpus.totals, target=f"{VERIFIED_TARGET:.0%}")

    # --- JSON, for a future mini-program front end --------------------------------------

    def work_json(work: dict) -> dict:
        return {
            "id": work["id"],
            "code": work["code"],
            "format": work["format"],
            "title": work["title"],
            "artist": work["artist"],
            "date": work["date"],
            "stats": work["stats"],
            "sources": work["sources"],
            "catalogue": (
                {
                    "source": work["catalogue"]["source"]["id"] if work["catalogue"]["source"] else None,
                    "fields": work["catalogue"]["fields"],
                }
                if work["catalogue"]
                else None
            ),
            "images": {
                key: {**image, "url": url_for("static", filename=image["src"])} for key, image in work["images"].items()
            },
            "layers": [
                {
                    "n": layer["n"],
                    "key": layer["key"],
                    "mode": layer["mode"],
                    "stops": [
                        {
                            "n": stop["n"],
                            "label": stop["label"],
                            "image": stop["image"],
                            "region": stop["region"],
                            "segments": [
                                {
                                    "text": seg["text"],
                                    "status": seg["status"],
                                    "source": seg["source"]["id"] if seg["source"] else None,
                                }
                                for seg in stop["segments"]
                            ],
                        }
                        for stop in layer["stops"]
                    ],
                }
                for layer in work["layers"]
            ],
        }

    @app.get("/api/works")
    def api_works():
        corpus = cache.get()
        return jsonify(
            {
                "target": VERIFIED_TARGET,
                "works": [
                    {
                        "code": w["code"],
                        "id": w["id"],
                        "format": w["format"],
                        "title": w["title"],
                        "artist": w["artist"],
                        "date": w["date"],
                        "stats": w["stats"],
                        "url": url_for("api_work", code=w["code"]),
                    }
                    for w in corpus.works
                ],
            }
        )

    @app.get("/api/works/<code>")
    def api_work(code: str):
        found = cache.get().get(code)
        if found is None:
            return jsonify({"error": "not found"}), 404
        return jsonify(work_json(found))

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
    corpus = app.extensions["kanjian_corpus"].get()
    reloaded = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    if not reloaded:
        totals = corpus.totals
        print(f"\nKànjiàn: {totals['works']} works, {totals['share']:.0%} of statements verified.")
        print(f"  On this computer:  http://127.0.0.1:{args.port}")
        if args.lan:
            address = lan_address()
            if address:
                print(f"  On a phone (same Wi-Fi):  http://{address}:{args.port}")
                print(f"  QR labels to print:  http://{address}:{args.port}/labels")
            else:
                print("  No local network address found; set KANJIAN_PUBLIC_URL for the QR labels.")
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
