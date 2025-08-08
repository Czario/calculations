"""Data repository for financial data operations."""

from typing import List, Dict, Optional, Any
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
    
    def get_income_statement_concepts(self, company_cik: str) -> List[Dict[str, Any]]:
        """Get all income statement concepts for a company, including dimensional concepts."""
        return list(self.normalized_concepts_quarterly.find({
            "company_cik": company_cik,
            "statement_type": "income_statement",
            "abstract": False  # Only exclude abstract concepts, include both dimensional and non-dimensional
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
    
    def get_quarterly_data_for_concept(
        self, 
        concept_id: ObjectId, 
        company_cik: str, 
        fiscal_year: int
    ) -> QuarterlyData:
        """Get quarterly data for a specific concept, company, and fiscal year."""
        
        # Get quarterly values (Q1, Q2, Q3)
        quarterly_values = list(self.concept_values_quarterly.find({
            "concept_id": concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": {"$in": [1, 2, 3]}
        }))
        
        # Get annual value
        annual_values = list(self.concept_values_annual.find({
            "concept_id": concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year
        }))
        
        # Initialize quarterly data
        quarterly_data = QuarterlyData(
            concept_id=concept_id,
            company_cik=company_cik,
            fiscal_year=fiscal_year
        )
        
        # Map quarterly values
        for q_value in quarterly_values:
            quarter = q_value["reporting_period"]["quarter"]
            value = q_value["value"]
            
            if quarter == 1:
                quarterly_data.q1_value = value
            elif quarter == 2:
                quarterly_data.q2_value = value
            elif quarter == 3:
                quarterly_data.q3_value = value
        
        # Set annual value
        if annual_values:
            quarterly_data.annual_value = annual_values[0]["value"]
        
        return quarterly_data

    def get_quarterly_data_for_concept_by_name(
        self, 
        concept_name: str,
        company_cik: str, 
        fiscal_year: int
    ) -> QuarterlyData:
        """Get quarterly data for a specific concept by name, company, and fiscal year."""
        
        # Get the quarterly concept for this concept name
        quarterly_concept = self.normalized_concepts_quarterly.find_one({
            "concept": concept_name,
            "company_cik": company_cik,
            "statement_type": "income_statement"
        })
        
        if not quarterly_concept:
            return QuarterlyData(
                concept_id=None,
                company_cik=company_cik,
                fiscal_year=fiscal_year
            )
        
        quarterly_concept_id = quarterly_concept["_id"]
        
        # Find the parent concept if this is a dimensional concept
        quarterly_parent_concept_id = quarterly_concept.get("concept_id")
        if quarterly_parent_concept_id:
            # This is a dimensional concept, use parent concept for matching
            quarterly_parent_concept = self.normalized_concepts_quarterly.find_one({
                "_id": quarterly_parent_concept_id
            })
            quarterly_parent_concept_name = quarterly_parent_concept.get("concept") if quarterly_parent_concept else None
        else:
            # This is a regular concept
            quarterly_parent_concept_name = concept_name
        
        # Find the matching annual concept using parent concept name
        annual_concept = None
        if quarterly_parent_concept_name:
            # Try to find annual concept by parent concept name first
            annual_concept = self.db["normalized_concepts_annual"].find_one({
                "concept": quarterly_parent_concept_name,
                "company_cik": company_cik,
                "statement_type": "income_statement"
            })
            
            # If not found and this is a dimensional concept, try to find by concept and dimensional relationship
            if not annual_concept and quarterly_parent_concept_id:
                # Look for dimensional concepts in annual that match the parent
                annual_dimensional_concepts = list(self.db["normalized_concepts_annual"].find({
                    "concept": concept_name,
                    "company_cik": company_cik,
                    "statement_type": "income_statement",
                    "dimension_concept": True
                }))
                
                # Find the one that has the same parent concept
                for dim_concept in annual_dimensional_concepts:
                    annual_parent_id = dim_concept.get("concept_id")
                    if annual_parent_id:
                        annual_parent = self.db["normalized_concepts_annual"].find_one({"_id": annual_parent_id})
                        if annual_parent and annual_parent.get("concept") == quarterly_parent_concept_name:
                            annual_concept = dim_concept
                            break
        
        # If still not found, fallback to original method
        if not annual_concept:
            annual_concept = self.db["normalized_concepts_annual"].find_one({
                "concept": concept_name,
                "company_cik": company_cik,
                "statement_type": "income_statement"
            })
        
        # Get quarterly values (Q1, Q2, Q3)
        quarterly_values = list(self.concept_values_quarterly.find({
            "concept_id": quarterly_concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": {"$in": [1, 2, 3]}
        }))
        
        # Get annual value using annual concept_id if available
        annual_values = []
        if annual_concept:
            annual_concept_id = annual_concept["_id"]
            annual_values = list(self.concept_values_annual.find({
                "concept_id": annual_concept_id,
                "company_cik": company_cik,
                "reporting_period.fiscal_year": fiscal_year
            }))
        
        # Initialize quarterly data
        quarterly_data = QuarterlyData(
            concept_id=quarterly_concept_id,
            company_cik=company_cik,
            fiscal_year=fiscal_year
        )
        
        # Map quarterly values
        for q_value in quarterly_values:
            quarter = q_value["reporting_period"]["quarter"]
            value = q_value["value"]
            
            if quarter == 1:
                quarterly_data.q1_value = value
            elif quarter == 2:
                quarterly_data.q2_value = value
            elif quarter == 3:
                quarterly_data.q3_value = value
        
        # Set annual value
        if annual_values:
            quarterly_data.annual_value = annual_values[0]["value"]
        
        return quarterly_data

    def get_quarterly_data_for_concept_by_name_and_path(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int
    ) -> QuarterlyData:
        """Get quarterly data for a specific concept by name and path, company, and fiscal year."""
        
        # Get the quarterly concept for this concept name and path
        quarterly_concept = self.normalized_concepts_quarterly.find_one({
            "concept": concept_name,
            "path": concept_path,
            "company_cik": company_cik,
            "statement_type": "income_statement"
        })
        
        if not quarterly_concept:
            return QuarterlyData(
                concept_id=None,
                company_cik=company_cik,
                fiscal_year=fiscal_year
            )
        
        quarterly_concept_id = quarterly_concept["_id"]
        
        # Find the parent concept if this is a dimensional concept
        quarterly_parent_concept_id = quarterly_concept.get("concept_id")
        if quarterly_parent_concept_id:
            # This is a dimensional concept, use parent concept for matching
            quarterly_parent_concept = self.normalized_concepts_quarterly.find_one({
                "_id": quarterly_parent_concept_id
            })
            quarterly_parent_concept_name = quarterly_parent_concept.get("concept") if quarterly_parent_concept else None
        else:
            # This is a regular concept
            quarterly_parent_concept_name = concept_name
        
        # Find the matching annual concept using parent concept name
        annual_concept = None
        if quarterly_parent_concept_name:
            # Try to find annual concept by parent concept name first
            annual_concept = self.db["normalized_concepts_annual"].find_one({
                "concept": quarterly_parent_concept_name,
                "company_cik": company_cik,
                "statement_type": "income_statement"
            })
            
            # If not found and this is a dimensional concept, try to find by concept and dimensional relationship
            if not annual_concept and quarterly_parent_concept_id:
                # Look for dimensional concepts in annual that match the parent
                annual_dimensional_concepts = list(self.db["normalized_concepts_annual"].find({
                    "concept": concept_name,
                    "company_cik": company_cik,
                    "statement_type": "income_statement",
                    "dimension_concept": True
                }))
                
                # Find the one that has the same parent concept
                for dim_concept in annual_dimensional_concepts:
                    annual_parent_id = dim_concept.get("concept_id")
                    if annual_parent_id:
                        annual_parent = self.db["normalized_concepts_annual"].find_one({"_id": annual_parent_id})
                        if annual_parent and annual_parent.get("concept") == quarterly_parent_concept_name:
                            annual_concept = dim_concept
                            break
        
        # If still not found, fallback to original method
        if not annual_concept:
            annual_concept = self.db["normalized_concepts_annual"].find_one({
                "concept": concept_name,
                "path": concept_path,
                "company_cik": company_cik,
                "statement_type": "income_statement"
            })
        
        # Get quarterly values (Q1, Q2, Q3)
        quarterly_values = list(self.concept_values_quarterly.find({
            "concept_id": quarterly_concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": {"$in": [1, 2, 3]}
        }))
        
        # Get annual value using annual concept_id if available
        annual_values = []
        if annual_concept:
            annual_concept_id = annual_concept["_id"]
            annual_values = list(self.concept_values_annual.find({
                "concept_id": annual_concept_id,
                "company_cik": company_cik,
                "reporting_period.fiscal_year": fiscal_year
            }))
        
        # Initialize quarterly data
        quarterly_data = QuarterlyData(
            concept_id=quarterly_concept_id,
            company_cik=company_cik,
            fiscal_year=fiscal_year
        )
        
        # Map quarterly values
        for q_value in quarterly_values:
            quarter = q_value["reporting_period"]["quarter"]
            value = q_value["value"]
            
            if quarter == 1:
                quarterly_data.q1_value = value
            elif quarter == 2:
                quarterly_data.q2_value = value
            elif quarter == 3:
                quarterly_data.q3_value = value
        
        # Set annual value
        if annual_values:
            quarterly_data.annual_value = annual_values[0]["value"]
        
        return quarterly_data
    
    def check_q4_exists(
        self, 
        concept_id: ObjectId, 
        company_cik: str, 
        fiscal_year: int
    ) -> bool:
        """Check if Q4 value already exists for the given parameters."""
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
        """Check if Q4 value already exists for the given concept name."""
        # Get the quarterly concept_id for this concept name
        quarterly_concept = self.normalized_concepts_quarterly.find_one({
            "concept": concept_name,
            "company_cik": company_cik,
            "statement_type": "income_statement"
        })
        
        if not quarterly_concept:
            return False
            
        quarterly_concept_id = quarterly_concept["_id"]
        
        existing_q4 = self.concept_values_quarterly.find_one({
            "concept_id": quarterly_concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": 4
        })
        return existing_q4 is not None

    def check_q4_exists_by_name_and_path(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int
    ) -> bool:
        """Check if Q4 value already exists for the given concept name and path."""
        # Get the quarterly concept_id for this concept name and path
        quarterly_concept = self.normalized_concepts_quarterly.find_one({
            "concept": concept_name,
            "path": concept_path,
            "company_cik": company_cik,
            "statement_type": "income_statement"
        })
        
        if not quarterly_concept:
            return False
            
        quarterly_concept_id = quarterly_concept["_id"]
        
        existing_q4 = self.concept_values_quarterly.find_one({
            "concept_id": quarterly_concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": 4
        })
        return existing_q4 is not None
    
    def get_annual_filing_metadata(
        self, 
        concept_id: ObjectId, 
        company_cik: str, 
        fiscal_year: int
    ) -> Optional[Dict[str, Any]]:
        """Get annual filing metadata for creating Q4 records."""
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
        """Get annual filing metadata by concept name for creating Q4 records."""
        # First get the quarterly concept for this concept name
        quarterly_concept = self.normalized_concepts_quarterly.find_one({
            "concept": concept_name,
            "company_cik": company_cik,
            "statement_type": "income_statement"
        })
        
        if not quarterly_concept:
            return None
        
        # Find the parent concept if this is a dimensional concept
        quarterly_parent_concept_id = quarterly_concept.get("concept_id")
        if quarterly_parent_concept_id:
            # This is a dimensional concept, use parent concept for matching
            quarterly_parent_concept = self.normalized_concepts_quarterly.find_one({
                "_id": quarterly_parent_concept_id
            })
            quarterly_parent_concept_name = quarterly_parent_concept.get("concept") if quarterly_parent_concept else None
        else:
            # This is a regular concept
            quarterly_parent_concept_name = concept_name
        
        # Find the matching annual concept using parent concept name
        annual_concept = None
        if quarterly_parent_concept_name:
            # Try to find annual concept by parent concept name first
            annual_concept = self.normalized_concepts_annual.find_one({
                "concept": quarterly_parent_concept_name,
                "company_cik": company_cik,
                "statement_type": "income_statement"
            })
            
            # If not found and this is a dimensional concept, try to find by concept and dimensional relationship
            if not annual_concept and quarterly_parent_concept_id:
                # Look for dimensional concepts in annual that match the parent
                annual_dimensional_concepts = list(self.normalized_concepts_annual.find({
                    "concept": concept_name,
                    "company_cik": company_cik,
                    "statement_type": "income_statement",
                    "dimension_concept": True
                }))
                
                # Find the one that has the same parent concept
                for dim_concept in annual_dimensional_concepts:
                    annual_parent_id = dim_concept.get("concept_id")
                    if annual_parent_id:
                        annual_parent = self.normalized_concepts_annual.find_one({"_id": annual_parent_id})
                        if annual_parent and annual_parent.get("concept") == quarterly_parent_concept_name:
                            annual_concept = dim_concept
                            break
        
        # If still not found, fallback to original method
        if not annual_concept:
            annual_concept = self.normalized_concepts_annual.find_one({
                "concept": concept_name,
                "company_cik": company_cik,
                "statement_type": "income_statement"
            })
        
        if not annual_concept:
            return None
            
        annual_concept_id = annual_concept["_id"]
        
        annual_record = self.concept_values_annual.find_one({
            "concept_id": annual_concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year
        })
        return annual_record

    def get_annual_filing_metadata_by_name_and_path(
        self, 
        concept_name: str,
        concept_path: str,
        company_cik: str, 
        fiscal_year: int
    ) -> Optional[Dict[str, Any]]:
        """Get annual filing metadata by concept name and path for creating Q4 records."""
        # First get the quarterly concept for this concept name and path
        quarterly_concept = self.normalized_concepts_quarterly.find_one({
            "concept": concept_name,
            "path": concept_path,
            "company_cik": company_cik,
            "statement_type": "income_statement"
        })
        
        if not quarterly_concept:
            return None
        
        # Find the parent concept if this is a dimensional concept
        quarterly_parent_concept_id = quarterly_concept.get("concept_id")
        if quarterly_parent_concept_id:
            # This is a dimensional concept, use parent concept for matching
            quarterly_parent_concept = self.normalized_concepts_quarterly.find_one({
                "_id": quarterly_parent_concept_id
            })
            quarterly_parent_concept_name = quarterly_parent_concept.get("concept") if quarterly_parent_concept else None
        else:
            # This is a regular concept
            quarterly_parent_concept_name = concept_name
        
        # Find the matching annual concept using parent concept name
        annual_concept = None
        if quarterly_parent_concept_name:
            # Try to find annual concept by parent concept name first
            annual_concept = self.normalized_concepts_annual.find_one({
                "concept": quarterly_parent_concept_name,
                "company_cik": company_cik,
                "statement_type": "income_statement"
            })
            
            # If not found and this is a dimensional concept, try to find by concept and dimensional relationship
            if not annual_concept and quarterly_parent_concept_id:
                # Look for dimensional concepts in annual that match the parent
                annual_dimensional_concepts = list(self.normalized_concepts_annual.find({
                    "concept": concept_name,
                    "company_cik": company_cik,
                    "statement_type": "income_statement",
                    "dimension_concept": True
                }))
                
                # Find the one that has the same parent concept
                for dim_concept in annual_dimensional_concepts:
                    annual_parent_id = dim_concept.get("concept_id")
                    if annual_parent_id:
                        annual_parent = self.normalized_concepts_annual.find_one({"_id": annual_parent_id})
                        if annual_parent and annual_parent.get("concept") == quarterly_parent_concept_name:
                            annual_concept = dim_concept
                            break
        
        # If still not found, fallback to original method
        if not annual_concept:
            annual_concept = self.normalized_concepts_annual.find_one({
                "concept": concept_name,
                "path": concept_path,
                "company_cik": company_cik,
                "statement_type": "income_statement"
            })
        
        if not annual_concept:
            return None
            
        annual_concept_id = annual_concept["_id"]
        
        annual_record = self.concept_values_annual.find_one({
            "concept_id": annual_concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year
        })
        return annual_record

    def get_parent_concept_name(self, concept_id: ObjectId, collection_name: str = "normalized_concepts_quarterly") -> Optional[str]:
        """Get the parent concept name for a given concept. Used for dimensional concepts."""
        collection = getattr(self.db, collection_name)
        
        concept = collection.find_one({"_id": concept_id})
        if not concept:
            return None
        
        # If this concept has a concept_id field, it's a dimensional concept
        parent_concept_id = concept.get("concept_id")
        if parent_concept_id:
            parent_concept = collection.find_one({"_id": parent_concept_id})
            return parent_concept.get("concept") if parent_concept else None
        else:
            # This is already a parent concept
            return concept.get("concept")

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
            # Look for dimensional concepts with same name and same parent
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
            # Convert dataclass to dict for MongoDB insertion
            q4_dict = self._concept_value_to_dict(q4_value)
            
            # Insert the Q4 value
            result = self.concept_values_quarterly.insert_one(q4_dict)
            return result.inserted_id is not None
            
        except Exception as e:
            print(f"Error inserting Q4 value: {e}")
            return False
    
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
        return {
            "concept_id": concept_value.concept_id,
            "company_cik": concept_value.company_cik,
            "statement_type": concept_value.statement_type,
            "form_type": concept_value.form_type,
            "filing_id": concept_value.filing_id,
            "reporting_period": {
                "end_date": concept_value.reporting_period.end_date,
                "period_date": concept_value.reporting_period.period_date,
                "period_type": concept_value.reporting_period.period_type,
                "form_type": concept_value.reporting_period.form_type,
                "fiscal_year_end_code": concept_value.reporting_period.fiscal_year_end_code,
                "data_source": concept_value.reporting_period.data_source,
                "company_cik": concept_value.reporting_period.company_cik,
                "company_name": concept_value.reporting_period.company_name,
                "start_date": concept_value.reporting_period.start_date,
                "fiscal_year": concept_value.reporting_period.fiscal_year,
                "quarter": concept_value.reporting_period.quarter,
                "note": concept_value.reporting_period.note
            },
            "value": concept_value.value,
            "created_at": concept_value.created_at,
            "dimension_value": concept_value.dimension_value,
            "calculated": concept_value.calculated,
            "fact_id": concept_value.fact_id,
            "decimals": concept_value.decimals,
            "dimensional_concept_id": concept_value.dimensional_concept_id
        }
