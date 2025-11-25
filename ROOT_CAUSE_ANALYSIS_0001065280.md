# Root Cause Analysis: CIK 0001065280 Wrong Calculated Values

## Executive Summary

CIK **0001065280** has **NO calculated Q4 values** and cannot have any calculated because the data structure for this company is fundamentally different from other companies in the database.

## Key Finding: Different Data Model

### Working Companies (e.g., Microsoft - 0000789019)
These companies use **concept_values_quarterly** and **concept_values_annual** collections:

```
normalized_concepts_quarterly (1,075 total) 
    ↓ (links via concept_id)
concept_values_quarterly (22,244 records)
    - Contains: actual quarterly values (Q1, Q2, Q3)
    - Has: reporting_period with fiscal_year and quarter
    - Structure: { concept_id, value, reporting_period: {fiscal_year, quarter, ...} }

normalized_concepts_annual (1,149 total)
    ↓ (links via concept_id)  
concept_values_annual (7,359 records)
    - Contains: actual annual values
    - Has: reporting_period with fiscal_year
    - Structure: { concept_id, value, reporting_period: {fiscal_year, ...} }
```

### CIK 0001065280 (Problematic Company)
This company uses **normalized_concepts** but has **NO concept_values**:

```
normalized_concepts_quarterly: 196 records ❌
    - NO corresponding concept_values_quarterly records
    - Missing: fiscal_year field (all NULL)
    - Missing: company_name field (all NULL)
    - Has: concept definitions only, no actual values

normalized_concepts_annual: 233 records ❌
    - NO corresponding concept_values_annual records  
    - Missing: fiscal_year field
    - Missing: company_name field
    - Has: concept definitions only, no actual values
```

## Database Collections Analysis

### Collections Overview:
1. **companies**: 4 companies total
2. **concept_values_annual**: 7,359 records (NONE for CIK 0001065280)
3. **concept_values_quarterly**: 22,244 records (NONE for CIK 0001065280)
4. **normalized_concepts_annual**: 1,149 records (233 for CIK 0001065280)
5. **normalized_concepts_quarterly**: 1,075 records (196 for CIK 0001065280)

### CIK 0001065280 Specific Data:
- **normalized_concepts_quarterly**: 196 records
  - All have `form_type: "10-Q"`
  - All have `fiscal_year: NULL` ❌
  - All have `company_name: NULL` ❌
  - Custom concepts like: `custom:BuildingsAndImprovements`, `custom:CapitalWorkinprogress`
  - 36 dimensional concepts, 160 regular concepts
  
- **normalized_concepts_annual**: 233 records
  - All have `form_type: "10-K"`
  - All have `fiscal_year: NULL` ❌
  - All have `company_name: NULL` ❌
  - Same custom concepts as quarterly

- **concept_values_quarterly**: 0 records ❌
- **concept_values_annual**: 0 records ❌

## Root Causes

### 1. Missing Critical Data Collections
The Q4 calculation service expects data in **concept_values_quarterly** and **concept_values_annual**, but CIK 0001065280 has:
- Zero records in `concept_values_quarterly` 
- Zero records in `concept_values_annual`

### 2. Incomplete Concept Metadata
The concepts for CIK 0001065280 are missing essential fields:
- `fiscal_year`: NULL (cannot match by year)
- `company_name`: NULL (cannot identify company)

### 3. Wrong Data Model
CIK 0001065280 appears to be using an older or different data model where:
- Only concept **definitions** are stored in `normalized_concepts_*`
- Actual **values** are missing from `concept_values_*`
- This is incompatible with the Q4 calculation service

## Why Q4 Calculation Fails

The Q4 calculation service requires:

```python
# For each concept, it needs:
1. Q1 value from concept_values_quarterly (quarter=1, fiscal_year=X)
2. Q2 value from concept_values_quarterly (quarter=2, fiscal_year=X)
3. Q3 value from concept_values_quarterly (quarter=3, fiscal_year=X)
4. Annual value from concept_values_annual (fiscal_year=X)

# Then calculates:
Q4 = Annual - (Q1 + Q2 + Q3)
```

For CIK 0001065280:
- ❌ No Q1 values (concept_values_quarterly is empty)
- ❌ No Q2 values (concept_values_quarterly is empty)
- ❌ No Q3 values (concept_values_quarterly is empty)
- ❌ No Annual values (concept_values_annual is empty)
- ❌ Cannot calculate Q4 = 0 - 0

## Comparison with Working Company

### Microsoft (CIK 0000789019) - WORKING ✅
```
concept_values_quarterly: thousands of records
  Example: {
    "concept_id": "6911e420b211498857b211d7",
    "company_cik": "0000789019",
    "value": 70066000000.0,
    "reporting_period": {
      "fiscal_year": 2025,
      "quarter": 3,
      "company_name": "MICROSOFT CORP"
    }
  }

concept_values_annual: thousands of records
  Example: {
    "concept_id": "6911e420b211498857b210ab",
    "company_cik": "0000789019", 
    "value": 281724000000.0,
    "reporting_period": {
      "fiscal_year": 2025,
      "company_name": "MICROSOFT CORP"
    }
  }
```

### CIK 0001065280 - BROKEN ❌
```
concept_values_quarterly: 0 records (EMPTY)
concept_values_annual: 0 records (EMPTY)

Only has concept definitions:
  {
    "_id": "6924772b56f81e890c36d474",
    "company_cik": "0001065280",
    "concept": "custom:BuildingsAndImprovements",
    "fiscal_year": null,  ❌
    "company_name": null  ❌
  }
```

## Solution Required

This is **NOT a bug in the Q4 calculation service**. The calculation service is working correctly for companies with proper data (like Microsoft).

### Required Actions:

1. **Data Migration Required**: Populate `concept_values_quarterly` and `concept_values_annual` for CIK 0001065280
   - Extract actual financial values from source SEC filings
   - Create proper concept_value records with fiscal_year and quarter information
   - Link to existing concepts via concept_id

2. **Fix Concept Metadata**: Update `normalized_concepts_*` records to include:
   - `fiscal_year`: Proper fiscal year for each concept
   - `company_name`: Actual company name for CIK 0001065280

3. **Data Pipeline Investigation**: 
   - Identify why CIK 0001065280 was processed differently
   - Determine if other companies have the same issue
   - Fix the upstream data normalization pipeline to prevent future occurrences

4. **Find Company Name**:
   - CIK 0001065280 is not in the `companies` collection
   - Need to look up this CIK in SEC EDGAR database to identify the company
   - Add company record to `companies` collection

## Verification Steps

After data is fixed, verify:
1. `concept_values_quarterly` has records for CIK 0001065280 with fiscal_year and quarter
2. `concept_values_annual` has records for CIK 0001065280 with fiscal_year
3. `normalized_concepts_*` records have fiscal_year and company_name populated
4. Run Q4 calculation service for CIK 0001065280
5. Verify Q4 values are calculated correctly

## Conclusion

The "wrong calculated values" for CIK 0001065280 are actually **no calculated values** because:
- The company data uses an incompatible data structure
- Essential collections (concept_values_*) are completely empty
- Required metadata (fiscal_year, company_name) is missing
- The Q4 calculation service cannot function without source data

**This is a data quality issue, not a code bug.**
