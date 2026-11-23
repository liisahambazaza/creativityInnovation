"""Chinese dynasties: names, dates, and how to recognise them in museum records."""

from __future__ import annotations

# key: (zh, en, start year, end year, era). The era groups dynasties on the gallery page.
PERIODS: dict[str, tuple[str, str, int, int, str]] = {
    "tang": ("唐", "Tang dynasty", 618, 907, "tang"),
    "five_dynasties": ("五代", "Five Dynasties", 907, 960, "tang"),
    "northern_song": ("北宋", "Northern Song dynasty", 960, 1127, "song"),
    "southern_song": ("南宋", "Southern Song dynasty", 1127, 1279, "song"),
    "song": ("宋", "Song dynasty", 960, 1279, "song"),
    "jin": ("金", "Jin dynasty", 1115, 1234, "song"),
    "yuan": ("元", "Yuan dynasty", 1271, 1368, "yuan"),
    "ming": ("明", "Ming dynasty", 1368, 1644, "ming"),
    "qing": ("清", "Qing dynasty", 1644, 1912, "qing"),
}

# Gallery sections, oldest first.
ERAS = ("tang", "song", "yuan", "ming", "qing", "other")

# Longest names first, so 北宋 is found before 宋.
_ZH_ORDER = sorted(PERIODS, key=lambda k: -len(PERIODS[k][0]))
_EN_NAMES = {
    "five_dynasties": "five dynasties",
    "northern_song": "northern song",
    "southern_song": "southern song",
    "tang": "tang dynasty",
    "song": "song dynasty",
    "jin": "jin dynasty",
    "yuan": "yuan dynasty",
    "ming": "ming dynasty",
    "qing": "qing dynasty",
}


def period_from_zh_prefix(title: str) -> str | None:
    """NPM titles start with the dynasty: 宋范寬谿山行旅圖 → 'song'."""
    for key in _ZH_ORDER:
        if title.startswith(PERIODS[key][0]):
            return key
    return None


def period_from_en(text: str) -> str | None:
    """Met and Cleveland records name the dynasty in English: 'Yuan dynasty (1271–1368)'."""
    low = (text or "").lower()
    for key in ("five_dynasties", "northern_song", "southern_song", "tang", "jin", "song", "yuan", "ming", "qing"):
        if _EN_NAMES[key] in low:
            return key
    return None


def era_of(period: str | None) -> str:
    return PERIODS[period][4] if period in PERIODS else "other"


def start_year(period: str | None) -> int | None:
    return PERIODS[period][2] if period in PERIODS else None


def label(period: str | None, lang: str) -> str:
    if period not in PERIODS:
        return ""
    zh, en, start, end, _ = PERIODS[period]
    return f"{zh}（{start}–{end}）" if lang == "zh" else f"{en} ({start}–{end})"
