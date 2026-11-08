"""LangChain agent with summary memory for the bus planner."""

from __future__ import annotations

import os

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain.chat_models import init_chat_model

from planner.tools import build_tools
from routing.optimize import load_network

SYSTEM_PROMPT = """You are a bus travel planner for Andhra Pradesh, Telangana, and nearby cities.

Cities you can plan: {cities}.
The timetable is sample data that repeats every day. You cannot book tickets.

How to run the conversation:
- Ask at most two questions in a message. Start with origin and destination if they are unknown.
- Then collect, if still missing: travel date (YYYY-MM-DD), budget per person in INR, bus type (AC sleeper, AC seater, or any), departure window (morning, afternoon, night, or any) and an optional stop city, then what matters most (cheapest, fastest, or most comfortable).
- Whenever the user states or changes a preference, call save_preferences before you reply.
- When save_preferences returns ready=true, call plan_routes before you reply.
- If they change one preference later, call save_preferences and plan_routes again. Keep every preference they did not change.

How to answer after plan_routes:
- Use only fares, times, operators, and boarding points from that tool result. Never invent a bus.
- Show up to three routes with rank, fare, total time, each leg, layover, and the reason from the tool.
- Ask which route they want, by rank.
- When they choose, write an itinerary for that route only: reach the boarding point 30 minutes before departure, each bus, what to do during a layover, arrival, and one short evening suggestion in the destination city. Do not add buses or change times.
- If the tool returns no routes, explain the note and ask which single preference they want to relax.

If the user writes in Telugu, reply in Telugu. Otherwise reply in English.
"""


def model_name() -> str:
    return os.getenv("MODEL", "groq:openai/gpt-oss-120b")


def missing_api_key() -> str | None:
    name = model_name()
    provider = name.split(":", 1)[0].lower()
    needed = {
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
        "google_genai": "GOOGLE_API_KEY",
        "gemini": "GOOGLE_API_KEY",
    }.get(provider)
    if needed and not os.getenv(needed):
        return needed
    return None


def build_agent(profile: dict, checkpointer):
    """Create an agent that summarizes older turns and keeps the latest six."""
    model = model_name()
    cities = ", ".join(load_network()["cities"])
    chat = init_chat_model(model)
    return create_agent(
        model=chat,
        tools=build_tools(profile),
        system_prompt=SYSTEM_PROMPT.format(cities=cities),
        middleware=[
            SummarizationMiddleware(
                model=chat,
                trigger=("tokens", 2000),
                keep=("messages", 6),
            )
        ],
        checkpointer=checkpointer,
    )
