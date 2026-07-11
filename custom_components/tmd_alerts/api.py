import aiohttp
import xml.etree.ElementTree as ET
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


def _last_text(element: ET.Element, tag: str, default: str = "") -> str:
    """Return text of the LAST child with the given tag.

    The TMD API duplicates English fields within each <Warning> block: the
    FIRST occurrence of TitleEnglish/HeadlineEnglish/etc. contains Thai text
    (a copy of the Thai fields); the LAST occurrence holds the actual English
    translation. findall()[-1] ensures we always get the real English value.
    """
    found = element.findall(tag)
    if not found:
        return default
    return (found[-1].text or "").strip() or default


async def fetch_warnings(hass: HomeAssistant, url: str, uid: str, ukey: str) -> list[dict]:
    session = async_get_clientsession(hass)
    timeout = aiohttp.ClientTimeout(total=30)

    async with session.get(url, params={"uid": uid, "ukey": ukey}, timeout=timeout) as resp:
        resp.raise_for_status()
        text = await resp.text(encoding="utf-8")

    root = ET.fromstring(text)
    warnings = []

    for warning in root.findall(".//Warning"):
        warnings.append({
            "issue_no": warning.findtext("IssueNo", ""),
            "effect_start": warning.findtext("EffectStartDate", ""),
            "effect_end": warning.findtext("EffectEndDate", ""),
            "announce_date": warning.findtext("AnnounceDate", ""),
            "title_en": _last_text(warning, "TitleEnglish"),
            "headline_en": _last_text(warning, "HeadlineEnglish"),
            "description_en": _last_text(warning, "DescriptionEnglish"),
            "url_en": _last_text(warning, "WebUrlEnglish"),
            "title_th": warning.findtext("TitleThai", ""),
            "headline_th": warning.findtext("HeadlineThai", ""),
            "description_th": warning.findtext("DescriptionThai", ""),
            "url_th": warning.findtext("WebUrlThai", ""),
            "contact": _last_text(warning, "ContactEnglish"),
        })

    return warnings
