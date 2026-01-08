# Q4 Calculation Service - Data Flow Documentation

## Purpose

The **Q4CalculationService** calculates missing Q4 (fourth quarter) values for financial statement concepts by either:
1. **Subtracting cumulative quarterly values from annual values** for flow concepts (income statement, cash flows)
2. **Copying the annual value** for point-in-time concepts (balance sheet items)

This service enables complete quarterly analysis by filling in the Q4 gap that exists because most companies file annual 10-K reports instead of Q4 10-Q reports.

## Data Flow

### Collections Used

1. **normalized_concepts_quarterly** (Read Only)
   - Contains all quarterly concept definitions
   - Filtered by: `company_cik`, `statement_type`
   - Provides: `concept`, `path`, `label`, `statement_type`

2. **normalized_concepts_annual** (Read Only)
   - Used for matching dimensional concepts
   - Enables fallback lookup when quarterly/annual concept names differ

3. **concept_values_quarterly** (Read & Write)
   - **Read:** Q1, Q2, Q3 values for calculation
   - **Write:** Inserts calculated Q4 values

4. **concept_values_annual** (Read Only)
   - Provides annual values for Q4 calculation
   - Provides annual filing metadata (accession number, dates, etc.)

### Flow Diagram

```
normalized_concepts_quarterly (by company + statement_type)
           ↓
    For each concept + fiscal year:
           ↓
    Retrieve Q1, Q2, Q3, Annual values
    (from concept_values_quarterly & concept_values_annual)
           ↓
    Check if Q4 already exists
           ↓
    Determine if point-in-time concept
           ↓
    ┌─────────────────────────────┐
    │  Point-in-Time Concept?     │
    └─────────────────────────────┘
         YES │           │ NO
             ↓           ↓
    Q4 = Annual    Q4 = Annual - (Q1 + Q2 + Q3)
             │           │
             └─────┬─────┘
                   ↓
    Create Q4 reporting period metadata
           ↓
    Insert into concept_values_quarterly
```

## Concept Types

### Flow Concepts (Calculated)
Represent **activity over a period** (cumulative):
- **Income Statement:** Revenue, Expenses, Net Income
- **Cash Flows:** Operating Cash Flow, Investing Cash Flow, Financing Cash Flow

**Formula:** `Q4 = Annual - (Q1 + Q2 + Q3)`

**Example:**
- Annual Revenue: $1,000M
- Q1: $220M, Q2: $250M, Q3: $270M
- **Q4 = $1,000M - ($220M + $250M + $270M) = $260M**

### Point-in-Time Concepts (Copied)
Represent **snapshots at specific dates** (not cumulative):
- **Balance Sheet Items:** Cash, Assets, Liabilities, Equity
- **Shares Outstanding:** WeightedAverageNumberOfShares
- **Exchange Rate Effects:** EffectOfExchangeRate
- **Period Markers:** EndOfYear, BeginningOfYear

**Formula:** `Q4 = Annual` (copy value)

**Example:**
- Annual Cash Balance (Dec 31): $500M
- **Q4 Cash Balance (Dec 31) = $500M** (same date, same value)

## Point-in-Time Pattern Detection

The service identifies point-in-time concepts using pattern matching:

### Balance Sheet Patterns
- `CashAndCashEquivalents`
- `CashCashEquivalents`
- `RestrictedCash`
- `CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents`

### Period Markers
- `EndOfYear`, `EndOfPeriod`, `EndOfTheYear`, `EndOfThePeriod`
- `BeginningOfYear`, `BeginningOfPeriod`, `BeginningOfTheYear`, `BeginningOfThePeriod`
- `AtEndOf`, `AtBeginningOf`

### Shares Outstanding
- `SharesOutstanding`
- `CommonStockSharesOutstanding`
- `StockSharesOutstanding`
- `WeightedAverageNumberOfShares`
- `WeightedAverageNumberOfDilutedShares`

### Reconciliation Items
- `PeriodIncreaseDecrease`
- `EffectOfExchangeRate`, `EffectOfExchange`
- `EndingBalance`, `BeginningBalance`
- `ClosingBalance`, `OpeningBalance`

**Pattern Matching:** Case-insensitive search in both `concept` name and `label`.

## Calculation Logic

### Step 1: Get All Concepts for Statement Type
Retrieve all normalized concepts for the company and statement type:

```python
concepts = repository.get_income_statement_concepts(company_cik)
# or
concepts = repository.get_cash_flow_concepts(company_cik)
```

Each concept contains:
```python
{
    "_id": ObjectId("..."),
    "concept": "Revenues",
    "path": "us-gaap:Revenues",
    "label": "Total Revenues",
    "statement_type": "income_statement",
    "company_cik": "0001018724"
}
```

### Step 2: Get All Fiscal Years
```python
fiscal_years = repository.get_fiscal_years_for_company(company_cik)
# Returns: [2020, 2021, 2022, 2023, 2024]
```

### Step 3: For Each Concept + Fiscal Year Combination

#### 3a. Retrieve Quarterly Data
Query concept_values_quarterly for Q1, Q2, Q3:

```python
quarterly_data = repository.get_quarterly_data_by_concept_id(
    concept_id, company_cik, fiscal_year, statement_type
)
```

Returns:
```python
QuarterlyData(
    concept_id=ObjectId("..."),
    q1_value=220_000_000,
    q2_value=250_000_000,
    q3_value=270_000_000,
    annual_value=1_000_000_000
)
```

#### 3b. Check if Q4 Already Exists
```python
if repository.check_q4_exists(concept_id, company_cik, fiscal_year):
    # Skip - Q4 already calculated
```

#### 3c. Determine if Point-in-Time
```python
is_point_in_time = _is_point_in_time_concept(concept_name, label)
```

#### 3d. Calculate Q4 Value

**For Point-in-Time Concepts:**
```python
if is_point_in_time:
    q4_value = quarterly_data.annual_value  # Copy annual
```

**For Flow Concepts:**
```python
else:
    if not quarterly_data.can_calculate_q4():
        # Missing Q1, Q2, Q3, or Annual
        return error
    
    q4_value = quarterly_data.calculate_q4()
    # Q4 = Annual - (Q1 + Q2 + Q3)
```

### Step 4: Create Q4 Reporting Period Metadata

The Q4 record inherits metadata from the annual 10-K filing:

```python
ReportingPeriod(
    end_date=annual_period["end_date"],           # Same as annual
    period_date=annual_period["period_date"],     # Same as annual
    form_type="10-Q",                             # Changed to quarterly
    fiscal_year_end_code=annual_period["fiscal_year_end_code"],
    data_source="calculated_from_sec_api_raw",
    company_cik=company_cik,
    company_name=annual_period["company_name"],
    fiscal_year=fiscal_year,
    quarter=4,                                     # Q4
    accession_number=annual_period["accession_number"],
    period_type="quarterly",
    start_date=annual_period.get("start_date"),
    context_id=annual_period.get("context_id"),
    item_period=annual_period.get("item_period"),
    unit=annual_period.get("unit"),
    note="Q4 calculated from annual 10-K minus Q1-Q3"
)
```

### Step 5: Insert Q4 Value

```python
ConceptValue(
    concept_id=quarterly_concept_id,
    company_cik=company_cik,
    statement_type=statement_type,
    form_type="10-Q",
    reporting_period=q4_reporting_period,
    value=q4_value,                    # Calculated value
    created_at=datetime.utcnow(),
    dimension_value=False,
    calculated=True,                   # Flag as calculated
    dimensional_concept_id=None
)

repository.insert_q4_value(q4_record)
```

## Method Overview

### Main Entry Points

#### `calculate_q4_for_company(company_cik)`
Calculates Q4 for all **income statement** concepts of a company.

**Returns:**
```python
{
    "company_cik": str,
    "statement_type": "income_statement",
    "processed_concepts": int,
    "successful_calculations": int,
    "skipped_concepts": int,
    "errors": List[str]
}
```

#### `calculate_q4_for_cash_flow(company_cik)`
Calculates Q4 for all **cash flow** concepts of a company.

**Returns:** Same structure as above with `"statement_type": "cash_flows"`

### Core Methods

#### `_calculate_q4_generic(concept_name, concept_path, company_cik, fiscal_year, statement_type, quarterly_concept=None)`
Unified calculation method for all statement types.

**Process:**
1. Get quarterly data (Q1, Q2, Q3, Annual)
2. Check if Q4 already exists
3. Determine if point-in-time concept
4. Calculate Q4 value (subtract or copy)
5. Create Q4 record with metadata
6. Insert into database

**Returns:**
```python
{
    "success": bool,
    "reason": str or None,          # Error message if not successful
    "is_point_in_time": bool
}
```

#### `_calculate_q4_for_statement_type(company_cik, statement_type, get_concepts_method)`
Generic method to process all concepts for a statement type.

**Process:**
1. Get all concepts using `get_concepts_method`
2. Get all fiscal years for company
3. For each concept × fiscal year:
   - Call `_calculate_q4_generic`
   - Track success/skip/error counts

### Helper Methods

#### `_is_point_in_time_concept(concept_name, label)`
Pattern matching against `POINT_IN_TIME_PATTERNS` list.

#### `_get_missing_values_list(quarterly_data)`
Returns list of missing values (Q1, Q2, Q3, Annual) needed for calculation.

#### `_create_q4_reporting_period(annual_period, company_cik, fiscal_year)`
Constructs Q4 reporting period metadata from annual 10-K filing.

#### `_create_q4_concept_value(quarterly_concept_id, company_cik, fiscal_year, q4_value, annual_metadata)`
Creates complete ConceptValue object for Q4.

#### `_create_q4_record(concept_name, concept_path, quarterly_concept_id, company_cik, fiscal_year, q4_value, statement_type)`
Unified Q4 record creation with fallback for dimensional concepts.

## Edge Cases and Handling

### Missing Values
- **Missing Q1, Q2, or Q3:** Cannot calculate Q4, record is skipped
- **Missing Annual:** Cannot calculate Q4, record is skipped
- **Result:** Logged in `errors` list but does not stop processing

### Point-in-Time Concepts
- **No Annual Value:** Logged as error, cannot copy value
- **Result:** Skipped but marked as `is_point_in_time` (not counted as error)

### Dimensional Concepts
If annual and quarterly concepts have different names:
1. Try to find by `concept_name` and `concept_path`
2. Fallback: Look up parent concept from quarterly
3. Find matching annual concept by parent
4. Use annual concept metadata

### Q4 Already Exists
- **Check:** Before calculation, verify Q4 doesn't exist
- **Result:** Skip calculation, log as "Q4 value already exists"
- **Idempotency:** Safe to run multiple times

### Concept Not Found
- **Quarterly Concept Missing:** Cannot proceed, skip concept
- **Annual Filing Metadata Missing:** Cannot create Q4 record, skip

## Usage Examples

### Calculate Q4 for Income Statement
```python
from services.q4_calculation_service import Q4CalculationService

service = Q4CalculationService(repository, verbose=True)
result = service.calculate_q4_for_company("0001018724")  # Netflix

print(f"Processed: {result['processed_concepts']}")
print(f"Successful: {result['successful_calculations']}")
print(f"Skipped: {result['skipped_concepts']}")
```

### Calculate Q4 for Cash Flows
```python
result = service.calculate_q4_for_cash_flow("0001018724")

print(f"Statement Type: {result['statement_type']}")
if result['errors']:
    print("Errors:")
    for error in result['errors']:
        print(f"  - {error}")
```

### Process All Companies
```python
companies = repository.get_all_companies()

for company_cik in companies:
    print(f"\nProcessing {company_cik}...")
    
    # Income statement
    income_result = service.calculate_q4_for_company(company_cik)
    print(f"  Income Statement: {income_result['successful_calculations']} calculated")
    
    # Cash flows
    cash_result = service.calculate_q4_for_cash_flow(company_cik)
    print(f"  Cash Flows: {cash_result['successful_calculations']} calculated")
```

## Relationship with Other Services

### Prerequisites
- **CashFlowFixService:** Should run BEFORE Q4CalculationService for cash flows
  - Ensures Q2 and Q3 values are actual quarterly (not cumulative)
  - Provides accurate Q1-Q3 values for Q4 calculation

### Dependent Services
- **GrossProfitService:** Can run independently (uses normalized concepts flow)
- **Other Calculation Services:** Q4 values enable complete quarterly analysis

### Service Order
```
1. CashFlowFixService (fix Q2/Q3 cumulative values for cash flows)
2. Q4CalculationService (calculate Q4 for income statement and cash flows)
3. GrossProfitService or other derived calculations
```

## Verbose Mode Output

When `verbose=True`, detailed progress is shown:

```
✓ Calculated Q4 for Revenues (income_statement) (Path: us-gaap:Revenues) FY2023: 260,000,000.00
✓ Calculated Q4 for CostOfRevenue (income_statement) (Path: us-gaap:CostOfRevenue) FY2023: 140,000,000.00
⏭️  Skipped Q4 for CashAndCashEquivalents (Point-in-time concept copied: 500,000,000.00)
```

## Database Inserts

### Flow Concept (Calculated)
```json
{
  "_id": ObjectId("..."),
  "concept_id": ObjectId("..."),
  "company_cik": "0001018724",
  "statement_type": "income_statement",
  "form_type": "10-Q",
  "reporting_period": {
    "fiscal_year": 2023,
    "quarter": 4,
    "end_date": "2023-12-31",
    "period_date": "2023-12-31",
    "note": "Q4 calculated from annual 10-K minus Q1-Q3"
  },
  "value": 260000000,
  "calculated": true,
  "created_at": ISODate("2024-01-15T10:30:00Z")
}
```

### Point-in-Time Concept (Copied)
```json
{
  "_id": ObjectId("..."),
  "concept_id": ObjectId("..."),
  "company_cik": "0001018724",
  "statement_type": "balance_sheet",
  "form_type": "10-Q",
  "reporting_period": {
    "fiscal_year": 2023,
    "quarter": 4,
    "end_date": "2023-12-31",
    "period_date": "2023-12-31",
    "note": "Q4 calculated from annual 10-K minus Q1-Q3"
  },
  "value": 500000000,
  "calculated": true,
  "created_at": ISODate("2024-01-15T10:30:00Z")
}
```

## Performance Considerations

- Processes all concepts for all fiscal years in a single call
- Uses batch queries for quarterly values
- Individual inserts per Q4 value
- For large companies with many concepts/years, processing time can be significant
- Progress tracking via verbose mode

## Summary

The Q4CalculationService fills a critical gap in quarterly financial data by calculating missing Q4 values using a smart approach:
- **Flow concepts** are calculated by subtraction: `Q4 = Annual - (Q1 + Q2 + Q3)`
- **Point-in-time concepts** are copied from annual values

This enables complete quarterly trend analysis and ensures data consistency. The service should run after CashFlowFixService for cash flow statements to ensure accurate Q1-Q3 inputs.
