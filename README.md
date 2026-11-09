Bus Travel Planner

A chat-based AI travel planner that asks users about their travel preferences, remembers their answers, and ranks sample intercity buses.

Older conversation turns are compressed using LangChain summary memory. Exact answers such as city, date, budget, and bus type are stored separately.

The timetable contains sample data for Hyderabad, Warangal, Vijayawada, Guntur, Rajahmundry, Visakhapatnam, Tirupati, Bengaluru, and Chennai. It is not a live booking feed.

Setup
bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env


Put your API key in .env.

The default model is Groq (GROQ_API_KEY). To use OpenAI, set MODEL=openai:gpt-4o-mini and OPENAI_API_KEY.

Run
bash
streamlit run app.py

Example

Try:

"Hyderabad to Vijayawada tomorrow, budget 800, any bus, night, cheapest."

Then select a route number for the itinerary.