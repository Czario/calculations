# Cash Flow Fix Service - Data Flow Documentation

## Purpose

The **CashFlowFixService** corrects cumulative cash flow values in Q2 and Q3 quarters by converting them from year-to-date cumulative values to actual quarterly values.

### Problem It Solves
Many companies report cash flow values cumulatively in their 10-Q filings:
- **Q2 value** represents the cumulative total for the **first 6 months** (Q1 + Q2)
- **Q3 value** represents the cumulative total for the **first 9 months** (Q1 + Q2 + Q3)

This service converts these cumulative values to true quarterly values to enable accurate quarter-over-quarter analysis.

## Incremental Processing (New!)

The service now supports **incremental processing** to avoid re-fixing already-fixed records:

### How It Works
1. Records are marked with `cashflow_fixed: true` after being fixed
2. The `original_cumulative_value` is stored for audit/rollback purposes
3. Subsequent runs automatically skip records with `cashflow_fixed: true`
4. Use `--force` flag to re-fix all records (ignores the flag)

### New Fields Added to Records
```json
{
  "cashflow_fixed": true,              // Boolean flag indicating record was fixed
  "cashflow_fixed_at": ISODate(...),   // Timestamp when fix was applied
  "original_cumulative_value": 250000000  // Original cumulative value (for audit)
}
```

### Benefits
- **Safe for incremental runs**: New quarters are processed without affecting existing data
- **Audit trail**: Original values are preserved for verification
- **Force mode available**: Use `--force` when you need to re-fix all records

## Data Flow

### Collections Used

1. **concept_values_quarterly** (Read & Update)
   - Source and target collection for cash flow values
   - Filters: `statement_type: "cash_flows"`, `form_type: "10-Q"`
   - Updates Q2 and Q3 values in place

2. **normalized_concepts_quarterly** (Read Only)
   - Used to retrieve concept names for logging purposes
   - Provides concept metadata

### Flow Diagram

```
concept_values_quarterly (Cash Flows, Q1-Q3)
           ↓
    Group by concept_id
           ↓
    Create lookups for Q1, Q2, Q3 values
           ↓
    Calculate actual values:
    • Q2_actual = Q2_cumulative - Q1
    • Q3_actual = Q3_cumulative - Q2_cumulative (original)
           ↓
    Update concept_values_quarterly
    (Q2 and Q3 records updated in place)
```

## Calculation Logic

### Step 1: Retrieve Quarterly Values
For each fiscal year of a company, retrieve all cash flow concept values for Q1, Q2, and Q3:

```python
query = {
    "company_cik": company_cik,
    "statement_type": "cash_flows",
    "reporting_period.fiscal_year": fiscal_year,
    "reporting_period.quarter": quarter,  # 1, 2, or 3
    "form_type": "10-Q"
}
```

### Step 2: Create Lookup Dictionaries
Organize values by `concept_id` to enable matching across quarters:

```python
q1_lookup = {str(value["concept_id"]): value for value in q1_values}
q2_lookup = {str(value["concept_id"]): value for value in q2_values}
q3_lookup = {str(value["concept_id"]): value for value in q3_values}
```

### Step 3: Fix Q2 Values
For each Q2 concept with a matching Q1 value:

**Formula:** `Q2_actual = Q2_cumulative - Q1`

**Example:**
- Q1 Operating Cash Flow: $100M
- Q2 Cumulative (6-month): $250M
- **Q2_actual = $250M - $100M = $150M**

```python
q2_actual = q2_value["value"] - q1_value["value"]

concept_values_quarterly.update_one(
    {"_id": q2_value["_id"]},
    {"$set": {"value": q2_actual}}
)
```

### Step 4: Fix Q3 Values
For each Q3 concept with a matching Q2 value:

**Formula:** `Q3_actual = Q3_cumulative - Q2_cumulative (original)`

**Important:** Use the **original Q2 cumulative** value (before fixing), not the updated Q2 value.

**Example:**
- Q2 Cumulative (6-month): $250M
- Q3 Cumulative (9-month): $380M
- **Q3_actual = $380M - $250M = $130M**

```python
q3_actual = q3_value["value"] - q2_value["value"]  # Original Q2 cumulative

concept_values_quarterly.update_one(
    {"_id": q3_value["_id"]},
    {"$set": {"value": q3_actual}}
)
```

## Method Overview

### Main Entry Points

#### `fix_cumulative_values_for_company(company_cik, target_quarter=None)`
Fixes cumulative values for all fiscal years of a specific company.

**Parameters:**
- `company_cik` (str): Company identifier
- `target_quarter` (int, optional): Specific quarter to fix (2 or 3). If None, fixes both Q2 and Q3.

**Returns:**
```python
{
    "company_cik": str,
    "fiscal_years_processed": int,
    "q2_fixed": int,           # Total Q2 values corrected
    "q3_fixed": int,           # Total Q3 values corrected
    "q2_skipped": int,         # Q2 values skipped (missing Q1)
    "q3_skipped": int,         # Q3 values skipped (missing Q2)
    "errors": List[str]
}
```

#### `fix_all_companies()`
Processes all companies with cash flow data in the database.

**Returns:**
```python
{
    "total_companies": int,
    "companies_processed": int,
    "total_q2_fixed": int,
    "total_q3_fixed": int,
    "total_q2_skipped": int,
    "total_q3_skipped": int,
    "company_results": List[Dict],
    "errors": List[str]
}
```

### Helper Methods

#### `_fix_fiscal_year(company_cik, fiscal_year, target_quarter=None)`
Fixes cumulative values for a single fiscal year.

**Core Logic:**
1. Retrieve all Q1, Q2, and Q3 cash flow values
2. Create lookup dictionaries by concept_id
3. Fix Q2 values using Q1 (if target_quarter is None or 2)
4. Fix Q3 values using original Q2 cumulative (if target_quarter is None or 3)
5. Update records in database

#### `_get_quarterly_values(company_cik, fiscal_year, quarter)`
Retrieves all cash flow concept values for a specific quarter.

#### `_get_concept_name(concept_id)`
Retrieves the concept name from `normalized_concepts_quarterly` for logging.

#### `_get_all_cashflow_companies()`
Returns list of all companies with cash flow data using aggregation pipeline.

## Edge Cases and Considerations

### Missing Values
- **Q2 without Q1:** Q2 value is skipped (cannot calculate Q2_actual)
- **Q3 without Q2:** Q3 value is skipped (cannot calculate Q3_actual)

### Q1 and Q4 Values
- **Q1:** Already represents actual quarterly value (no fix needed)
- **Q4:** Calculated separately by Q4CalculationService using formula: `Q4 = Annual - (Q1 + Q2 + Q3)`

### Idempotency
The service now supports true incremental processing:
- Records are marked with `cashflow_fixed: true` after fixing
- Subsequent runs automatically skip already-fixed records
- Use `force=True` to re-fix all records regardless of status
- **Best Practice:** Run this service BEFORE Q4CalculationService to ensure Q1-Q3 values are correct

### Data Integrity
- All updates are done within database transactions
- Original cumulative values are preserved in `original_cumulative_value` field
- Errors are logged without stopping the entire process
- Verbose mode provides detailed logging of each fix

## Usage Examples

### Command Line Usage

```bash
# Incremental processing (default) - only fixes new records
uv run app.py --fix-cashflow --all-companies

# Fix specific company (incremental)
uv run app.py --fix-cashflow --cik 0001018724

# Force re-fix ALL records (ignores cashflow_fixed flag)
uv run app.py --fix-cashflow --all-companies --force

# Fix specific company with force mode
uv run app.py --fix-cashflow --cik 0001018724 --force

# Fix specific fiscal year
uv run app.py --fix-cashflow --cik 0001018724 --fiscal-year 2025

# Fix specific quarter
uv run app.py --fix-cashflow --cik 0001018724 --quarter 2
```

### Python API Usage

#### Fix Single Company (Incremental)
```python
from services.cashflow_fix_service import CashFlowFixService

service = CashFlowFixService(repository, verbose=True)
result = service.fix_cumulative_values_for_company("0001018724")  # Netflix

print(f"Q2 values fixed: {result['q2_fixed']}")
print(f"Q3 values fixed: {result['q3_fixed']}")
print(f"Q2 already fixed (skipped): {result['q2_already_fixed']}")
print(f"Q3 already fixed (skipped): {result['q3_already_fixed']}")
```

#### Force Re-Fix (Python API)
```python
# Force mode - re-fix all records regardless of cashflow_fixed flag
service = CashFlowFixService(repository, verbose=True, force=True)
result = service.fix_cumulative_values_for_company("0001018724")
```

### Fix Specific Quarter
```python
# Fix only Q2 values
result = service.fix_cumulative_values_for_company("0001018724", quarter=2)

# Fix only Q3 values
result = service.fix_cumulative_values_for_company("0001018724", quarter=3)
```

### Fix All Companies
```python
results = service.fix_all_companies()
print(f"Total companies processed: {results['companies_processed']}")
print(f"Total Q2 fixed: {results['total_q2_fixed']}")
print(f"Total Q3 fixed: {results['total_q3_fixed']}")
```

## Relationship with Other Services

### Prerequisites
- Data must exist in `concept_values_quarterly` for cash flows (Q1, Q2, Q3)
- No dependencies on other calculation services

### Dependent Services
- **Q4CalculationService:** Should run AFTER CashFlowFixService to use corrected Q1-Q3 values for accurate Q4 calculation

### Service Order
```
1. CashFlowFixService (fix Q2/Q3 cumulative values)
2. Q4CalculationService (calculate Q4 using corrected Q1-Q3)
3. GrossProfitService (calculate derived metrics)
```

## Performance Considerations

- Processes all fiscal years for a company in a single call
- Uses bulk lookups and dictionary-based matching for efficiency
- Updates are done individually per concept per quarter
- For large datasets, consider processing companies in batches

## Verbose Mode Output

When `verbose=True`, the service outputs detailed progress:

```
Processing fiscal year 2023...
    ✓ Fixed Q2 for NetCashProvidedByUsedInOperatingActivities: 5,500,000.00 → 2,800,000.00 (Q2 - Q1)
    ✓ Fixed Q3 for NetCashProvidedByUsedInOperatingActivities: 8,200,000.00 → 2,700,000.00 (Q3 - Q2)
    ⏭️  Skipped Q2 for ConceptWithoutQ1: No Q1 value found
```

## Database Updates

### Before Fix
```json
{
  "_id": ObjectId("..."),
  "concept_id": ObjectId("..."),
  "company_cik": "0001018724",
  "reporting_period": {"fiscal_year": 2023, "quarter": 2},
  "value": 250000000,  // Cumulative 6-month value
  "statement_type": "cash_flows"
}
```

### After Fix (with incremental fields)
```json
{
  "_id": ObjectId("..."),
  "concept_id": ObjectId("..."),
  "company_cik": "0001018724",
  "reporting_period": {"fiscal_year": 2023, "quarter": 2},
  "value": 150000000,  // Actual Q2 value (250M - 100M)
  "statement_type": "cash_flows",
  "cashflow_fixed": true,
  "cashflow_fixed_at": ISODate("2026-03-04T10:30:00Z"),
  "original_cumulative_value": 250000000
}
```

## Migration Script

If you have existing data that was already fixed before the incremental feature was added, use the migration script to mark those records:

```bash
# Preview what will be updated (dry run - default)
uv run scripts/migrate_cashflow_fixed.py --dry-run

# Preview with per-company breakdown
uv run scripts/migrate_cashflow_fixed.py --dry-run --verbose

# Actually mark records as fixed
uv run scripts/migrate_cashflow_fixed.py --execute

# Migrate specific company only
uv run scripts/migrate_cashflow_fixed.py --cik 0001326801 --execute
```

The migration script adds:
- `cashflow_fixed: true`
- `cashflow_fixed_at: <timestamp>`
- `cashflow_fixed_by: "migration_script"`

**Note:** Run the migration script **before** using the incremental cashflow fix to avoid re-fixing already fixed data.

## Summary

The CashFlowFixService is a critical preprocessing step that ensures cash flow values represent true quarterly figures rather than cumulative year-to-date values. This enables accurate quarter-over-quarter analysis and correct Q4 calculations. 

**Key features:**
- **Incremental processing**: Only processes new/unfixed records by default
- **Force mode**: Use `--force` to re-fix all records when needed
- **Audit trail**: Stores original cumulative values for verification
- **Migration support**: Script available for marking existing fixed data

It should always be run before Q4CalculationService for cash flow statements.
