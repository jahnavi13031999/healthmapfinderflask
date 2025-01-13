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
from fuzzywuzzy import process
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


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
        # Parse city and state from location string (format: "CITY, STATE")
        city, state = [part.strip() for part in location.split(',', 1)]
        
        # Filter hospitals by city and state
        matching_hospitals = dataset[
            (dataset['City'].str.upper() == city.upper()) & 
            (dataset['State'].str.upper() == state.upper())
        ]

        if matching_hospitals.empty:
            return jsonify([]), 200

        # Sort hospitals by Score (assuming higher is better)
        matching_hospitals = matching_hospitals.sort_values('Score', ascending=False)

        # Prepare results
        results = []
        for _, hospital in matching_hospitals.iterrows():
            results.append({
                "id": str(hospital.get("Provider ID", "")),
                "name": str(hospital.get("Hospital Name", "")),
                "address": str(hospital.get("Address", "")),
                "city": str(hospital.get("City", "")),
                "state": str(hospital.get("State", "")),
                "zipCode": str(hospital.get("ZIP Code", "")),
                "county": str(hospital.get("County", "")),
                "score": float(hospital.get("Score", 0)),
                "distance": None,  # To be implemented with geolocation
                "specialties": [],  # To be implemented with additional data
                "ratings": {
                    "overall": float(hospital.get("Score", 0)) / 20,  # Convert score to 0-5 scale
                    "quality": None,  # To be implemented with additional data
                    "safety": None   # To be implemented with additional data
                }
            })
        print(results)

        return jsonify(results), 200

    except Exception as e:
        print(f"Error processing hospital search request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


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
        print(results)
        return jsonify(results.tolist()), 200

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500





if __name__ == '__main__':
    app.run(debug=True)