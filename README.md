# HealthMap Finder

HealthMap Finder is a web application designed to help users find healthcare facilities based on their location and specific health conditions. The application provides personalized hospital recommendations and detailed information about each facility.

## Features

- Search for hospitals based on location and health conditions.
- View detailed hospital information, including performance ratings and statistics.
- Use geolocation to find nearby healthcare facilities.
- Responsive UI with a user-friendly interface.

## Technologies Used

- **Frontend**: React, TypeScript, Tailwind CSS
- **Backend**: Flask, Pandas, Geopy
- **Database**: CSV file for hospital data
- **APIs**: Custom API endpoints for searching locations and conditions

## Prerequisites

- Node.js and npm
- Python 3.x
- Flask
- Pandas
- Geopy

## Setup Instructions

### Frontend

1. Navigate to the `healthmap-finder` directory:
   ```bash
   cd healthmap-finder
   ```

2. Install the dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

### Backend

1. Navigate to the `healthmapfinderflask` directory:
   ```bash
   cd healthmapfinderflask
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:

   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. Install the required Python packages:
   ```bash
   pip install -r req.txt
   ```

5. Run the Flask application:
   ```bash
   python app.py
   ```

## Usage

- Access the frontend application at `http://localhost:5173`.
- Use the search form to enter your location and health condition.
- View the list of recommended hospitals and their details.

## API Endpoints

- **GET /api/locations/search**: Search for locations based on a query.
- **GET /api/hospitals/search**: Search for hospitals based on location and health conditions.
- **GET /api/conditions/search**: Search for health conditions.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

