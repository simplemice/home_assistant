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
STATE_READY_TO_SHIP = "ready_to_ship"
STATE_PICKED_UP = "picked_up"
STATE_AWAITING_COLLECTION = "awaiting_collection"
STATE_IN_TRANSIT = "in_transit"
STATE_OUT_FOR_DELIVERY = "out_for_delivery"
STATE_DELIVERED = "delivered"
STATE_PROBLEM = "problem"
STATE_UNKNOWN = "unknown"

STATES = [
    STATE_NOT_FOUND,
    STATE_READY_TO_SHIP,
    STATE_PICKED_UP,
    STATE_IN_TRANSIT,
    STATE_OUT_FOR_DELIVERY,
    STATE_AWAITING_COLLECTION,
    STATE_DELIVERED,
    STATE_PROBLEM,
    STATE_UNKNOWN,
]

SENSOR_NAME = {"en": "Status", "th": "สถานะ"}

STATE_TEXT = {
    "en": {
        STATE_NOT_FOUND: "Not found",
        STATE_READY_TO_SHIP: "Ready to ship",
        STATE_PICKED_UP: "Picked up",
        STATE_IN_TRANSIT: "In transit",
        STATE_OUT_FOR_DELIVERY: "Out for delivery",
        STATE_AWAITING_COLLECTION: "Ready for collection",
        STATE_DELIVERED: "Delivered",
        STATE_PROBLEM: "Problem",
        STATE_UNKNOWN: "Unknown",
    },
    "th": {
        STATE_NOT_FOUND: "ไม่พบพัสดุ",
        STATE_READY_TO_SHIP: "เตรียมจัดส่ง",
        STATE_PICKED_UP: "รับพัสดุแล้ว",
        STATE_IN_TRANSIT: "อยู่ระหว่างขนส่ง",
        STATE_OUT_FOR_DELIVERY: "กำลังนำส่ง",
        STATE_AWAITING_COLLECTION: "รอรับที่จุดรับพัสดุ",
        STATE_DELIVERED: "จัดส่งสำเร็จ",
        STATE_PROBLEM: "มีปัญหา",
        STATE_UNKNOWN: "ไม่ทราบสถานะ",
    },
}

SENSOR_NAME_DETAILS = {"en": "Details", "th": "รายละเอียด"}

# Official LEX TH status codes, taken from the enum and i18n strings in the
# lex.th tracking page (g.alicdn.com/logistics-fe/lex-web). code -> (state, en, th)
RAW_STATUS = {
    "package_created": (
        STATE_READY_TO_SHIP,
        "Package has been created",
        "สร้างพัสดุแล้ว",
    ),
    "package_ready_to_be_shipped": (
        STATE_READY_TO_SHIP,
        "Seller has prepared the package and it is waiting to be picked up by LEX TH",
        "ผู้ขายเตรียมพัสดุเรียบร้อยแล้ว และรอ LEX TH เข้ารับพัสดุ",
    ),
    "domestic_planned_for_pickup": (
        STATE_READY_TO_SHIP,
        "Package pickup has been planned",
        "พัสดุอยู่ในแผนการเข้ารับแล้ว",
    ),
    "domestic_about_to_pickup": (
        STATE_READY_TO_SHIP,
        "Courier will try to pick up the package within the next hour",
        "พนักงานจะเข้ารับพัสดุภายในชั่วโมงถัดไป",
    ),
    "domestic_pickup/sign_in_failure": (
        STATE_PROBLEM,
        "Pickup failed, courier could not collect the package",
        "เข้ารับพัสดุไม่สำเร็จ",
    ),
    "domestic_pickup/sign_in_success": (
        STATE_PICKED_UP,
        "Package has been picked up and received by LEX TH",
        "LEX TH รับพัสดุเรียบร้อยแล้ว",
    ),
    "domestic_sc_sign_in_success": (
        STATE_PICKED_UP,
        "Seller dropped the package at a service point and it entered the shipping process",
        "ผู้ขายนำพัสดุส่งที่จุดบริการและเข้าสู่กระบวนการขนส่งแล้ว",
    ),
    "domestic_handover_accepted": (
        STATE_PICKED_UP,
        "Delivery partner has received the package",
        "ผู้ให้บริการจัดส่งได้รับพัสดุเรียบร้อยแล้ว",
    ),
    "domestic_pkg_outbound_attendance": (
        STATE_IN_TRANSIT,
        "Package received for onward shipping",
        "พัสดุถูกรับเข้าเพื่อทำการส่งต่อไป",
    ),
    "domestic_ib_success_in_sort_center": (
        STATE_IN_TRANSIT,
        "Package is being sorted and will soon head to the delivery facility",
        "พัสดุอยู่ระหว่างการคัดแยก และจะถูกส่งต่อไปยังศูนย์กระจายสินค้าปลายทางเร็วๆ นี้",
    ),
    "domestic_ib_failure_in_sort_center": (
        STATE_PROBLEM,
        "Sort center failed to receive the package",
        "ศูนย์กระจายพัสดุรับพัสดุเข้าไม่สำเร็จ",
    ),
    "domestic_ob_success_in_sort_center": (
        STATE_IN_TRANSIT,
        "Package has left the sort center",
        "พัสดุออกจากศูนย์คัดแยกแล้ว",
    ),
    "domestic_linehaul_packed": (
        STATE_IN_TRANSIT,
        "Package is loaded on a truck between facilities",
        "บรรจุเข้ารถขนส่งระหว่างศูนย์ฯ แล้ว",
    ),
    "domestic_package_stationed_in": (
        STATE_IN_TRANSIT,
        "Package has arrived at the delivery facility and will be out for delivery soon",
        "พัสดุถึงศูนย์กระจายสินค้าปลายทางแล้ว และจะถูกนำส่งเร็วๆ นี้",
    ),
    "domestic_package_stationed_out": (
        STATE_IN_TRANSIT,
        "Package has left the facility and is on its way to the recipient",
        "พัสดุออกจากศูนย์โลจิสติกส์และกำลังนำส่งไปยังผู้รับ",
    ),
    "domestic_handover_to_cp": (
        STATE_IN_TRANSIT,
        "Package is on its way to the pickup point",
        "พัสดุกำลังถูกส่งไปยังจุดรับพัสดุ",
    ),
    "domestic_about_to_deliver": (
        STATE_OUT_FOR_DELIVERY,
        "Package will be delivered within the next hour",
        "พัสดุจะถูกนำส่งภายในชั่วโมงข้างหน้า",
    ),
    "domestic_out_for_delivery": (
        STATE_OUT_FOR_DELIVERY,
        "Package is out for delivery and will arrive today",
        "พัสดุกำลังนำส่งและจะถึงในวันนี้",
    ),
    "domestic_redelivery": (
        STATE_OUT_FOR_DELIVERY,
        "Courier is attempting delivery again today",
        "พนักงานจะพยายามนำส่งพัสดุอีกครั้งในวันนี้",
    ),
    "domestic_last_mile_customer_station_inbound": (
        STATE_AWAITING_COLLECTION,
        "Package is ready for collection at the pickup point",
        "พัสดุพร้อมให้รับที่จุดบริการรับพัสดุแล้ว",
    ),
    "domestic_delivered": (
        STATE_DELIVERED,
        "Package has been delivered",
        "จัดส่งพัสดุสำเร็จแล้ว",
    ),
    "domestic_last_mile_customer_station_outbound_success": (
        STATE_DELIVERED,
        "Package has been collected and delivered",
        "รับพัสดุที่จุดบริการสำเร็จแล้ว",
    ),
    "domestic_1st_attempt_failed": (
        STATE_PROBLEM,
        "First delivery attempt failed, another attempt will follow",
        "จัดส่งไม่สำเร็จ จะพยายามจัดส่งอีกครั้ง",
    ),
    "domestic_reattempts_failed": (
        STATE_PROBLEM,
        "Delivery attempts failed",
        "จัดส่งพัสดุไม่สำเร็จ",
    ),
    "domestic_delivery_failed": (
        STATE_PROBLEM,
        "Delivery failed, package will be returned to the seller",
        "จัดส่งไม่สำเร็จ พัสดุจะถูกส่งคืนผู้ขาย",
    ),
    "domestic_last_mile_station_customer_failed_pickup": (
        STATE_PROBLEM,
        "Package was not collected in time and will be returned",
        "ไม่ได้รับพัสดุภายในเวลาที่กำหนด พัสดุจะถูกส่งคืน",
    ),
    "domestic_on_hold": (
        STATE_PROBLEM,
        "Package is temporarily on hold",
        "พัสดุถูกระงับไว้ชั่วคราว",
    ),
    "domestic_cp_return_to_3pl": (
        STATE_PROBLEM,
        "Package was not collected and is returning to the logistics center",
        "พัสดุไม่ถูกรับและกำลังส่งกลับศูนย์โลจิสติกส์",
    ),
    "domestic_return_at_transit_hub": (
        STATE_PROBLEM,
        "Returning package arrived at a logistics center",
        "พัสดุที่ส่งคืนถึงศูนย์โลจิสติกส์แล้ว",
    ),
    "domestic_return_with_last_mile_3pl": (
        STATE_PROBLEM,
        "Returning package arrived at a logistics center",
        "พัสดุที่ส่งคืนถึงศูนย์โลจิสติกส์แล้ว",
    ),
    "domestic_with_hub_returned_from_station": (
        STATE_PROBLEM,
        "Package was returned from the pickup point to the hub",
        "พัสดุถูกส่งคืนจากจุดรับพัสดุไปยังศูนย์กระจายพัสดุแล้ว",
    ),
    "domestic_back_to_shipper": (
        STATE_PROBLEM,
        "Package has been returned to the seller",
        "พัสดุถูกส่งคืนให้ผู้ขายแล้ว",
    ),
    "domestic_package_returned": (
        STATE_PROBLEM,
        "Package has been returned to the seller",
        "พัสดุถูกส่งคืนให้ผู้ขายสำเร็จแล้ว",
    ),
    "domestic_warehouse_returned": (
        STATE_PROBLEM,
        "Package has returned to the warehouse",
        "พัสดุกลับไปยังคลังสินค้าแล้ว",
    ),
    "domestic_package_return_attempt_failed": (
        STATE_PROBLEM,
        "Return to seller failed, another attempt will follow",
        "ส่งคืนผู้ขายไม่สำเร็จ จะพยายามอีกครั้ง",
    ),
    "domestic_package_return_failed": (
        STATE_PROBLEM,
        "Return to seller failed",
        "ส่งคืนผู้ขายไม่สำเร็จ",
    ),
    "domestic_package_return_failed_pickup_pending": (
        STATE_PROBLEM,
        "Return to seller failed, waiting for the seller to collect",
        "ส่งคืนผู้ขายไม่สำเร็จ รอผู้ขายมารับคืน",
    ),
    "package_breached": (
        STATE_PROBLEM,
        "Package was not delivered within the promised time",
        "พัสดุไม่ได้ถูกจัดส่งภายในเวลาที่กำหนด",
    ),
    "package_cancelled": (
        STATE_PROBLEM,
        "Package has been cancelled",
        "พัสดุถูกยกเลิกแล้ว",
    ),
    "package_damaged": (
        STATE_PROBLEM,
        "Package is damaged",
        "พัสดุเสียหาย",
    ),
    "package_intercepted": (
        STATE_PROBLEM,
        "Delivery was cancelled by the courier",
        "การจัดส่งถูกยกเลิกโดยบริษัทขนส่ง",
    ),
    "package_lost": (
        STATE_PROBLEM,
        "Package was lost in transit",
        "พัสดุสูญหายระหว่างการจัดส่ง",
    ),
    "package_scrapped": (
        STATE_PROBLEM,
        "Return failed, package is held awaiting collection by the seller",
        "ส่งคืนไม่สำเร็จ พัสดุถูกเก็บไว้รอรับคืน",
    ),
}


# Fallback sentences by canonical state, used for unverified raw codes.
STATE_DESCRIPTIONS = {
    "en": {
        STATE_NOT_FOUND: "No tracking information yet",
        STATE_READY_TO_SHIP: "Seller has prepared the package and it is waiting to be picked up",
        STATE_PICKED_UP: "Package has been picked up and received by LEX TH",
        STATE_IN_TRANSIT: "Package is on its way",
        STATE_OUT_FOR_DELIVERY: "Package is out for delivery and will arrive soon",
        STATE_AWAITING_COLLECTION: "Package is ready for collection at the pickup point",
        STATE_DELIVERED: "Package has been delivered",
        STATE_PROBLEM: "There is a problem with the delivery",
        STATE_UNKNOWN: "Tracking update received",
    },
    "th": {
        STATE_NOT_FOUND: "ยังไม่มีข้อมูลการติดตามพัสดุ",
        STATE_READY_TO_SHIP: "ผู้ขายเตรียมพัสดุแล้ว และรอเข้ารับพัสดุ",
        STATE_PICKED_UP: "LEX TH รับพัสดุเรียบร้อยแล้ว",
        STATE_IN_TRANSIT: "พัสดุอยู่ระหว่างการขนส่ง",
        STATE_OUT_FOR_DELIVERY: "พัสดุกำลังนำส่งและจะถึงเร็วๆ นี้",
        STATE_AWAITING_COLLECTION: "พัสดุพร้อมให้รับที่จุดรับพัสดุแล้ว",
        STATE_DELIVERED: "จัดส่งพัสดุสำเร็จแล้ว",
        STATE_PROBLEM: "การจัดส่งมีปัญหา",
        STATE_UNKNOWN: "มีการอัปเดตสถานะพัสดุ",
    },
}


def describe_status(raw: str | None, state: str, language: str) -> str:
    """Human-friendly sentence for a raw status code."""
    known = RAW_STATUS.get(raw or "")
    if known:
        return known[1] if language == "en" else known[2]
    text = STATE_DESCRIPTIONS[language][state]
    if state == STATE_UNKNOWN and raw:
        return f"{text} ({raw})"
    return text


# Fallback heuristics for codes missing from RAW_STATUS (LEX may add new ones).
# The raw status is always exposed as an attribute. Order matters: pickup must
# win over "success"/"sign".
_PROBLEM_TOKENS = ("fail", "exception", "return", "reject", "lost", "damage", "cancel")
_OUT_FOR_DELIVERY_TOKENS = ("out_for_delivery", "delivering", "delivery_start", "on_delivery")
_DELIVERED_TOKENS = ("delivered", "delivery_success", "sign_success", "signed", "sign_in_success")
_IN_TRANSIT_TOKENS = ("sort_center", "stationed", "transit", "linehaul", "arrive", "depart", "dispatch", "hub", "_ib_", "_ob_")


def normalize_status(raw: str | None) -> str:
    """Map a raw LEX TH status code to a canonical state."""
    if not raw:
        return STATE_UNKNOWN
    status = raw.lower()
    if status in RAW_STATUS:
        return RAW_STATUS[status][0]
    if "ready_to_be_shipped" in status or "ready_to_ship" in status:
        return STATE_READY_TO_SHIP
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
