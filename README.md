# Kànjiàn 看见 (prototype)

An introduction to Chinese painting and calligraphy, in Chinese and English.
The site shows masterpieces from the open collections of three museums, grouped
by dynasty. Each work page has:

- the image, with handscrolls unrolling from right to left as real ones do;
- a short **introduction** and **things to look for**, drafted with AI help, every
  sentence citing its sources and checked against them, and labelled as not yet
  reviewed by a curator;
- **what critics and historians say**: named scholars paraphrased, traditional critics
  and inscriptions quoted, each with its source;
- the **museum's own text** and catalogue details, quoted with their source and licence;
- a **Read aloud** button (Ava for English and Tingting for Chinese, when installed).

## Run it

```sh
make setup    # once: creates .venv and installs everything
make run      # http://127.0.0.1:8000
make phone    # also open it from a phone on the same Wi-Fi
```

Pages: `/` the gallery (`?category=painting` or `calligraphy`) · `/w/<id>` a work,
e.g. `/w/npm-1195` · `/about` sources and licences · `/api/works` JSON.

## Where the art comes from

| Museum | How | Licence |
| --- | --- | --- |
| National Palace Museum, Taipei | open-data site and its IIIF image service | CC BY 4.0: the credit line the museum asks for is shown with each image |
| The Metropolitan Museum of Art | Open Access API | CC0 |
| The Cleveland Museum of Art | Open Access API | CC0 |

The Palace Museum in **Beijing** is not included: its digital collection is for
personal study only, and reuse or automated collection needs written permission.

## Adding works

Find a work's number in the museum's collection, then import it:

```sh
make search SOURCE=npm Q=早春圖                 # Taipei: prints numbers like 47:P
make search SOURCE=cma Q="bamboo"               # Cleveland: accession numbers
make add SOURCE=npm IDS="47 1195"               # Taipei record numbers
make add SOURCE=met IDS=45636                   # Met object IDs
make add SOURCE=cma IDS=1953.126                # Cleveland accession numbers
make refresh                                    # re-import everything already here
make collection                                 # list works and anything still missing
```

Each work is one file, `data/works/<museum>-<number>.json`, with its images in
`static/img/works/`. The importer writes the museum's data; the `editorial` block is
ours and is never overwritten by an import:

| `editorial` field | What it is |
| --- | --- |
| `intro`, `look_for` | lists of statements: `zh`, `en` and `sources` (the keys of the sources that support it) |
| `views` | what named critics and historians said: `who`, `about`, the paraphrase (`zh`, `en`), an optional short `quote`, and `sources` |
| `sources` | each source by key: `kind` (`museum`, `museum_essay`, `inscription`, `scholarship`, `encyclopedia`), `title`, `url`, `accessed`. Built in: `museum` (the work's own record) and `image` (visible in the image) |
| `checked` | `on`: the date every statement was last checked against its sources |
| `alt` | the image description (`zh` and `en`) |
| `overrides` | corrections or translations of museum fields (`title`, `artist`, `date`, `period`, `year`, …) |
| `image_choice` | which image to use: `canvas` (a Taipei image label), `region` (`pct:x,y,w,h`), `crop`, or `keep: true` |
| `status` | `ai_draft` until a person has reviewed the text |

**Every statement must cite a source, and the text must be marked as checked.**
`make collection` (and so `make check` and the commit hook) fails otherwise. The
procedure for writing and checking introductions is in `CLAUDE.md`. On the page, each
sentence links to its numbered source.

The site picks up changes without a restart. `make collection` warns about any work
that still lacks an introduction or image description in either language.

## Check it

```sh
make check    # code style, the collection check, and all tests (including real-browser tests)
make fast     # the same without the browser tests (a few seconds)
make hooks    # run `make fast` before every git commit
```

The browser tests use the Google Chrome already installed on this Mac. They run the
axe checker on every page, check that nothing scrolls sideways on a phone, that
handscrolls open at their right-hand end, and drive Read aloud with a stand-in voice.
The importer tests run offline against saved copies of real museum responses in
`tests/fixtures/`. GitHub Actions runs `make check` on every push.

## Where things are

| Path | What it holds |
| --- | --- |
| `app.py` | the web app (Flask): gallery, work pages, language choice, JSON API |
| `kanjian/works.py` | loads and checks `data/works/*.json` |
| `kanjian/importers/` | one importer per museum, plus the `search` / `add` / `refresh` command line |
| `kanjian/museums.py` | the museums, their licences and credit lines |
| `kanjian/periods.py` | dynasties, their dates, and how to recognise them in museum records |
| `kanjian/i18n.py` | every piece of interface text, in Chinese and English |
| `templates/`, `static/` | pages, stylesheet, script, images |
| `tests/` | the collection, the importers, pages and API, translations, real-browser tests |
