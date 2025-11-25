"""Service for Q4 calculation business logic - Refactored with DRY principles."""

from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from bson import ObjectId
except ImportError:
    print("PyMongo not installed. Please run: pip install pymongo")
    raise

from models.financial_data import QuarterlyData, ConceptValue, ReportingPeriod
from repositories.financial_repository import FinancialDataRepository


class Q4CalculationService:
    """Service for calculating Q4 values for financial statement concepts."""
    
    # Point-in-time concept patterns that should NOT be calculated
    # These represent snapshots at specific dates, not flows over periods
    POINT_IN_TIME_PATTERNS = [
        # Cash and equivalents (balance sheet items)
        "CashAndCashEquivalents",
        "CashCashEquivalents",
        "RestrictedCash",
        # Period markers
        "EndOfYear",
        "EndOfPeriod",
        "EndOfTheYear",
        "EndOfThePeriod",
        "BeginningOfYear",
        "BeginningOfPeriod",
        "BeginningOfTheYear",
        "BeginningOfThePeriod",
        "AtEndOf",
        "AtBeginningOf",
        # Shares outstanding (point-in-time, not cumulative)
        "SharesOutstanding",
        "CommonStockSharesOutstanding",
        "StockSharesOutstanding",
        # Exchange rate effects and increases/decreases
        "PeriodIncreaseDecrease",
        "EffectOfExchangeRate",
        "EffectOfExchange",
        # Ending/beginning balances
        "EndingBalance",
        "BeginningBalance",
        "ClosingBalance",
        "OpeningBalance"
    ]
    
    def __init__(self, repository: FinancialDataRepository, verbose: bool = False):
        self.repository = repository
        self.verbose = verbose
    
    # ==================== HELPER METHODS ====================
    
    def _is_point_in_time_concept(self, concept_name: str, label: str = "") -> bool:
        """Check if a concept is point-in-time and should NOT be calculated.
        
        Point-in-time concepts represent snapshots at specific dates (like cash balances)
        rather than flows over a period, so Q4 = Annual - (Q1+Q2+Q3) doesn't apply.
        """
        concept_lower = concept_name.lower()
        label_lower = label.lower()
        
        for pattern in self.POINT_IN_TIME_PATTERNS:
            pattern_lower = pattern.lower()
            if pattern_lower in concept_lower or pattern_lower in label_lower:
                return True
        
        return False
    
    def _get_missing_values_list(self, quarterly_data: QuarterlyData) -> List[str]:
        """Get list of missing values required for Q4 calculation."""
        missing = []
        if quarterly_data.q1_value is None:
            missing.append("Q1")
        if quarterly_data.q2_value is None:
            missing.append("Q2")
        if quarterly_data.q3_value is None:
            missing.append("Q3")
        if quarterly_data.annual_value is None:
            missing.append("Annual")
        return missing
    
    def _create_q4_reporting_period(
        self,
        annual_period: Dict[str, Any],
        company_cik: str,
        fiscal_year: int
    ) -> ReportingPeriod:
        """Create Q4 reporting period from annual filing metadata."""
        return ReportingPeriod(
            end_date=annual_period["end_date"],
            period_date=annual_period["period_date"],
            form_type="10-Q",
            fiscal_year_end_code=annual_period["fiscal_year_end_code"],
            data_source="calculated_from_sec_api_raw",
            company_cik=company_cik,
            company_name=annual_period["company_name"],
            fiscal_year=fiscal_year,
            quarter=4,
            accession_number=annual_period["accession_number"],
            period_type="quarterly",
            start_date=annual_period.get("start_date"),
            context_id=annual_period.get("context_id"),
            item_period=annual_period.get("item_period"),
            unit=annual_period.get("unit"),
            note="Q4 calculated from annual 10-K minus Q1-Q3"
        )
    
    def _create_q4_concept_value(
        self,
        quarterly_concept_id: ObjectId,
        company_cik: str,
        fiscal_year: int,
        q4_value: float,
        annual_metadata: Dict[str, Any]
    ) -> ConceptValue:
        """Create Q4 ConceptValue record."""
        annual_period = annual_metadata["reporting_period"]
        
        q4_reporting_period = self._create_q4_reporting_period(
            annual_period, company_cik, fiscal_year
        )
        
        return ConceptValue(
            concept_id=quarterly_concept_id,
            company_cik=company_cik,
            statement_type=annual_metadata["statement_type"],
            form_type="10-Q",
            reporting_period=q4_reporting_period,
            value=q4_value,
            created_at=datetime.utcnow(),
            dimension_value=annual_metadata.get("dimension_value", False),
            calculated=True,
            dimensional_concept_id=annual_metadata.get("dimensional_concept_id")
        )
    
    def _create_q4_record(
        self, 
        concept_name: str,
        concept_path: str,
        quarterly_concept_id: ObjectId,
        company_cik: str, 
        fiscal_year: int, 
        q4_value: float,
        statement_type: str
    ) -> Optional[ConceptValue]:
        """Create a Q4 ConceptValue record - unified method.
        
        This method handles all Q4 record creation, with fallback logic for
        dimensional concepts that might have different naming in annual vs quarterly.
        """
        # Get annual filing metadata
        annual_metadata = self.repository.get_annual_filing_metadata_by_name_and_path(
            concept_name, concept_path, company_cik, fiscal_year, statement_type
        )
        
        # If not found, try alternative matching using parent concept lookup
        if not annual_metadata:
            quarterly_parent_name = self.repository.get_root_parent_concept_name(
                quarterly_concept_id, "normalized_concepts_quarterly"
            )
            if quarterly_parent_name:
                annual_concept = self.repository.find_matching_concept_by_parent(
                    concept_name, quarterly_concept_id, "normalized_concepts_annual", company_cik
                )
                
                if annual_concept:
                    annual_metadata = self.repository.db["concept_values_annual"].find_one({
                        "concept_id": annual_concept["_id"],
                        "company_cik": company_cik,
                        "reporting_period.fiscal_year": fiscal_year
                    })
        
        if not annual_metadata:
            return None
        
        return self._create_q4_concept_value(
            quarterly_concept_id, company_cik, fiscal_year, q4_value, annual_metadata
        )
    
    def _calculate_q4_generic(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int,
        statement_type: str,
        quarterly_concept: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate Q4 for any statement type - unified calculation method.
        
        This method handles all Q4 calculations regardless of statement type.
        For dimensional concepts with same path, quarterly_concept should be passed
        to ensure correct concept matching.
        """
        result = {"success": False, "reason": None, "is_point_in_time": False}
        
        try:
            # For dimensional concepts with same path, use concept_id directly
            if quarterly_concept and quarterly_concept.get("_id"):
                quarterly_data = self.repository.get_quarterly_data_by_concept_id(
                    quarterly_concept["_id"], company_cik, fiscal_year, statement_type
                )
            else:
                # Fallback to path-based lookup for non-dimensional concepts
                quarterly_data = self.repository.get_quarterly_data_for_concept_by_name_and_path(
                    concept_name, concept_path, company_cik, fiscal_year, statement_type
                )
            
            # Check if concept was found
            if quarterly_data.concept_id is None:
                result["reason"] = "Concept not found in quarterly data"
                return result
            
            # Check if Q4 already exists using concept_id (more reliable)
            if self.repository.check_q4_exists(
                quarterly_data.concept_id, company_cik, fiscal_year
            ):
                result["reason"] = "Q4 value already exists"
                return result
            
            # Check if this is a point-in-time concept
            # For point-in-time concepts, Q4 value = Annual value (not calculated)
            label = quarterly_concept.get("label", "") if quarterly_concept else ""
            is_point_in_time = self._is_point_in_time_concept(concept_name, label)
            
            if is_point_in_time:
                # For point-in-time concepts, copy annual value to Q4
                if quarterly_data.annual_value is None:
                    result["reason"] = "Point-in-time concept with no annual value"
                    result["is_point_in_time"] = True
                    return result
                
                q4_value = quarterly_data.annual_value
                result["is_point_in_time"] = True
            else:
                # For flow concepts, calculate Q4 = Annual - (Q1 + Q2 + Q3)
                if not quarterly_data.can_calculate_q4():
                    missing_values = self._get_missing_values_list(quarterly_data)
                    result["reason"] = f"Missing values: {', '.join(missing_values)}"
                    return result
                
                # Calculate Q4 value
                q4_value = quarterly_data.calculate_q4()
            
            # Create Q4 record
            q4_record = self._create_q4_record(
                concept_name, concept_path, quarterly_data.concept_id, 
                company_cik, fiscal_year, q4_value, statement_type
            )
            
            if q4_record is None:
                result["reason"] = "Could not create Q4 record (missing annual filing metadata)"
                return result
            
            # Insert Q4 value
            if self.repository.insert_q4_value(q4_record):
                result["success"] = True
                if self.verbose:
                    print(f"✓ Calculated Q4 for {concept_name} ({statement_type}) (Path: {concept_path}) FY{fiscal_year}: {q4_value:,.2f}")
            else:
                result["reason"] = "Failed to insert Q4 value into database"
        
        except Exception as e:
            result["reason"] = f"Calculation error: {str(e)}"
        
        return result
    
    def _calculate_q4_for_statement_type(
        self, 
        company_cik: str,
        statement_type: str,
        get_concepts_method
    ) -> Dict[str, Any]:
        """Generic method to calculate Q4 for any statement type.
        
        Args:
            company_cik: Company CIK
            statement_type: Type of statement (income_statement, cash_flows, etc.)
            get_concepts_method: Method to get concepts for this statement type
        """
        results = {
            "company_cik": company_cik,
            "statement_type": statement_type,
            "processed_concepts": 0,
            "successful_calculations": 0,
            "skipped_concepts": 0,
            "errors": []
        }
        
        try:
            # Get all concepts for the statement type
            concepts = get_concepts_method(company_cik)
            
            if not concepts:
                results["errors"].append(
                    f"No {statement_type} concepts found for company {company_cik}"
                )
                return results
            
            # Get all fiscal years for the company
            fiscal_years = self.repository.get_fiscal_years_for_company(company_cik)
            
            if not fiscal_years:
                results["errors"].append(f"No fiscal years found for company {company_cik}")
                return results
            
            # Process each concept for each fiscal year
            for concept in concepts:
                concept_name = concept.get("concept", "Unknown")
                concept_path = concept.get("path", "")
                
                for fiscal_year in fiscal_years:
                    try:
                        result = self._calculate_q4_generic(
                            concept_name, 
                            concept_path,
                            company_cik, 
                            fiscal_year,
                            statement_type,
                            quarterly_concept=concept  # Pass the full concept document
                        )
                        
                        results["processed_concepts"] += 1
                        
                        if result["success"]:
                            results["successful_calculations"] += 1
                        else:
                            results["skipped_concepts"] += 1
                            # Only log as error if it's NOT a point-in-time concept
                            # Point-in-time concepts are expected behavior, not errors
                            if result.get("reason") and not result.get("is_point_in_time", False):
                                results["errors"].append(
                                    f"Concept {concept_name} (Path: {concept_path}) FY{fiscal_year}: {result['reason']}"
                                )
                    
                    except Exception as e:
                        results["errors"].append(
                            f"Error processing concept {concept_name} FY{fiscal_year}: {str(e)}"
                        )
                        results["processed_concepts"] += 1
        
        except Exception as e:
            results["errors"].append(f"General error: {str(e)}")
        
        return results
    
    # ==================== PUBLIC API METHODS ====================
    
    def calculate_q4_for_company(self, company_cik: str) -> Dict[str, Any]:
        """Calculate Q4 values for all income statement concepts of a company."""
        return self._calculate_q4_for_statement_type(
            company_cik,
            "income_statement",
            self.repository.get_income_statement_concepts
        )
    
    def calculate_q4_for_cash_flow(self, company_cik: str) -> Dict[str, Any]:
        """Calculate Q4 values for all cash flow statement concepts of a company."""
        return self._calculate_q4_for_statement_type(
            company_cik,
            "cash_flows",
            self.repository.get_cash_flow_concepts
        )
    
    # ==================== LEGACY COMPATIBILITY METHODS ====================
    
    def _calculate_q4_for_concept(
        self, 
        concept_id: ObjectId, 
        company_cik: str, 
        fiscal_year: int,
        concept_name: str = "Unknown"
    ) -> Dict[str, Any]:
        """Legacy method - Calculate Q4 by concept_id."""
        concept = self.repository.normalized_concepts_quarterly.find_one({"_id": concept_id})
        if not concept:
            return {"success": False, "reason": "Concept not found"}
        
        return self._calculate_q4_generic(
            concept["concept"],
            concept.get("path", ""),
            company_cik,
            fiscal_year,
            concept.get("statement_type", "income_statement")
        )
    
    def _calculate_q4_for_concept_by_name(
        self, 
        concept_name: str,
        company_cik: str, 
        fiscal_year: int
    ) -> Dict[str, Any]:
        """Legacy method - Calculate Q4 by name (assumes income statement)."""
        return self._calculate_q4_generic(
            concept_name, "", company_cik, fiscal_year, "income_statement"
        )
    
    def _calculate_q4_for_concept_by_name_and_path(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int
    ) -> Dict[str, Any]:
        """Legacy method - Calculate Q4 by name and path (assumes income statement)."""
        return self._calculate_q4_generic(
            concept_name, concept_path, company_cik, fiscal_year, "income_statement"
        )
