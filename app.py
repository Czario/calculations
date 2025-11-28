"""Main application orchestrator for Q4 calculations."""

import logging
from typing import List, Optional, Dict
from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository
from services.q4_calculation_service import Q4CalculationService
from services.cashflow_fix_service import CashFlowFixService


class Q4CalculationApp:
    """Main application for Q4 calculations."""
    
    def __init__(self, verbose: bool = False):
        self.config = DatabaseConfig()
        self.verbose = verbose
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.WARNING
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def run_q4_calculation(self, company_cik: Optional[str] = None, recalculate: bool = False) -> None:
        """Run Q4 calculation for specified company or all companies.
        
        Args:
            company_cik: Company CIK to process. If None, processes all companies.
            recalculate: If True, removes existing Q4 values before recalculating.
        """
        
        if self.verbose:
            self.logger.info("Starting Q4 calculation process...")
        
        try:
            with DatabaseConnection(self.config) as db:
                repository = FinancialDataRepository(db)
                service = Q4CalculationService(repository, verbose=self.verbose)
                
                # Remove existing Q4 values if recalculate flag is set
                if recalculate:
                    if self.verbose:
                        self.logger.info("Recalculate mode: Removing existing Q4 values...")
                    deleted_count = repository.delete_all_q4_values(company_cik)
                    if self.verbose:
                        self.logger.info(f"Deleted {deleted_count} existing Q4 values")
                
                if company_cik:
                    # Process specific company
                    self._process_company(service, company_cik)
                else:
                    # Process all companies
                    self._process_all_companies(service, repository)
                    
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise
    
    def run_cashflow_fix(self, company_cik: Optional[str] = None) -> None:
        """Run cash flow fix process to convert cumulative Q2/Q3 values to quarterly values.
        
        This process:
        - Converts Q2 6-month cumulative values to 3-month quarterly: Q2 = Q2 - Q1
        - Converts Q3 9-month cumulative values to 3-month quarterly: Q3 = Q3 - Q2
        
        Args:
            company_cik: Company CIK to process. If None, processes all companies.
        """
        
        if self.verbose:
            self.logger.info("Starting cash flow fix process...")
        
        try:
            with DatabaseConnection(self.config) as db:
                repository = FinancialDataRepository(db)
                service = CashFlowFixService(repository, verbose=self.verbose)
                
                if company_cik:
                    # Process specific company
                    print(f"Processing cash flow fix for company: {company_cik}")
                    print("=" * 60)
                    
                    results = service.fix_cumulative_values_for_company(company_cik)
                    self._log_cashflow_fix_results(results)
                else:
                    # Process all companies
                    print("Processing cash flow fix for all companies...")
                    print("=" * 60)
                    
                    overall_results = service.fix_all_companies()
                    self._log_overall_cashflow_fix_results(overall_results)
                    
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise
    
    def _process_company(self, service: Q4CalculationService, company_cik: str) -> None:
        """Process Q4 calculations for a specific company (both income statement and cash flow)."""
        
        if self.verbose:
            self.logger.info(f"Processing Q4 calculations for company: {company_cik}")
        
        # Process income statement
        if self.verbose:
            self.logger.info(f"Calculating income statement Q4 for {company_cik}...")
        income_results = service.calculate_q4_for_company(company_cik)
        self._log_results(company_cik, income_results)
        
        # Process cash flow statement
        if self.verbose:
            self.logger.info(f"Calculating cash flow statement Q4 for {company_cik}...")
        cashflow_results = service.calculate_q4_for_cash_flow(company_cik)
        self._log_results(company_cik, cashflow_results)
    
    def _process_all_companies(
        self, 
        service: Q4CalculationService, 
        repository: FinancialDataRepository
    ) -> None:
        """Process Q4 calculations for all companies."""
        
        if self.verbose:
            self.logger.info("Processing Q4 calculations for all companies...")
        
        # Get all unique company CIKs
        companies = self._get_all_companies(repository)
        
        if not companies:
            self.logger.warning("No companies found in the database")
            return
        
        if self.verbose:
            self.logger.info(f"Found {len(companies)} companies to process")
        
        total_processed = 0
        total_successful = 0
        total_skipped = 0
        
        for idx, company_cik in enumerate(companies, 1):
            try:
                if self.verbose:
                    self.logger.info(f"Processing company {idx}/{len(companies)}: {company_cik}")
                
                # Process income statement
                if self.verbose:
                    self.logger.info(f"  → Income Statement Q4 calculations")
                income_results = service.calculate_q4_for_company(company_cik)
                self._log_results(company_cik, income_results)
                
                total_processed += income_results["processed_concepts"]
                total_successful += income_results["successful_calculations"]
                total_skipped += income_results["skipped_concepts"]
                
                # Process cash flow statement
                if self.verbose:
                    self.logger.info(f"  → Cash Flow Statement Q4 calculations")
                cashflow_results = service.calculate_q4_for_cash_flow(company_cik)
                self._log_results(company_cik, cashflow_results)
                
                total_processed += cashflow_results["processed_concepts"]
                total_successful += cashflow_results["successful_calculations"]
                total_skipped += cashflow_results["skipped_concepts"]
                
            except Exception as e:
                self.logger.error(f"Error processing company {company_cik}: {e}")
        
        # Log summary (always show)
        print("=" * 60)
        print("🎯 Q4 CALCULATION SUMMARY")
        print("=" * 60)
        print(f"📊 Companies processed: {len(companies)}")
        print(f"📈 Concepts processed: {total_processed}")
        print(f"✅ Successful Q4 calculations: {total_successful}")
        print(f"⏭️  Skipped concepts: {total_skipped}")
        
        if total_processed > 0:
            success_rate = (total_successful / total_processed) * 100
            print(f"🎯 Overall success rate: {success_rate:.1f}%")
        
        print("=" * 60)
    
    def _get_all_companies(self, repository: FinancialDataRepository) -> List[str]:
        """Get all unique company CIKs from the database."""
        try:
            pipeline = [
                {"$group": {"_id": "$company_cik"}},
                {"$sort": {"_id": 1}}
            ]
            
            result = list(repository.concept_values_annual.aggregate(pipeline))
            return [item["_id"] for item in result if item["_id"]]
            
        except Exception as e:
            self.logger.error(f"Error getting companies list: {e}")
            return []
    
    def _log_results(self, company_cik: str, results: dict) -> None:
        """Log the results of Q4 calculation for a company with improved formatting."""
        
        statement_type = results.get("statement_type", "Unknown")
        
        # In verbose mode, show full details
        if self.verbose:
            # Main results summary
            self.logger.info(f"Results for company {company_cik} ({statement_type}):")
            self.logger.info(f"  📊 Processed concepts: {results['processed_concepts']}")
            self.logger.info(f"  ✅ Successful calculations: {results['successful_calculations']}")
            self.logger.info(f"  ⏭️  Skipped concepts: {results['skipped_concepts']}")
            
            # Add explanation for cash flows if no successful calculations
            if statement_type == "cash_flows" and results['successful_calculations'] == 0:
                if results['processed_concepts'] > 0:
                    self.logger.info(f"  💡 Note: Cash flow statements often lack quarterly data (Q1, Q2, Q3) needed for Q4 calculation")
        
        # Show errors (both verbose and non-verbose mode, but different detail levels)
        if results["errors"]:
            # Categorize errors for better insights
            error_categories = self._categorize_errors(results["errors"])
            
            # In non-verbose mode, only show if there are actual errors (not just existing Q4)
            if not self.verbose:
                # Only show errors that aren't "Q4 already exists" and aren't just missing data
                real_errors = []
                for error in results["errors"]:
                    error_lower = error.lower()
                    if ("q4 value already exists" not in error_lower and 
                        "missing values:" not in error_lower and
                        "concept not found" not in error_lower):
                        real_errors.append(error)
                
                if real_errors:
                    print(f"⚠️  Errors in {company_cik} ({statement_type}): {len(real_errors)} issues found")
                    # Show just a few examples of real errors
                    for error in real_errors[:3]:
                        print(f"  - {error}")
                    if len(real_errors) > 3:
                        print(f"  ... and {len(real_errors) - 3} more errors")
            else:
                # Verbose mode: show full error details
                self.logger.warning(f"  ⚠️  Issues found: {len(results['errors'])}")
                
                # Log summary by category
                for category, count in error_categories.items():
                    if count > 0:
                        self.logger.warning(f"    • {category}: {count} concepts")
                
                # Show sample errors for main categories (limit to prevent log spam)
                self._log_sample_errors(results["errors"], error_categories)
            
        # Success rate calculation (verbose mode only)
        if self.verbose and results['processed_concepts'] > 0:
            success_rate = (results['successful_calculations'] / results['processed_concepts']) * 100
            self.logger.info(f"  📈 Success rate: {success_rate:.1f}%")
        
        # In non-verbose mode, show final summary for each company
        if not self.verbose:
            print(f"📊 {company_cik} ({statement_type}): {results['successful_calculations']} successful calculations, {results['skipped_concepts']} skipped")
    
    def _categorize_errors(self, errors: List[str]) -> dict:
        """Categorize errors to provide better insights."""
        categories = {
            "Missing all values": 0,
            "Missing Q4 data only": 0,
            "Missing Annual data": 0,
            "Missing some quarterly data": 0,
            "Q4 already exists": 0,
            "Metadata issues": 0,
            "Other": 0
        }
        
        for error in errors:
            error_lower = error.lower()
            
            if "missing values: q1, q2, q3, annual" in error_lower:
                categories["Missing all values"] += 1
            elif "missing values: q1, q2, q3" in error_lower:
                categories["Missing Q4 data only"] += 1
            elif "annual" in error_lower and "missing" in error_lower:
                categories["Missing Annual data"] += 1
            elif "missing values:" in error_lower:
                categories["Missing some quarterly data"] += 1
            elif "q4 value already exists" in error_lower:
                categories["Q4 already exists"] += 1
            elif "metadata" in error_lower or "concept not found" in error_lower:
                categories["Metadata issues"] += 1
            else:
                categories["Other"] += 1
        
        return categories
    
    def _log_sample_errors(self, errors: List[str], categories: dict) -> None:
        """Log sample errors for each major category to help with debugging."""
        
        max_samples_per_category = 2
        max_total_samples = 6
        total_logged = 0
        
        # In verbose mode, show all errors
        if self.verbose:
            max_samples_per_category = len(errors)
            max_total_samples = len(errors)
        
        # Group errors by category
        categorized_errors = {
            "Missing all values": [],
            "Missing Q4 data only": [],
            "Missing Annual data": [],
            "Missing some quarterly data": [],
            "Q4 already exists": [],
            "Metadata issues": [],
            "Other": []
        }
        
        for error in errors:
            if total_logged >= max_total_samples:
                break
                
            error_lower = error.lower()
            
            if "missing values: q1, q2, q3, annual" in error_lower and len(categorized_errors["Missing all values"]) < max_samples_per_category:
                categorized_errors["Missing all values"].append(error)
                total_logged += 1
            elif "missing values: q1, q2, q3" in error_lower and len(categorized_errors["Missing Q4 data only"]) < max_samples_per_category:
                categorized_errors["Missing Q4 data only"].append(error)
                total_logged += 1
            elif "annual" in error_lower and "missing" in error_lower and len(categorized_errors["Missing Annual data"]) < max_samples_per_category:
                categorized_errors["Missing Annual data"].append(error)
                total_logged += 1
            elif "missing values:" in error_lower and len(categorized_errors["Missing some quarterly data"]) < max_samples_per_category:
                categorized_errors["Missing some quarterly data"].append(error)
                total_logged += 1
            elif "q4 value already exists" in error_lower and len(categorized_errors["Q4 already exists"]) < max_samples_per_category:
                categorized_errors["Q4 already exists"].append(error)
                total_logged += 1
        
        # Log sample errors for significant categories
        for category, category_errors in categorized_errors.items():
            if category_errors and categories[category] > 0:
                self.logger.warning(f"      {category} examples:")
                for error in category_errors:
                    # Truncate very long concept names for readability
                    display_error = self._truncate_error_message(error)
                    self.logger.warning(f"        - {display_error}")
        
        # Show additional count if there are many more errors
        remaining_errors = len(errors) - total_logged
        if remaining_errors > 0 and not self.verbose:
            self.logger.warning(f"      ... and {remaining_errors} more issues (use --verbose for full details)")
    
    def _truncate_error_message(self, error: str, max_length: int = 120) -> str:
        """Truncate long error messages for better readability."""
        if len(error) <= max_length:
            return error
        
        # Try to preserve the concept name and key information
        parts = error.split(":")
        if len(parts) >= 2:
            concept_part = parts[0]
            reason_part = ":".join(parts[1:])
            
            if len(concept_part) > 60:
                concept_part = concept_part[:57] + "..."
            
            truncated = f"{concept_part}:{reason_part}"
            if len(truncated) > max_length:
                truncated = truncated[:max_length-3] + "..."
            return truncated
        
        return error[:max_length-3] + "..."
    
    def _log_cashflow_fix_results(self, results: dict) -> None:
        """Log the results of cash flow fix for a single company."""
        
        print("\n" + "=" * 60)
        print(f"🔧 CASH FLOW FIX RESULTS - {results['company_cik']}")
        print("=" * 60)
        print(f"📊 Fiscal years processed: {results['fiscal_years_processed']}")
        print(f"✅ Q2 values fixed: {results['q2_fixed']}")
        print(f"✅ Q3 values fixed: {results['q3_fixed']}")
        print(f"⏭️  Q2 values skipped: {results['q2_skipped']}")
        print(f"⏭️  Q3 values skipped: {results['q3_skipped']}")
        
        if results["errors"]:
            print(f"\n⚠️  Errors encountered: {len(results['errors'])}")
            if self.verbose:
                for error in results["errors"][:10]:  # Show max 10 errors
                    print(f"  - {error}")
                if len(results["errors"]) > 10:
                    print(f"  ... and {len(results['errors']) - 10} more errors")
        
        print("=" * 60)
    
    def _log_overall_cashflow_fix_results(self, results: dict) -> None:
        """Log the overall results of cash flow fix for all companies."""
        
        print("\n" + "=" * 60)
        print("🎯 OVERALL CASH FLOW FIX SUMMARY")
        print("=" * 60)
        print(f"📊 Total companies: {results['total_companies']}")
        print(f"✅ Companies processed: {results['companies_processed']}")
        print(f"🔧 Total Q2 values fixed: {results['total_q2_fixed']}")
        print(f"🔧 Total Q3 values fixed: {results['total_q3_fixed']}")
        print(f"⏭️  Total Q2 values skipped: {results['total_q2_skipped']}")
        print(f"⏭️  Total Q3 values skipped: {results['total_q3_skipped']}")
        
        total_fixed = results['total_q2_fixed'] + results['total_q3_fixed']
        print(f"\n💡 Total values corrected: {total_fixed}")
        
        if results["errors"]:
            print(f"\n⚠️  Overall errors: {len(results['errors'])}")
            if self.verbose:
                for error in results["errors"][:10]:
                    print(f"  - {error}")
                if len(results["errors"]) > 10:
                    print(f"  ... and {len(results['errors']) - 10} more errors")
        
        print("=" * 60)


def main():
    """Main entry point."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Financial data processing tool for Q4 calculations and cash flow fixes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Q4 Calculation:
  python app.py                           # Process all companies
  python app.py --cik 0000789019          # Process Microsoft only
  python app.py --cik 0000320193          # Process Apple only
  python app.py --recalculate             # Delete all Q4 values and recalculate for all companies
  python app.py --cik 0000789019 --recalculate  # Delete and recalculate Q4 for Microsoft only
  
  # Cash Flow Fix (convert cumulative Q2/Q3 to quarterly):
  python app.py fix-cashflow                    # Fix all companies
  python app.py fix-cashflow --cik 0001326801   # Fix Meta Platforms only
  python app.py fix-cashflow --verbose          # Fix all companies with detailed output

The Q4 system calculates Q4 using: Q4 = Annual - (Q1 + Q2 + Q3)
The fix-cashflow process converts cumulative values: Q2 = Q2 - Q1, Q3 = Q3 - Q2
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='q4',
        choices=['q4', 'fix-cashflow'],
        help='Command to execute: q4 (default) for Q4 calculation, fix-cashflow for cash flow fix'
    )
    
    parser.add_argument(
        '--cik',
        type=str,
        help='Company CIK to process (e.g., 0000789019 for Microsoft). If not provided, processes all companies.'
    )
    
    parser.add_argument(
        '--recalculate',
        action='store_true',
        help='Delete all existing Q4 values before recalculating. Use with caution! (Q4 mode only)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging showing all error details'
    )
    
    args = parser.parse_args()
    
    app = Q4CalculationApp(verbose=args.verbose)
    
    # Execute the appropriate command
    if args.command == 'fix-cashflow':
        # Cash flow fix mode
        print("\n" + "=" * 60)
        print("🔧 CASH FLOW FIX MODE - Converting Cumulative to Quarterly Values")
        print("=" * 60)
        print("This process will:")
        print("  • Convert Q2 6-month cumulative values to 3-month: Q2 = Q2 - Q1")
        print("  • Convert Q3 9-month cumulative values to 3-month: Q3 = Q3 - Q2")
        print("  • Update values in the database")
        
        if args.cik:
            print(f"\nTarget: Company {args.cik}")
        else:
            print("\nTarget: All companies with cash flow data")
        
        print("=" * 60 + "\n")
        
        if args.recalculate:
            print("⚠️  Warning: --recalculate flag is ignored in fix-cashflow mode")
        
        try:
            app.run_cashflow_fix(args.cik)
            print("\n✅ Cash flow fix completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    
    else:
        # Q4 calculation mode (default)
        # Display processing message
        if args.recalculate:
            if args.cik:
                print(f"⚠️  RECALCULATE MODE: Removing existing Q4 values for company {args.cik}")
            else:
                print("⚠️  RECALCULATE MODE: Removing ALL existing Q4 values from database")
            print("This will delete Q4 values from income_statement and cash_flow_statement")
            print()
        
        if args.cik:
            print(f"Processing Q4 calculations for company: {args.cik}")
        else:
            print("Processing Q4 calculations for all companies...")
        
        try:
            app.run_q4_calculation(args.cik, recalculate=args.recalculate)
            print("Q4 calculation completed successfully!")
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
