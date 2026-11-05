"""Keyword classification of TMD warnings (English and Thai)."""
import re

# Word boundaries keep "thunderstorm" from matching "storm" and "heat wave"
# from matching "wave". Thai has no word boundaries, so use lookaheads.
CATEGORY_PATTERNS: dict[str, re.Pattern] = {
    "storm": re.compile(
        r"\b(?:storms?|tropical|typhoons?|cyclones?|depressions?)\b"
        r"|พายุหมุนเขตร้อน|พายุโซนร้อน|ไต้ฝุ่น|ดีเปรสชัน|ไซโคลน"
        r"|พายุ(?!ฝนฟ้าคะนอง|ฤดูร้อน)",
        re.IGNORECASE,
    ),
    "heavy_rain": re.compile(
        r"heavy rain|heavy to very heavy|flash floods?|\bfloods?(?:ing)?\b"
        r"|ฝนตกหนัก|น้ำท่วม|น้ำป่า",
        re.IGNORECASE,
    ),
    "wave": re.compile(
        r"\b(?<!heat )waves?\b|wind-waves?|rough seas?|high seas?"
        r"|คลื่น(?!ความร้อน)",
        re.IGNORECASE,
    ),
    "thunderstorm": re.compile(
        r"thunderstorms?|lightning|\bgusts?\b|\bhail\b"
        r"|ฝนฟ้าคะนอง|ลมกระโชก|ลูกเห็บ|ฟ้าผ่า",
        re.IGNORECASE,
    ),
    "monsoon": re.compile(
        r"monsoon|cold front|\bcold\b|strong winds?"
        r"|มรสุม|ลมหนาว|อากาศหนาว|ลมแรง",
        re.IGNORECASE,
    ),
}

SEVERE_PATTERN = re.compile(
    r"very heavy|typhoon|tropical storm|cyclone|severe|extreme|flash flood"
    r"|ฝนตกหนักมาก|ไต้ฝุ่น|พายุหมุนเขตร้อน|พายุโซนร้อน|น้ำท่วมฉับพลัน|น้ำป่า",
    re.IGNORECASE,
)

SEVERITY_OPTIONS = ["none", "advisory", "warning", "severe"]


def warning_text(warning: dict) -> str:
    """Title and headline in both languages (description is too noisy)."""
    return " ".join(
        warning.get(key, "")
        for key in ("title_en", "headline_en", "title_th", "headline_th")
    )


def matches(warnings: list[dict], category: str) -> bool:
    pattern = CATEGORY_PATTERNS[category]
    return any(pattern.search(warning_text(w)) for w in warnings)


def severity(warnings: list[dict]) -> str:
    """none / advisory / warning (known hazard) / severe (extreme keywords)."""
    if not warnings:
        return "none"
    texts = [warning_text(w) for w in warnings]
    if any(SEVERE_PATTERN.search(t) for t in texts):
        return "severe"
    if any(p.search(t) for p in CATEGORY_PATTERNS.values() for t in texts):
        return "warning"
    return "advisory"
