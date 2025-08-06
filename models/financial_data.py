"""Models for financial data structures."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

try:
    from bson import ObjectId
except ImportError:
    print("PyMongo not installed. Please run: pip install pymongo")
    raise


@dataclass
class ReportingPeriod:
    """Represents a reporting period for financial data."""
    end_date: datetime
    period_date: str
    period_type: str
    form_type: str
    fiscal_year_end_code: str
    data_source: str
    company_cik: str
    company_name: str
    start_date: datetime
    fiscal_year: int
    quarter: int
    note: Optional[str] = None


@dataclass
class ConceptValue:
    """Represents a financial concept value."""
    concept_id: ObjectId
    company_cik: str
    statement_type: str
    form_type: str
    filing_id: ObjectId
    reporting_period: ReportingPeriod
    value: float
    created_at: datetime
    dimension_value: bool
    calculated: bool
    fact_id: str
    decimals: str
    dimensional_concept_id: Optional[ObjectId] = None


@dataclass
class QuarterlyData:
    """Represents quarterly data for a specific concept and fiscal year."""
    concept_id: Optional[ObjectId]
    company_cik: str
    fiscal_year: int
    q1_value: Optional[float] = None
    q2_value: Optional[float] = None
    q3_value: Optional[float] = None
    annual_value: Optional[float] = None
    
    def has_complete_quarterly_data(self) -> bool:
        """Check if Q1, Q2, Q3 values are available."""
        return all(v is not None for v in [self.q1_value, self.q2_value, self.q3_value])
    
    def has_annual_value(self) -> bool:
        """Check if annual value is available."""
        return self.annual_value is not None
    
    def can_calculate_q4(self) -> bool:
        """Check if Q4 can be calculated."""
        return self.has_complete_quarterly_data() and self.has_annual_value()
    
    def calculate_q4(self) -> float:
        """Calculate Q4 value using the formula: Annual - (Q1 + Q2 + Q3)."""
        if not self.can_calculate_q4():
            raise ValueError("Cannot calculate Q4: missing required values")
        
        # Type assertion is safe here because can_calculate_q4() checks for None values
        assert self.annual_value is not None
        assert self.q1_value is not None
        assert self.q2_value is not None
        assert self.q3_value is not None
        
        return self.annual_value - (self.q1_value + self.q2_value + self.q3_value)
