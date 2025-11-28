"""Service for fixing cumulative cash flow values in Q2 and Q3.

This service converts 6-month (Q2) and 9-month (Q3) cumulative values 
to actual quarterly values by subtracting previous quarters.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from bson import ObjectId
    from pymongo.database import Database
    from pymongo.collection import Collection
except ImportError:
    print("PyMongo not installed. Please run: pip install pymongo")
    raise

from repositories.financial_repository import FinancialDataRepository


class CashFlowFixService:
    """Service for fixing cumulative cash flow values in Q2 and Q3."""
    
    def __init__(self, repository: FinancialDataRepository, verbose: bool = False):
        self.repository = repository
        self.verbose = verbose
        self.concept_values_quarterly: Collection = repository.concept_values_quarterly
    
    def fix_cumulative_values_for_company(self, company_cik: str) -> Dict[str, Any]:
        """Fix cumulative cash flow values for a specific company.
        
        Args:
            company_cik: Company CIK to process
            
        Returns:
            Dictionary with statistics about the fix operation
        """
        results = {
            "company_cik": company_cik,
            "fiscal_years_processed": 0,
            "q2_fixed": 0,
            "q3_fixed": 0,
            "q2_skipped": 0,
            "q3_skipped": 0,
            "errors": []
        }
        
        try:
            # Get all fiscal years for the company
            fiscal_years = self.repository.get_fiscal_years_for_company(company_cik)
            
            if not fiscal_years:
                results["errors"].append(f"No fiscal years found for company {company_cik}")
                return results
            
            if self.verbose:
                print(f"\nProcessing company {company_cik}: {len(fiscal_years)} fiscal years found")
            
            # Process each fiscal year
            for fiscal_year in fiscal_years:
                try:
                    year_result = self._fix_fiscal_year(company_cik, fiscal_year)
                    results["fiscal_years_processed"] += 1
                    results["q2_fixed"] += year_result["q2_fixed"]
                    results["q3_fixed"] += year_result["q3_fixed"]
                    results["q2_skipped"] += year_result["q2_skipped"]
                    results["q3_skipped"] += year_result["q3_skipped"]
                    results["errors"].extend(year_result["errors"])
                    
                except Exception as e:
                    results["errors"].append(f"Error processing FY{fiscal_year}: {str(e)}")
        
        except Exception as e:
            results["errors"].append(f"General error: {str(e)}")
        
        return results
    
    def _fix_fiscal_year(self, company_cik: str, fiscal_year: int) -> Dict[str, Any]:
        """Fix cumulative values for a specific fiscal year.
        
        Args:
            company_cik: Company CIK
            fiscal_year: Fiscal year to process
            
        Returns:
            Dictionary with statistics for this fiscal year
        """
        results = {
            "q2_fixed": 0,
            "q3_fixed": 0,
            "q2_skipped": 0,
            "q3_skipped": 0,
            "errors": []
        }
        
        if self.verbose:
            print(f"  Processing FY{fiscal_year}...")
        
        # Get all cash flow concepts for Q1, Q2, and Q3
        q1_values = self._get_quarterly_values(company_cik, fiscal_year, 1)
        q2_values = self._get_quarterly_values(company_cik, fiscal_year, 2)
        q3_values = self._get_quarterly_values(company_cik, fiscal_year, 3)
        
        # Create lookup dictionaries by concept_id
        q1_lookup = {str(val["concept_id"]): val for val in q1_values}
        q2_lookup = {str(val["concept_id"]): val for val in q2_values}
        q3_lookup = {str(val["concept_id"]): val for val in q3_values}
        
        if self.verbose:
            print(f"    Found Q1: {len(q1_values)}, Q2: {len(q2_values)}, Q3: {len(q3_values)} values")
        
        # Fix Q2 values (Q2_actual = Q2_cumulative - Q1)
        for concept_id_str, q2_value in q2_lookup.items():
            q1_value = q1_lookup.get(concept_id_str)
            
            if q1_value:
                # Calculate actual Q2 value
                q2_cumulative = q2_value["value"]
                q1_actual = q1_value["value"]
                q2_actual = q2_cumulative - q1_actual
                
                # Update Q2 value in database
                try:
                    self.concept_values_quarterly.update_one(
                        {"_id": q2_value["_id"]},
                        {"$set": {"value": q2_actual}}
                    )
                    results["q2_fixed"] += 1
                    
                    if self.verbose:
                        concept_name = self._get_concept_name(q2_value["concept_id"])
                        print(f"    ✓ Fixed Q2 for {concept_name}: {q2_cumulative:,.2f} → {q2_actual:,.2f} (Q2 - Q1)")
                
                except Exception as e:
                    results["errors"].append(
                        f"Error updating Q2 value for concept_id {concept_id_str}: {str(e)}"
                    )
            else:
                results["q2_skipped"] += 1
                if self.verbose:
                    concept_name = self._get_concept_name(q2_value["concept_id"])
                    print(f"    ⏭️  Skipped Q2 for {concept_name}: No Q1 value found")
        
        # Fix Q3 values (Q3_actual = Q3_cumulative - Q2_cumulative)
        # Note: We use the ORIGINAL Q2 cumulative value, not the fixed Q2 value
        for concept_id_str, q3_value in q3_lookup.items():
            q2_value = q2_lookup.get(concept_id_str)
            
            if q2_value:
                # Calculate actual Q3 value using original cumulative values
                q3_cumulative = q3_value["value"]
                q2_cumulative = q2_value["value"]  # This is the ORIGINAL cumulative value
                q3_actual = q3_cumulative - q2_cumulative
                
                # Update Q3 value in database
                try:
                    self.concept_values_quarterly.update_one(
                        {"_id": q3_value["_id"]},
                        {"$set": {"value": q3_actual}}
                    )
                    results["q3_fixed"] += 1
                    
                    if self.verbose:
                        concept_name = self._get_concept_name(q3_value["concept_id"])
                        print(f"    ✓ Fixed Q3 for {concept_name}: {q3_cumulative:,.2f} → {q3_actual:,.2f} (Q3 - Q2)")
                
                except Exception as e:
                    results["errors"].append(
                        f"Error updating Q3 value for concept_id {concept_id_str}: {str(e)}"
                    )
            else:
                results["q3_skipped"] += 1
                if self.verbose:
                    concept_name = self._get_concept_name(q3_value["concept_id"])
                    print(f"    ⏭️  Skipped Q3 for {concept_name}: No Q2 value found")
        
        return results
    
    def _get_quarterly_values(
        self, 
        company_cik: str, 
        fiscal_year: int, 
        quarter: int
    ) -> List[Dict[str, Any]]:
        """Get all cash flow values for a specific quarter.
        
        Args:
            company_cik: Company CIK
            fiscal_year: Fiscal year
            quarter: Quarter number (1, 2, or 3)
            
        Returns:
            List of value documents
        """
        return list(self.concept_values_quarterly.find({
            "company_cik": company_cik,
            "statement_type": "cash_flows",
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": quarter,
            "form_type": "10-Q"
        }))
    
    def _get_concept_name(self, concept_id: ObjectId) -> str:
        """Get concept name from concept_id.
        
        Args:
            concept_id: Concept ObjectId
            
        Returns:
            Concept name or 'Unknown'
        """
        try:
            concept = self.repository.normalized_concepts_quarterly.find_one(
                {"_id": concept_id},
                {"concept": 1}
            )
            return concept.get("concept", "Unknown") if concept else "Unknown"
        except Exception:
            return "Unknown"
    
    def fix_all_companies(self) -> Dict[str, Any]:
        """Fix cumulative cash flow values for all companies.
        
        Returns:
            Dictionary with overall statistics
        """
        overall_results = {
            "total_companies": 0,
            "companies_processed": 0,
            "total_q2_fixed": 0,
            "total_q3_fixed": 0,
            "total_q2_skipped": 0,
            "total_q3_skipped": 0,
            "company_results": [],
            "errors": []
        }
        
        try:
            # Get all unique companies with cash flow data
            companies = self._get_all_cashflow_companies()
            overall_results["total_companies"] = len(companies)
            
            if not companies:
                overall_results["errors"].append("No companies with cash flow data found")
                return overall_results
            
            print(f"Found {len(companies)} companies with cash flow data")
            print("=" * 60)
            
            # Process each company
            for idx, company_cik in enumerate(companies, 1):
                try:
                    print(f"\n[{idx}/{len(companies)}] Processing {company_cik}...")
                    
                    company_result = self.fix_cumulative_values_for_company(company_cik)
                    overall_results["companies_processed"] += 1
                    overall_results["total_q2_fixed"] += company_result["q2_fixed"]
                    overall_results["total_q3_fixed"] += company_result["q3_fixed"]
                    overall_results["total_q2_skipped"] += company_result["q2_skipped"]
                    overall_results["total_q3_skipped"] += company_result["q3_skipped"]
                    overall_results["company_results"].append(company_result)
                    
                    # Show company summary
                    if not self.verbose:
                        print(f"  ✓ Fixed Q2: {company_result['q2_fixed']}, Q3: {company_result['q3_fixed']}")
                        if company_result["errors"]:
                            print(f"  ⚠️  Errors: {len(company_result['errors'])}")
                
                except Exception as e:
                    overall_results["errors"].append(f"Error processing company {company_cik}: {str(e)}")
                    print(f"  ❌ Error: {str(e)}")
            
        except Exception as e:
            overall_results["errors"].append(f"General error: {str(e)}")
        
        return overall_results
    
    def _get_all_cashflow_companies(self) -> List[str]:
        """Get all unique company CIKs that have cash flow data.
        
        Returns:
            List of company CIKs
        """
        try:
            pipeline = [
                {
                    "$match": {
                        "statement_type": "cash_flows",
                        "form_type": "10-Q",
                        "reporting_period.quarter": {"$in": [1, 2, 3]}
                    }
                },
                {"$group": {"_id": "$company_cik"}},
                {"$sort": {"_id": 1}}
            ]
            
            result = list(self.concept_values_quarterly.aggregate(pipeline))
            return [item["_id"] for item in result if item["_id"]]
        
        except Exception as e:
            print(f"Error getting companies list: {e}")
            return []
