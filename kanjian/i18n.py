"""Interface text in Chinese and English.

Every key must have both languages; ``tests/test_i18n.py`` checks that, and that
templates only use keys defined here.
"""

from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    # --- general
    "app_name_full": {"zh": "看见 Kànjiàn", "en": "Kànjiàn 看见"},
    "tagline": {
        "zh": "为视障观众讲述中国艺术品的语音导览",
        "en": "Spoken descriptions of Chinese artworks for blind and low-vision visitors",
    },
    "skip": {"zh": "跳到主要内容", "en": "Skip to main content"},
    "language": {"zh": "语言", "en": "Language"},
    "home": {"zh": "首页", "en": "home"},
    "footer_nav": {"zh": "项目页面", "en": "Project pages"},
    "footer_labels": {"zh": "展签二维码", "en": "QR labels"},
    "footer_corpus": {"zh": "语料核实情况", "en": "Corpus status"},
    "prototype_note": {
        "zh": "原型版本。示例内容尚未经策展人审核。",
        "en": "Prototype. The sample content has not been reviewed by a curator.",
    },
    # --- settings
    "settings": {"zh": "设置", "en": "Settings"},
    "set_voice": {"zh": "内置语音", "en": "Built-in voice"},
    "set_voice_on": {"zh": "朗读讲解", "en": "Read descriptions aloud"},
    "set_voice_off": {"zh": "不朗读，我用自己的读屏软件", "en": "Stay silent: I use my own screen reader"},
    "set_speed": {"zh": "语速", "en": "Speaking speed"},
    "speed_slow": {"zh": "慢", "en": "Slow"},
    "speed_normal": {"zh": "正常", "en": "Normal"},
    "speed_fast": {"zh": "快", "en": "Fast"},
    "set_content": {"zh": "讲解内容", "en": "What to include"},
    "set_verified_only": {
        "zh": "只要已核实的内容（跳过 AI 描述）",
        "en": "Verified content only (skip AI descriptions)",
    },
    "set_auto": {"zh": "自动接着播放下一段", "en": "Continue to the next part automatically"},
    "set_text": {"zh": "文字大小", "en": "Text size"},
    "text_standard": {"zh": "标准", "en": "Standard"},
    "text_large": {"zh": "大", "en": "Large"},
    "text_xlarge": {"zh": "特大", "en": "Extra large"},
    "settings_note": {"zh": "设置保存在这台设备上。", "en": "Settings are saved on this device."},
    # --- home
    "find_heading": {"zh": "找到作品", "en": "Find a work"},
    "code_label": {"zh": "展签上的编号", "en": "Number on the label"},
    "code_hint": {
        "zh": "输入作品旁展签上的数字，例如 01。",
        "en": "Type the number printed on the label beside the work, for example 01.",
    },
    "code_go": {"zh": "打开讲解", "en": "Open the description"},
    "code_error": {
        "zh": "没有编号为 {code} 的作品。请再核对一下展签。",
        "en": "There is no work numbered {code}. Please check the label again.",
    },
    "code_empty": {"zh": "请输入展签上的编号。", "en": "Please enter the number on the label."},
    "works_heading": {"zh": "全部作品", "en": "All works"},
    "how_heading": {"zh": "讲解怎么听", "en": "How the guide works"},
    "how_two_kinds": {
        "zh": "每一句讲解都标明它的来历，分为两种。",
        "en": "Every statement is marked by where it comes from. There are two kinds.",
    },
    "how_verified": {
        "zh": "有出处可查，例如馆方的藏品记录、展签或策展人访谈。",
        "en": "It can be checked against a source, such as the museum's record, a wall label or a curator interview.",
    },
    "how_inferred": {
        "zh": "由 AI 看图或凭一般知识写成，还没有人核对过，可能有错。",
        "en": "Written by AI from the image or from general knowledge. No one has checked it yet, and it may be wrong.",
    },
    "how_sound": {
        "zh": "朗读时，两种内容之前各有不同的提示音，AI 描述的声调也略低。",
        "en": "When read aloud, each kind is introduced by its own sound, and AI descriptions are spoken at a slightly lower pitch.",
    },
    "hear_verified": {"zh": "试听“已核实”的提示音", "en": "Hear the sound for verified"},
    "hear_inferred": {"zh": "试听“AI 描述”的提示音", "en": "Hear the sound for AI description"},
    "how_layers": {
        "zh": "每件作品分四层，由浅入深：概览、构图、材质与笔墨、背景。听多深由您决定。",
        "en": "Each work has four layers, from brief to deep: orientation, composition, material and brushwork, and context. You decide how deep to go.",
    },
    # --- statement status
    "tag_verified": {"zh": "已核实", "en": "Verified"},
    "tag_inferred": {"zh": "AI 描述 · 未核实", "en": "AI description · not verified"},
    "say_verified": {"zh": "已核实。", "en": "Verified."},
    "say_inferred": {"zh": "AI 描述，未核实。", "en": "AI description, not verified."},
    "say_none_verified": {
        "zh": "这一部分还没有已核实的内容。",
        "en": "There is no verified content for this part yet.",
    },
    "none_verified_note": {
        "zh": "这一部分还没有已核实的内容。",
        "en": "There is no verified content for this part yet.",
    },
    "source_ref": {"zh": "来源 {n}：{title}", "en": "Source {n}: {title}"},
    # --- formats
    "format_handscroll": {"zh": "手卷", "en": "Handscroll"},
    "format_hanging_scroll": {"zh": "立轴", "en": "Hanging scroll"},
    "format_calligraphy": {"zh": "书法", "en": "Calligraphy"},
    "format_contemporary": {"zh": "当代作品", "en": "Contemporary work"},
    # --- layers
    "layer_orientation": {"zh": "概览", "en": "Orientation"},
    "layer_composition": {"zh": "构图", "en": "Composition"},
    "layer_material": {"zh": "材质与笔墨", "en": "Material and brushwork"},
    "layer_context": {"zh": "背景", "en": "Context"},
    "mode_traversal": {"zh": "展卷导览", "en": "scroll traversal"},
    "mode_reading_path": {"zh": "观看路径", "en": "reading path"},
    "mode_brushwork": {"zh": "笔法细看", "en": "brushwork close-up"},
    "mode_provenance": {"zh": "题跋与印章", "en": "seals and writing"},
    "layer_status": {"zh": "第 {n} 层 {title}", "en": "Layer {n}: {title}"},
    "pos_traversal": {"zh": "第 {n} 段，共 {total} 段", "en": "Section {n} of {total}"},
    "pos_reading_path": {"zh": "第 {n} 站，共 {total} 站", "en": "Stop {n} of {total}"},
    "pos_brushwork": {"zh": "第 {n} 处，共 {total} 处", "en": "Passage {n} of {total}"},
    "pos_default": {"zh": "第 {n} 部分，共 {total} 部分", "en": "Part {n} of {total}"},
    "say_layer": {"zh": "第 {n} 层，共 4 层：{title}。", "en": "Layer {n} of 4: {title}."},
    "say_count_traversal": {"zh": "共 {total} 段，自右向左。", "en": "{total} sections, from right to left."},
    "say_count_reading_path": {"zh": "共 {total} 站。", "en": "{total} stops along the reading path."},
    "say_count_brushwork": {"zh": "共 {total} 处。", "en": "{total} passages."},
    "say_count_default": {"zh": "共 {total} 部分。", "en": "{total} parts."},
    "say_layer_end": {
        "zh": "“{title}”结束。按“下一段”继续深入：{next}。",
        "en": "End of {title}. Press Next to go deeper: {next}.",
    },
    "say_work_end": {"zh": "这件作品的讲解到此结束。", "en": "That is the end of the description of this work."},
    # --- player
    "player_label": {"zh": "语音导览控制", "en": "Audio guide controls"},
    "btn_prev": {"zh": "上一段", "en": "Back"},
    "btn_play": {"zh": "播放", "en": "Play"},
    "btn_pause": {"zh": "暂停", "en": "Pause"},
    "btn_next": {"zh": "下一段", "en": "Next"},
    "status_ready": {"zh": "按“播放”开始。", "en": "Press Play to start."},
    "status_silent": {"zh": "按“下一段”逐段阅读。", "en": "Press Next to read part by part."},
    "no_speech": {
        "zh": "这个浏览器不能朗读。请用读屏软件阅读下面的文字，或换一个浏览器。",
        "en": "This browser cannot read aloud. Use your screen reader to read the text below, or try another browser.",
    },
    # --- work page
    "work_number": {"zh": "{code} 号", "en": "No. {code}"},
    "catalogue_heading": {"zh": "藏品信息", "en": "Catalogue details"},
    "cat_artist": {"zh": "作者", "en": "Artist"},
    "cat_period": {"zh": "时代", "en": "Period"},
    "cat_date": {"zh": "年代", "en": "Date"},
    "cat_medium": {"zh": "形制与材质", "en": "Format and medium"},
    "cat_dimensions": {"zh": "尺寸", "en": "Dimensions"},
    "cat_collection": {"zh": "收藏", "en": "Collection"},
    "cat_credit": {"zh": "来源说明", "en": "Credit line"},
    "cat_accession": {"zh": "藏品编号", "en": "Accession number"},
    "catalogue_verified": {"zh": "以上信息出自：", "en": "These details come from:"},
    "catalogue_unverified": {"zh": "以上信息尚未核实。", "en": "These details have not been verified."},
    "sources_heading": {"zh": "来源", "en": "Sources"},
    "sources_none": {"zh": "这件作品还没有登记任何来源。", "en": "No sources have been recorded for this work yet."},
    "source_accessed": {"zh": "查阅日期 {date}", "en": "accessed {date}"},
    "source_license": {"zh": "许可 {license}", "en": "licence {license}"},
    "source_link": {"zh": "打开来源", "en": "Open the source"},
    "kind_catalogue": {"zh": "馆方藏品记录", "en": "Museum catalogue record"},
    "kind_wall_label": {"zh": "展签", "en": "Wall label"},
    "kind_audio_guide": {"zh": "语音导览稿", "en": "Audio-guide script"},
    "kind_curator_interview": {"zh": "策展人访谈", "en": "Curator interview"},
    "kind_publication": {"zh": "出版物", "en": "Publication"},
    "verified_share": {
        "zh": "{segments} 句中有 {verified} 句已核实（{pct}）。",
        "en": "{verified} of {segments} statements are verified ({pct}).",
    },
    "demo_note": {
        "zh": "示例内容：标为“AI 描述”的句子由 AI 根据照片和一般知识起草，尚未经策展人审核。",
        "en": "Sample content: statements marked as AI description were drafted by AI from photographs and general knowledge, and have not been reviewed by a curator.",
    },
    "back_to_list": {"zh": "返回全部作品", "en": "Back to all works"},
    # --- not found
    "not_found_title": {"zh": "找不到页面", "en": "Page not found"},
    "not_found_body": {"zh": "这个地址没有内容。", "en": "There is nothing at this address."},
    # --- QR labels
    "labels_title": {"zh": "展签二维码", "en": "QR labels"},
    "labels_intro": {
        "zh": "打印后贴在作品旁。用手机相机或微信“扫一扫”即可打开讲解，也可以在首页输入编号。",
        "en": "Print these and place one beside each work. Scanning with a phone camera or WeChat opens the description. The number can also be typed on the home page.",
    },
    "labels_base": {"zh": "二维码指向：", "en": "The codes point to:"},
    "labels_local_warning": {
        "zh": "这个地址只能在本机打开，手机扫码无法访问。请用“make phone”启动，或设置 KANJIAN_PUBLIC_URL。",
        "en": "This address only works on this computer, so phones cannot open it. Start the app with “make phone”, or set KANJIAN_PUBLIC_URL.",
    },
    "labels_no_qr": {
        "zh": "未安装二维码组件 segno，只显示网址。",
        "en": "The QR library segno is not installed, so only the address is shown.",
    },
    "labels_qr_alt": {"zh": "{code} 号作品的二维码", "en": "QR code for work {code}"},
    "print": {"zh": "打印本页", "en": "Print this page"},
    # --- corpus status
    "corpus_title": {"zh": "语料核实情况", "en": "Corpus status"},
    "corpus_intro": {
        "zh": "项目目标：至少 {target} 的陈述有出处可查。",
        "en": "Project target: at least {target} of statements can be checked against a source.",
    },
    "corpus_caption": {"zh": "每件作品的核实比例", "en": "Share of verified statements for each work"},
    "col_work": {"zh": "作品", "en": "Work"},
    "col_format": {"zh": "形制", "en": "Format"},
    "col_segments": {"zh": "句数", "en": "Statements"},
    "col_verified": {"zh": "已核实", "en": "Verified"},
    "col_share": {"zh": "比例", "en": "Share"},
    "col_sources": {"zh": "来源数", "en": "Sources"},
    "col_target": {"zh": "目标", "en": "Target"},
    "target_met": {"zh": "达到", "en": "Met"},
    "target_below": {"zh": "未达到", "en": "Below"},
    "corpus_total": {"zh": "合计", "en": "Total"},
    "problems_heading": {"zh": "数据文件中的问题", "en": "Problems in the data files"},
    "problems_none": {"zh": "没有发现问题。", "en": "No problems found."},
    "level_error": {"zh": "错误", "en": "Error"},
    "level_warning": {"zh": "提醒", "en": "Warning"},
}

# Text the browser script needs.
JS_KEYS = (
    "btn_play",
    "btn_pause",
    "status_ready",
    "status_silent",
    "no_speech",
    "say_verified",
    "say_inferred",
    "say_none_verified",
    "none_verified_note",
)


def t(key: str, lang: str, **values) -> str:
    """Look up interface text. Unknown keys raise, so typos fail loudly in tests."""
    text = STRINGS[key][lang]
    return text.format(**values) if values else text


def js_strings(lang: str) -> dict[str, str]:
    return {key: STRINGS[key][lang] for key in JS_KEYS}
