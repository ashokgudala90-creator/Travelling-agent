"""Agent tools. Both close over the Streamlit session profile dict."""

from __future__ import annotations

import json

from langchain_core.tools import tool

from planner.profile import apply_updates, is_ready, missing_fields, public_profile
from routing.optimize import plan_routes as rank_routes


def build_tools(profile: dict):
    @tool
    def save_preferences(
        origin: str = "",
        destination: str = "",
        date: str = "",
        budget: str = "",
        bus_type: str = "",
        departure_window: str = "",
        via: str = "",
        priority: str = "",
    ) -> str:
        """Save travel preferences the user just stated.

        Call this as soon as the user mentions any of these. Leave unknown
        arguments empty. date is YYYY-MM-DD. budget is INR per person.
        bus_type is ac_sleeper, ac_seater, or any. departure_window is
        morning, afternoon, night, or any. priority is cheapest, fastest,
        or comfortable. via is an optional stop city, or "none" to clear it.
        """
        result = apply_updates(
            profile,
            {
                "origin": origin,
                "destination": destination,
                "date": date,
                "budget": budget,
                "bus_type": bus_type,
                "departure_window": departure_window,
                "via": via,
                "priority": priority,
            },
        )
        return json.dumps(result)

    @tool
    def plan_routes() -> str:
        """Rank up to three bus routes from the saved preferences.

        Call this only after save_preferences reports ready=true, and again
        after the user changes a preference. Fares and times in the result
        are the only ones you may tell the user.
        """
        if not is_ready(profile):
            return json.dumps(
                {
                    "routes": [],
                    "note": "Preferences are incomplete.",
                    "missing": missing_fields(profile),
                    "profile": public_profile(profile),
                }
            )
        ranked = rank_routes(
            origin=profile["origin"],
            destination=profile["destination"],
            budget_inr=int(profile["budget"]),
            bus_type=profile["bus_type"],
            departure_window=profile["departure_window"],
            via=profile.get("via") or "",
            priority=profile["priority"],
        )
        ranked["profile"] = public_profile(profile)
        profile["_last_plan"] = ranked
        return json.dumps(ranked)

    return [save_preferences, plan_routes]
