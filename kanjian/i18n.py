"""Interface text in Chinese and English.

Every key must have both languages; ``tests/test_i18n.py`` checks that, and that
templates only use keys defined here.
"""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    # --- general
    "app_name_full": {"zh": "看见 Kànjiàn", "en": "Kànjiàn 看见"},
    "tagline": {
        "zh": "中国书画入门：从唐代到明代的名作，一件一件慢慢看",
        "en": "An introduction to Chinese painting and calligraphy, one great work at a time",
    },
    "skip": {"zh": "跳到主要内容", "en": "Skip to main content"},
    "language": {"zh": "语言", "en": "Language"},
    "home": {"zh": "首页", "en": "home"},
    "main_nav": {"zh": "主导航", "en": "Main"},
    "nav_gallery": {"zh": "作品", "en": "Works"},
    "nav_about": {"zh": "关于本站", "en": "About"},
    "footer_note": {
        "zh": "原型版本。图像与馆方资料来自开放数据，导读文字由 AI 协助撰写，尚未经策展人审核。",
        "en": "Prototype. Images and museum records come from open data; the introductions were drafted with AI help and have not been reviewed by a curator.",
    },
    # --- gallery
    "gallery_lede": {
        "zh": "这里收集了台北故宫、大都会艺术博物馆和克利夫兰艺术博物馆开放的书画名作。每件作品配有一段简短导读、几处值得细看的地方，以及馆方自己的说明。",
        "en": "Masterpieces of painting and calligraphy from the open collections of the National Palace Museum in Taipei, the Metropolitan Museum of Art and the Cleveland Museum of Art. Each comes with a short introduction, a few things to look for, and the museum's own notes.",
    },
    "filter_label": {"zh": "显示", "en": "Show"},
    "filter_all": {"zh": "全部", "en": "Everything"},
    "filter_painting": {"zh": "绘画", "en": "Painting"},
    "filter_calligraphy": {"zh": "书法", "en": "Calligraphy"},
    "works_count": {"zh": "共 {n} 件作品", "en": "{n} works"},
    "era_tang": {"zh": "唐与五代", "en": "Tang and Five Dynasties"},
    "era_song": {"zh": "宋", "en": "Song"},
    "era_yuan": {"zh": "元", "en": "Yuan"},
    "era_ming": {"zh": "明", "en": "Ming"},
    "era_qing": {"zh": "清", "en": "Qing"},
    "era_other": {"zh": "其他", "en": "Other works"},
    "era_dates_tang": {"zh": "618–960年", "en": "618–960"},
    "era_dates_song": {"zh": "960–1279年", "en": "960–1279"},
    "era_dates_yuan": {"zh": "1271–1368年", "en": "1271–1368"},
    "era_dates_ming": {"zh": "1368–1644年", "en": "1368–1644"},
    "era_dates_qing": {"zh": "1644–1912年", "en": "1644–1912"},
    "era_dates_other": {"zh": "年代不详", "en": "Date not recorded"},
    "era_intro_tang": {
        "zh": "书法的黄金时代。草书在这一时期变得前所未有地自由奔放。",
        "en": "A golden age of calligraphy, when cursive script became freer and wilder than ever before.",
    },
    "era_intro_song": {
        "zh": "宏伟的山水画在北宋成熟；文人开始把书画当作表达自我的方式。",
        "en": "Monumental landscape painting matured, and scholars began to treat painting and calligraphy as a way of expressing the self.",
    },
    "era_intro_yuan": {
        "zh": "在蒙古统治下，许多文人不再做官，转而用简淡的笔墨描绘内心的山水。",
        "en": "Under Mongol rule many scholars turned away from official life and painted quiet, personal landscapes in ink.",
    },
    "era_intro_ming": {
        "zh": "画家们反复研究古代大师，再用自己的方式重新组合山水。",
        "en": "Painters studied the old masters closely, then rebuilt the landscape in their own way.",
    },
    "era_intro_qing": {
        "zh": "宫廷艺术与个性鲜明的画家并存，西方画法也开始进入宫廷。",
        "en": "Court art and fiercely individual painters flourished side by side, and Western techniques reached the palace.",
    },
    "era_intro_other": {"zh": "尚未归入朝代的作品。", "en": "Works not yet placed in a dynasty."},
    "none_in_filter": {"zh": "这一类还没有作品。", "en": "There are no works of this kind yet."},
    "how_to_read_heading": {"zh": "怎样看中国书画", "en": "How to look at Chinese painting"},
    "how_to_read_scrolls": {
        "zh": "立轴挂起来从上往下看；手卷放在桌上，从右往左一段段展开，就像一次旅行。",
        "en": "A hanging scroll is hung and read from top to bottom. A handscroll is unrolled on a table, a section at a time, from right to left, like a journey.",
    },
    "how_to_read_seals": {
        "zh": "画上的红色印章，多是后来的收藏者盖的。印章和题跋记录了作品流传的历史。",
        "en": "Most of the red seals were stamped by later collectors. Seals and inscriptions record the history of who owned and admired a work.",
    },
    "how_to_read_brush": {
        "zh": "书法和绘画用的是同一支笔。看笔触的快慢、轻重和干湿，就像听一个人的声音。",
        "en": "Calligraphy and painting use the same brush. Watching how fast, heavy or dry a stroke is can feel like hearing a person's voice.",
    },
    # --- formats and categories
    "format_handscroll": {"zh": "手卷", "en": "Handscroll"},
    "format_hanging_scroll": {"zh": "立轴", "en": "Hanging scroll"},
    "format_album_leaf": {"zh": "册页", "en": "Album leaf"},
    "format_album": {"zh": "册", "en": "Album"},
    "format_fan": {"zh": "扇面", "en": "Fan"},
    "format_other": {"zh": "其他形制", "en": "Other format"},
    "category_painting": {"zh": "绘画", "en": "Painting"},
    "category_calligraphy": {"zh": "书法", "en": "Calligraphy"},
    "category_other": {"zh": "其他", "en": "Other"},
    # --- work page
    "intro_heading": {"zh": "导读", "en": "Introduction"},
    "ai_badge": {"zh": "AI 协助撰写 · 未经审核", "en": "AI-drafted · not reviewed"},
    "ai_note": {
        "zh": "导读和“细看”由 AI 协助撰写，参考了馆方资料，但尚未经策展人审核，可能有错。",
        "en": "The introduction and 'Look closer' were drafted with AI help from the museum's records, but have not been reviewed by a curator and may contain mistakes.",
    },
    "look_heading": {"zh": "细看", "en": "Look closer"},
    "museum_heading": {"zh": "馆方说明", "en": "From the museum"},
    "museum_text_source": {"zh": "以下文字来自{museum}。", "en": "This text is from the museum's record ({museum})."},
    "museum_text_only_zh": {"zh": "馆方只提供中文说明。", "en": "The museum's text is only available in Chinese."},
    "museum_text_only_en": {"zh": "馆方只提供英文说明。", "en": "The museum's text is only available in English."},
    "museum_text_none": {
        "zh": "馆方记录中没有文字说明，只有下面的基本资料。",
        "en": "The museum's record has no descriptive text, only the details below.",
    },
    "details_heading": {"zh": "基本资料", "en": "Details"},
    "cat_artist": {"zh": "作者", "en": "Artist"},
    "cat_period": {"zh": "朝代", "en": "Period"},
    "cat_date": {"zh": "年代", "en": "Date"},
    "cat_format": {"zh": "形制", "en": "Format"},
    "cat_medium": {"zh": "材质", "en": "Medium"},
    "cat_dimensions": {"zh": "尺寸", "en": "Dimensions"},
    "cat_museum": {"zh": "收藏", "en": "Collection"},
    "cat_object_number": {"zh": "编号", "en": "Object number"},
    "cat_credit_line": {"zh": "来源", "en": "Credit line"},
    "record_link": {"zh": "在馆方网站查看这件作品", "en": "See this work on the museum's website"},
    "license_line": {"zh": "授权：{license}", "en": "Licence: {license}"},
    "image_note_label": {"zh": "关于这张图像", "en": "About this image"},
    "unknown_artist": {"zh": "作者不详", "en": "Artist unknown"},
    "viewer_label": {"zh": "作品图像", "en": "Image of the work"},
    "viewer_handscroll_hint": {
        "zh": "手卷从右往左看。左右滑动，展开全卷。",
        "en": "Handscrolls are read from right to left. Scroll sideways to unroll it.",
    },
    "viewer_open_full": {"zh": "打开原尺寸图像", "en": "Open the full-size image"},
    "prev_work": {"zh": "上一件", "en": "Previous"},
    "next_work": {"zh": "下一件", "en": "Next"},
    "work_nav": {"zh": "其他作品", "en": "More works"},
    "back_to_gallery": {"zh": "返回全部作品", "en": "Back to all works"},
    "read_aloud": {"zh": "朗读导读", "en": "Read aloud"},
    "stop_reading": {"zh": "停止朗读", "en": "Stop reading"},
    "no_speech": {
        "zh": "这个浏览器无法朗读。您可以试试 Safari 或 Chrome。",
        "en": "This browser cannot read aloud. Try Safari or Chrome.",
    },
    # --- about
    "about_title": {"zh": "关于本站", "en": "About Kànjiàn"},
    "about_intro": {
        "zh": "看见（Kànjiàn）是一个原型，想让第一次接触中国书画的观众也能看懂、看进去。每件作品都配有一段简短导读和几处值得细看的地方，旁边就是馆方自己的说明。",
        "en": "Kànjiàn (看见, 'to see') is a prototype that helps people new to Chinese painting and calligraphy find their way into it. Each work has a short introduction and a few things to look for, alongside the museum's own notes.",
    },
    "about_sources_heading": {"zh": "图像和资料从哪里来", "en": "Where the images and records come from"},
    "about_sources_text": {
        "zh": "所有图像和馆方资料都来自博物馆的开放数据，按各馆的授权使用：",
        "en": "Every image and museum record comes from a museum's open data, used under that museum's licence:",
    },
    "about_npm": {
        "zh": "国立故宫博物院（台北）：开放数据平台和 IIIF 图像服务，图像与文字以 CC BY 4.0 授权，每张图像旁附上馆方要求的署名。",
        "en": "National Palace Museum, Taipei: its open-data platform and IIIF image service. Images and text are CC BY 4.0, and each image carries the credit line the museum asks for.",
    },
    "about_met": {
        "zh": "大都会艺术博物馆：开放获取 API，CC0（公共领域）。",
        "en": "The Metropolitan Museum of Art: its Open Access API, CC0 (public domain).",
    },
    "about_cma": {
        "zh": "克利夫兰艺术博物馆：开放获取 API，CC0（公共领域）。",
        "en": "The Cleveland Museum of Art: its Open Access API, CC0 (public domain).",
    },
    "about_beijing_heading": {
        "zh": "为什么没有北京故宫的作品",
        "en": "Why there is nothing from the Palace Museum in Beijing",
    },
    "about_beijing_text": {
        "zh": "北京故宫博物院的数字文物库只供个人研究浏览，未经书面许可不得转载或批量获取。在得到许可之前，本站不收录那里的图像。",
        "en": "The Palace Museum in Beijing makes its digital collection available for personal study only, and does not allow reuse or automated collection without written permission. Until that permission is given, this site does not include its images.",
    },
    "about_ai_heading": {"zh": "导读是谁写的", "en": "Who wrote the introductions"},
    "about_ai_text": {
        "zh": "导读、“细看”和图像描述由 AI 协助撰写，参考了馆方资料和一般艺术史知识，在页面上标为“AI 协助撰写 · 未经审核”。馆方说明则原样引用，并注明出处。正式使用前，导读需要由策展人或研究者审核。",
        "en": "The introductions, 'Look closer' notes and image descriptions were drafted with AI help, using the museums' records and general art-historical knowledge, and are labelled 'AI-drafted · not reviewed'. The museums' own texts are quoted as they are, with their source. Before real use, the introductions need review by a curator or scholar.",
    },
    "about_add_heading": {"zh": "加入更多作品", "en": "Adding more works"},
    "about_add_text": {
        "zh": "项目附带导入工具，可以按编号从这三家博物馆导入作品；详见项目的 README。",
        "en": "The project includes an importer that adds works from these three museums by their collection number; see the project README.",
    },
    # --- errors
    "not_found_title": {"zh": "找不到这一页", "en": "Page not found"},
    "not_found_text": {"zh": "这个地址没有对应的作品或页面。", "en": "There is no work or page at this address."},
}

# Text the browser script needs.
JS_KEYS = ("read_aloud", "stop_reading", "no_speech")


def t(key: str, lang: str, **values) -> str:
    """Look up interface text. Unknown keys raise, so typos fail loudly in tests."""
    text = STRINGS[key][lang]
    return text.format(**values) if values else text


def js_strings(lang: str) -> dict[str, str]:
    return {key: STRINGS[key][lang] for key in JS_KEYS}
