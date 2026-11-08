"""Rank direct buses and one-change journeys from the sample timetable."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "buses.json"

MIN_LAYOVER = 45
MAX_LAYOVER = 6 * 60
COMFORT = {"ac_sleeper": 3, "ac_seater": 2, "non_ac": 1}
TYPE_LABEL = {
    "ac_sleeper": "AC sleeper",
    "ac_seater": "AC seater",
    "non_ac": "non-AC seater",
}


def clock_minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def layover_minutes(arrival: str, departure: str) -> int:
    gap = clock_minutes(departure) - clock_minutes(arrival)
    if gap < 0:
        gap += 24 * 60
    return gap


def in_window(departure: str, window: str) -> bool:
    if window in ("", "any"):
        return True
    minute = clock_minutes(departure)
    if window == "morning":
        return 5 * 60 <= minute < 12 * 60
    if window == "afternoon":
        return 12 * 60 <= minute < 17 * 60
    if window == "night":
        return minute >= 17 * 60 or minute < 5 * 60
    return True


def type_matches(bus_type: str, preference: str) -> bool:
    if preference in ("", "any"):
        return True
    return bus_type == preference


def format_duration(total: int) -> str:
    hours, minutes = divmod(total, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


@lru_cache(maxsize=1)
def load_network() -> dict:
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _leg(service: dict) -> dict:
    return {
        "id": service["id"],
        "operator": service["operator"],
        "from": service["from"],
        "to": service["to"],
        "type": service["type"],
        "type_label": TYPE_LABEL.get(service["type"], service["type"]),
        "departure": service["departure"],
        "arrival": service["arrival"],
        "duration_minutes": service["duration_minutes"],
        "fare_inr": service["fare_inr"],
        "boarding_point": service["boarding_point"],
    }


def _route(legs: list[dict], layover: int | None) -> dict:
    total_minutes = sum(leg["duration_minutes"] for leg in legs)
    if layover:
        total_minutes += layover
    comfort = sum(COMFORT[leg["type"]] for leg in legs) / len(legs)
    return {
        "total_fare_inr": sum(leg["fare_inr"] for leg in legs),
        "total_minutes": total_minutes,
        "total_time": format_duration(total_minutes),
        "comfort": comfort,
        "layover_minutes": layover,
        "legs": legs,
    }


def _via_ok(route: dict, via: str) -> bool:
    if not via:
        return True
    cities = [route["legs"][0]["from"]]
    cities.extend(leg["to"] for leg in route["legs"])
    return via in cities


def _sort_key(route: dict, priority: str) -> tuple:
    if priority == "fastest":
        return (route["total_minutes"], route["total_fare_inr"], -route["comfort"])
    if priority == "comfortable":
        return (-route["comfort"], route["total_minutes"], route["total_fare_inr"])
    return (route["total_fare_inr"], route["total_minutes"], -route["comfort"])


def _reason(route: dict, best: dict, priority: str, rank: int) -> str:
    if rank == 1:
        if priority == "fastest":
            return "Shortest door-to-door time, including any layover."
        if priority == "comfortable":
            return "Best comfort match. AC sleeper ranks above AC seater."
        return "Lowest fare among buses that match your filters."
    fare_gap = route["total_fare_inr"] - best["total_fare_inr"]
    time_gap = route["total_minutes"] - best["total_minutes"]
    if priority == "cheapest" and time_gap < 0:
        return f"Costs ₹{fare_gap} more and saves {format_duration(-time_gap)}."
    if priority == "fastest" and fare_gap < 0:
        return f"Takes {format_duration(time_gap)} longer and saves ₹{-fare_gap}."
    if fare_gap == 0 and time_gap == 0:
        return "Same fare and time, with a different operator or bus type."
    bits = []
    if fare_gap:
        bits.append(f"₹{abs(fare_gap)} {'more' if fare_gap > 0 else 'less'}")
    if time_gap:
        bits.append(
            f"{format_duration(abs(time_gap))} {'slower' if time_gap > 0 else 'faster'}"
        )
    return "Alternative: " + " and ".join(bits) + "."


def plan_routes(
    origin: str,
    destination: str,
    budget_inr: int,
    bus_type: str = "any",
    departure_window: str = "any",
    via: str = "",
    priority: str = "cheapest",
) -> dict:
    """Return up to three routes. Times and fares come only from buses.json."""
    network = load_network()
    cities = set(network["cities"])
    missing = [name for name in (origin, destination, via) if name and name not in cities]
    if missing:
        known = ", ".join(network["cities"])
        return {
            "routes": [],
            "note": f"No timetable for {', '.join(missing)}. Served cities: {known}.",
        }
    if origin == destination:
        return {"routes": [], "note": "Origin and destination are the same city."}

    services = network["services"]
    candidates: list[dict] = []

    for service in services:
        if service["from"] != origin or service["to"] != destination:
            continue
        if not type_matches(service["type"], bus_type):
            continue
        if not in_window(service["departure"], departure_window):
            continue
        candidates.append(_route([_leg(service)], None))

    for first in services:
        if first["from"] != origin:
            continue
        if not type_matches(first["type"], bus_type):
            continue
        if not in_window(first["departure"], departure_window):
            continue
        for second in services:
            if second["from"] != first["to"] or second["to"] != destination:
                continue
            if second["id"] == first["id"]:
                continue
            if not type_matches(second["type"], bus_type):
                continue
            gap = layover_minutes(first["arrival"], second["departure"])
            if gap < MIN_LAYOVER or gap > MAX_LAYOVER:
                continue
            candidates.append(_route([_leg(first), _leg(second)], gap))

    if not candidates:
        return {
            "routes": [],
            "note": "No direct bus or one-change journey matches that type and departure window.",
        }

    through_via = [route for route in candidates if _via_ok(route, via)]
    if not through_via:
        return {
            "routes": [],
            "note": f"No matching bus goes through {via} with a layover of 45 minutes to 6 hours.",
        }

    within_budget = [
        route for route in through_via if route["total_fare_inr"] <= budget_inr
    ]
    if not within_budget:
        cheapest = min(route["total_fare_inr"] for route in through_via)
        return {
            "routes": [],
            "note": (
                f"Matching buses start at ₹{cheapest}, which is above the ₹{budget_inr} budget."
            ),
        }

    within_budget.sort(key=lambda route: _sort_key(route, priority))
    best = within_budget[0]
    ranked = []
    for index, route in enumerate(within_budget[:3], start=1):
        ranked.append(
            {
                "rank": index,
                "total_fare_inr": route["total_fare_inr"],
                "total_minutes": route["total_minutes"],
                "total_time": route["total_time"],
                "layover_minutes": route["layover_minutes"],
                "legs": route["legs"],
                "reason": _reason(route, best, priority, index),
            }
        )
    return {"routes": ranked, "note": ""}
