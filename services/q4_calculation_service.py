"""Service for Q4 calculation business logic."""

from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from bson import ObjectId
except ImportError:
    print("PyMongo not installed. Please run: pip install pymongo")
    raise

from models.financial_data import QuarterlyData, ConceptValue, ReportingPeriod
from repositories.financial_repository import FinancialDataRepository


class Q4CalculationService:
    """Service for calculating Q4 values for income statement concepts."""
    
    def __init__(self, repository: FinancialDataRepository):
        self.repository = repository
    
    def calculate_q4_for_company(self, company_cik: str) -> Dict[str, Any]:
        """Calculate Q4 values for all income statement concepts of a company."""
        
        results = {
            "company_cik": company_cik,
            "processed_concepts": 0,
            "successful_calculations": 0,
            "skipped_concepts": 0,
            "errors": []
        }
        
        try:
            # Get all income statement concepts for the company
            concepts = self.repository.get_income_statement_concepts(company_cik)
            
            if not concepts:
                results["errors"].append(f"No income statement concepts found for company {company_cik}")
                return results
            
            # Get all fiscal years for the company
            fiscal_years = self.repository.get_fiscal_years_for_company(company_cik)
            
            if not fiscal_years:
                results["errors"].append(f"No fiscal years found for company {company_cik}")
                return results
            
            # Process each concept for each fiscal year
            for concept in concepts:
                concept_id = concept["_id"]
                concept_name = concept.get("concept", "Unknown")
                concept_path = concept.get("path", "")
                
                for fiscal_year in fiscal_years:
                    try:
                        result = self._calculate_q4_for_concept_by_name_and_path(
                            concept_name, 
                            concept_path,
                            company_cik, 
                            fiscal_year
                        )
                        
                        results["processed_concepts"] += 1
                        
                        if result["success"]:
                            results["successful_calculations"] += 1
                        else:
                            results["skipped_concepts"] += 1
                            if result.get("reason"):
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
    
    def _calculate_q4_for_concept(
        self, 
        concept_id: ObjectId, 
        company_cik: str, 
        fiscal_year: int,
        concept_name: str = "Unknown"
    ) -> Dict[str, Any]:
        """Calculate Q4 for a specific concept, company, and fiscal year."""
        
        result = {"success": False, "reason": None}
        
        try:
            # Check if Q4 already exists
            if self.repository.check_q4_exists(concept_id, company_cik, fiscal_year):
                result["reason"] = "Q4 value already exists"
                return result
            
            # Get quarterly data
            quarterly_data = self.repository.get_quarterly_data_for_concept(
                concept_id, company_cik, fiscal_year
            )
            
            # Check if we can calculate Q4
            if not quarterly_data.can_calculate_q4():
                missing_values = []
                if quarterly_data.q1_value is None:
                    missing_values.append("Q1")
                if quarterly_data.q2_value is None:
                    missing_values.append("Q2")
                if quarterly_data.q3_value is None:
                    missing_values.append("Q3")
                if quarterly_data.annual_value is None:
                    missing_values.append("Annual")
                
                result["reason"] = f"Missing values: {', '.join(missing_values)}"
                return result
            
            # Calculate Q4 value
            q4_value = quarterly_data.calculate_q4()
            
            # Create Q4 record
            q4_record = self._create_q4_record(
                concept_id, company_cik, fiscal_year, q4_value
            )
            
            if q4_record is None:
                result["reason"] = "Could not create Q4 record (missing annual filing metadata)"
                return result
            
            # Insert Q4 value
            if self.repository.insert_q4_value(q4_record):
                result["success"] = True
                print(f"✓ Calculated Q4 for {concept_name} FY{fiscal_year}: {q4_value:,.2f}")
            else:
                result["reason"] = "Failed to insert Q4 value into database"
        
        except Exception as e:
            result["reason"] = f"Calculation error: {str(e)}"
        
        return result
    
    def _create_q4_record(
        self, 
        concept_id: ObjectId, 
        company_cik: str, 
        fiscal_year: int, 
        q4_value: float
    ) -> Optional[ConceptValue]:
        """Create a Q4 ConceptValue record based on annual filing metadata."""
        
        # Get annual filing metadata
        annual_metadata = self.repository.get_annual_filing_metadata(
            concept_id, company_cik, fiscal_year
        )
        
        if not annual_metadata:
            return None
        
        # Extract reporting period from annual data
        annual_period = annual_metadata["reporting_period"]
        
        # Create Q4 reporting period
        q4_reporting_period = ReportingPeriod(
            end_date=annual_period["end_date"],
            period_date=annual_period["period_date"],
            period_type="quarterly",
            form_type="10-Q",
            fiscal_year_end_code=annual_period["fiscal_year_end_code"],
            data_source="calculated_from_sec_api_raw",
            company_cik=company_cik,
            company_name=annual_period["company_name"],
            start_date=annual_period.get("start_date", annual_period["end_date"]),
            fiscal_year=fiscal_year,
            quarter=4,
            note="Q4 calculated from annual 10-K minus Q1-Q3 individual values - preserving raw SEC API metadata"
        )
        
        # Create Q4 ConceptValue
        q4_concept_value = ConceptValue(
            concept_id=concept_id,
            company_cik=company_cik,
            statement_type=annual_metadata["statement_type"],
            form_type="10-Q",
            filing_id=annual_metadata["filing_id"],
            reporting_period=q4_reporting_period,
            value=q4_value,
            created_at=datetime.utcnow(),
            dimension_value=annual_metadata.get("dimension_value", False),
            calculated=True,  # Mark as calculated
            fact_id=f"Q4_CALC_{annual_metadata['fact_id']}",
            decimals=annual_metadata.get("decimals", "-6"),
            dimensional_concept_id=annual_metadata.get("dimensional_concept_id")
        )
        
        return q4_concept_value

    def _create_q4_record_by_name(
        self, 
        concept_name: str,
        quarterly_concept_id: ObjectId,
        company_cik: str, 
        fiscal_year: int, 
        q4_value: float
    ) -> Optional[ConceptValue]:
        """Create a Q4 ConceptValue record based on annual filing metadata using concept name."""
        
        # Get annual filing metadata by concept name
        annual_metadata = self.repository.get_annual_filing_metadata_by_name(
            concept_name, company_cik, fiscal_year
        )
        
        if not annual_metadata:
            return None
        
        # Extract reporting period from annual data
        annual_period = annual_metadata["reporting_period"]
        
        # Create Q4 reporting period
        q4_reporting_period = ReportingPeriod(
            end_date=annual_period["end_date"],
            period_date=annual_period["period_date"],
            period_type="quarterly",
            form_type="10-Q",
            fiscal_year_end_code=annual_period["fiscal_year_end_code"],
            data_source="calculated_from_sec_api_raw",
            company_cik=company_cik,
            company_name=annual_period["company_name"],
            start_date=annual_period.get("start_date", annual_period["end_date"]),
            fiscal_year=fiscal_year,
            quarter=4,
            note="Q4 calculated from annual 10-K minus Q1-Q3 individual values - preserving raw SEC API metadata"
        )
        
        # Create Q4 ConceptValue using quarterly concept_id
        q4_concept_value = ConceptValue(
            concept_id=quarterly_concept_id,  # Use quarterly concept_id for consistency
            company_cik=company_cik,
            statement_type=annual_metadata["statement_type"],
            form_type="10-Q",
            filing_id=annual_metadata["filing_id"],
            reporting_period=q4_reporting_period,
            value=q4_value,
            created_at=datetime.utcnow(),
            dimension_value=annual_metadata.get("dimension_value", False),
            calculated=True,  # Mark as calculated
            fact_id=f"Q4_CALC_{annual_metadata.get('fact_id', str(annual_metadata['_id']))}",
            decimals=annual_metadata.get("decimals", "-6"),
            dimensional_concept_id=annual_metadata.get("dimensional_concept_id")
        )
        
        return q4_concept_value

    def _calculate_q4_for_concept_by_name(
        self, 
        concept_name: str,
        company_cik: str, 
        fiscal_year: int
    ) -> Dict[str, Any]:
        """Calculate Q4 for a specific concept by name, company, and fiscal year."""
        
        result = {"success": False, "reason": None}
        
        try:
            # Get quarterly data using concept name
            quarterly_data = self.repository.get_quarterly_data_for_concept_by_name(
                concept_name, company_cik, fiscal_year
            )
            
            # Check if concept was found
            if quarterly_data.concept_id is None:
                result["reason"] = "Concept not found in quarterly data"
                return result
            
            # Check if Q4 already exists
            if self.repository.check_q4_exists_by_name(concept_name, company_cik, fiscal_year):
                result["reason"] = "Q4 value already exists"
                return result
            
            # Check if we can calculate Q4
            if not quarterly_data.can_calculate_q4():
                missing_values = []
                if quarterly_data.q1_value is None:
                    missing_values.append("Q1")
                if quarterly_data.q2_value is None:
                    missing_values.append("Q2")
                if quarterly_data.q3_value is None:
                    missing_values.append("Q3")
                if quarterly_data.annual_value is None:
                    missing_values.append("Annual")
                
                result["reason"] = f"Missing values: {', '.join(missing_values)}"
                return result
            
            # Calculate Q4 value
            q4_value = quarterly_data.calculate_q4()
            
            # Create Q4 record
            q4_record = self._create_q4_record_by_name(
                concept_name, quarterly_data.concept_id, company_cik, fiscal_year, q4_value
            )
            
            if q4_record is None:
                result["reason"] = "Could not create Q4 record (missing annual filing metadata)"
                return result
            
            # Insert Q4 value
            if self.repository.insert_q4_value(q4_record):
                result["success"] = True
                print(f"✓ Calculated Q4 for {concept_name} FY{fiscal_year}: {q4_value:,.2f}")
            else:
                result["reason"] = "Failed to insert Q4 value into database"
        
        except Exception as e:
            result["reason"] = f"Calculation error: {str(e)}"
        
        return result

    def _calculate_q4_for_concept_by_name_and_path(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int
    ) -> Dict[str, Any]:
        """Calculate Q4 for a specific concept by name and path, company, and fiscal year.
        Uses parent concept matching to ensure consistency between quarterly and annual filings."""
        
        result = {"success": False, "reason": None}
        
        try:
            # Get quarterly data using enhanced parent concept matching
            quarterly_data = self.repository.get_quarterly_data_for_concept_by_name_and_path(
                concept_name, concept_path, company_cik, fiscal_year
            )
            
            # Check if concept was found
            if quarterly_data.concept_id is None:
                result["reason"] = "Concept not found in quarterly data"
                return result
            
            # Check if Q4 already exists
            if self.repository.check_q4_exists_by_name_and_path(concept_name, concept_path, company_cik, fiscal_year):
                result["reason"] = "Q4 value already exists"
                return result
            
            # Check if we can calculate Q4
            if not quarterly_data.can_calculate_q4():
                missing_values = []
                if quarterly_data.q1_value is None:
                    missing_values.append("Q1")
                if quarterly_data.q2_value is None:
                    missing_values.append("Q2")
                if quarterly_data.q3_value is None:
                    missing_values.append("Q3")
                if quarterly_data.annual_value is None:
                    missing_values.append("Annual")
                
                result["reason"] = f"Missing values: {', '.join(missing_values)}"
                return result
            
            # Calculate Q4 value
            q4_value = quarterly_data.calculate_q4()
            
            # Create Q4 record using enhanced parent concept matching
            q4_record = self._create_q4_record_by_name_and_path_with_parent_matching(
                concept_name, concept_path, quarterly_data.concept_id, company_cik, fiscal_year, q4_value
            )
            
            if q4_record is None:
                result["reason"] = "Could not create Q4 record (missing annual filing metadata or parent concept mismatch)"
                return result
            
            # Insert Q4 value
            if self.repository.insert_q4_value(q4_record):
                result["success"] = True
                print(f"✓ Calculated Q4 for {concept_name} (Path: {concept_path}) FY{fiscal_year}: {q4_value:,.2f}")
            else:
                result["reason"] = "Failed to insert Q4 value into database"
        
        except Exception as e:
            result["reason"] = f"Calculation error: {str(e)}"
        
        return result

    def _create_q4_record_by_name_and_path(
        self, 
        concept_name: str,
        concept_path: str,
        quarterly_concept_id: ObjectId,
        company_cik: str, 
        fiscal_year: int, 
        q4_value: float
    ) -> Optional[ConceptValue]:
        """Create a Q4 ConceptValue record based on annual filing metadata using concept name and path."""
        
        # Get annual filing metadata by concept name and path
        annual_metadata = self.repository.get_annual_filing_metadata_by_name_and_path(
            concept_name, concept_path, company_cik, fiscal_year
        )
        
        if not annual_metadata:
            return None
        
        # Extract reporting period from annual data
        annual_period = annual_metadata["reporting_period"]
        
        # Create Q4 reporting period
        q4_reporting_period = ReportingPeriod(
            end_date=annual_period["end_date"],
            period_date=annual_period["period_date"],
            period_type="quarterly",
            form_type="10-Q",
            fiscal_year_end_code=annual_period["fiscal_year_end_code"],
            data_source="calculated_from_sec_api_raw",
            company_cik=company_cik,
            company_name=annual_period["company_name"],
            start_date=annual_period.get("start_date", annual_period["end_date"]),
            fiscal_year=fiscal_year,
            quarter=4,
            note="Q4 calculated from annual 10-K minus Q1-Q3 individual values - preserving raw SEC API metadata"
        )
        
        # Create Q4 ConceptValue using quarterly concept_id
        q4_concept_value = ConceptValue(
            concept_id=quarterly_concept_id,  # Use quarterly concept_id for consistency
            company_cik=company_cik,
            statement_type=annual_metadata["statement_type"],
            form_type="10-Q",
            filing_id=annual_metadata["filing_id"],
            reporting_period=q4_reporting_period,
            value=q4_value,
            created_at=datetime.utcnow(),
            dimension_value=annual_metadata.get("dimension_value", False),
            calculated=True,  # Mark as calculated
            fact_id=f"Q4_CALC_{annual_metadata.get('fact_id', str(annual_metadata['_id']))}",
            decimals=annual_metadata.get("decimals", "-6"),
            dimensional_concept_id=annual_metadata.get("dimensional_concept_id")
        )
        
        return q4_concept_value

    def _create_q4_record_by_name_and_path_with_parent_matching(
        self, 
        concept_name: str,
        concept_path: str,
        quarterly_concept_id: ObjectId,
        company_cik: str, 
        fiscal_year: int, 
        q4_value: float
    ) -> Optional[ConceptValue]:
        """Create a Q4 ConceptValue record using enhanced parent concept matching between quarterly and annual filings."""
        
        # Get annual filing metadata using enhanced parent concept matching
        annual_metadata = self.repository.get_annual_filing_metadata_by_name_and_path(
            concept_name, concept_path, company_cik, fiscal_year
        )
        
        if not annual_metadata:
            # Try alternative matching using parent concept lookup
            quarterly_parent_name = self.repository.get_parent_concept_name(quarterly_concept_id, "normalized_concepts_quarterly")
            if quarterly_parent_name:
                # Look for annual concept by parent concept name
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
        
        # Extract reporting period from annual data
        annual_period = annual_metadata["reporting_period"]
        
        # Create Q4 reporting period
        q4_reporting_period = ReportingPeriod(
            end_date=annual_period["end_date"],
            period_date=annual_period["period_date"],
            period_type="quarterly",
            form_type="10-Q",
            fiscal_year_end_code=annual_period["fiscal_year_end_code"],
            data_source="calculated_from_sec_api_raw_with_parent_matching",
            company_cik=company_cik,
            company_name=annual_period["company_name"],
            start_date=annual_period.get("start_date", annual_period["end_date"]),
            fiscal_year=fiscal_year,
            quarter=4,
            note="Q4 calculated from annual 10-K minus Q1-Q3 individual values - using parent concept matching for dimensional consistency"
        )
        
        # Create Q4 ConceptValue using quarterly concept_id
        q4_concept_value = ConceptValue(
            concept_id=quarterly_concept_id,  # Use quarterly concept_id for consistency
            company_cik=company_cik,
            statement_type=annual_metadata["statement_type"],
            form_type="10-Q",
            filing_id=annual_metadata["filing_id"],
            reporting_period=q4_reporting_period,
            value=q4_value,
            created_at=datetime.utcnow(),
            dimension_value=annual_metadata.get("dimension_value", False),
            calculated=True,  # Mark as calculated
            fact_id=f"Q4_CALC_PARENT_MATCH_{annual_metadata.get('fact_id', str(annual_metadata['_id']))}",
            decimals=annual_metadata.get("decimals", "-6"),
            dimensional_concept_id=annual_metadata.get("dimensional_concept_id")
        )
        
        return q4_concept_value
