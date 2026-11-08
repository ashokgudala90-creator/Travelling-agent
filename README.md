# Bus travel planner

A chat that asks a few preference questions, remembers them, and ranks sample intercity buses. Older turns are compressed with LangChain summary memory. Exact answers (city, date, budget, bus type) are stored separately so a summary cannot drop them.

The timetable is sample data for Hyderabad, Warangal, Vijayawada, Guntur, Rajahmundry, Visakhapatnam, Tirupati, Bengaluru, and Chennai. It is not a live booking feed.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Put your key in `.env`. The default model is Groq (`GROQ_API_KEY`). To use OpenAI, set `MODEL=openai:gpt-4o-mini` and `OPENAI_API_KEY`.

## Run

```bash
streamlit run app.py
```

Try: “Hyderabad to Vijayawada tomorrow, budget 800, any bus, night, cheapest.” Then pick a route number for the itinerary. “Make it more comfortable” keeps the other answers and ranks again.
