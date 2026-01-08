# Calculation Services - Overview & Documentation

This document provides an overview of all calculation services in the DataServices/calculations project. Each service performs specific financial data calculations and transformations to enable comprehensive financial analysis.

## Services Overview

| Service | Purpose | Input Collections | Output Collections | Order |
|---------|---------|-------------------|-------------------|-------|
| **CashFlowFixService** | Fix cumulative Q2/Q3 cash flow values | concept_values_quarterly | concept_values_quarterly (updates) | 1 |
| **Q4CalculationService** | Calculate missing Q4 values | concept_values_quarterly, concept_values_annual | concept_values_quarterly (inserts) | 2 |
| **GrossProfitService** | Calculate Gross Profit metrics | standardlabels → concepts_standard_mapping → us_gaap_taxonomy → normalized_concepts → concept_values | concept_values_quarterly, concept_values_annual (inserts) | 3 |

## Service Execution Order

For complete and accurate financial calculations, run services in this order:

```
1. CashFlowFixService
   ↓ (fixes cumulative Q2/Q3 values)
   
2. Q4CalculationService
   ↓ (calculates Q4 using corrected Q1-Q3)
   
3. GrossProfitService
   ↓ (calculates derived metrics)
   
[Other calculation services]
```

### Why This Order?

1. **CashFlowFixService first:** Corrects cumulative Q2/Q3 values to actual quarterly values
   - Without this, Q4CalculationService would use incorrect Q2/Q3 values
   
2. **Q4CalculationService second:** Fills missing Q4 gaps using corrected Q1-Q3
   - Provides complete quarterly data (Q1-Q4)
   
3. **GrossProfitService third (or later):** Calculates derived metrics
   - Independent of other services
   - Uses standard label lookup flow

## Detailed Documentation

### 1. CashFlow Fix Service
**File:** [cashflow-fix-flow.md](./cashflow-fix-flow.md)

**Purpose:** Corrects cumulative cash flow values in Q2 and Q3 quarters

**Problem Solved:**
- Companies report Q2 as 6-month cumulative (Q1+Q2)
- Companies report Q3 as 9-month cumulative (Q1+Q2+Q3)
- Service converts these to actual quarterly values

**Key Operations:**
- `Q2_actual = Q2_cumulative - Q1`
- `Q3_actual = Q3_cumulative - Q2_cumulative (original)`

**Collections:**
- **Read/Update:** concept_values_quarterly (cash_flows)

**Entry Points:**
```python
service.fix_cumulative_values_for_company(company_cik)
service.fix_all_companies()
```

---

### 2. Q4 Calculation Service
**File:** [q4-calculation-flow.md](./q4-calculation-flow.md)

**Purpose:** Calculates missing Q4 values for all financial statements

**Problem Solved:**
- Companies file annual 10-K instead of Q4 10-Q
- Q4 data is missing from quarterly filings
- Service calculates Q4 to enable complete quarterly analysis

**Key Operations:**
- **Flow Concepts:** `Q4 = Annual - (Q1 + Q2 + Q3)`
- **Point-in-Time Concepts:** `Q4 = Annual` (copy value)

**Collections:**
- **Read:** normalized_concepts_quarterly, normalized_concepts_annual, concept_values_quarterly, concept_values_annual
- **Write:** concept_values_quarterly (inserts Q4 records)

**Entry Points:**
```python
service.calculate_q4_for_company(company_cik)  # Income statement
service.calculate_q4_for_cash_flow(company_cik)  # Cash flows
```

**Point-in-Time Concepts:**
- Balance sheet items (Cash, Assets, Liabilities)
- Shares outstanding
- Exchange rate effects
- Period markers (EndOfYear, BeginningOfYear)

---

### 3. Gross Profit Service
**File:** [gross-profit-cal-flow.md](./gross-profit-cal-flow.md)

**Purpose:** Calculates Gross Profit using standard label lookup flow

**Formula:** `Gross Profit = Total Revenues - Cost of Revenues`

**Key Features:**
- Looks up concepts through 5-collection standard flow
- Handles BOTH quarterly and annual calculations independently
- Tries ALL possible concept mappings for each company
- Calculates for all fiscal years automatically

**Collections (5-Step Flow):**
1. **standardlabels** - Find standard labels for "Total Revenues" and "Cost of Revenues"
2. **concepts_standard_mapping** - Get all possible concept_ids for each label
3. **us_gaap_taxonomy** - Verify concepts exist in GAAP taxonomy
4. **normalized_concepts_quarterly/annual** - Find company-specific concepts
5. **concept_values_quarterly/annual** - Retrieve/insert values

**Entry Points:**
```python
service.calculate_gross_profit_for_company(company_cik)
```

**Standard Label Lookup:**
- Primary Label: "Total Revenues"
- Alternative Labels: ["Total Revenues", "Revenues", "Revenue", "Total Revenue", "Sales"]
- Cost of Revenue Labels: ["Cost of Revenues", "Cost of Revenue", "Cost of Sales", "Cost of Goods Sold"]

---

## Common Patterns

### Repository Pattern
All services use `FinancialDataRepository` for database access:
```python
from repositories.financial_repository import FinancialDataRepository
from services.cashflow_fix_service import CashFlowFixService

repository = FinancialDataRepository(db)
service = CashFlowFixService(repository, verbose=True)
```

### Verbose Mode
All services support verbose logging:
```python
service = Q4CalculationService(repository, verbose=True)
# Outputs detailed progress and calculations
```

### Result Format
All services return structured result dictionaries:
```python
{
    "company_cik": str,
    "processed_concepts": int,
    "successful_calculations": int,
    "skipped_concepts": int,
    "errors": List[str]
}
```

### Error Handling
- Errors are logged but don't stop processing
- Missing values result in skipped calculations (logged)
- Database errors are caught and reported in results

## MongoDB Collections

### Core Data Collections

#### normalized_concepts_quarterly
Contains quarterly concept definitions for each company
```javascript
{
  "_id": ObjectId("..."),
  "concept": "Revenues",
  "path": "us-gaap:Revenues",
  "label": "Total Revenues",
  "statement_type": "income_statement",
  "company_cik": "0001018724",
  "parent_concept_id": ObjectId("...")
}
```

#### normalized_concepts_annual
Contains annual concept definitions for each company (structure similar to quarterly)

#### concept_values_quarterly
Contains actual quarterly values (Q1, Q2, Q3, Q4)
```javascript
{
  "_id": ObjectId("..."),
  "concept_id": ObjectId("..."),
  "company_cik": "0001018724",
  "statement_type": "income_statement",
  "form_type": "10-Q",
  "reporting_period": {
    "fiscal_year": 2023,
    "quarter": 2,
    "end_date": "2023-06-30",
    "period_date": "2023-06-30"
  },
  "value": 250000000,
  "calculated": false
}
```

#### concept_values_annual
Contains annual values from 10-K filings (structure similar to quarterly)

### Standard Label Lookup Collections

#### standardlabels
Maps standard financial terms to normalized labels
```javascript
{
  "_id": ObjectId("..."),
  "label": "Total Revenues",
  "normalized_label": "Revenue",
  "category": "income_statement"
}
```

#### concepts_standard_mapping
Maps standard labels to US GAAP concepts
```javascript
{
  "_id": ObjectId("..."),
  "normalized_label": "Revenue",
  "concept_ids": ["us-gaap:Revenues", "us-gaap:SalesRevenueNet", ...]
}
```

#### us_gaap_taxonomy
Contains official US GAAP taxonomy definitions
```javascript
{
  "_id": ObjectId("..."),
  "concept": "Revenues",
  "path": "us-gaap:Revenues",
  "label": "Revenue from Contract with Customer, Excluding Assessed Tax",
  "statement_type": "income_statement"
}
```

## Usage Examples

### Complete Company Processing
```python
from config.database import get_database
from repositories.financial_repository import FinancialDataRepository
from services.cashflow_fix_service import CashFlowFixService
from services.q4_calculation_service import Q4CalculationService
from services.gross_profit_service import GrossProfitService

# Setup
db = get_database()
repository = FinancialDataRepository(db)

company_cik = "0001018724"  # Netflix

# Step 1: Fix cumulative cash flows
cashflow_service = CashFlowFixService(repository, verbose=True)
cf_result = cashflow_service.fix_cumulative_values_for_company(company_cik)
print(f"Cash Flow Fix: Q2={cf_result['q2_fixed']}, Q3={cf_result['q3_fixed']}")

# Step 2: Calculate Q4 values
q4_service = Q4CalculationService(repository, verbose=True)
income_result = q4_service.calculate_q4_for_company(company_cik)
cash_result = q4_service.calculate_q4_for_cash_flow(company_cik)
print(f"Q4 Calculated: Income={income_result['successful_calculations']}, Cash={cash_result['successful_calculations']}")

# Step 3: Calculate Gross Profit
gp_service = GrossProfitService(repository, verbose=True)
gp_result = gp_service.calculate_gross_profit_for_company(company_cik)
print(f"Gross Profit: Quarterly={gp_result['quarterly_inserted']}, Annual={gp_result['annual_inserted']}")
```

### Batch Processing All Companies
```python
# Get all companies
companies = repository.get_all_companies()

for company_cik in companies:
    print(f"\n{'='*60}")
    print(f"Processing: {company_cik}")
    print('='*60)
    
    # Fix cash flows
    cf_result = cashflow_service.fix_cumulative_values_for_company(company_cik)
    
    # Calculate Q4
    income_result = q4_service.calculate_q4_for_company(company_cik)
    cash_result = q4_service.calculate_q4_for_cash_flow(company_cik)
    
    # Calculate Gross Profit
    gp_result = gp_service.calculate_gross_profit_for_company(company_cik)
    
    # Summary
    print(f"\nSummary:")
    print(f"  Cash Flow Fixed: Q2={cf_result['q2_fixed']}, Q3={cf_result['q3_fixed']}")
    print(f"  Q4 Calculated: Income={income_result['successful_calculations']}, Cash={cash_result['successful_calculations']}")
    print(f"  Gross Profit: Quarterly={gp_result['quarterly_inserted']}, Annual={gp_result['annual_inserted']}")
```

## Testing and Validation

### Test with Known Company
Netflix (CIK: 0001018724) is a good test case:
```python
# Has clean financial data
# Reports quarterly and annual values
# Has clear revenue and cost structure

service = GrossProfitService(repository, verbose=True)
result = service.calculate_gross_profit_for_company("0001018724")

# Expected: Multiple years of quarterly and annual Gross Profit values
```

### Verify Results
```python
# Check inserted values in MongoDB
db.concept_values_quarterly.find({
    "company_cik": "0001018724",
    "reporting_period.quarter": 4,  # Check Q4 calculations
    "calculated": True
})

db.concept_values_quarterly.find({
    "concept_id": gross_profit_concept_id,  # Check Gross Profit
    "company_cik": "0001018724"
})
```

## Performance Considerations

### CashFlowFixService
- **Speed:** Fast (in-place updates)
- **Scale:** Processes all fiscal years per company
- **Memory:** Low (streaming updates)

### Q4CalculationService
- **Speed:** Moderate (calculates per concept per year)
- **Scale:** Processes all concepts × all fiscal years
- **Memory:** Moderate (batch queries)

### GrossProfitService
- **Speed:** Moderate (5-collection lookup per label)
- **Scale:** Tries all concept mappings
- **Memory:** Low to moderate

### Optimization Tips
1. Process companies in batches
2. Use verbose=False for production
3. Index MongoDB collections properly
4. Run services during off-peak hours for large datasets

## Troubleshooting

### Common Issues

#### No Values Calculated
**Possible Causes:**
- Missing quarterly or annual data in concept_values collections
- Concepts not found in normalized_concepts
- Data quality issues (missing Q1, Q2, or Q3)

**Solution:**
```python
# Check data availability
result = service.calculate_gross_profit_for_company(company_cik)
print(result['errors'])  # Review error messages
```

#### Q4 Values Incorrect
**Likely Cause:** Cash flow Q2/Q3 values are cumulative

**Solution:**
```python
# Always run CashFlowFixService first
cashflow_service.fix_cumulative_values_for_company(company_cik)
```

#### Gross Profit Not Found
**Possible Causes:**
- Company reports Gross Profit directly (not calculated)
- Different label terminology
- Missing revenue or cost concepts

**Solution:**
```python
# Check what concepts the company has
concepts = repository.get_income_statement_concepts(company_cik)
for concept in concepts:
    print(f"{concept['concept']} - {concept['label']}")
```

## Contributing

When adding new calculation services:

1. **Follow the pattern:**
   - Use `FinancialDataRepository` for DB access
   - Support `verbose` mode
   - Return structured result dictionaries

2. **Document the flow:**
   - Create detailed documentation in `/doc` folder
   - Explain collection flow and formulas
   - Include usage examples

3. **Update this index:**
   - Add service to overview table
   - Update execution order if applicable
   - Add to common patterns if introducing new patterns

## Additional Resources

- **MongoDB Documentation:** Understanding collection schemas
- **SEC EDGAR:** Understanding financial statement structures
- **US GAAP Taxonomy:** Official accounting concept definitions

## Support

For questions or issues:
1. Check service-specific documentation
2. Review error messages in result dictionaries
3. Enable verbose mode for detailed debugging
4. Verify data availability in MongoDB collections
