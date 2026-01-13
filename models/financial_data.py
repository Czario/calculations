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
    form_type: str
    fiscal_year_end_code: str
    data_source: str
    company_cik: str
    company_name: str
    fiscal_year: int
    quarter: int
    accession_number: str  # Always present in real schema
    period_type: Optional[str] = None  # Not always present
    start_date: Optional[datetime] = None  # Not always present
    context_id: Optional[str] = None  # Present in real data
    item_period: Optional[datetime] = None  # Present in real data
    unit: Optional[str] = None  # Present in real data
    note: Optional[str] = None


@dataclass
class ConceptValue:
    """Represents a financial concept value."""
    concept_id: ObjectId
    company_cik: str
    statement_type: str
    form_type: str
    reporting_period: ReportingPeriod
    value: float
    created_at: datetime
    dimension_value: bool
    calculated: bool
    # Note: filing_id and fact_id do NOT exist in the actual database schema
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
        """
        Check if Q4 can be calculated.
        
        Q4 can always be calculated. Any null or missing values are treated as 0.
        This ensures Q4 is calculated even when quarterly or annual data is incomplete.
        """
        return True
    
    def calculate_q4(self) -> float:
        """
        Calculate Q4 value using the formula: Annual - (Q1 + Q2 + Q3).
        
        Any null or missing values are treated as 0.
        This ensures Q4 is calculated even when quarterly or annual data is incomplete.
        """
        # Treat None values as 0
        annual = self.annual_value if self.annual_value is not None else 0.0
        q1 = self.q1_value if self.q1_value is not None else 0.0
        q2 = self.q2_value if self.q2_value is not None else 0.0
        q3 = self.q3_value if self.q3_value is not None else 0.0
        
        return annual - (q1 + q2 + q3)
