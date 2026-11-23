"""Interface text: every string exists in both languages, and nothing asks for a missing one."""

from __future__ import annotations

import re
import string

import pytest

from kanjian import i18n, periods
from kanjian.works import CATEGORIES, FORMATS, LANGS
from tests.conftest import ROOT


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


@pytest.mark.parametrize("key", sorted(i18n.STRINGS))
def test_every_string_has_both_languages(key):
    entry = i18n.STRINGS[key]
    assert set(entry) == set(LANGS), key
    for lang in LANGS:
        assert entry[lang].strip(), f"{key} is empty in {lang}"


@pytest.mark.parametrize("key", sorted(i18n.STRINGS))
def test_both_languages_take_the_same_values(key):
    entry = i18n.STRINGS[key]
    assert placeholders(entry["zh"]) == placeholders(entry["en"]), key


def test_chinese_strings_are_in_chinese():
    same = [k for k, v in i18n.STRINGS.items() if v["zh"] == v["en"]]
    assert same == [], f"not translated: {same}"


def test_unknown_key_fails_loudly():
    with pytest.raises(KeyError):
        i18n.t("no_such_key", "en")


def _template_keys() -> tuple[set[str], set[str]]:
    """Keys the templates ask for: whole keys, and prefixes joined to a value (t('format_' + x))."""
    whole, prefixes = set(), set()
    for path in (ROOT / "templates").glob("*.html"):
        for key, plus in re.findall(r"\bt\('([a-z_]+)'(\s*\+)?", path.read_text(encoding="utf-8")):
            (prefixes if plus else whole).add(key)
    app_text = (ROOT / "app.py").read_text(encoding="utf-8")
    whole |= set(re.findall(r"""\bt\(["']([a-z_]+)["'][,)]""", app_text))
    whole |= set(re.findall(r"""\(["'](cat_[a-z_]+)["'],""", app_text))  # detail rows name their label key
    return whole, prefixes


def test_templates_and_app_only_use_defined_keys():
    whole, _ = _template_keys()
    missing = sorted(whole - set(i18n.STRINGS))
    assert missing == [], f"used but not defined: {missing}"


def test_template_prefixes_are_the_ones_covered_below():
    _, prefixes = _template_keys()
    assert prefixes <= {"format_", "category_", "era_", "era_dates_", "era_intro_"}, prefixes


@pytest.mark.parametrize(
    "prefix, values",
    [
        ("format_", FORMATS),
        ("category_", CATEGORIES),
        ("era_", periods.ERAS),
        ("era_dates_", periods.ERAS),
        ("era_intro_", periods.ERAS),
    ],
)
def test_every_value_built_into_a_key_has_text(prefix, values):
    missing = [prefix + v for v in values if prefix + v not in i18n.STRINGS]
    assert missing == []


def test_strings_the_script_reads_are_sent_to_it():
    script = (ROOT / "static" / "js" / "kanjian.js").read_text(encoding="utf-8")
    used = set(re.findall(r"\bS\.([a-z_]+)", script))
    assert used, "expected the script to read interface strings"
    assert used <= set(i18n.JS_KEYS), sorted(used - set(i18n.JS_KEYS))
    for lang in LANGS:
        assert set(i18n.js_strings(lang)) == set(i18n.JS_KEYS)
