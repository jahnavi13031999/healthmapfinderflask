# HealthMap Finder

HealthMap Finder is a comprehensive web application designed to assist users in locating healthcare facilities based on their geographical location and specific health conditions. The application offers personalized hospital recommendations and detailed insights into each facility's performance metrics.

## Features

- **Location-Based Search**: Find hospitals near you by entering your location or using geolocation services.
- **Condition-Specific Search**: Search for hospitals that specialize in treating specific health conditions.
- **Detailed Hospital Information**: Access performance ratings, statistics, and other relevant details for each hospital.
- **User-Friendly Interface**: Enjoy a responsive and intuitive UI designed for ease of use.

## Technologies Used

- **Frontend**: React, TypeScript, Tailwind CSS
- **Backend**: Flask, Pandas, Geopy
- **Database**: CSV file for hospital data
- **APIs**: Custom API endpoints for searching locations and conditions

## Prerequisites

- **Frontend**: Node.js and npm
- **Backend**: Python 3.x, Flask, Pandas, Geopy

## Setup Instructions

### Frontend

1. **Navigate to the Frontend Directory**:
   ```bash
   cd healthmap-finder
   ```

2. **Install Dependencies**:
   ```bash
   npm install
   ```

3. **Start the Development Server**:
   ```bash
   npm run dev
   ```

### Backend

1. **Navigate to the Backend Directory**:
   ```bash
   cd healthmapfinderflask
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the Virtual Environment**:

   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install Required Python Packages**:
   ```bash
   pip install -r req.txt
   ```

5. **Run the Flask Application**:
   ```bash
   python app.py
   ```

## Usage

- **Access the Application**: Open your browser and navigate to `http://localhost:5173`.
- **Search for Hospitals**: Use the search form to input your location and health condition.
- **View Results**: Browse through the list of recommended hospitals and explore detailed information about each facility.

## API Endpoints

- **GET /api/locations/search**: Retrieve a list of locations based on a search query.
- **GET /api/hospitals/search**: Find hospitals based on location and health conditions.
- **GET /api/conditions/search**: Search for health conditions.

## Contributing

We welcome contributions! If you have suggestions or improvements, please fork the repository and submit a pull request. Ensure your code adheres to the project's coding standards and includes relevant tests.

## License

This project is licensed under the MIT License. For more details, see the [LICENSE](LICENSE) file.

## Contact

For questions or feedback, please contact the project maintainer at [Your Email].

