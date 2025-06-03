from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Literal, List, Optional
from utils.recommend import load_trips_from_db, score_trips_with_gemini
import os
import logging

app = FastAPI()

class RecommendationRequest(BaseModel):
    trip_type: Literal["Historical", "Adventure", "Cultural", "Beach", "Nature", "Food", "Relaxation"]
    budget: Literal["Low", "Medium", "High"]
    duration: Literal["Half-day", "Full-day", "Multi-day"]
    companions: Literal["Solo", "Couple", "Family", "Group"]
    special_interest: Literal["Cultural Tips", "Photography", "Food", "Nature", "Archaeology", "History"]
    exclude_ids: Optional[List[int]] = Field(default_factory=list)

@app.post('/recommend')
def recommend(req: RecommendationRequest):
    trips = load_trips_from_db()
    preferences = req.dict()
    preferences.pop('exclude_ids', None)  # Not used in /recommend
    try:
        recommendations = score_trips_with_gemini(preferences, trips)
    except Exception as e:
        logging.exception("Gemini API error")
        return {"status": "error", "message": f'Gemini API error: {str(e)}', "recommendations": []}
    if not recommendations:
        return {"status": "success", "recommendations": [], "message": "No matches found. Here are some popular alternatives:", "user_data": {"preferences": preferences}}
    return {"status": "success", "recommendations": recommendations[:3], "user_data": {"preferences": preferences}}

@app.post('/regenerate_recommendations')
def regenerate_recommendations(req: RecommendationRequest):
    trips = load_trips_from_db()
    preferences = req.dict()
    exclude_ids = preferences.pop('exclude_ids', [])
    # Filter out trips with IDs in exclude_ids
    trips = [trip for trip in trips if trip['id'] not in exclude_ids]
    try:
        recommendations = score_trips_with_gemini(preferences, trips)
    except Exception as e:
        logging.exception("Gemini API error")
        return {"status": "error", "message": f'Gemini API error: {str(e)}', "recommendations": []}
    if not recommendations:
        return {"status": "success", "recommendations": [], "message": "No matches found. Here are some popular alternatives:", "user_data": {"preferences": preferences, "exclude_ids": exclude_ids}}
    return {"status": "success", "recommendations": recommendations[:3], "user_data": {"preferences": preferences, "exclude_ids": exclude_ids}} 