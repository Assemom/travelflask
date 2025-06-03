from flask import Flask, request, jsonify
from typing import List, Optional, Dict, Any
import os
from utils.recommend import load_trips_from_db, score_trips_with_gemini

app = Flask(__name__)

def validate_request_data(data: Dict[str, Any]) -> tuple[bool, str]:
    required_fields = {
        'trip_type': ["Historical", "Adventure", "Cultural", "Beach", "Nature", "Food", "Relaxation"],
        'budget': ["Low", "Medium", "High"],
        'duration': ["Half-day", "Full-day", "Multi-day"],
        'companions': ["Solo", "Couple", "Family", "Group"],
        'special_interest': ["Cultural Tips", "Photography", "Food", "Nature", "Archaeology", "History"]
    }
    
    for field, allowed_values in required_fields.items():
        if field not in data:
            return False, f"Missing required field: {field}"
        if data[field] not in allowed_values:
            return False, f"Invalid value for {field}. Allowed values: {allowed_values}"
    
    return True, ""

@app.route('/recommend', methods=['POST'])
def recommend():
    try:
        data = request.get_json()
        is_valid, error_message = validate_request_data(data)
        
        if not is_valid:
            return jsonify({
                "status": "error",
                "message": error_message
            }), 400

        trips = load_trips_from_db()
        preferences = data.copy()
        preferences.pop('exclude_ids', None)  # Not used in /recommend
        
        try:
            recommendations = score_trips_with_gemini(preferences, trips)
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f'Gemini API error: {str(e)}'
            }), 500
        
        if not recommendations:
            return jsonify({
                "status": "success",
                "recommendations": [],
                "message": "No matches found. Here are some popular alternatives:",
                "user_data": {"preferences": preferences}
            })
        
        return jsonify({
            "status": "success",
            "recommendations": recommendations[:3],
            "user_data": {"preferences": preferences}
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

@app.route('/regenerate_recommendations', methods=['POST'])
def regenerate_recommendations():
    try:
        data = request.get_json()
        is_valid, error_message = validate_request_data(data)
        
        if not is_valid:
            return jsonify({
                "status": "error",
                "message": error_message
            }), 400

        trips = load_trips_from_db()
        preferences = data.copy()
        exclude_ids = preferences.pop('exclude_ids', [])
        
        # Filter out trips with IDs in exclude_ids
        trips = [trip for trip in trips if trip['id'] not in exclude_ids]
        
        try:
            recommendations = score_trips_with_gemini(preferences, trips)
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f'Gemini API error: {str(e)}'
            }), 500
        
        if not recommendations:
            return jsonify({
                "status": "success",
                "recommendations": [],
                "message": "No matches found. Here are some popular alternatives:",
                "user_data": {"preferences": preferences, "exclude_ids": exclude_ids}
            })
        
        return jsonify({
            "status": "success",
            "recommendations": recommendations[:3],
            "user_data": {"preferences": preferences, "exclude_ids": exclude_ids}
        })
    
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Server error: {str(e)}"
        }), 500

# For local development
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10418))) 