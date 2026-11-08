"""Structured trip preferences. The ranker reads this, not the chat summary."""

from __future__ import annotations

import re
from datetime import datetime

from routing.optimize import load_network

REQUIRED_FIELDS = (
    "origin",
    "destination",
    "date",
    "budget",
    "bus_type",
    "departure_window",
    "priority",
)

BUS_TYPES = {"ac_sleeper", "ac_seater", "any"}
WINDOWS = {"morning", "afternoon", "night", "any"}
PRIORITIES = {"cheapest", "fastest", "comfortable"}

ALIASES = {
    "hyd": "Hyderabad",
    "hyderabad": "Hyderabad",
    "secunderabad": "Hyderabad",
    "warangal": "Warangal",
    "wgl": "Warangal",
    "vijayawada": "Vijayawada",
    "bezawada": "Vijayawada",
    "bza": "Vijayawada",
    "vijaywada": "Vijayawada",
    "guntur": "Guntur",
    "rajahmundry": "Rajahmundry",
    "rajamundry": "Rajahmundry",
    "rjy": "Rajahmundry",
    "visakhapatnam": "Visakhapatnam",
    "vizag": "Visakhapatnam",
    "vskp": "Visakhapatnam",
    "vizianagaram": "Visakhapatnam",
    "tirupati": "Tirupati",
    "tirupathi": "Tirupati",
    "tpty": "Tirupati",
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "blr": "Bengaluru",
    "chennai": "Chennai",
    "madras": "Chennai",
    "maa": "Chennai",
}

LABELS = {
    "origin": "From",
    "destination": "To",
    "date": "Date",
    "budget": "Budget",
    "bus_type": "Bus type",
    "departure_window": "Departure",
    "via": "Stop city",
    "priority": "Priority",
}


def empty_profile() -> dict:
    return {
        "origin": "",
        "destination": "",
        "date": "",
        "budget": None,
        "bus_type": "",
        "departure_window": "",
        "via": "",
        "priority": "",
    }


def missing_fields(profile: dict) -> list[str]:
    missing = []
    for field in REQUIRED_FIELDS:
        value = profile.get(field)
        if value is None or value == "":
            missing.append(field)
    return missing


def is_ready(profile: dict) -> bool:
    return not missing_fields(profile)


def canonical_city(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value.strip())
    if not cleaned:
        return ""
    known = {city.lower(): city for city in load_network()["cities"]}
    key = cleaned.lower()
    if key in ALIASES:
        return ALIASES[key]
    if key in known:
        return known[key]
    return cleaned.title()


def _choice(value: str, allowed: set[str], aliases: dict[str, str]) -> str:
    key = value.strip().lower().replace("-", "_").replace(" ", "_")
    key = aliases.get(key, key)
    if key not in allowed:
        raise ValueError(f"use one of: {', '.join(sorted(allowed))}")
    return key


def apply_updates(profile: dict, updates: dict) -> dict:
    """Merge non-empty updates into profile. Returns errors and what is still missing."""
    errors: list[str] = []

    def take(field: str) -> str:
        value = updates.get(field)
        if value is None:
            return ""
        return str(value).strip()

    origin = take("origin")
    if origin:
        profile["origin"] = canonical_city(origin)

    destination = take("destination")
    if destination:
        profile["destination"] = canonical_city(destination)

    via = take("via")
    if via:
        if via.lower() in {"none", "no", "direct", "skip"}:
            profile["via"] = ""
        else:
            profile["via"] = canonical_city(via)

    date = take("date")
    if date:
        try:
            parsed = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            errors.append("date must be YYYY-MM-DD")
        else:
            profile["date"] = parsed.strftime("%Y-%m-%d")

    budget = take("budget")
    if budget:
        digits = re.sub(r"[^\d]", "", budget)
        if not digits or int(digits) <= 0:
            errors.append("budget must be a positive amount in INR")
        else:
            profile["budget"] = int(digits)

    bus_type = take("bus_type")
    if bus_type:
        try:
            profile["bus_type"] = _choice(
                bus_type,
                BUS_TYPES,
                {"sleeper": "ac_sleeper", "ac": "ac_seater", "seater": "ac_seater"},
            )
        except ValueError as exc:
            errors.append(f"bus_type: {exc}")

    window = take("departure_window")
    if window:
        try:
            profile["departure_window"] = _choice(
                window,
                WINDOWS,
                {"evening": "night", "anytime": "any"},
            )
        except ValueError as exc:
            errors.append(f"departure_window: {exc}")

    priority = take("priority")
    if priority:
        try:
            profile["priority"] = _choice(
                priority,
                PRIORITIES,
                {
                    "cheap": "cheapest",
                    "cheapest": "cheapest",
                    "fast": "fastest",
                    "fastest": "fastest",
                    "comfort": "comfortable",
                    "comfortable": "comfortable",
                },
            )
        except ValueError as exc:
            errors.append(f"priority: {exc}")

    missing = missing_fields(profile)
    return {
        "profile": public_profile(profile),
        "missing": missing,
        "ready": not missing,
        "errors": errors,
    }


def public_profile(profile: dict) -> dict:
    shown = {}
    for field in (*REQUIRED_FIELDS, "via"):
        value = profile.get(field)
        shown[field] = value if value not in ("", None) else None
    return shown


def display_value(field: str, value) -> str:
    if value in ("", None):
        return "not set"
    if field == "budget":
        return f"₹{value}"
    if field == "bus_type":
        return {
            "ac_sleeper": "AC sleeper",
            "ac_seater": "AC seater",
            "any": "Any",
        }.get(value, str(value))
    if field == "departure_window":
        return str(value).capitalize()
    if field == "priority":
        return str(value).capitalize()
    return str(value)
