# Cash Flow Fix Process (fix-cashflow)

## Overview

This document explains the `fix-cashflow` process that converts cumulative quarterly cash flow values to actual quarterly values.

## Problem Statement

In financial reporting, cash flow statements for Q2 and Q3 often contain **cumulative values** instead of quarterly values:

- **Q2 10-Q filing**: Contains 6-month cumulative value (Jan-Jun) instead of 3-month quarterly value (Apr-Jun)
- **Q3 10-Q filing**: Contains 9-month cumulative value (Jan-Sep) instead of 3-month quarterly value (Jul-Sep)

This makes it impossible to calculate accurate Q4 values using the formula: `Q4 = Annual - (Q1 + Q2 + Q3)`

## Solution

The `fix-cashflow` process converts these cumulative values to actual quarterly values:

### Formula

- **Q2 quarterly** = Q2 cumulative - Q1
- **Q3 quarterly** = Q3 cumulative - Q2 cumulative

### Example

Given the sample data from Meta Platforms (CIK: 0001326801) for FY2012:

**Before Fix (Cumulative Values):**
```
Q1: $100M  (3 months: Jan-Mar)
Q2: $250M  (6 months: Jan-Jun) ← CUMULATIVE
Q3: $400M  (9 months: Jan-Sep) ← CUMULATIVE
```

**After Fix (Quarterly Values):**
```
Q1: $100M  (3 months: Jan-Mar)
Q2: $150M  (3 months: Apr-Jun) = $250M - $100M
Q3: $150M  (3 months: Jul-Sep) = $400M - $250M
```

## Usage

### Fix All Companies

```bash
python app.py --fix-cashflow --all-companies
```

This will:
- Find all companies with cash flow data
- Process all fiscal years for each company
- Convert Q2 and Q3 values to quarterly values
- Update the database with corrected values

### Fix Single Company

```bash
python app.py --fix-cashflow --cik 0001326801
```

Replace `0001326801` with the desired company CIK.

### Verbose Output

```bash
python app.py --fix-cashflow --all-companies --verbose
python app.py --fix-cashflow --cik 0001326801 --verbose
```

Shows detailed processing information including:
- Each concept being processed
- Before and after values
- Concepts skipped due to missing data

## Database Impact

### Collections Modified

- **concept_values_quarterly**: Updates `value` field for Q2 and Q3 records where:
  - `statement_type = "cash_flows"`
  - `form_type = "10-Q"`
  - `reporting_period.quarter` in [2, 3]

### Data Structure

The service modifies existing records in the `concept_values_quarterly` collection:

```javascript
{
  "_id": ObjectId("..."),
  "concept_id": ObjectId("..."),
  "company_cik": "0001326801",
  "statement_type": "cash_flows",
  "form_type": "10-Q",
  "reporting_period": {
    "quarter": 2,  // or 3
    "fiscal_year": 2012,
    // ... other fields
  },
  "value": 150000000,  // ← UPDATED from cumulative to quarterly
  // ... other fields
}
```

## Process Details

### Algorithm

For each company and fiscal year:

1. **Retrieve quarterly values**
   - Get all Q1, Q2, Q3 cash flow values
   - Group by `concept_id` for matching

2. **Fix Q2 values**
   - For each Q2 value with matching Q1:
     - Calculate: `Q2_new = Q2_old - Q1`
     - Update database

3. **Fix Q3 values**
   - For each Q3 value with matching Q2:
     - Calculate: `Q3_new = Q3_old - Q2_old` (uses original Q2 cumulative)
     - Update database

### Skipped Values

Values are skipped when:
- **Q2 fix**: No matching Q1 value exists
- **Q3 fix**: No matching Q2 value exists

This is normal and expected for concepts that only appear in certain quarters.

## Testing

### Test Script

A test script is provided to verify the fix process:

```bash
cd scripts/debug
python test_cashflow_fix.py
```

This will:
- Show sample data BEFORE the fix
- Run the fix process
- Show sample data AFTER the fix
- Verify calculations are correct

Test specific company:
```bash
python test_cashflow_fix.py --cik 0000789019
```

### Verification

The test script verifies:
- Q2 values: `Q2_after = Q2_before - Q1`
- Q3 values: `Q3_after = Q3_before - Q2_before`

## Important Notes

### ⚠️ Backup Recommendation

Before running the fix process on production data:
1. Backup your database
2. Test on a single company first
3. Verify results using the test script

### 🔄 Re-running the Process

**DO NOT** run the fix process twice on the same data!

If you run it twice:
- Q2 will become: `(Q2 - Q1) - Q1 = Q2 - 2*Q1` ❌
- Q3 will become: `(Q3 - Q2) - (Q2 - Q1) = Q3 - 2*Q2 + Q1` ❌

If you need to re-run:
1. Restore from backup, OR
2. Re-import the original data

### 📊 Integration with Q4 Calculation

After running `fix-cashflow`, the Q4 calculation will work correctly:

```bash
# Step 1: Fix cumulative values
python app.py fix-cashflow

# Step 2: Calculate Q4 values
python app.py q4
```

The Q4 calculation uses: `Q4 = Annual - (Q1 + Q2 + Q3)`

With corrected quarterly values, this formula produces accurate Q4 results.

## Output Example

```
Processing company 0001326801...

  Processing FY2012...
    Found Q1: 45, Q2: 45, Q3: 45 values
    ✓ Fixed Q2 for NetCashProvidedByUsedInOperatingActivities: 250000000 → 150000000 (Q2 - Q1)
    ✓ Fixed Q3 for NetCashProvidedByUsedInOperatingActivities: 400000000 → 150000000 (Q3 - Q2)
    ...

════════════════════════════════════════════════════════════
🔧 CASH FLOW FIX RESULTS - 0001326801
════════════════════════════════════════════════════════════
📊 Fiscal years processed: 5
✅ Q2 values fixed: 225
✅ Q3 values fixed: 225
⏭️  Q2 values skipped: 3
⏭️  Q3 values skipped: 2
════════════════════════════════════════════════════════════
```

## Technical Implementation

### Service Class

`CashFlowFixService` in `services/cashflow_fix_service.py`

### Key Methods

- `fix_all_companies()`: Process all companies
- `fix_cumulative_values_for_company(company_cik)`: Process single company
- `_fix_fiscal_year(company_cik, fiscal_year)`: Process single fiscal year

### Dependencies

- MongoDB with `concept_values_quarterly` collection
- Company must have Q1, Q2, Q3 cash flow data in the database

## Troubleshooting

### No values fixed

**Possible causes:**
- Company has no cash flow data
- All Q2/Q3 values already processed
- Missing Q1 or Q2 values for calculation

**Solution:** Check database for existence of quarterly cash flow data

### Verification failed

**Possible causes:**
- Process was run multiple times
- Data was modified externally

**Solution:** Restore from backup and re-run once

### High skip rate

**Normal behavior** if:
- Some concepts only appear in certain quarters
- Company structure changed over time

**Investigate** if skip rate > 50%

## Related Documentation

- [Q4 Calculation Process](../README.md)
- [Database Schema](../../README.md)
- [Test Scripts](README.md)

## Version History

- **v1.0** (2025-11-28): Initial implementation of fix-cashflow process
