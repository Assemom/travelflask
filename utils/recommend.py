import mysql.connector
import os
from dotenv import load_dotenv
import requests
import json
import time
import re

load_dotenv()

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        port=int(os.getenv('MYSQL_PORT')),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASSWORD'),
        database=os.getenv('MYSQL_DB')
    )

def load_trips_from_db():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM trips')
    trips = cursor.fetchall()
    cursor.close()
    conn.close()
    return trips

def filter_trip_columns(trips):
    # Only keep relevant columns for Gemini
    keep = ["id", "name", "category", "entry_fee", "duration", "cultural_tip", "location_link", "image"]
    return [ {k: trip.get(k) for k in keep} for trip in trips ]

def trips_to_json(trips):
    return json.dumps(trips, ensure_ascii=False)

def filter_trips_by_category(trips, trip_type):
    # Filter trips where the category matches the user's trip_type (case-insensitive, partial match allowed)
    filtered = [trip for trip in trips if trip_type.lower() in (trip.get('category') or '').lower()]
    return filtered if filtered else trips  # Fallback to all trips if no matches

def extract_trip_ids_from_json(text):
    # Extract trip IDs from a JSON list response, possibly wrapped in markdown code block
    text = text.strip()
    if text.startswith('```'):
        # Remove markdown code block
        text = re.sub(r'^```[a-zA-Z]*\n', '', text)
        text = re.sub(r'\n```$', '', text)
    try:
        ids = json.loads(text)
        if isinstance(ids, list):
            return [int(i) for i in ids if isinstance(i, int) or (isinstance(i, str) and i.isdigit())][:3]
    except Exception:
        pass
    return []

def score_trips_with_gemini(user_answers, trips, max_retries=3, delay=3):
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise Exception('No Gemini API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY in your environment.')
    # Filter trips by category before sending to Gemini
    filtered_trips = filter_trips_by_category(trips, user_answers.get('trip_type', ''))
    filtered_trips = filter_trip_columns(filtered_trips)
    json_data = trips_to_json(filtered_trips)
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={api_key}"
    prompt = f"""
Analyze these user preferences (keys: trip_type, budget, duration, companions, special_interest): {user_answers}. Compare against these Egypt trips [JSON data]. 
Score each trip 0-100 based on: 
- 40% category match (trip_type)
- 25% budget appropriateness (budget vs entry_fee)
- 20% duration match
- 15% special interest alignment (special_interest vs cultural_tip)
Return only a valid JSON list of the IDs of the top 3 most relevant trips (e.g., [66, 68, 67]). Do not include any other information, text, or explanation. Only output the JSON list of IDs.

[JSON data]
{json_data}
"""
    print("\n--- GEMINI PROMPT ---\n", prompt)
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    last_error = None
    for attempt in range(max_retries):
        response = requests.post(endpoint, json=data)
        print("\n--- GEMINI RAW RESPONSE ---\n", response.text)
        if response.status_code == 200:
            try:
                text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                trip_ids = extract_trip_ids_from_json(text)
                id_to_trip = {trip['id']: trip for trip in filtered_trips}
                recommendations = [id_to_trip[tid] for tid in trip_ids if tid in id_to_trip]
            except Exception:
                recommendations = []
            return recommendations
        elif response.status_code == 503:
            last_error = response.text
            time.sleep(delay)
        else:
            last_error = response.text
            break
    raise Exception(f"Gemini API error: {last_error}")