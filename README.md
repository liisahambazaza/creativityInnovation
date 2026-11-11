# Kànjiàn 看见 (prototype)

Spoken descriptions of Chinese artworks for blind and low-vision visitors, in
Chinese and English. A visitor types the number on a wall label (or scans its
QR code) and hears the work described in four layers: orientation,
composition, material and brushwork, and context. Each statement is
marked as either **verified** (it cites a museum source) or **AI description, not
verified**, in text, by a sound cue, and by voice pitch.

## Run it

```sh
make setup    # once: creates .venv and installs everything
make run      # http://127.0.0.1:8000
make phone    # also open it from a phone on the same Wi-Fi
```

Pages: `/` home and number entry · `/w/01` a work · `/labels` printable QR
labels · `/corpus` how much of each description is verified · `/api/works` JSON.

## Check it

```sh
make check    # code style, corpus audit, and all tests (including real-browser tests)
make fast     # the same without the browser tests (a few seconds)
make audit    # verified share per work, against the 95% target
make hooks    # run `make fast` before every git commit (needs `git init` first)
```

The browser tests use the Google Chrome already installed on this Mac. They
check every page with the axe accessibility checker, check that nothing
scrolls sideways on a phone, and drive the audio player with a stand-in
voice. GitHub Actions runs `make check` on every push (`.github/workflows/check.yml`).

## Where things are

| Path | What it holds |
| --- | --- |
| `app.py` | the web app (Flask): pages, language choice, QR labels, JSON API |
| `kanjian/corpus.py` | loads and validates `data/works/*.json`; enforces "verified needs a source" |
| `kanjian/i18n.py` | every piece of interface text, in Chinese and English |
| `data/works/` | one JSON file per artwork |
| `templates/` | HTML pages |
| `static/` | stylesheet, the audio player script, artwork images |
| `tests/` | data rules, pages and API, translations, real-browser tests |
| `scripts/check.py` | the one command behind `make check` |

## Adding a work

Copy a file in `data/works/`, change the `code` to the next label number, and
put its images in `static/img/works/`. The app picks up the change without a
restart. `make audit` reports anything wrong, such as a statement marked
verified that cites no source (it is then shown as unverified).

The sample content was drafted for the prototype and has not been reviewed by
a curator.
