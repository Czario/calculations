# Target Database Schema Documentation

## Overview

The target database (`normalize_data`) is the processed, normalized version of financial data extracted from SEC filings. It contains clean, structured data optimized for financial analysis and reporting.

## Database Configuration

```yaml
Database Name: normalize_data (configurable via TARGET_DB_NAME env var)
MongoDB URI: mongodb://localhost:27017 (configurable via MONGODB_URI)
Source Database: financial_base_data (raw SEC data)
```

## Collections Overview

The target database contains the following main collections:

1. **companies** - Company master data
2. **normalized_concepts_annual** - Normalized concepts from 10-K annual filings
3. **normalized_concepts_quarterly** - Normalized concepts from 10-Q quarterly filings
4. **concept_values_annual** - Financial values for annual concepts
5. **concept_values_quarterly** - Financial values for quarterly concepts (includes calculated Q4 values)

## Collection Schemas

### 1. companies Collection

**Purpose**: Master data for companies extracted from SEC filings.

```json
{
  "_id": ObjectId,
  "cik": "0000320193",
  "name": "Apple Inc.",
  "ticker_symbol": "AAPL",
  "corporate_info": {
    "entity_type": "operating",
    "sic": "3571",
    "state_of_incorporation": "CA"
  },
  "industry": {
    "sic_description": "Electronic Computers",
    "business_description": "..."
  },
  "market_info": {
    "exchange": "NASDAQ",
    "trading_symbol": "AAPL"
  },
  "created_at": ISODate,
  "updated_at": ISODate
}
```

**Indexes**:
- `{"cik": 1}` - Primary lookup by CIK
- `{"ticker_symbol": 1}` - Lookup by ticker symbol

---

### 2. normalized_concepts_annual / normalized_concepts_quarterly Collections

**Purpose**: Normalized financial statement line items and dimensional concepts with hierarchical structure.

#### Regular Line Item Concept Document

```json
{
  "_id": ObjectId,
  "company_cik": "0000320193",
  "statement_type": "income_statement",
  "concept": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
  "form_type": "10-K",
  "label": "Net sales",
  "path": "001",
  "order_key": "a",
  "abstract": false,
  "dimension": false,
  "dimension_concept": false
}
```

#### Dimensional Concept Document

```json
{
  "_id": ObjectId,
  "company_cik": "0000320193",
  "statement_type": "income_statement",
  "concept": "us-gaap:ProductMember",
  "form_type": "10-K",
  "label": "iPhone",
  "path": "001.001",
  "order_key": "a",
  "abstract": false,
  "dimension": false,
  "dimension_concept": true,
  "concept_id": ObjectId("parent_concept_id"),
  "segment_type": "product",
  "context_id": "context_123",
  "unit_id": "USD",
  "period": "2024-09-28",
  "concept_name": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
  "fact_label": "Net sales - iPhone",
  "dimensions": {
    "us-gaap:ProductOrServiceAxis": "us-gaap:ProductMember"
  },
  "dimension_details": {
    "axis": "us-gaap:ProductOrServiceAxis",
    "member": "us-gaap:ProductMember",
    "explicit": true
  }
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `company_cik` | String | SEC CIK identifier (10 digits with leading zeros) |
| `statement_type` | String | Type of financial statement (`income_statement`, `balance_sheet`, `cash_flow`) |
| `concept` | String | US-GAAP or company-specific concept identifier |
| `form_type` | String | SEC form type (`10-K`, `10-Q`) |
| `label` | String | Human-readable label from taxonomy |
| `path` | String | Materialized path for hierarchy (`001`, `001.001`, `001.002`) |
| `order_key` | String | Lexicographic ordering key (`a`, `b`, `c`, etc.) |
| `abstract` | Boolean | Whether this is a section header (no values) |
| `dimension` | Boolean | Whether this concept has dimensional breakdowns |
| `dimension_concept` | Boolean | Whether this is a dimensional concept itself |
| `concept_id` | ObjectId | Parent concept ID (for dimensional concepts only) |
| `segment_type` | String | Type of dimensional segment (`product`, `geographic`, `business`) |

**Indexes**:
- `{"company_cik": 1, "statement_type": 1, "concept": 1}` - Primary concept lookup
- `{"company_cik": 1, "statement_type": 1, "path": 1}` - Hierarchy queries
- `{"concept_id": 1, "segment_type": 1}` - Dimensional concept relationships

---

### 3. concept_values_annual / concept_values_quarterly Collections

**Purpose**: Actual financial values associated with concepts, including calculated Q4 values.

#### Regular Value Document

```json
{
  "_id": ObjectId,
  "concept_id": ObjectId("normalized_concept_id"),
  "company_cik": "0000320193",
  "statement_type": "income_statement",
  "form_type": "10-Q",
  "filing_id": ObjectId("filing_reference"),
  "reporting_period": {
    "end_date": ISODate("2024-09-28T00:00:00.000Z"),
    "period_date": "2024-09-28",
    "period_type": "quarterly",
    "form_type": "10-Q",
    "fiscal_year_end_code": "0927",
    "data_source": "sec_api_raw_only",
    "company_cik": "0000320193",
    "company_name": "Apple Inc.",
    "start_date": ISODate("2024-07-01T00:00:00.000Z"),
    "fiscal_year": 2024,
    "quarter": 4
  },
  "value": 391035000000,
  "created_at": ISODate,
  "dimension_value": false,
  "calculated": false,
  "fact_id": "F_12345_us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax",
  "decimals": "-6"
}
```

#### Dimensional Value Document

```json
{
  "_id": ObjectId,
  "concept_id": ObjectId("dimensional_concept_id"),
  "company_cik": "0000320193",
  "statement_type": "income_statement",
  "form_type": "10-Q",
  "filing_id": ObjectId("filing_reference"),
  "reporting_period": {
    "end_date": ISODate("2024-09-28T00:00:00.000Z"),
    "period_date": "2024-09-28",
    "period_type": "quarterly",
    "fiscal_year": 2024,
    "quarter": 4
  },
  "value": 200000000000,
  "created_at": ISODate,
  "dimension_value": true,
  "dimensional_concept_id": ObjectId("dimensional_concept_id"),
  "calculated": false,
  "fact_id": "F_67890_us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax_iPhone",
  "decimals": "-6"
}
```

#### Calculated Q4 Value Document

```json
{
  "_id": ObjectId,
  "concept_id": ObjectId("concept_id"),
  "company_cik": "0000320193",
  "statement_type": "income_statement",
  "form_type": "10-Q",
  "filing_id": ObjectId("annual_filing_id"),
  "reporting_period": {
    "end_date": ISODate("2024-09-28T00:00:00.000Z"),
    "period_date": "2024-09-28",
    "period_type": "quarterly",
    "form_type": "10-Q",
    "fiscal_year_end_code": "0927",
    "data_source": "calculated_from_sec_api_raw",
    "company_cik": "0000320193",
    "company_name": "Apple Inc.",
    "note": "Q4 calculated from annual 10-K minus Q1-Q3 individual values - preserving raw SEC API metadata",
    "start_date": ISODate("2024-07-01T00:00:00.000Z"),
    "fiscal_year": 2024,
    "quarter": 4
  },
  "value": 94880000000,
  "created_at": ISODate,
  "dimension_value": false,
  "calculated": true,
  "fact_id": "Q4_CALC_F_original_fact_id",
  "decimals": "-6"
}
```

**Field Descriptions**:

| Field | Type | Description |
|-------|------|-------------|
| `concept_id` | ObjectId | Reference to normalized concept document |
| `company_cik` | String | SEC CIK identifier |
| `statement_type` | String | Financial statement type |
| `form_type` | String | SEC form type (`10-K`, `10-Q`) |
| `filing_id` | ObjectId | Reference to source filing |
| `reporting_period` | Object | Complete period information from SEC |
| `value` | Number | Actual financial value (may be negative) |
| `dimension_value` | Boolean | Whether this is a dimensional value |
| `dimensional_concept_id` | ObjectId | Reference to dimensional concept (if applicable) |
| `calculated` | Boolean | Whether this value was calculated (Q4 values, deaccumulated cash flow) |
| `fact_id` | String | Original SEC fact identifier for traceability |
| `decimals` | String | Decimal precision from SEC filing |

**Indexes**:
- `{"concept_id": 1, "company_cik": 1, "reporting_period.fiscal_year": 1}` - Primary value lookup
- `{"company_cik": 1, "statement_type": 1, "reporting_period.fiscal_year": 1}` - Company reports
- `{"filing_id": 1}` - Values by filing
- `{"dimension_value": 1, "dimensional_concept_id": 1}` - Dimensional value queries
- `{"calculated": 1}` - Calculated vs. original values

---

## Data Processing Features

### 1. Hierarchical Structure

**Materialized Paths**: Each concept has a `path` field that enables efficient hierarchy queries:
- Root level: `"001"`, `"002"`, `"003"`
- Second level: `"001.001"`, `"001.002"`, `"002.001"`
- Third level: `"001.001.001"`, `"001.001.002"`

**Order Keys**: Lexicographic ordering within each hierarchy level:
- `"a"`, `"b"`, `"c"` for sequential ordering
- Enables proper financial statement presentation order

### 2. Dimensional Analysis

**Dimensional Concepts**: Support for SEC dimensional reporting:
- Product segments (iPhone, iPad, Mac, etc.)
- Geographic regions (Americas, Europe, China, etc.)
- Business segments (Products, Services)

**Relationship Mapping**: Dimensional concepts link to parent line items via `concept_id`

### 3. Calculated Values

**Q4 Calculations**: Missing Q4 quarterly values calculated as:
```
Q4 = Annual (10-K) - (Q1 + Q2 + Q3)
```

**Cash Flow Deaccumulation**: Cumulative cash flow values converted to individual quarters:
- Q1: Original value (individual)
- Q2: Q2_cumulative - Q1_individual  
- Q3: Q3_cumulative - (Q1_individual + Q2_individual)

### 4. Data Quality Features

**Duplicate Prevention**: 
- Concepts: Unique by company + statement + concept + path + order
- Values: Unique by concept + filing + reporting period

**Data Lineage**: 
- `fact_id` preserves original SEC fact identifiers
- `calculated` flag distinguishes computed values
- `data_source` tracks data origin

**Fiscal Year Accuracy**: 
- Uses original fiscal year from SEC filings
- No recalculation to prevent errors

---

## Query Patterns

### Common Query Examples

#### Get Company's Income Statement Hierarchy
```javascript
db.normalized_concepts_quarterly.find({
  "company_cik": "0000320193",
  "statement_type": "income_statement"
}).sort({"path": 1, "order_key": 1})
```

#### Get Q4 Values for a Fiscal Year
```javascript
db.concept_values_quarterly.find({
  "company_cik": "0000320193",
  "reporting_period.fiscal_year": 2024,
  "reporting_period.quarter": 4
})
```

#### Get Dimensional Breakdown for Revenue
```javascript
// First find the revenue concept
const revenueConcept = db.normalized_concepts_quarterly.findOne({
  "company_cik": "0000320193",
  "concept": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
})

// Then find its dimensional concepts
db.normalized_concepts_quarterly.find({
  "concept_id": revenueConcept._id,
  "dimension_concept": true
})
```

#### Get All Calculated Values
```javascript
db.concept_values_quarterly.find({
  "calculated": true,
  "company_cik": "0000320193"
})
```

---

## Performance Considerations

### Collection Separation Strategy

**Annual vs. Quarterly Split**: 
- Separate collections for 10-K and 10-Q data improve query performance
- Reduces index size and query complexity
- Enables targeted queries by form type

**Indexing Strategy**:
- Compound indexes for common query patterns
- Sparse indexes for optional fields
- Text indexes for concept labels (if needed)

### Storage Optimization

**Document Size**: Optimized for MongoDB document limits
**Field Types**: Appropriate types for efficient storage and queries
**Denormalization**: Reporting period details included for query efficiency

---

## Data Validation Rules

### Concept Documents
- `company_cik` must be 10-digit string with leading zeros
- `path` must follow materialized path format
- `order_key` must be unique within path level
- Dimensional concepts must have valid `concept_id` reference

### Value Documents  
- `value` must be numeric (can be negative)
- `reporting_period.fiscal_year` must be integer
- `fact_id` must be preserved from source data
- Calculated values must have `calculated: true`

### Referential Integrity
- `concept_id` must reference existing concept document
- `filing_id` must reference source filing
- `dimensional_concept_id` must reference valid dimensional concept

---

## Maintenance Operations

### Data Cleanup
```javascript
// Remove calculated values for recalculation
db.concept_values_quarterly.deleteMany({"calculated": true})

// Remove duplicate prevention
db.normalized_concepts_quarterly.createIndex(
  {"company_cik": 1, "statement_type": 1, "concept": 1}, 
  {"unique": true}
)
```

### Performance Monitoring
```javascript
// Check collection sizes
db.stats()

// Analyze query performance
db.concept_values_quarterly.explain("executionStats").find({
  "company_cik": "0000320193"
})
```

---

## Migration and Backup

### Backup Strategy
- Regular MongoDB dumps of target database
- Point-in-time recovery capability
- Separate backup of calculated vs. source-derived data

### Data Migration
- Source database remains unchanged
- Target database can be rebuilt from source
- Incremental updates supported for new filings

---

This database structure provides a robust foundation for financial analysis, reporting, and SEC compliance while maintaining data quality and query performance.
