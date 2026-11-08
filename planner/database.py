
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise ValueError("Supabase credentials are missing.")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)


def test_connection():
    return (
        supabase.table("trip_plans")
        .select("id")
        .limit(1)
        .execute()
    )


def save_trip_plan(
    thread_id,
    origin,
    destination,
    travel_date,
    budget,
    bus_type,
    departure,
    stop_city,
    priority,
    ai_response
):
    data = {
        "thread_id": thread_id,
        "origin": origin,
        "destination": destination,
        "travel_date": str(travel_date),
        "budget": budget,
        "bus_type": bus_type,
        "departure_window": departure,
        "stop_city": stop_city or None,
        "priority": priority,
        "ai_response": ai_response
    }

    result = (
        supabase.table("trip_plans")
        .insert(data)
        .execute()
    )

    return result.data[0]["id"]


def save_chat_message(trip_id, role, content):
    return (
        supabase.table("chat_messages")
        .insert({
            "trip_id": trip_id,
            "role": role,
            "content": content
        })
        .execute()
    )


def get_trip_history(limit=10):
    return (
        supabase.table("trip_plans")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    ).data


def get_chat_history(trip_id):
    return (
        supabase.table("chat_messages")
        .select("*")
        .eq("trip_id", trip_id)
        .order("created_at")
        .execute()
    ).data
