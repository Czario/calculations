# Quick Reference Guide

## Command Cheat Sheet

### Q4 Calculation

```bash
# All companies
python app.py
python app.py q4

# Single company
python app.py --cik 0000789019
python app.py q4 --cik 0000789019

# Recalculate (delete + recalculate)
python app.py --recalculate
python app.py --cik 0000789019 --recalculate

# Verbose output
python app.py --verbose
```

### Cash Flow Fix (fix-cashflow)

```bash
# All companies
python app.py fix-cashflow

# Single company
python app.py fix-cashflow --cik 0001326801

# Verbose output
python app.py fix-cashflow --verbose

# Test before running
cd scripts/debug
python test_cashflow_fix.py
python test_cashflow_fix.py --cik 0000789019
```

## Common Company CIKs

| Company | CIK |
|---------|-----|
| Meta Platforms (Facebook) | 0001326801 |
| Microsoft | 0000789019 |
| Apple | 0000320193 |
| Amazon | 0001018724 |
| Alphabet (Google) | 0001652044 |

## Formulas

### Q4 Calculation
```
Q4 = Annual - (Q1 + Q2 + Q3)
```

**Required:** All 4 values must exist (Annual, Q1, Q2, Q3)

### Cash Flow Fix
```
Q2_quarterly = Q2_cumulative - Q1
Q3_quarterly = Q3_cumulative - Q2_cumulative
```

**Required:** 
- For Q2: Q1 must exist
- For Q3: Q2 (original cumulative) must exist

## Typical Workflow

### First Time Setup
```bash
# 1. Install dependencies
pip install -e .

# 2. Configure environment
cp .env.example .env
# Edit .env with your MongoDB details

# 3. Verify connection
python -c "from config.database import DatabaseConfig, DatabaseConnection; \
           config = DatabaseConfig(); \
           with DatabaseConnection(config) as db: \
               print('✅ Connected:', db.name)"
```

### Processing Cash Flow Data
```bash
# 1. Fix cumulative values
python app.py fix-cashflow

# 2. Calculate Q4
python app.py q4
```

### Processing Income Statement Data
```bash
# Calculate Q4 directly (no fix needed)
python app.py q4
```

## Verification

### Check Q4 Calculations

```bash
cd scripts/debug
python 05_check_calculation_status.py
```

### Test Cash Flow Fix

```bash
cd scripts/debug
python test_cashflow_fix.py --cik 0001326801
```

## Troubleshooting

### Common Issues

**Issue:** `No fiscal years found`
- **Solution:** Check if annual data exists in `concept_values_annual`

**Issue:** `Missing values: Q1, Q2, Q3, Annual`
- **Solution:** Normal - some concepts don't have all quarterly data

**Issue:** `Q4 value already exists`
- **Solution:** Use `--recalculate` to delete and recalculate

**Issue:** Cash flow fix shows high skip rate
- **Solution:** Normal if some concepts only appear in certain quarters

### Get Help

```bash
python app.py --help
```

## Database Collections

| Collection | Description |
|------------|-------------|
| `normalized_concepts_quarterly` | Quarterly concepts metadata |
| `normalized_concepts_annual` | Annual concepts metadata |
| `concept_values_quarterly` | Quarterly values (Q1-Q4) |
| `concept_values_annual` | Annual values (10-K) |

## Important Fields

### concept_values_quarterly

```javascript
{
  "concept_id": ObjectId,
  "company_cik": String,
  "statement_type": "income_statement" | "cash_flows" | ...,
  "form_type": "10-Q" | "10-K",
  "reporting_period": {
    "quarter": 1 | 2 | 3 | 4,
    "fiscal_year": Number,
    // ... other fields
  },
  "value": Number,
  "calculated": Boolean,  // true for Q4
  "dimension_value": Boolean
}
```

## Environment Variables

Create `.env` file:

```bash
MONGODB_URI=mongodb://localhost:27017
TARGET_DB_NAME=normalize_data
```

## Exit Codes

- `0` - Success
- `1` - Error occurred (check output for details)
