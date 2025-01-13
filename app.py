import json
import requests
import datetime
from flask import Flask, render_template, request, jsonify
import pandas as pd
import base64
from io import BytesIO
from os import getenv
import pathlib
import os
from flask_cors import CORS
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from functools import lru_cache
import time

app = Flask(__name__)
# Enable CORS with credentials support
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:8080",
            "http://localhost:3000",
            "http://localhost:5173",
            "https://lovable.dev",
            "https://gptengineer.app"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Load the dataset once when the app starts
try:
    dataset = pd.read_csv(r"D:\Assignment\Assignment\Capstone-Project-Final\healthmapfinderflask\Hospital inmoratlity.csv")
    # Clean column names and handle missing values
    dataset = dataset.fillna('')  # Replace NaN with empty string
    # Ensure all required columns exist
    # Map the column names from the dataset to the required format
    dataset = dataset.rename(columns={
        'Facility ID': 'Provider ID',
        'Facility Name': 'Hospital Name', 
        'Address': 'Address',
        'City/Town': 'City',
        'State': 'State',
        'ZIP Code': 'ZIP Code',
        'County/Parish': 'County',
        'Score': 'Score'
    })
    required_columns = ['Provider ID', 'Hospital Name', 'Address', 'City', 'State', 'ZIP Code', 'County', 'Score']
    for col in required_columns:
        if col not in dataset.columns:
            raise ValueError(f"Required column '{col}' not found in dataset")
except Exception as e:
    print(f"Error loading dataset: {str(e)}")
    dataset = pd.DataFrame()  # Create empty DataFrame if loading fails

@dataclass
class HospitalStats:
    denominator: str
    lower_estimate: str
    higher_estimate: str
    measure_name: str

    @classmethod
    def from_measure(cls, measure: pd.Series) -> 'HospitalStats':
        return cls(
            denominator=str(measure.get('Denominator', 'Not Available')),
            lower_estimate=str(measure.get('Lower Estimate', 'Not Available')),
            higher_estimate=str(measure.get('Higher Estimate', 'Not Available')),
            measure_name=str(measure.get('Measure Name', 'Not Available'))
        )

    def format_comment(self) -> str:
        if self.denominator != 'Not Available':
            return (f"Based on {self.denominator} patients. "
                   f"Mortality rate estimate ranges from {self.lower_estimate}% to {self.higher_estimate}%. "
                   f"Measure: {self.measure_name}")
        return "Detailed statistics not available."

def calculate_performance(score: float) -> Tuple[str, str]:
    if score == 25:
        return "No Rating Available", "data not available"
    
    performance_levels = [
        (8, "Excellent", "significantly better than national average"),
        (12, "Good", "better than national average"),
        (16, "Average", "similar to national average"),
        (20, "Below Average", "worse than national average"),
        (float('inf'), "Poor", "significantly worse than national average")
    ]
    
    for threshold, level, detail in performance_levels:
        if score <= threshold:
            return level, detail
    
    return "Poor", "significantly worse than national average"

def calculate_hospital_score(measures: pd.DataFrame) -> Tuple[float, bool]:
    scores = measures['Score']
    valid_scores = scores[scores != 'Not Available'].astype(float)
    if valid_scores.empty:
        return 25.0, False
    return float(valid_scores.mean()), True

# Cache for geocoding results
@lru_cache(maxsize=1000)
def geocode_address(address: str) -> tuple[float, float] | None:
    try:
        # Create a new geolocator instance with increased timeout
        geolocator = Nominatim(
            user_agent="healthmapfinder",
            timeout=5
        )
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
        return None
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error for address {address}: {str(e)}")
        return None

def calculate_distance(hospital: pd.Series, search_coords: Optional[Tuple[float, float]]) -> float:
    if not search_coords:
        return 0
    
    try:
        hospital_address = f"{hospital['Address']}, {hospital['City']}, {hospital['State']} {hospital['ZIP Code']}"
        
        # Add delay between requests to avoid rate limiting
        time.sleep(0.1)  # 100ms delay
        
        hospital_coords = geocode_address(hospital_address)
        if hospital_coords:
            return round(geodesic(search_coords, hospital_coords).miles, 1)
        return 0
    except Exception as e:
        print(f"Error calculating distance for {hospital['Hospital Name']}: {str(e)}")
        return 0

def create_hospital_dict(hospital: pd.Series, avg_score: float, has_data: bool, 
                        stats: HospitalStats, distance: float, 
                        performance: str, performance_detail: str) -> Dict:
    overall_rating = max(1, min(5, 5 - (avg_score / 5))) if has_data else None
    
    return {
        "id": str(hospital['Provider ID']),
        "name": str(hospital['Hospital Name']),
        "address": str(hospital['Address']),
        "city": str(hospital['City']),
        "state": str(hospital['State']),
        "zipCode": str(hospital['ZIP Code']),
        "county": str(hospital['County']),
        "score": avg_score,
        "hasData": has_data,
        "ratings": {
            "overall": round(overall_rating, 1) if overall_rating is not None else None,
            "quality": round(overall_rating * 0.8, 1) if overall_rating is not None else None,
            "safety": round(overall_rating * 0.9, 1) if overall_rating is not None else None
        },
        "performanceLevel": performance,
        "description": (
            f"Hospital in {hospital['City']}, {hospital['State']} - "
            f"Performance is {performance_detail}. "
            f"{stats.format_comment()}"
        ),
        "statistics": {
            "denominator": stats.denominator,
            "lowerEstimate": stats.lower_estimate,
            "higherEstimate": stats.higher_estimate,
            "measureName": stats.measure_name,
            "bedsCount": None,
            "annualAdmissions": None,
            "outpatientVisits": None
        },
        "distance": distance,
        "specialties": []
    }

@app.route('/api/locations/search', methods=['GET'])
def search_locations():
    
    if dataset.empty:
        return jsonify({"error": "Dataset not available"}), 500

    query = request.args.get('query', '').strip()
    field = request.args.get('field', 'City')
    if not query or len(query) < 2:
        return jsonify([]), 200

    try:
        # Map of valid fields to their dataset column names
        field_mapping = {
            'City': 'City',
            'State': 'State',
            'County': 'County'
        }
        
        if field not in field_mapping:
            return jsonify({"error": f"Invalid field. Valid fields are: {', '.join(field_mapping.keys())}"}), 400
            
        # Get unique values from dataset that match the query
        column = field_mapping[field]
        # Convert to string and handle case-insensitive search
        matching_rows = dataset[dataset[column].astype(str).str.contains(query, case=False, na=False)]
        
        # Get unique cities
        unique_locations = matching_rows.groupby(['City', 'State', 'County', 'ZIP Code']).first().reset_index()
        
        # Prepare results
        # Get unique display strings first
        display_strings = unique_locations.apply(lambda x: f"{x['City']}, {x['State']}", axis=1).unique()
        
        # Create results from unique display strings
        results = []
        for i, display_string in enumerate(display_strings[:10]):  # Limit to 10 results
            city, state = display_string.split(", ")
            row = unique_locations[
                (unique_locations['City'] == city) & 
                (unique_locations['State'] == state)
            ].iloc[0]
            
            results.append({
                "id": str(i + 1),
                "city": str(row.get("City", "")),
                "state": str(row.get("State", "")), 
                "county": str(row.get("County", "")),
                "displayString": display_string
            })
        return jsonify(results), 200
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/hospitals/search', methods=['GET'])
def search_hospitals():
    if dataset.empty:
        return jsonify({"error": "Dataset not available"}), 500

    location = request.args.get('location', '').strip()
    health_issue = request.args.get('healthIssue', '').strip()

    if not location:
        return jsonify({"error": "Location is required"}), 400

    try:
        # Filter hospitals based on health issue
        matching_hospitals = dataset.copy()
        if health_issue:
            condition_hospitals = matching_hospitals[
                matching_hospitals['Measure Name'].str.contains(health_issue, case=False, na=False)
            ]
            if not condition_hospitals.empty:
                matching_hospitals = condition_hospitals

        results: List[Dict] = []
        
        # Group hospitals and convert to DataFrame
        hospitals_grouped = matching_hospitals.groupby(
            ['Provider ID', 'Hospital Name', 'Address', 'City', 'State', 'ZIP Code', 'County']
        ).first().reset_index()
            
        for _, hospital in hospitals_grouped.iterrows():
            try:
                # Get hospital measures
                hospital_measures = matching_hospitals[
                    matching_hospitals['Provider ID'] == hospital['Provider ID']
                ]
                
                # Calculate average score
                hospital_scores = hospital_measures['Score']
                valid_scores = hospital_scores[hospital_scores != 'Not Available'].astype(float)
                avg_score = valid_scores.mean() if not valid_scores.empty else 25
                has_data = not valid_scores.empty
                
                # Get statistics from latest measure
                latest_measure = hospital_measures.iloc[0] if not hospital_measures.empty else pd.Series()
                stats = HospitalStats.from_measure(latest_measure)
                
                # Calculate performance level based on score
                if avg_score <= 8:
                    performance = "Excellent"
                    performance_detail = "significantly better than national average"
                elif avg_score <= 12:
                    performance = "Good"
                    performance_detail = "better than national average"
                elif avg_score <= 16:
                    performance = "Average"
                    performance_detail = "similar to national average"
                elif avg_score <= 20:
                    performance = "Below Average"
                    performance_detail = "worse than national average"
                else:
                    performance = "No Rating Available" if avg_score == 25 else "Poor"
                    performance_detail = "data not available" if avg_score == 25 else "significantly worse than national average"

                # Calculate overall rating (1-5 scale, inverted from score)
                overall_rating = 5 - (avg_score / 5) if has_data else None
                
                hospital_dict = {
                    "id": str(hospital['Provider ID']),
                    "name": str(hospital['Hospital Name']),
                    "address": str(hospital['Address']),
                    "city": str(hospital['City']),
                    "state": str(hospital['State']),
                    "zipCode": str(hospital['ZIP Code']),
                    "county": str(hospital['County']),
                    "score": float(avg_score),
                    "hasData": has_data,
                    "ratings": {
                        "overall": round(overall_rating, 1) if overall_rating is not None else None,
                        "quality": round(overall_rating * 0.8, 1) if overall_rating is not None else None,
                        "safety": round(overall_rating * 0.9, 1) if overall_rating is not None else None
                    },
                    "performanceLevel": performance,
                    "description": (
                        f"Hospital in {hospital['City']}, {hospital['State']} - "
                        f"Performance is {performance_detail}. "
                        f"{stats.format_comment()}"
                    ),
                    "statistics": {
                        "denominator": stats.denominator,
                        "lowerEstimate": stats.lower_estimate,
                        "higherEstimate": stats.higher_estimate,
                        "measureName": stats.measure_name
                    }
                }
                
                results.append(hospital_dict)
                
            except Exception as hospital_error:
                print(f"Error processing hospital {hospital['Hospital Name']}: {str(hospital_error)}")
                continue

        if not results:
            return jsonify([]), 200

        # Sort results by score only (lower scores are better)
        results.sort(key=lambda x: (not x['hasData'], x['score']))
        
        return jsonify(results), 200

    except Exception as e:
        print(f"Error processing hospital search request: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route('/api/conditions/search', methods=['GET'])
def search_conditions():
    if dataset.empty:
        return jsonify({"error": "Dataset not available"}), 500

    query = request.args.get('query', '').strip()
    if not query or len(query) < 2:
        return jsonify([]), 200

    try:
        # Filter the dataset to match health conditions (Measure Name in your case)
        matching_rows = dataset[dataset['Measure Name'].str.contains(query, case=False, na=False)]

        # Prepare the results
        results = matching_rows['Measure Name'].unique()
        
        return jsonify(results.tolist()), 200

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500





if __name__ == '__main__':
    app.run(debug=True)