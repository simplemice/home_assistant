from datetime import datetime, time, timedelta, timezone
import xml.etree.ElementTree as ET

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


# Thailand has no DST, so a fixed offset is safe and avoids blocking tz lookups.
_TH_TZ = timezone(timedelta(hours=7))

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
)


def parse_tmd_datetime(value: str, end_of_day: bool = False) -> datetime | None:
    """Parse a TMD date string into an aware datetime (Thai time).

    TMD endpoints mix formats, so try several. Date-only values resolve to
    start of day, or end of day when end_of_day is set (for expiry times).
    Returns None when nothing matches.
    """
    value = (value or "").strip()
    if not value:
        return None
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if parsed.year > 2400:  # Buddhist Era year
            parsed = parsed.replace(year=parsed.year - 543)
        if "%H" not in fmt and end_of_day:
            parsed = datetime.combine(parsed.date(), time(23, 59, 59))
        return parsed.replace(tzinfo=_TH_TZ)
    return None


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
        effect_start = warning.findtext("EffectStartDate", "")
        effect_end = warning.findtext("EffectEndDate", "")
        announce_date = warning.findtext("AnnounceDate", "")
        warnings.append({
            "issue_no": warning.findtext("IssueNo", ""),
            "effect_start": effect_start,
            "effect_end": effect_end,
            "announce_date": announce_date,
            "effect_start_dt": parse_tmd_datetime(effect_start),
            "effect_end_dt": parse_tmd_datetime(effect_end, end_of_day=True),
            "announce_dt": parse_tmd_datetime(announce_date),
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
