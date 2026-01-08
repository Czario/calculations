"""Service for calculating and inserting Gross Profit values.

This service:
1. Looks up Total Revenue and Cost of Revenues concepts
2. Calculates Gross Profit = Total Revenues - Cost of Revenues
3. Creates Gross Profit concept if not exists (us-gaap:GrossProfit, path: 003)
4. Inserts calculated values into quarterly and annual collections
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

try:
    from bson import ObjectId
    from pymongo.database import Database
    from pymongo.collection import Collection
except ImportError:
    print("PyMongo not installed. Please run: pip install pymongo")
    raise

from repositories.financial_repository import FinancialDataRepository


class GrossProfitService:
    """Service for calculating and inserting Gross Profit values."""
    
    # Concept configuration for Gross Profit
    GROSS_PROFIT_CONCEPT = "us-gaap:GrossProfit"
    GROSS_PROFIT_LABEL = "Gross Profit"
    GROSS_PROFIT_PATH = "003"
    STATEMENT_TYPE = "income_statement"
    
    # Standard labels (exact match required)
    REVENUE_LABEL = "Total Revenues"
    COST_LABEL = "Cost of Revenues"
    
    def __init__(self, repository: FinancialDataRepository, verbose: bool = False):
        self.repository = repository
        self.verbose = verbose
        self.db = repository.db
        
        # Collections for concept metadata
        self.normalized_concepts_quarterly: Collection = repository.normalized_concepts_quarterly
        self.normalized_concepts_annual: Collection = repository.normalized_concepts_annual
        
        # Collections for concept values
        self.concept_values_quarterly: Collection = repository.concept_values_quarterly
        self.concept_values_annual: Collection = repository.concept_values_annual
        
        # Additional collections mentioned in requirements (if they exist)
        self.standardlabels: Collection = self.db.get_collection("standardlabels")
        self.concepts_standard_mapping: Collection = self.db.get_collection("concepts_standard_mapping")
        self.us_gaap_taxonomy: Collection = self.db.get_collection("us_gaap_taxonomy")
    
    def calculate_gross_profit_for_company(
        self, 
        company_cik: str,
        recalculate: bool = False
    ) -> Dict[str, Any]:
        """Calculate and insert Gross Profit for a specific company.
        
        Args:
            company_cik: Company CIK to process
            recalculate: If True, recalculates even if Gross Profit already exists
            
        Returns:
            Dictionary with statistics about the calculation
        """
        results = {
            "company_cik": company_cik,
            "fiscal_years_processed": 0,
            "quarterly_values_inserted": 0,
            "annual_values_inserted": 0,
            "quarterly_concepts_created": 0,
            "annual_concepts_created": 0,
            "errors": [],
            "skipped_periods": []
        }
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Processing Gross Profit calculation for company: {company_cik}")
            print(f"{'='*60}")
        
        try:
            # Step 1: Find or create Gross Profit concept
            gross_profit_quarterly_concept = self._ensure_gross_profit_concept_exists(
                company_cik, is_annual=False
            )
            gross_profit_annual_concept = self._ensure_gross_profit_concept_exists(
                company_cik, is_annual=True
            )
            
            if gross_profit_quarterly_concept.get("created"):
                results["quarterly_concepts_created"] += 1
            if gross_profit_annual_concept.get("created"):
                results["annual_concepts_created"] += 1
            
            # Step 2: Find Revenue and Cost concepts for both quarterly and annual
            revenue_quarterly_concept, cost_quarterly_concept, revenue_annual_concept, cost_annual_concept = self._find_revenue_and_cost_concepts(company_cik)
            
            # Check quarterly concepts
            if not revenue_quarterly_concept:
                if self.verbose:
                    print(f"  ⚠️  Could not find Total Revenue quarterly concept")
            
            if not cost_quarterly_concept:
                if self.verbose:
                    print(f"  ⚠️  Could not find Cost of Revenues quarterly concept")
            
            # Check annual concepts
            if not revenue_annual_concept:
                if self.verbose:
                    print(f"  ⚠️  Could not find Total Revenue annual concept")
            
            if not cost_annual_concept:
                if self.verbose:
                    print(f"  ⚠️  Could not find Cost of Revenues annual concept")
            
            # We need at least one set (either quarterly or annual) to proceed
            has_quarterly = revenue_quarterly_concept and cost_quarterly_concept
            has_annual = revenue_annual_concept and cost_annual_concept
            
            if not has_quarterly and not has_annual:
                results["errors"].append("Could not find revenue and cost concepts in either quarterly or annual")
                return results
            
            if self.verbose:
                if has_quarterly and revenue_quarterly_concept and cost_quarterly_concept:
                    print(f"✓ Found Quarterly Revenue concept: {revenue_quarterly_concept.get('label')} ({revenue_quarterly_concept.get('concept')})")
                    print(f"✓ Found Quarterly Cost concept: {cost_quarterly_concept.get('label')} ({cost_quarterly_concept.get('concept')})")
                if has_annual and revenue_annual_concept and cost_annual_concept:
                    print(f"✓ Found Annual Revenue concept: {revenue_annual_concept.get('label')} ({revenue_annual_concept.get('concept')})")
                    print(f"✓ Found Annual Cost concept: {cost_annual_concept.get('label')} ({cost_annual_concept.get('concept')})")
            
            # Step 3: Get fiscal years to process
            fiscal_years = self._get_fiscal_years_for_company(company_cik)
            
            if not fiscal_years:
                results["errors"].append("No fiscal years found for company")
                return results
            
            if self.verbose:
                print(f"✓ Found {len(fiscal_years)} fiscal years to process")
            
            # Step 4: Process each fiscal year
            for fiscal_year in fiscal_years:
                try:
                    year_results = self._process_fiscal_year(
                        company_cik,
                        fiscal_year,
                        revenue_quarterly_concept,
                        cost_quarterly_concept,
                        revenue_annual_concept,
                        cost_annual_concept,
                        gross_profit_quarterly_concept["concept"],
                        gross_profit_annual_concept["concept"],
                        recalculate
                    )
                    
                    results["fiscal_years_processed"] += 1
                    results["quarterly_values_inserted"] += year_results["quarterly_inserted"]
                    results["annual_values_inserted"] += year_results["annual_inserted"]
                    results["skipped_periods"].extend(year_results["skipped"])
                    results["errors"].extend(year_results["errors"])
                    
                except Exception as e:
                    results["errors"].append(f"Error processing FY{fiscal_year}: {str(e)}")
            
        except Exception as e:
            results["errors"].append(f"General error: {str(e)}")
        
        return results
    
    def calculate_gross_profit_for_all_companies(
        self,
        recalculate: bool = False
    ) -> Dict[str, Any]:
        """Calculate and insert Gross Profit for all companies.
        
        Args:
            recalculate: If True, recalculates even if Gross Profit already exists
            
        Returns:
            Dictionary with overall statistics
        """
        overall_results = {
            "companies_processed": 0,
            "companies_successful": 0,
            "companies_failed": 0,
            "total_quarterly_values": 0,
            "total_annual_values": 0,
            "total_concepts_created": 0,
            "company_results": []
        }
        
        try:
            # Get all company CIKs
            companies = self._get_all_companies()
            
            if not companies:
                print("No companies found in database")
                return overall_results
            
            print(f"\n{'='*60}")
            print(f"Processing Gross Profit calculation for {len(companies)} companies")
            print(f"{'='*60}\n")
            
            for idx, company_cik in enumerate(companies, 1):
                try:
                    if self.verbose:
                        print(f"\n[{idx}/{len(companies)}] Processing company: {company_cik}")
                    else:
                        print(f"[{idx}/{len(companies)}] Processing company: {company_cik}")
                    
                    results = self.calculate_gross_profit_for_company(company_cik, recalculate)
                    
                    overall_results["companies_processed"] += 1
                    overall_results["total_quarterly_values"] += results["quarterly_values_inserted"]
                    overall_results["total_annual_values"] += results["annual_values_inserted"]
                    overall_results["total_concepts_created"] += (
                        results["quarterly_concepts_created"] + results["annual_concepts_created"]
                    )
                    
                    if results["errors"]:
                        overall_results["companies_failed"] += 1
                        if not self.verbose:
                            print(f"  ✗ Errors: {len(results['errors'])}")
                    else:
                        overall_results["companies_successful"] += 1
                        if not self.verbose:
                            print(f"  ✓ Success: {results['quarterly_values_inserted']} quarterly, "
                                  f"{results['annual_values_inserted']} annual values")
                    
                    overall_results["company_results"].append(results)
                    
                except Exception as e:
                    overall_results["companies_failed"] += 1
                    print(f"  ✗ Error processing company {company_cik}: {str(e)}")
            
        except Exception as e:
            print(f"Error in overall processing: {str(e)}")
        
        return overall_results
    
    def _ensure_gross_profit_concept_exists(
        self,
        company_cik: str,
        is_annual: bool
    ) -> Dict[str, Any]:
        """Ensure Gross Profit concept exists in the appropriate collection.
        
        Logic:
        - If concept EXISTS: Use existing concept, don't create new one
        - If concept DOESN'T EXIST: Create new concept with proper metadata
        
        Returns:
            Dictionary with concept details and 'created' flag (True if newly created)
        """
        collection = self.normalized_concepts_annual if is_annual else self.normalized_concepts_quarterly
        
        # Check if Gross Profit concept already exists for this company
        existing_concept = collection.find_one({
            "company_cik": company_cik,
            "concept": self.GROSS_PROFIT_CONCEPT,
            "statement_type": self.STATEMENT_TYPE,
            "path": self.GROSS_PROFIT_PATH
        })
        
        if existing_concept:
            # Concept already exists - use it, don't create new one
            return {
                "concept": existing_concept,
                "created": False
            }
        
        # Concept doesn't exist - create new one
        new_concept = {
            "company_cik": company_cik,
            "statement_type": self.STATEMENT_TYPE,
            "concept": self.GROSS_PROFIT_CONCEPT,
            "form_type": "10-K" if is_annual else "10-Q",
            "label": self.GROSS_PROFIT_LABEL,
            "path": self.GROSS_PROFIT_PATH,
            "order_key": "c",  # Following the pattern: 001=a, 002=b, 003=c
            "abstract": False,
            "dimension": False,
            "dimension_concept": False,
            "created_at": datetime.utcnow(),
            "calculated": True,
            "dimension_value": False
        }
        
        result = collection.insert_one(new_concept)
        new_concept["_id"] = result.inserted_id
        
        if self.verbose:
            period_type = "annual" if is_annual else "quarterly"
            print(f"✓ Created {period_type} Gross Profit concept for company {company_cik}")
        
        return {
            "concept": new_concept,
            "created": True
        }
    
    def _find_revenue_and_cost_concepts(
        self,
        company_cik: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Find Total Revenues and Cost of Revenues concepts using the standard flow:
        1. Look up label in standardlabels collection -> get id
        2. Use id to look up in concepts_standard_mapping -> get concept_id
        3. Use concept_id in us_gaap_taxonomy -> get concept
        4. Use concept to find in normalized_concepts_quarterly/annual
        
        Returns:
            Tuple of (revenue_quarterly_concept, cost_quarterly_concept, revenue_annual_concept, cost_annual_concept)
        """
        # Find revenue concepts for both quarterly and annual
        revenue_quarterly_concept = self._find_concept_via_standard_flow(
            self.REVENUE_LABEL, 
            company_cik,
            is_annual=False
        )
        revenue_annual_concept = self._find_concept_via_standard_flow(
            self.REVENUE_LABEL, 
            company_cik,
            is_annual=True
        )
        
        # Find cost concepts for both quarterly and annual
        cost_quarterly_concept = self._find_concept_via_standard_flow(
            self.COST_LABEL,
            company_cik,
            is_annual=False
        )
        cost_annual_concept = self._find_concept_via_standard_flow(
            self.COST_LABEL,
            company_cik,
            is_annual=True
        )
        
        return revenue_quarterly_concept, cost_quarterly_concept, revenue_annual_concept, cost_annual_concept
    
    def _find_concept_via_standard_flow(
        self,
        label: str,
        company_cik: str,
        is_annual: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Find concept using the standard flow through multiple collections.
        
        Flow:
        1. standardlabels (standard_label) -> _id
        2. concepts_standard_mapping (standard_label_id) -> concept_ids (array)
        3. us_gaap_taxonomy (concept_ids) -> concepts
        4. normalized_concepts_quarterly/annual (concept + company_cik) -> concept document
        
        Args:
            label: The standard label to look up (e.g., "Total Revenues")
            company_cik: The company CIK
            is_annual: If True, search in normalized_concepts_annual; if False, search in quarterly
            
        Returns:
            Concept document from normalized_concepts collection, or None if not found
        """
        collection = self.normalized_concepts_annual if is_annual else self.normalized_concepts_quarterly
        collection_name = "annual" if is_annual else "quarterly"
        
        try:
            # Step 1: Look up label in standardlabels collection
            standard_label = self.standardlabels.find_one({
                "standard_label": label,
                "statement_type": self.STATEMENT_TYPE
            })
            if not standard_label:
                if self.verbose:
                    print(f"  ⚠️  Label '{label}' not found in standardlabels collection")
                return None
            
            standard_label_id = standard_label.get("_id")
            if self.verbose:
                print(f"  → Found standard label '{label}' with id: {standard_label_id}")
            
            # Step 2: Look up in concepts_standard_mapping to get concept_ids
            mapping = self.concepts_standard_mapping.find_one({
                "standard_label_id": standard_label_id
            })
            if not mapping:
                if self.verbose:
                    print(f"  ⚠️  No mapping found for label id: {standard_label_id}")
                return None
            
            concept_ids = mapping.get("concept_ids", [])
            if not concept_ids:
                if self.verbose:
                    print(f"  ⚠️  No concept_ids found in mapping")
                return None
            
            if self.verbose:
                print(f"  → Found {len(concept_ids)} concept_ids in mapping")
            
            # Step 3: Look up in us_gaap_taxonomy to get concept names
            # Try each concept_id until we find one that exists for this company
            for concept_id in concept_ids:
                taxonomy = self.us_gaap_taxonomy.find_one({"_id": concept_id})
                if not taxonomy:
                    continue
                
                concept_name = taxonomy.get("concept")
                if not concept_name:
                    continue
                
                if self.verbose:
                    print(f"  → Found concept in taxonomy: {concept_name}")
                
                # Step 4: Look up in the specified normalized_concepts collection
                normalized_concept = collection.find_one({
                    "concept": concept_name,
                    "company_cik": company_cik,
                    "statement_type": self.STATEMENT_TYPE
                })
                
                if normalized_concept:
                    if self.verbose:
                        print(f"  ✓ Found normalized concept in {collection_name}: {normalized_concept.get('label')} ({concept_name})")
                    return normalized_concept
                else:
                    if self.verbose:
                        print(f"  → Concept '{concept_name}' not found in {collection_name} for company {company_cik}, trying next...")
            
            # If we get here, none of the concepts were found for this company
            if self.verbose:
                print(f"  ⚠️  No matching concept found in normalized_concepts_{collection_name} for company {company_cik}")
            return None
            
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️  Error in standard flow for label '{label}': {str(e)}")
            return None
    
    def _get_fiscal_years_for_company(self, company_cik: str) -> List[int]:
        """Get all fiscal years for a company."""
        pipeline = [
            {"$match": {"company_cik": company_cik}},
            {"$group": {"_id": "$reporting_period.fiscal_year"}},
            {"$sort": {"_id": 1}}
        ]
        
        result = list(self.concept_values_quarterly.aggregate(pipeline))
        return [item["_id"] for item in result if item["_id"]]
    
    def _get_all_companies(self) -> List[str]:
        """Get all unique company CIKs."""
        pipeline = [
            {"$group": {"_id": "$company_cik"}},
            {"$sort": {"_id": 1}}
        ]
        
        result = list(self.normalized_concepts_quarterly.aggregate(pipeline))
        return [item["_id"] for item in result if item["_id"]]
    
    def _process_fiscal_year(
        self,
        company_cik: str,
        fiscal_year: int,
        revenue_quarterly_concept: Optional[Dict[str, Any]],
        cost_quarterly_concept: Optional[Dict[str, Any]],
        revenue_annual_concept: Optional[Dict[str, Any]],
        cost_annual_concept: Optional[Dict[str, Any]],
        gross_profit_quarterly_concept: Dict[str, Any],
        gross_profit_annual_concept: Dict[str, Any],
        recalculate: bool
    ) -> Dict[str, Any]:
        """Process a single fiscal year for Gross Profit calculation.
        
        Returns:
            Dictionary with results for this fiscal year
        """
        results = {
            "fiscal_year": fiscal_year,
            "quarterly_inserted": 0,
            "annual_inserted": 0,
            "skipped": [],
            "errors": []
        }
        
        # Process quarterly values (Q1, Q2, Q3, Q4) if we have quarterly concepts
        if revenue_quarterly_concept and cost_quarterly_concept:
            for quarter in [1, 2, 3, 4]:
                try:
                    inserted = self._calculate_and_insert_quarterly_value(
                        company_cik,
                        fiscal_year,
                        quarter,
                        revenue_quarterly_concept,
                        cost_quarterly_concept,
                        gross_profit_quarterly_concept,
                        recalculate
                    )
                    if inserted:
                        results["quarterly_inserted"] += 1
                    else:
                        results["skipped"].append(f"FY{fiscal_year} Q{quarter}")
                        
                except Exception as e:
                    results["errors"].append(f"Q{quarter} error: {str(e)}")
        
        # Process annual value if we have annual concepts
        if revenue_annual_concept and cost_annual_concept:
            try:
                inserted = self._calculate_and_insert_annual_value(
                    company_cik,
                    fiscal_year,
                    revenue_annual_concept,
                    cost_annual_concept,
                    gross_profit_annual_concept,
                    recalculate
                )
                if inserted:
                    results["annual_inserted"] += 1
                else:
                    results["skipped"].append(f"FY{fiscal_year} Annual")
                    
            except Exception as e:
                results["errors"].append(f"Annual error: {str(e)}")
        
        return results
    
    def _calculate_and_insert_quarterly_value(
        self,
        company_cik: str,
        fiscal_year: int,
        quarter: int,
        revenue_concept: Dict[str, Any],
        cost_concept: Dict[str, Any],
        gross_profit_concept: Dict[str, Any],
        recalculate: bool
    ) -> bool:
        """Calculate and insert quarterly Gross Profit value.
        
        Skip Logic:
        - If value EXISTS and recalculate=False: SKIP (don't insert)
        - If value EXISTS and recalculate=True: UPDATE (replace existing)
        - If value DOESN'T EXIST: INSERT (create new)
        - If revenue or cost values missing: SKIP (can't calculate)
        
        Returns:
            True if value was inserted/updated, False if skipped
        """
        # Check if Gross Profit value already exists for this period
        existing_value = self.concept_values_quarterly.find_one({
            "concept_id": gross_profit_concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": quarter
        })
        
        # If value exists and we're not recalculating, skip this period
        if existing_value and not recalculate:
            if self.verbose:
                print(f"  ⏭  Skipping FY{fiscal_year} Q{quarter} - value already exists")
            return False
        
        # Get revenue value
        revenue_value_doc = self.concept_values_quarterly.find_one({
            "concept_id": revenue_concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": quarter
        })
        
        if not revenue_value_doc:
            if self.verbose:
                print(f"  ⏭  Skipping FY{fiscal_year} Q{quarter} - no revenue value")
            return False
        
        # Get cost value
        cost_value_doc = self.concept_values_quarterly.find_one({
            "concept_id": cost_concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": quarter
        })
        
        if not cost_value_doc:
            if self.verbose:
                print(f"  ⏭  Skipping FY{fiscal_year} Q{quarter} - no cost value")
            return False
        
        # Calculate Gross Profit
        revenue = revenue_value_doc["value"]
        cost = cost_value_doc["value"]
        gross_profit = revenue - cost
        
        # Prepare the Gross Profit value document
        gross_profit_doc = {
            "concept_id": gross_profit_concept["_id"],
            "company_cik": company_cik,
            "statement_type": self.STATEMENT_TYPE,
            "form_type": revenue_value_doc.get("form_type", "10-Q"),
            "reporting_period": revenue_value_doc["reporting_period"],
            "value": gross_profit,
            "created_at": datetime.utcnow(),
            "dimension_value": False,
            "calculated": True
        }
        
        # Insert or update based on whether value existed
        if existing_value and recalculate:
            # Value exists and recalculate=True: UPDATE existing value
            self.concept_values_quarterly.replace_one(
                {"_id": existing_value["_id"]},
                gross_profit_doc
            )
            if self.verbose:
                print(f"  ✓ Updated FY{fiscal_year} Q{quarter}: {gross_profit:,.2f}")
        else:
            # Value doesn't exist: INSERT new value
            self.concept_values_quarterly.insert_one(gross_profit_doc)
            if self.verbose:
                print(f"  ✓ Inserted FY{fiscal_year} Q{quarter}: {gross_profit:,.2f}")
        
        return True
    
    def _calculate_and_insert_annual_value(
        self,
        company_cik: str,
        fiscal_year: int,
        revenue_concept: Dict[str, Any],
        cost_concept: Dict[str, Any],
        gross_profit_concept: Dict[str, Any],
        recalculate: bool
    ) -> bool:
        """Calculate and insert annual Gross Profit value.
        
        Skip Logic:
        - If value EXISTS and recalculate=False: SKIP (don't insert)
        - If value EXISTS and recalculate=True: UPDATE (replace existing)
        - If value DOESN'T EXIST: INSERT (create new)
        - If revenue or cost values missing: SKIP (can't calculate)
        
        Returns:
            True if value was inserted/updated, False if skipped
        """
        # Check if Gross Profit value already exists for this fiscal year
        existing_value = self.concept_values_annual.find_one({
            "concept_id": gross_profit_concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year
        })
        
        # If value exists and we're not recalculating, skip this period
        if existing_value and not recalculate:
            if self.verbose:
                print(f"  ⏭  Skipping FY{fiscal_year} Annual - value already exists")
            return False
        
        # For annual values, we need to look up the annual concept IDs
        revenue_annual_concept = self.normalized_concepts_annual.find_one({
            "company_cik": company_cik,
            "concept": revenue_concept["concept"],
            "statement_type": self.STATEMENT_TYPE
        })
        
        cost_annual_concept = self.normalized_concepts_annual.find_one({
            "company_cik": company_cik,
            "concept": cost_concept["concept"],
            "statement_type": self.STATEMENT_TYPE
        })
        
        if not revenue_annual_concept or not cost_annual_concept:
            if self.verbose:
                print(f"  ⏭  Skipping FY{fiscal_year} Annual - annual concepts not found")
            return False
        
        # Get revenue value
        revenue_value_doc = self.concept_values_annual.find_one({
            "concept_id": revenue_annual_concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year
        })
        
        if not revenue_value_doc:
            if self.verbose:
                print(f"  ⏭  Skipping FY{fiscal_year} Annual - no revenue value")
            return False
        
        # Get cost value
        cost_value_doc = self.concept_values_annual.find_one({
            "concept_id": cost_annual_concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year
        })
        
        if not cost_value_doc:
            if self.verbose:
                print(f"  ⏭  Skipping FY{fiscal_year} Annual - no cost value")
            return False
        
        # Calculate Gross Profit
        revenue = revenue_value_doc["value"]
        cost = cost_value_doc["value"]
        gross_profit = revenue - cost
        
        # Prepare the Gross Profit value document
        gross_profit_doc = {
            "concept_id": gross_profit_concept["_id"],
            "company_cik": company_cik,
            "statement_type": self.STATEMENT_TYPE,
            "form_type": revenue_value_doc.get("form_type", "10-K"),
            "reporting_period": revenue_value_doc["reporting_period"],
            "value": gross_profit,
            "created_at": datetime.utcnow(),
            "dimension_value": False,
            "calculated": True
        }
        
        # Insert or update based on whether value existed
        if existing_value and recalculate:
            # Value exists and recalculate=True: UPDATE existing value
            self.concept_values_annual.replace_one(
                {"_id": existing_value["_id"]},
                gross_profit_doc
            )
            if self.verbose:
                print(f"  ✓ Updated FY{fiscal_year} Annual: {gross_profit:,.2f}")
        else:
            # Value doesn't exist: INSERT new value
            self.concept_values_annual.insert_one(gross_profit_doc)
            if self.verbose:
                print(f"  ✓ Inserted FY{fiscal_year} Annual: {gross_profit:,.2f}")
        
        return True
