# Q4 Financial Calculations & Cash Flow Fix

This project provides two main functionalities:

1. **Q4 Calculation**: Calculates Quarter 4 (Q4) values for financial statements using the formula:
   ```
   Q4 = Annual Value - (Q1 + Q2 + Q3)
   ```

2. **Cash Flow Fix (fix-cashflow)**: Converts cumulative Q2/Q3 cash flow values to actual quarterly values:
   ```
   Q2_quarterly = Q2_cumulative - Q1
   Q3_quarterly = Q3_cumulative - Q2_cumulative
   ```

**⚠️ CRITICAL RULE:** Q4 is **NEVER** calculated if **ANY** of the required values (Annual, Q1, Q2, or Q3) are missing. This rule applies to **ALL DATA TYPES**:
- ✅ Regular income statement concepts
- ✅ Cash flow statement concepts
- ✅ Dimensional concepts (e.g., country:US, segment data)  
- ✅ Any other financial data

The system will **COMPLETELY SKIP** the calculation if even **ONE** value is unavailable, regardless of the data type or concept structure.

## Features

- Connects to MongoDB database containing normalized financial data
- **Q4 Calculation**: Calculates Q4 values for **income_statement** and **cash_flows** concepts
- **Cash Flow Fix**: Converts cumulative Q2/Q3 values to quarterly values for cash flow statements
- Preserves `accession_number` and other metadata from annual filings in Q4 records
- Skips calculations when required values (Annual, Q1, Q2, Q3) are missing
- Follows clean code principles with modular architecture (DRY - Don't Repeat Yourself)
- Comprehensive logging and error handling

## Project Structure

```
calculations/
├── app.py                      # Main application entry point
├── config/
│   ├── __init__.py
│   └── database.py             # Database configuration and connection
├── models/
│   ├── __init__.py
│   └── financial_data.py       # Data models and structures
├── repositories/
│   ├── __init__.py
│   └── financial_repository.py # Data access layer (refactored)
├── services/
│   ├── __init__.py
│   ├── q4_calculation_service.py     # Q4 calculation business logic
│   └── cashflow_fix_service.py       # Cash flow fix business logic
├── scripts/
│   └── debug/                  # Diagnostic and debugging utilities
│       ├── test_cashflow_fix.py      # Test script for cash flow fix
│       ├── CASHFLOW_FIX_DOCUMENTATION.md  # Detailed fix-cashflow docs
│       ├── 01_analyze_database.py
│       ├── 02_debug_filing_id.py
│       ├── 03_debug_annual_metadata.py
│       ├── 04_investigate_gaming_member.py
│       ├── 05_check_calculation_status.py
│       └── README.md
├── pyproject.toml              # Project configuration and dependencies
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## Recent Refactoring

The codebase has been significantly refactored to apply DRY (Don't Repeat Yourself) principles:
- **46% code reduction** (1635 → 880 lines)
- Eliminated duplicate methods across repository and service layers
- Single source of truth for all operations
- Backward compatible with all existing interfaces
- Improved maintainability and testability

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

### Q4 Calculation Mode

#### Show help:
```bash
python app.py --help
```

#### Calculate Q4 for a specific company:
```bash
python app.py --cik 0000789019  # Microsoft Corp.
python app.py --cik 0000320193  # Apple Inc.
python app.py q4 --cik 0000789019  # Explicit Q4 mode
```

#### Calculate Q4 for all companies:
```bash
python app.py
python app.py q4  # Explicit Q4 mode
```

#### Recalculate Q4 (delete existing and recalculate):
```bash
python app.py --recalculate  # All companies
python app.py --cik 0000789019 --recalculate  # Specific company
```

**Note:** The system processes both income statement and cash flow concepts for each company.

### Cash Flow Fix Mode (fix-cashflow)

#### Fix cumulative Q2/Q3 values for all companies:
```bash
python app.py fix-cashflow
```

#### Fix specific company:
```bash
python app.py fix-cashflow --cik 0001326801  # Meta Platforms
```

#### Verbose output:
```bash
python app.py fix-cashflow --verbose
```

#### Test the fix before running:
```bash
cd scripts/debug
python test_cashflow_fix.py  # Test Meta Platforms (default)
python test_cashflow_fix.py --cik 0000789019  # Test Microsoft
```

**📖 For detailed documentation on the cash flow fix process, see:** [`scripts/debug/CASHFLOW_FIX_DOCUMENTATION.md`](scripts/debug/CASHFLOW_FIX_DOCUMENTATION.md)

**⚠️ Important:** 
- Run `fix-cashflow` BEFORE calculating Q4 for cash flow statements
- Do NOT run `fix-cashflow` twice on the same data
- Backup your database before running on production data

### Recommended Workflow

For processing cash flow statements with cumulative values:

```bash
# Step 1: Fix cumulative Q2/Q3 values (convert to quarterly)
python app.py fix-cashflow

# Step 2: Calculate Q4 values using corrected quarterly values
python app.py q4
```

For processing income statements (no fix needed):

```bash
# Calculate Q4 directly
python app.py q4
```

## Database Schema

The application works with the following MongoDB collections:

- `normalized_concepts_quarterly` - Quarterly concepts metadata (income statement and cash flow)
- `normalized_concepts_annual` - Annual concepts metadata (income statement and cash flow)
- `concept_values_quarterly` - Quarterly financial values (Q1, Q2, Q3)
- `concept_values_annual` - Annual financial values from 10-K filings

### Q4 Record Structure

Q4 records match the structure of existing quarterly records with these key fields:
- `accession_number` - Preserved from the annual filing (required)
- `statement_type` - One of: `income_statement`, `cash_flows`, `balance_sheet`, `comprehensive_income`
- `dimension_value` - Boolean indicating if this is dimensional data
- `dimensional_concept_id` - Link to the dimensional concept if applicable
- `calculated` - Always `true` for Q4 records
- `data_source` - Set to `calculated_from_sec_api_raw`
- Additional metadata fields: `context_id`, `item_period`, `unit` (preserved from annual filing)

## Business Logic

1. **Universal Strict Validation:** Q4 calculations are **ONLY** performed when **ALL** required values (Annual, Q1, Q2, Q3) are available. If **ANY** value is missing, the calculation is **SKIPPED ENTIRELY** - this applies to **ALL DATA TYPES** including regular concepts, dimensional concepts, and any other financial data.
2. **Parent Concept Matching:** Uses parent concept relationships (not path-based matching) to ensure consistency between quarterly and annual filings.
3. **Duplicate Prevention:** Skips calculation if Q4 value already exists.
4. **Error Handling:** Logs detailed information about missing data and errors.
5. **Metadata Preservation:** Maintains original SEC filing metadata in calculated records.

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
