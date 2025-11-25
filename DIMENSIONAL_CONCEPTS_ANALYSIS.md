# DIMENSIONAL CONCEPTS Q4 CALCULATION ANALYSIS - Netflix (0001065280)

## Executive Summary

Dimensional concepts for Netflix have **7 negative Q4 values (15.2%)** compared to **254 negative values (35.8%)** for non-dimensional concepts. The dimensional concept issues are caused by a **DIFFERENT root cause** than the non-dimensional issues.

## Two Distinct Problems

### Problem 1: Non-Dimensional Concepts (254 negative, 35.8%)
**Root Cause**: Point-in-time/balance concepts treated as flow concepts
- Affects: Cash balances, asset balances, balance sheet items
- Formula used: `Q4 = Annual - (Q1+Q2+Q3)` ❌
- Should use: `Q4 = Annual` (for point-in-time concepts) ✅

### Problem 2: Dimensional Concepts (7 negative, 15.2%)  
**Root Cause**: Incorrect concept matching - matching by NAME only
- Affects: Same concept name used for different metrics
- Multiple concepts with identical names but different paths/labels
- Formula is correct, but matching wrong concepts together

## Dimensional Concept Issue: Detailed Analysis

### The Matching Error

For `nflx:DomesticDvdMember` in 2018:

**There are 3 QUARTERLY concepts with the same name:**
1. Label: "Domestic Dvd", Path: `002.003` ✅
   - Q1: 42,393,000
   - Q2: 39,924,000  
   - Q3: 37,101,000
   - Sum: 119,418,000

2. Label: "DVD revenues", Path: `001.003` ⚠️
   - Q1: 98,751,000
   - Q2: 92,904,000
   - Q3: 88,777,000
   - Sum: 280,432,000

3. Label: "Domestic Dvd", Path: `004.002.003`
   - (Limited data)

**There is 1 ANNUAL concept:**
- Label: "Domestic Dvd", Path: `002.003`
- Annual: 153,097,000

### What Should Happen ✅

Match quarterly concept #1 with annual concept (both path `002.003`):
```
Q4 = 153,097,000 - (42,393,000 + 39,924,000 + 37,101,000)
Q4 = 153,097,000 - 119,418,000
Q4 = 33,679,000 ✅ CORRECT
```

This calculation DOES exist in the database and is correct!

### What's Also Happening ❌

Match quarterly concept #2 with annual concept (different paths):
```
Q4 = 153,097,000 - (98,751,000 + 92,904,000 + 88,777,000)
Q4 = 153,097,000 - 280,432,000  
Q4 = -127,335,000 ❌ WRONG - NEGATIVE!
```

This creates a duplicate, incorrect Q4 calculation.

## Root Cause in Code

The Q4 calculation service's `_find_matching_annual_concept()` method is matching dimensional concepts by:
1. ✅ Concept name (e.g., `nflx:DomesticDvdMember`)
2. ✅ Company CIK
3. ✅ Statement type
4. ❌ **NOT checking path** - MISSING!
5. ❌ **NOT checking label** - MISSING!

When multiple quarterly concepts share the same name, it matches the WRONG one to the annual concept.

## The 7 Negative Dimensional Values

All 7 are the same issue - `nflx:DomesticDvdMember` mismatches:

| Year | Q1+Q2+Q3 | Annual | Q4 Calculated | Status |
|------|----------|--------|---------------|--------|
| 2012 | 882,504,000 | 591,432,000 | -291,072,000 | ❌ |
| 2013 | 697,539,000 | 459,349,000 | -238,190,000 | ❌ |
| 2014 | 585,672,000 | 396,882,000 | -188,790,000 | ❌ |
| 2015 | 494,742,000 | 323,908,000 | -170,834,000 | ❌ |
| 2016 | 415,854,000 | 262,742,000 | -153,112,000 | ❌ |
| 2017 | 345,345,000 | 202,525,000 | -142,820,000 | ❌ |
| 2018 | 280,432,000 | 153,097,000 | -127,335,000 | ❌ |

Pattern: Q1+Q2+Q3 > Annual for all years, suggesting wrong quarterly concept matched to annual.

## Why This Happens

### Scenario: Netflix Financial Reporting Structure

**Concept Name**: `nflx:DomesticDvdMember` (a dimension)

Netflix might report this dimension in multiple contexts:
- **Context 1**: Segment revenue breakdown (path 002.003)
  - "Domestic Dvd" = DVD segment revenue
  - Smaller numbers (Q1: ~42M)
  
- **Context 2**: Total DVD revenues (path 001.003)  
  - "DVD revenues" = All DVD revenue (domestic + international)
  - Larger numbers (Q1: ~98M)

Both use the same XBRL concept name `nflx:DomesticDvdMember` but represent different metrics!

The annual report only includes Context 1 (segment breakdown), so when the Q4 calculation service:
1. Finds quarterly values from Context 2 (larger numbers)
2. Matches to annual from Context 1 (smaller number)
3. Calculates Q4 = Small annual - Large quarterlies = Negative ❌

## Fix Required

### Solution: Enhance Dimensional Concept Matching

The `_find_matching_annual_concept()` method needs additional matching criteria for dimensional concepts:

```python
def _find_matching_annual_concept(
    self,
    concept_name: str,
    company_cik: str,
    statement_type: str,
    quarterly_concept: Dict[str, Any]  # NEW: Pass full quarterly concept
) -> Optional[Dict[str, Any]]:
    """Find matching annual concept with enhanced matching for dimensions."""
    
    # Find candidates by name, cik, statement
    candidates = list(self.normalized_concepts_annual.find({
        "concept": concept_name,
        "company_cik": company_cik,
        "statement_type": statement_type,
        "dimension_concept": quarterly_concept.get("dimension_concept", False)
    }))
    
    if len(candidates) == 1:
        return candidates[0]
    
    # If multiple candidates, use additional matching
    if len(candidates) > 1:
        quarterly_path = quarterly_concept.get("path", "")
        quarterly_label = quarterly_concept.get("label", "")
        
        # Try exact path match first
        for candidate in candidates:
            if candidate.get("path") == quarterly_path:
                return candidate
        
        # Try exact label match
        for candidate in candidates:
            if candidate.get("label") == quarterly_label:
                return candidate
        
        # Try path prefix match (same segment)
        quarterly_path_parts = quarterly_path.split('.')
        for candidate in candidates:
            candidate_path = candidate.get("path", "")
            candidate_parts = candidate_path.split('.')
            # Match first 2 segments
            if (len(quarterly_path_parts) >= 2 and 
                len(candidate_parts) >= 2 and
                quarterly_path_parts[:2] == candidate_parts[:2]):
                return candidate
        
        # Log warning about ambiguous match
        self.logger.warning(
            f"Multiple annual concepts found for {concept_name}, "
            f"path: {quarterly_path}, label: {quarterly_label}"
        )
        
        # Return first as fallback (not ideal)
        return candidates[0]
    
    return None
```

## Verification After Fix

After implementing the fix:

1. **Delete duplicate Q4 values** for `nflx:DomesticDvdMember` (7 wrong ones)
2. **Re-run calculation** with enhanced matching
3. **Verify**:
   - Only ONE Q4 value per dimensional concept per year
   - No negative Q4 values for DVD revenues
   - Correct path matching (002.003 to 002.003)

## Summary

### Dimensional Concepts (15.2% negative)
- ✅ **Formula is correct** (Q4 = Annual - Q1+Q2+Q3)
- ❌ **Matching is wrong** (matching by name only, ignoring path/label)
- **Fix**: Enhance concept matching to consider path and label
- **Impact**: 7 negative values, all from same concept mismatch

### Non-Dimensional Concepts (35.8% negative)
- ❌ **Formula is wrong** for point-in-time concepts
- ✅ **Matching is correct**
- **Fix**: Detect point-in-time concepts and use different formula
- **Impact**: 254 negative values, mostly balance sheet items

Both issues need separate fixes in the Q4 calculation service!
