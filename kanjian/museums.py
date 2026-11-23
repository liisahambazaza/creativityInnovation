"""The collections works are imported from, their licences and required credit lines."""

from __future__ import annotations

MUSEUMS: dict[str, dict] = {
    "npm": {
        "name": {"zh": "国立故宫博物院（台北）", "en": "National Palace Museum, Taipei"},
        "short": {"zh": "台北故宫", "en": "Palace Museum, Taipei"},
        "site": "https://digitalarchive.npm.gov.tw/opendata",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        # The museum's open-data declaration asks for exactly this form, with the work's name first.
        "credit": {
            "zh": "{title} 國立故宮博物院，臺北，CC BY 4.0 @ www.npm.gov.tw",
            "en": "{title} The National Palace Museum, Taipei, CC BY 4.0 @ www.npm.gov.tw",
        },
    },
    "met": {
        "name": {"zh": "大都会艺术博物馆（纽约）", "en": "The Metropolitan Museum of Art, New York"},
        "short": {"zh": "大都会博物馆", "en": "The Met"},
        "site": "https://www.metmuseum.org/about-the-met/policies-and-documents/open-access",
        "license": "CC0 1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "credit": {
            "zh": "图像与资料：大都会艺术博物馆开放获取（CC0）",
            "en": "Image and data: The Metropolitan Museum of Art, Open Access (CC0)",
        },
    },
    "cma": {
        "name": {"zh": "克利夫兰艺术博物馆", "en": "The Cleveland Museum of Art"},
        "short": {"zh": "克利夫兰博物馆", "en": "Cleveland Museum of Art"},
        "site": "https://www.clevelandart.org/open-access",
        "license": "CC0 1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "credit": {
            "zh": "图像与资料：克利夫兰艺术博物馆开放获取（CC0）",
            "en": "Image and data: The Cleveland Museum of Art, Open Access (CC0)",
        },
    },
}


def credit(museum: str, lang: str, title: dict) -> str:
    """The credit line to print next to a work's image, in the visitor's language."""
    template = MUSEUMS[museum]["credit"][lang]
    name = title.get(lang) or title.get("zh") or title.get("en") or ""
    if museum == "npm":
        # the museum's form names the work in the same language as the credit
        name = (title.get("zh") if lang == "zh" else title.get("en")) or name
    return template.format(title=name).strip()
