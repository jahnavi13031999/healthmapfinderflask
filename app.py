import json
import requests
import datetime
from flask import Flask, render_template, request, jsonify, make_response
import pandas as pd
import base64
from io import BytesIO
from os import getenv
import pathlib
import os
from flask_cors import CORS
# from geopy.geocoders import Nominatim
# from geopy.distance import geodesic
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
# from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from functools import lru_cache
import time
import math
import numpy as np

app = Flask(__name__)
CORS(app)

# Load dataset once when app starts
try:
    dataset = pd.read_csv(r"Hospital inmoratlity.csv")
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
def filter_hospitals(health_issue: str) -> pd.DataFrame:
    """Filter hospitals based on health issue"""
    if not health_issue or dataset.empty:
        return dataset
    return dataset[dataset['Measure Name'].str.contains(health_issue, case=False, na=False)]
def get_location_relevance(hospital: pd.Series, search_location: str) -> str:
    """Determine hospital location relevance"""
    try:
        if ',' in search_location:
            search_city, search_state = [x.strip() for x in search_location.split(',', 1)]
        else:
            search_city = search_location.strip()
            search_state = ''
        
        hospital_city = str(hospital['City']).strip().upper()
        hospital_state = str(hospital['State']).strip().upper()
        search_city = search_city.upper()
        search_state = search_state.upper()
        
        if hospital_city == search_city:
            return 'city'
        elif hospital_state == search_state:
            return 'state'
        return 'other'
    except Exception as e:
        print(f"Error in location relevance: {str(e)}")
        return 'other'

def create_hospital_dict(hospital: pd.Series, relevance: str) -> dict:
    """Create hospital dictionary"""
    return {
        'id': str(hospital['Provider ID']),
        'name': str(hospital['Hospital Name']),
        'address': str(hospital['Address']),
        'city': str(hospital['City']),
        'state': str(hospital['State']),
        'zipCode': str(hospital['ZIP Code']),
        'county': str(hospital['County']),
        'score': float(hospital['Score']) if hospital['Score'] != 'Not Available' else 25.0,
        'hasData': hospital['Score'] != 'Not Available',
        'locationRelevance': relevance
    }

@app.route('/api/hospitals/search', methods=['GET'])
def search_hospitals():
    try:
        location = request.args.get('location', '').strip()
        health_issue = request.args.get('healthIssue', '').strip()
        
        print(f"Search request - Location: {location}, Issue: {health_issue}")

        if not location:
            return jsonify({"error": "Location is required"}), 400

        filtered_df = filter_hospitals(health_issue)
        results = []

        for _, hospital in filtered_df.iterrows():
            try:
                relevance = get_location_relevance(hospital, location)
                hospital_dict = create_hospital_dict(hospital, relevance)
                results.append(hospital_dict)
            except Exception as e:
                print(f"Error processing hospital: {str(e)}")
                continue

        return jsonify({
            'hospitals': results,
            'metadata': {
                'total': len(results)
            }
        })

    except Exception as e:
        print(f"Server Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)