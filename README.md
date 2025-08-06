# Q4 Financial Calculations

This project calculates Quarter 4 (Q4) values for income statement concepts by using the formula:

```
Q4 = Annual Value - (Q1 + Q2 + Q3)
```

## Features

- Connects to MongoDB database containing normalized financial data
- Calculates Q4 values for income statement concepts
- Skips calculations when required values (Annual, Q1, Q2, Q3) are missing
- Follows clean code principles with modular architecture
- Comprehensive logging and error handling

## Project Structure

```
calculations/
├── app.py                      # Main application entry point
├── config/
│   └── database.py            # Database configuration and connection
├── models/
│   └── financial_data.py      # Data models and structures
├── repositories/
│   └── financial_repository.py # Data access layer
├── services/
│   └── q4_calculation_service.py # Business logic for Q4 calculations
├── pyproject.toml             # Project configuration and dependencies
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## Setup

1. **Install dependencies:**
   ```bash
   pip install -e .
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your MongoDB connection details
   ```

3. **Ensure MongoDB is running:**
   ```bash
   # If using Docker:
   docker run -d -p 27017:27017 --name mongodb mongo:latest
   ```

## Usage

### Calculate Q4 for all companies:
```bash
python app.py
```

### Calculate Q4 for a specific company:
```bash
python app.py 0000320193  # Apple Inc.
```

## Database Schema

The application works with the following MongoDB collections:

- `normalized_concepts_quarterly` - Income statement concepts metadata
- `concept_values_quarterly` - Quarterly financial values (Q1, Q2, Q3)
- `concept_values_annual` - Annual financial values from 10-K filings

## Business Logic

1. **Data Validation:** Only processes concepts where all required values (Annual, Q1, Q2, Q3) are available
2. **Duplicate Prevention:** Skips calculation if Q4 value already exists
3. **Error Handling:** Logs detailed information about missing data and errors
4. **Metadata Preservation:** Maintains original SEC filing metadata in calculated records

## Output

The application creates Q4 records in `concept_values_quarterly` collection with:
- `calculated: true` flag
- `data_source: "calculated_from_sec_api_raw"`
- Detailed audit trail in reporting period notes

## Logging

Comprehensive logging includes:
- Processing progress for companies and concepts
- Success/failure counts
- Detailed error messages for troubleshooting
- Summary statistics
