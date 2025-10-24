"""Data repository for financial data operations - Refactored with DRY principles."""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

try:
    from bson import ObjectId
    from pymongo.database import Database
    from pymongo.collection import Collection
except ImportError:
    print("PyMongo not installed. Please run: pip install pymongo")
    raise

from models.financial_data import QuarterlyData, ConceptValue, ReportingPeriod


class FinancialDataRepository:
    """Repository for financial data operations."""
    
    def __init__(self, database: Database):
        self.db = database
        self.concept_values_quarterly: Collection = database["concept_values_quarterly"]
        self.concept_values_annual: Collection = database["concept_values_annual"]
        self.normalized_concepts_quarterly: Collection = database["normalized_concepts_quarterly"]
        self.normalized_concepts_annual: Collection = database["normalized_concepts_annual"]
    
    # ==================== HELPER METHODS ====================
    
    def _find_quarterly_concept(
        self,
        company_cik: str,
        statement_type: str,
        concept_name: Optional[str] = None,
        concept_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Find a quarterly concept by name and/or path."""
        query = {
            "company_cik": company_cik,
            "statement_type": statement_type
        }
        if concept_name:
            query["concept"] = concept_name
        if concept_path:
            query["path"] = concept_path
        
        return self.normalized_concepts_quarterly.find_one(query)
    
    def _get_parent_concept_info(
        self,
        concept: Dict[str, Any],
        collection_name: str = "normalized_concepts_quarterly"
    ) -> Tuple[Optional[ObjectId], Optional[str]]:
        """Get parent concept ID and name for a given concept.
        
        Returns:
            Tuple of (parent_concept_id, parent_concept_name)
        """
        collection = getattr(self.db, collection_name)
        parent_concept_id = concept.get("concept_id")
        
        if parent_concept_id:
            # This is a dimensional concept
            parent_concept = collection.find_one({"_id": parent_concept_id})
            parent_concept_name = parent_concept.get("concept") if parent_concept else None
        else:
            # This is a root concept
            parent_concept_name = concept.get("concept")
        
        return parent_concept_id, parent_concept_name
    
    def _find_matching_annual_concept(
        self,
        concept_name: str,
        company_cik: str,
        statement_type: str,
        quarterly_parent_concept_id: Optional[ObjectId] = None,
        quarterly_parent_concept_name: Optional[str] = None,
        quarterly_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Find matching annual concept using parent concept matching logic.
        
        Priority order:
        1. Exact match by concept name AND path (for precise dimensional matching)
        2. Exact match by concept name only (for root concepts or single dimensional instance)
        3. Parent concept match (fallback for dimensional concepts without own annual value)
        """
        
        if not quarterly_parent_concept_name:
            return None
        
        # PRIORITY 1: Try to find exact match by concept name AND path
        # This ensures we get the correct dimensional breakdown when multiple paths exist
        if quarterly_path:
            exact_match_with_path = self.normalized_concepts_annual.find_one({
                "concept": concept_name,
                "path": quarterly_path,
                "company_cik": company_cik,
                "statement_type": statement_type
            })
            
            if exact_match_with_path:
                return exact_match_with_path
        
        # PRIORITY 2: Try to find exact match by concept name only
        # This works for root concepts and dimensional concepts with single instance
        exact_match = self.normalized_concepts_annual.find_one({
            "concept": concept_name,
            "company_cik": company_cik,
            "statement_type": statement_type
        })
        
        if exact_match:
            return exact_match
        
        # PRIORITY 2: If no exact match and this is a dimensional concept, try to find by parent relationship
        if quarterly_parent_concept_id:
            # Try to find dimensional concept with same parent
            annual_dimensional_concepts = list(self.normalized_concepts_annual.find({
                "concept": concept_name,
                "company_cik": company_cik,
                "statement_type": statement_type,
                "dimension_concept": True
            }))
            
            # Find the one with the same parent concept
            for dim_concept in annual_dimensional_concepts:
                annual_parent_id = dim_concept.get("concept_id")
                if annual_parent_id:
                    annual_parent = self.normalized_concepts_annual.find_one({"_id": annual_parent_id})
                    if annual_parent and annual_parent.get("concept") == quarterly_parent_concept_name:
                        return dim_concept
        
        # PRIORITY 3: Fallback to parent concept (will be filtered out later if dimensional)
        parent_concept = self.normalized_concepts_annual.find_one({
            "concept": quarterly_parent_concept_name,
            "company_cik": company_cik,
            "statement_type": statement_type
        })
        
        return parent_concept
    
    def _map_quarterly_values(self, quarterly_data: QuarterlyData, values: List[Dict]) -> None:
        """Map quarterly values (Q1, Q2, Q3) to QuarterlyData object."""
        for q_value in values:
            quarter = q_value["reporting_period"]["quarter"]
            value = q_value["value"]
            
            if quarter == 1:
                quarterly_data.q1_value = value
            elif quarter == 2:
                quarterly_data.q2_value = value
            elif quarter == 3:
                quarterly_data.q3_value = value
    
    # ==================== CONCEPT RETRIEVAL ====================
    
    def get_statement_concepts(self, company_cik: str, statement_type: str) -> List[Dict[str, Any]]:
        """Get all concepts for a company by statement type."""
        return list(self.normalized_concepts_quarterly.find({
            "company_cik": company_cik,
            "statement_type": statement_type,
            "abstract": False
        }, {
            "_id": 1,
            "concept": 1,
            "path": 1,
            "order_key": 1,
            "label": 1,
            "dimension_concept": 1,
            "concept_name": 1,
            "dimensions": 1
        }))
    
    def get_income_statement_concepts(self, company_cik: str) -> List[Dict[str, Any]]:
        """Get all income statement concepts for a company."""
        return self.get_statement_concepts(company_cik, "income_statement")
    
    def get_cash_flow_concepts(self, company_cik: str) -> List[Dict[str, Any]]:
        """Get all cash flow concepts for a company."""
        return self.get_statement_concepts(company_cik, "cash_flows")
    
    # ==================== QUARTERLY DATA RETRIEVAL ====================
    
    def get_quarterly_data_for_concept_by_name_and_path(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int,
        statement_type: str = "income_statement"
    ) -> QuarterlyData:
        """Get quarterly data for a specific concept by name and path.
        
        This is the unified method that handles all quarterly data retrieval.
        """
        
        # Find quarterly concept
        quarterly_concept = self._find_quarterly_concept(
            company_cik, statement_type, concept_name, concept_path
        )
        
        if not quarterly_concept:
            return QuarterlyData(
                concept_id=None,
                company_cik=company_cik,
                fiscal_year=fiscal_year
            )
        
        quarterly_concept_id = quarterly_concept["_id"]
        
        # Get parent concept information
        quarterly_parent_id, quarterly_parent_name = self._get_parent_concept_info(
            quarterly_concept, "normalized_concepts_quarterly"
        )
        
        # Find matching annual concept (pass concept_path for precise matching)
        annual_concept = self._find_matching_annual_concept(
            concept_name, company_cik, statement_type,
            quarterly_parent_id, quarterly_parent_name, concept_path
        )
        
        # Get quarterly values (Q1, Q2, Q3)
        quarterly_values = list(self.concept_values_quarterly.find({
            "concept_id": quarterly_concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": {"$in": [1, 2, 3]}
        }))
        
        # Get annual value if annual concept found
        annual_values = []
        if annual_concept:
            # For dimensional concepts, only use annual value if it's an exact match (same concept name)
            # Don't use parent's annual value as it would give incorrect Q4 calculations
            is_dimensional = quarterly_concept.get("dimension_concept", False)
            is_exact_match = annual_concept.get("concept") == concept_name
            
            if not is_dimensional or is_exact_match:
                annual_values = list(self.concept_values_annual.find({
                    "concept_id": annual_concept["_id"],
                    "company_cik": company_cik,
                    "reporting_period.fiscal_year": fiscal_year
                }))
        
        # Initialize and populate quarterly data
        quarterly_data = QuarterlyData(
            concept_id=quarterly_concept_id,
            company_cik=company_cik,
            fiscal_year=fiscal_year
        )
        
        self._map_quarterly_values(quarterly_data, quarterly_values)
        
        if annual_values:
            quarterly_data.annual_value = annual_values[0]["value"]
        
        return quarterly_data
    
    # Compatibility aliases for existing code
    def get_quarterly_data_for_concept(
        self, 
        concept_id: ObjectId, 
        company_cik: str, 
        fiscal_year: int
    ) -> QuarterlyData:
        """Legacy method - Get quarterly data by concept_id."""
        # Get concept to find name and path
        concept = self.normalized_concepts_quarterly.find_one({"_id": concept_id})
        if not concept:
            return QuarterlyData(concept_id=None, company_cik=company_cik, fiscal_year=fiscal_year)
        
        return self.get_quarterly_data_for_concept_by_name_and_path(
            concept["concept"],
            concept.get("path", ""),
            company_cik,
            fiscal_year,
            concept.get("statement_type", "income_statement")
        )
    
    def get_quarterly_data_for_concept_by_name(
        self, 
        concept_name: str,
        company_cik: str, 
        fiscal_year: int
    ) -> QuarterlyData:
        """Legacy method - Get quarterly data by name only (assumes income statement)."""
        return self.get_quarterly_data_for_concept_by_name_and_path(
            concept_name, "", company_cik, fiscal_year, "income_statement"
        )
    
    def get_quarterly_data_for_concept_by_name_and_path_generic(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int,
        statement_type: str
    ) -> QuarterlyData:
        """Alias for main method - maintained for compatibility."""
        return self.get_quarterly_data_for_concept_by_name_and_path(
            concept_name, concept_path, company_cik, fiscal_year, statement_type
        )
    
    # ==================== Q4 EXISTENCE CHECKS ====================
    
    def check_q4_exists_by_name_and_path(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int,
        statement_type: str = "income_statement"
    ) -> bool:
        """Check if Q4 value already exists for the given concept.
        
        This is the unified method for Q4 existence checks.
        """
        quarterly_concept = self._find_quarterly_concept(
            company_cik, statement_type, concept_name, concept_path
        )
        
        if not quarterly_concept:
            return False
        
        existing_q4 = self.concept_values_quarterly.find_one({
            "concept_id": quarterly_concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": 4
        })
        return existing_q4 is not None
    
    # Compatibility aliases
    def check_q4_exists(
        self, 
        concept_id: ObjectId, 
        company_cik: str, 
        fiscal_year: int
    ) -> bool:
        """Legacy method - Check Q4 exists by concept_id."""
        existing_q4 = self.concept_values_quarterly.find_one({
            "concept_id": concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": 4
        })
        return existing_q4 is not None
    
    def check_q4_exists_by_name(
        self, 
        concept_name: str,
        company_cik: str, 
        fiscal_year: int
    ) -> bool:
        """Legacy method - Check Q4 exists by name only."""
        return self.check_q4_exists_by_name_and_path(
            concept_name, "", company_cik, fiscal_year, "income_statement"
        )
    
    def check_q4_exists_by_name_and_path_generic(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int,
        statement_type: str
    ) -> bool:
        """Alias for main method - maintained for compatibility."""
        return self.check_q4_exists_by_name_and_path(
            concept_name, concept_path, company_cik, fiscal_year, statement_type
        )
    
    # ==================== ANNUAL FILING METADATA ====================
    
    def get_annual_filing_metadata_by_name_and_path(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int,
        statement_type: str = "income_statement"
    ) -> Optional[Dict[str, Any]]:
        """Get annual filing metadata by concept name and path.
        
        This is the unified method for retrieving annual filing metadata.
        """
        # Find quarterly concept
        quarterly_concept = self._find_quarterly_concept(
            company_cik, statement_type, concept_name, concept_path
        )
        
        if not quarterly_concept:
            return None
        
        # Get parent concept information
        quarterly_parent_id, quarterly_parent_name = self._get_parent_concept_info(
            quarterly_concept, "normalized_concepts_quarterly"
        )
        
        # Find matching annual concept
        annual_concept = self._find_matching_annual_concept(
            concept_name, company_cik, statement_type,
            quarterly_parent_id, quarterly_parent_name
        )
        
        if not annual_concept:
            return None
        
        # Get annual record
        annual_record = self.concept_values_annual.find_one({
            "concept_id": annual_concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year
        })
        return annual_record
    
    # Compatibility aliases
    def get_annual_filing_metadata(
        self, 
        concept_id: ObjectId, 
        company_cik: str, 
        fiscal_year: int
    ) -> Optional[Dict[str, Any]]:
        """Legacy method - Get annual metadata by concept_id."""
        annual_record = self.concept_values_annual.find_one({
            "concept_id": concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year
        })
        return annual_record
    
    def get_annual_filing_metadata_by_name(
        self, 
        concept_name: str,
        company_cik: str, 
        fiscal_year: int
    ) -> Optional[Dict[str, Any]]:
        """Legacy method - Get annual metadata by name only."""
        return self.get_annual_filing_metadata_by_name_and_path(
            concept_name, "", company_cik, fiscal_year, "income_statement"
        )
    
    def get_annual_filing_metadata_by_name_and_path_generic(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int,
        statement_type: str
    ) -> Optional[Dict[str, Any]]:
        """Alias for main method - maintained for compatibility."""
        return self.get_annual_filing_metadata_by_name_and_path(
            concept_name, concept_path, company_cik, fiscal_year, statement_type
        )
    
    # ==================== UTILITY METHODS ====================
    
    def get_parent_concept_name(
        self, 
        concept_id: ObjectId, 
        collection_name: str = "normalized_concepts_quarterly"
    ) -> Optional[str]:
        """Get the parent concept name for a given concept."""
        collection = getattr(self.db, collection_name)
        concept = collection.find_one({"_id": concept_id})
        
        if not concept:
            return None
        
        _, parent_name = self._get_parent_concept_info(concept, collection_name)
        return parent_name
    
    def find_matching_concept_by_parent(
        self,
        concept_name: str,
        source_concept_id: ObjectId,
        target_collection: str,
        company_cik: str
    ) -> Optional[Dict[str, Any]]:
        """Find a matching concept in target collection based on parent concept relationship."""
        source_collection_name = "normalized_concepts_quarterly" if target_collection == "normalized_concepts_annual" else "normalized_concepts_quarterly"
        source_collection = getattr(self.db, source_collection_name)
        target_collection_obj = getattr(self.db, target_collection)
        
        # Get the source concept
        source_concept = source_collection.find_one({"_id": source_concept_id})
        if not source_concept:
            return None
        
        # Get parent concept name
        parent_concept_name = self.get_parent_concept_name(source_concept_id, source_collection_name)
        if not parent_concept_name:
            return None
        
        # First try to find by exact concept name match
        target_concept = target_collection_obj.find_one({
            "concept": concept_name,
            "company_cik": company_cik,
            "statement_type": "income_statement"
        })
        
        if target_concept:
            return target_concept
        
        # If source is dimensional, look for dimensional concepts in target with same parent
        if source_concept.get("dimension_concept"):
            dimensional_concepts = list(target_collection_obj.find({
                "concept": concept_name,
                "company_cik": company_cik,
                "statement_type": "income_statement",
                "dimension_concept": True
            }))
            
            for dim_concept in dimensional_concepts:
                target_parent_name = self.get_parent_concept_name(dim_concept["_id"], target_collection)
                if target_parent_name == parent_concept_name:
                    return dim_concept
        
        return None
    
    def insert_q4_value(self, q4_value: ConceptValue) -> bool:
        """Insert calculated Q4 value into the database."""
        try:
            q4_dict = self._concept_value_to_dict(q4_value)
            result = self.concept_values_quarterly.insert_one(q4_dict)
            return result.inserted_id is not None
        except Exception as e:
            print(f"Error inserting Q4 value: {e}")
            return False
    
    def delete_all_q4_values(self, company_cik: Optional[str] = None) -> int:
        """Delete all Q4 values for income statement and cash flow statements.
        
        Args:
            company_cik: If provided, deletes Q4 values for specific company only.
                        If None, deletes Q4 values for all companies.
        
        Returns:
            Number of deleted Q4 records.
        """
        query = {
            "reporting_period.quarter": 4,
            "statement_type": {"$in": ["income_statement", "cash_flow_statement"]}
        }
        
        if company_cik:
            query["company_cik"] = company_cik
        
        try:
            result = self.concept_values_quarterly.delete_many(query)
            return result.deleted_count
        except Exception as e:
            print(f"Error deleting Q4 values: {e}")
            return 0
    
    def get_fiscal_years_for_company(self, company_cik: str) -> List[int]:
        """Get all fiscal years available for a company."""
        pipeline = [
            {"$match": {"company_cik": company_cik}},
            {"$group": {"_id": "$reporting_period.fiscal_year"}},
            {"$sort": {"_id": 1}}
        ]
        
        result = list(self.concept_values_annual.aggregate(pipeline))
        return [item["_id"] for item in result if item["_id"] is not None]
    
    def _concept_value_to_dict(self, concept_value: ConceptValue) -> Dict[str, Any]:
        """Convert ConceptValue dataclass to dictionary for MongoDB insertion."""
        reporting_period_dict = {
            "end_date": concept_value.reporting_period.end_date,
            "period_date": concept_value.reporting_period.period_date,
            "form_type": concept_value.reporting_period.form_type,
            "fiscal_year_end_code": concept_value.reporting_period.fiscal_year_end_code,
            "data_source": concept_value.reporting_period.data_source,
            "company_cik": concept_value.reporting_period.company_cik,
            "company_name": concept_value.reporting_period.company_name,
            "fiscal_year": concept_value.reporting_period.fiscal_year,
            "quarter": concept_value.reporting_period.quarter,
            "accession_number": concept_value.reporting_period.accession_number
        }
        
        # Add optional reporting period fields if they exist
        optional_fields = ["period_type", "start_date", "context_id", "item_period", "unit", "note"]
        for field in optional_fields:
            value = getattr(concept_value.reporting_period, field, None)
            if value is not None:
                reporting_period_dict[field] = value
        
        result = {
            "concept_id": concept_value.concept_id,
            "company_cik": concept_value.company_cik,
            "statement_type": concept_value.statement_type,
            "form_type": concept_value.form_type,
            "reporting_period": reporting_period_dict,
            "value": concept_value.value,
            "created_at": concept_value.created_at,
            "dimension_value": concept_value.dimension_value,
            "calculated": concept_value.calculated
        }
        
        # Add optional dimensional_concept_id if it exists
        if concept_value.dimensional_concept_id is not None:
            result["dimensional_concept_id"] = concept_value.dimensional_concept_id
        
        return result
