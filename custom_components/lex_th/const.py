"""Constants for the LEX TH parcel tracking integration."""
from __future__ import annotations

from datetime import timedelta
import re

DOMAIN = "lex_th"

API_URL = "https://lex.th/api/get_package_history"
TRACKING_URL = "https://lex.th/tracking?references={number}"

SCAN_INTERVAL = timedelta(minutes=30)
REQUEST_TIMEOUT = 20

CONF_TRACKING_NUMBER = "tracking_number"
CONF_LANGUAGE = "language"
LANGUAGES = ["en", "th"]
DEFAULT_LANGUAGE = "en"
TRACKING_NUMBER_RE = re.compile(r"^[A-Z0-9]{8,32}$")

STATE_NOT_FOUND = "not_found"
STATE_PICKED_UP = "picked_up"
STATE_IN_TRANSIT = "in_transit"
STATE_OUT_FOR_DELIVERY = "out_for_delivery"
STATE_DELIVERED = "delivered"
STATE_PROBLEM = "problem"
STATE_UNKNOWN = "unknown"

STATES = [
    STATE_NOT_FOUND,
    STATE_PICKED_UP,
    STATE_IN_TRANSIT,
    STATE_OUT_FOR_DELIVERY,
    STATE_DELIVERED,
    STATE_PROBLEM,
    STATE_UNKNOWN,
]

SENSOR_NAME = {"en": "Status", "th": "สถานะ"}

STATE_TEXT = {
    "en": {
        STATE_NOT_FOUND: "Not found",
        STATE_PICKED_UP: "Picked up",
        STATE_IN_TRANSIT: "In transit",
        STATE_OUT_FOR_DELIVERY: "Out for delivery",
        STATE_DELIVERED: "Delivered",
        STATE_PROBLEM: "Problem",
        STATE_UNKNOWN: "Unknown",
    },
    "th": {
        STATE_NOT_FOUND: "ไม่พบพัสดุ",
        STATE_PICKED_UP: "รับพัสดุแล้ว",
        STATE_IN_TRANSIT: "อยู่ระหว่างขนส่ง",
        STATE_OUT_FOR_DELIVERY: "กำลังนำส่ง",
        STATE_DELIVERED: "จัดส่งสำเร็จ",
        STATE_PROBLEM: "มีปัญหา",
        STATE_UNKNOWN: "ไม่ทราบสถานะ",
    },
}

SENSOR_NAME_DETAILS = {"en": "Details", "th": "รายละเอียด"}

# Lazada-app style sentences for verified raw codes.
RAW_DESCRIPTIONS = {
    "domestic_ib_success_in_sort_center": {
        "en": "Package is being sorted and will soon head to the delivery facility",
        "th": "พัสดุอยู่ระหว่างการคัดแยก และจะถูกส่งต่อไปยังศูนย์กระจายสินค้าปลายทางเร็วๆ นี้",
    },
    "domestic_pickup/sign_in_success": {
        "en": "Package has been picked up and received by LEX TH",
        "th": "LEX TH รับพัสดุเรียบร้อยแล้ว",
    },
}

# Fallback sentences by canonical state, used for unverified raw codes.
STATE_DESCRIPTIONS = {
    "en": {
        STATE_NOT_FOUND: "No tracking information yet",
        STATE_PICKED_UP: "Package has been picked up and received by LEX TH",
        STATE_IN_TRANSIT: "Package is on its way",
        STATE_OUT_FOR_DELIVERY: "Package is out for delivery and will arrive soon",
        STATE_DELIVERED: "Package has been delivered",
        STATE_PROBLEM: "There is a problem with the delivery",
        STATE_UNKNOWN: "Tracking update received",
    },
    "th": {
        STATE_NOT_FOUND: "ยังไม่มีข้อมูลการติดตามพัสดุ",
        STATE_PICKED_UP: "LEX TH รับพัสดุเรียบร้อยแล้ว",
        STATE_IN_TRANSIT: "พัสดุอยู่ระหว่างการขนส่ง",
        STATE_OUT_FOR_DELIVERY: "พัสดุกำลังนำส่งและจะถึงเร็วๆ นี้",
        STATE_DELIVERED: "จัดส่งพัสดุสำเร็จแล้ว",
        STATE_PROBLEM: "การจัดส่งมีปัญหา",
        STATE_UNKNOWN: "มีการอัปเดตสถานะพัสดุ",
    },
}


def describe_status(raw: str | None, state: str, language: str) -> str:
    """Human-friendly sentence for a raw status code."""
    known = RAW_DESCRIPTIONS.get(raw or "")
    if known and language in known:
        return known[language]
    return STATE_DESCRIPTIONS[language][state]


# Only `domestic_ib_success_in_sort_center` and `domestic_pickup/sign_in_success`
# are verified. Everything else is a best-effort guess; the raw status is always
# exposed as an attribute. Order matters: pickup must win over "success"/"sign".
_PROBLEM_TOKENS = ("fail", "exception", "return", "reject", "lost", "damage", "cancel")
_OUT_FOR_DELIVERY_TOKENS = ("out_for_delivery", "delivering", "delivery_start", "on_delivery")
_DELIVERED_TOKENS = ("delivered", "delivery_success", "sign_success", "signed", "sign_in_success")
_IN_TRANSIT_TOKENS = ("sort_center", "transit", "linehaul", "arrive", "depart", "dispatch", "hub", "_ib_", "_ob_")


def normalize_status(raw: str | None) -> str:
    """Map a raw LEX TH status code to a canonical state."""
    if not raw:
        return STATE_UNKNOWN
    status = raw.lower()
    if "pickup" in status:
        return STATE_PICKED_UP
    if any(t in status for t in _PROBLEM_TOKENS):
        return STATE_PROBLEM
    if any(t in status for t in _OUT_FOR_DELIVERY_TOKENS):
        return STATE_OUT_FOR_DELIVERY
    if any(t in status for t in _DELIVERED_TOKENS):
        return STATE_DELIVERED
    if any(t in status for t in _IN_TRANSIT_TOKENS):
        return STATE_IN_TRANSIT
    return STATE_UNKNOWN
