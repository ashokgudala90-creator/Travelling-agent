
"""Streamlit UI for the Bus Travel Planner."""

from __future__ import annotations

import uuid
from datetime import date

import streamlit as st
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver

from planner.agent import build_agent, missing_api_key, model_name
from planner.profile import (
    LABELS,
    display_value,
    empty_profile,
    public_profile,
)

from planner.database import (
    save_trip_plan,
    save_chat_message,
    get_trip_history,
)

load_dotenv()

st.set_page_config(
    page_title="Bus Travel Planner",
    page_icon="🚌",
    layout="centered",
)

GREETING = (
    "Hello! Your Bus Travel Planner is ready. "
    "You can change your travel preferences below or ask me anything."
)


def ensure_state():

    if "profile" not in st.session_state:
        st.session_state.profile = empty_profile()

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    if "checkpointer" not in st.session_state:
        st.session_state.checkpointer = InMemorySaver()

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": GREETING}
        ]

    if "trip_id" not in st.session_state:
        st.session_state.trip_id = None


def reset_chat():

    st.session_state.profile = empty_profile()
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.checkpointer = InMemorySaver()
    st.session_state.trip_id = None

    st.session_state.messages = [
        {"role": "assistant", "content": GREETING}
    ]


def message_text(message):

    content = message.content if hasattr(message, "content") else message

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for block in content:
            if isinstance(block, str):
                parts.append(block)

            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")

            elif hasattr(block, "text"):
                parts.append(block.text or "")

        return "\n".join(parts).strip()

    return str(content or "").strip()


def latest_assistant_text(result):

    for message in reversed(result.get("messages", [])):

        role = (
            getattr(message, "type", None)
            or getattr(message, "role", None)
        )

        if role in {"ai", "assistant"}:

            text = message_text(message)

            if text:
                return text

    return "I could not read a reply. Please try again."


def reply_to(user_text):

    missing = missing_api_key()

    if missing:
        return f"Please configure {missing} in your .env file."

    agent = build_agent(
        st.session_state.profile,
        st.session_state.checkpointer,
    )

    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_text}]},
        config={
            "configurable": {
                "thread_id": st.session_state.thread_id
            }
        },
    )

    return latest_assistant_text(result)


def render_profile():

    st.sidebar.header("Remembered Preferences")

    shown = public_profile(st.session_state.profile)

    for field, label in LABELS.items():

        st.sidebar.write(
            f"**{label}:** {display_value(field, shown.get(field))}"
        )

    st.sidebar.divider()

    st.sidebar.caption(f"Model: {model_name()}")

    # Travel History

    st.sidebar.subheader("📚 Travel History")

    try:

        trips = get_trip_history()

        if trips:

            for trip in trips:

                with st.sidebar.expander(
                    f"{trip['origin']} → {trip['destination']}"
                ):

                    st.write(
                        f"📅 Date: {trip['travel_date']}"
                    )

                    st.write(
                        f"💰 Budget: ₹{trip['budget']}"
                    )

                    st.write(
                        f"🚌 Bus Type: {trip['bus_type']}"
                    )

                    st.write(
                        f"⭐ Priority: {trip['priority']}"
                    )

        else:

            st.sidebar.info("No previous trips found.")

    except Exception as exc:

        st.sidebar.warning(
            f"Travel history unavailable: {exc}"
        )

    st.sidebar.divider()

    if st.sidebar.button(
        "Start Over",
        use_container_width=True
    ):

        reset_chat()
        st.rerun()


ensure_state()
render_profile()


# Header

st.title("🚌 Bus Travel Planner")

st.caption(
    "Plan your bus journey across Andhra Pradesh, Telangana, "
    "Bengaluru and Chennai."
)

st.divider()


# Travel preference form

st.subheader("✈️ Plan Your Trip")

st.write("Enter all your travel preferences below.")

with st.form("travel_preferences_form"):

    col1, col2 = st.columns(2)

    with col1:

        origin = st.text_input(
            "📍 From (Origin)",
            placeholder="Example: Hyderabad",
        )

    with col2:

        destination = st.text_input(
            "📍 To (Destination)",
            placeholder="Example: Vijayawada",
        )

    travel_date = st.date_input(
        "📅 Travel Date",
        value=date.today(),
        min_value=date.today(),
    )

    col3, col4 = st.columns(2)

    with col3:

        budget = st.selectbox(
            "💰 Budget per person",
            [500, 1000, 1500, 2000, 3000, 5000],
            format_func=lambda x: f"₹{x}",
        )

    with col4:

        bus_type = st.selectbox(
            "🚌 Bus Type",
            ["Any", "AC Sleeper", "AC Seater"],
        )

    departure = st.selectbox(
        "🕒 Preferred Departure Time",
        ["Any", "Morning", "Afternoon", "Night"],
    )

    stop_city = st.text_input(
        "📍 Optional Stop City",
        placeholder="Enter stop city (optional)",
    )

    priority = st.radio(
        "⭐ What matters most to you?",
        ["Cheapest", "Fastest", "Most comfortable"],
        horizontal=True,
    )

    submitted = st.form_submit_button(
        "🔍 Plan My Trip",
        use_container_width=True,
        type="primary",
    )


# Plan Trip

if submitted:

    if not origin.strip() or not destination.strip():

        st.error("Please enter both origin and destination.")

    elif origin.strip().lower() == destination.strip().lower():

        st.error("Origin and destination cannot be the same.")

    elif travel_date < date.today():

        st.error("Please select a valid future date.")

    else:

        travel_request = f"""
        I want to plan a bus journey with these preferences.

        Please save ALL these preferences using save_preferences
        and then call plan_routes when ready.

        Origin: {origin.strip()}
        Destination: {destination.strip()}
        Travel date: {travel_date.isoformat()}
        Budget per person: INR {budget}
        Bus type: {bus_type}
        Departure window: {departure}
        Optional stop city: {stop_city.strip() or "None"}
        Priority: {priority}

        All preferences are provided.
        Do not ask me to repeat any details.
        Plan the available bus routes.
        """

        with st.spinner("🤖 Finding the best bus routes..."):

            try:
                answer = reply_to(travel_request)

            except Exception as exc:
                answer = f"Planner error: {exc}"

        # Save trip and conversation

        if not answer.startswith("Planner error:"):

            try:

                trip_id = save_trip_plan(
                    thread_id=st.session_state.thread_id,
                    origin=origin.strip(),
                    destination=destination.strip(),
                    travel_date=travel_date,
                    budget=budget,
                    bus_type=bus_type,
                    departure=departure,
                    stop_city=stop_city.strip(),
                    priority=priority,
                    ai_response=answer
                )

                st.session_state.trip_id = trip_id

                save_chat_message(
                    trip_id,
                    "user",
                    travel_request
                )

                save_chat_message(
                    trip_id,
                    "assistant",
                    answer
                )

                st.session_state.db_notice = (
                    "Trip and chat history saved successfully!"
                )

            except Exception as exc:

                st.session_state.db_notice = (
                    f"Database save failed: {exc}"
                )

        st.session_state.messages.append(
            {"role": "user", "content": travel_request}
        )

        st.session_state.messages.append(
            {"role": "assistant", "content": answer}
        )

        st.rerun()


# Database notification

if st.session_state.get("db_notice"):

    st.info(st.session_state.db_notice)

    del st.session_state.db_notice


st.divider()


# Chat section

st.subheader("💬 Chat with Your Travel Assistant")

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


prompt = st.chat_input(
    "Ask something or change your travel preferences..."
)


if prompt:

    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):

        st.markdown(prompt)

    with st.chat_message("assistant"):

        with st.spinner(
            "Checking your travel preferences and buses..."
        ):

            try:
                answer = reply_to(prompt)

            except Exception as exc:
                answer = f"Planner error: {exc}"

        st.markdown(answer)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )

    # Save follow-up chat to Supabase

    trip_id = st.session_state.get("trip_id")

    if trip_id:

        try:

            save_chat_message(
                trip_id,
                "user",
                prompt
            )

            save_chat_message(
                trip_id,
                "assistant",
                answer
            )

        except Exception as exc:

            st.warning(
                f"Chat history save failed: {exc}"
            )
