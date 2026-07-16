"""Main application orchestrator for Q4 calculations."""

import logging
from typing import List, Optional, Dict
from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository
from services.q4_calculation_service import Q4CalculationService
from services.cashflow_fix_service import CashFlowFixService
from services.gross_profit_service import GrossProfitService


class Q4CalculationApp:
    """Main application for Q4 calculations."""
    
    def __init__(self, verbose: bool = False):
        self.config = DatabaseConfig()
        self.verbose = verbose
        self.setup_logging()
    
    def resolve_tickers_to_ciks(self, tickers: List[str]) -> Dict[str, Optional[str]]:
        """Resolve ticker symbols to CIK numbers using the companies collection.
        
        Args:
            tickers: List of ticker symbols (e.g., ['AAPL', 'MSFT'])
            
        Returns:
            Dict mapping each ticker to its CIK (or None if not found)
        """
        result = {}
        try:
            with DatabaseConnection(self.config) as db:
                companies_collection = db["companies"]
                for ticker in tickers:
                    ticker_clean = ticker.strip().upper()
                    company = companies_collection.find_one({"ticker_symbol": ticker_clean})
                    if company and company.get("cik"):
                        result[ticker_clean] = company["cik"]
                        if self.verbose:
                            self.logger.info(f"Resolved {ticker_clean} -> CIK {company['cik']} ({company.get('name', '')})")
                    else:
                        result[ticker_clean] = None
                        self.logger.warning(f"Ticker '{ticker_clean}' not found in companies collection")
        except Exception as e:
            self.logger.error(f"Error resolving tickers: {e}")
            for ticker in tickers:
                result[ticker.strip().upper()] = None
        return result
    
    def read_tickers_from_file(self, filepath: str) -> List[str]:
        """Read ticker symbols from a file (one per line, skips blanks/comments).
        
        Args:
            filepath: Path to the ticker file
            
        Returns:
            List of ticker symbols
        """
        tickers = []
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        tickers.append(line)
            if self.verbose:
                self.logger.info(f"Read {len(tickers)} ticker(s) from {filepath}")
        except Exception as e:
            self.logger.error(f"Error reading ticker file {filepath}: {e}")
            raise
        return tickers
    
    def setup_logging(self):
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.WARNING
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def run_q4_calculation(
        self,
        company_cik: Optional[str] = None,
        recalculate: bool = False,
        statement: str = "all"
    ) -> None:
        """Run Q4 calculation for specified company or all companies.
        
        Args:
            company_cik: Company CIK to process. If None, processes all companies.
            recalculate: If True, removes existing Q4 values before recalculating.
            statement: Which statement to calculate — "is" (income statement),
                       "cf" (cash flows), or "all" (both). Default: "all".
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
                    self._process_company(service, company_cik, statement)
                else:
                    # Process all companies
                    self._process_all_companies(service, repository, statement)
                    
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise
    
    def run_gross_profit_calculation(
        self,
        company_cik: Optional[str] = None,
        recalculate: bool = False
    ) -> None:
        """Run Gross Profit calculation and insertion process.
        
        This process:
        - Finds Total Revenue and Cost of Revenues concepts
        - Calculates: Gross Profit = Total Revenues - Cost of Revenues
        - Creates Gross Profit concept if not exists (us-gaap:GrossProfit, path: 003)
        - Inserts calculated values for all fiscal years and quarters
        
        Args:
            company_cik: Company CIK to process. If None, processes all companies.
            recalculate: If True, recalculates even if Gross Profit already exists.
        """
        
        if self.verbose:
            self.logger.info("Starting Gross Profit calculation process...")
        
        try:
            with DatabaseConnection(self.config) as db:
                repository = FinancialDataRepository(db)
                service = GrossProfitService(repository, verbose=self.verbose)
                
                if company_cik:
                    # Process specific company
                    print(f"Processing Gross Profit calculation for company: {company_cik}")
                    if recalculate:
                        print("⚠️  RECALCULATE MODE: Will overwrite existing Gross Profit values")
                    print("=" * 60)
                    
                    results = service.calculate_gross_profit_for_company(company_cik, recalculate)
                    self._log_gross_profit_results(results)
                else:
                    # Process all companies
                    print("Processing Gross Profit calculation for all companies...")
                    if recalculate:
                        print("⚠️  RECALCULATE MODE: Will overwrite existing Gross Profit values")
                    print("=" * 60)
                    
                    overall_results = service.calculate_gross_profit_for_all_companies(recalculate)
                    self._log_overall_gross_profit_results(overall_results)
                    
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise
    
    def run_cashflow_fix(
        self, 
        company_cik: Optional[str] = None,
        fiscal_year: Optional[int] = None,
        quarter: Optional[int] = None,
        force: bool = False
    ) -> None:
        """Run cash flow fix process to convert cumulative Q2/Q3 values to quarterly values.
        
        This process:
        - Converts Q2 6-month cumulative values to 3-month quarterly: Q2 = Q2 - Q1
        - Converts Q3 9-month cumulative values to 3-month quarterly: Q3 = Q3 - Q2
        - Skips already-fixed records unless force=True
        
        Args:
            company_cik: Company CIK to process. If None, processes all companies.
            fiscal_year: Optional specific fiscal year to fix. If None, fixes all years.
            quarter: Optional specific quarter to fix (2 or 3). If None, fixes both Q2 and Q3.
            force: If True, re-fix all records regardless of whether they were already fixed.
        """
        
        if self.verbose:
            self.logger.info("Starting cash flow fix process...")
        
        try:
            with DatabaseConnection(self.config) as db:
                repository = FinancialDataRepository(db)
                service = CashFlowFixService(repository, verbose=self.verbose, force=force)
                
                if company_cik:
                    # Process specific company
                    target_info = []
                    if fiscal_year:
                        target_info.append(f"FY {fiscal_year}")
                    if quarter:
                        target_info.append(f"Q{quarter}")
                    if force:
                        target_info.append("FORCE MODE")
                    
                    target_str = " - " + ", ".join(target_info) if target_info else ""
                    print(f"Processing cash flow fix for company: {company_cik}{target_str}")
                    print("=" * 60)
                    
                    results = service.fix_cumulative_values_for_company(company_cik, fiscal_year, quarter)
                    self._log_cashflow_fix_results(results)
                else:
                    # Process all companies
                    force_info = " [FORCE MODE]" if force else ""
                    print(f"Processing cash flow fix for all companies...{force_info}")
                    if fiscal_year or quarter:
                        print("⚠️  Warning: fiscal_year and quarter filters are ignored when processing all companies")
                    print("=" * 60)
                    
                    overall_results = service.fix_all_companies()
                    self._log_overall_cashflow_fix_results(overall_results)
                    
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise
    
    def _process_company(
        self,
        service: Q4CalculationService,
        company_cik: str,
        statement: str = "all"
    ) -> None:
        """Process Q4 calculations for a specific company.
        
        Args:
            statement: "is", "cf", or "all".
        """
        
        if self.verbose:
            self.logger.info(f"Processing Q4 calculations for company: {company_cik}")
        
        # Process income statement
        if statement in ("is", "all"):
            if self.verbose:
                self.logger.info(f"Calculating income statement Q4 for {company_cik}...")
            income_results = service.calculate_q4_for_company(company_cik)
            self._log_results(company_cik, income_results)
        
        # Process cash flow statement
        if statement in ("cf", "all"):
            if self.verbose:
                self.logger.info(f"Calculating cash flow statement Q4 for {company_cik}...")
            cashflow_results = service.calculate_q4_for_cash_flow(company_cik)
            self._log_results(company_cik, cashflow_results)
    
    def _process_all_companies(
        self, 
        service: Q4CalculationService, 
        repository: FinancialDataRepository,
        statement: str = "all"
    ) -> None:
        """Process Q4 calculations for all companies.
        
        Args:
            statement: "is", "cf", or "all".
        """
        
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
                if statement in ("is", "all"):
                    if self.verbose:
                        self.logger.info(f"  → Income Statement Q4 calculations")
                    income_results = service.calculate_q4_for_company(company_cik)
                    self._log_results(company_cik, income_results)
                    
                    total_processed += income_results["processed_concepts"]
                    total_successful += income_results["successful_calculations"]
                    total_skipped += income_results["skipped_concepts"]
                
                # Process cash flow statement
                if statement in ("cf", "all"):
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
        print(f"⏩ Q2 already fixed: {results.get('q2_already_fixed', 0)}")
        print(f"⏩ Q3 already fixed: {results.get('q3_already_fixed', 0)}")
        print(f"⏭️  Q2 values skipped (no Q1): {results['q2_skipped']}")
        print(f"⏭️  Q3 values skipped (no Q2): {results['q3_skipped']}")
        
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
        print(f"⏩ Total Q2 already fixed: {results.get('total_q2_already_fixed', 0)}")
        print(f"⏩ Total Q3 already fixed: {results.get('total_q3_already_fixed', 0)}")
        print(f"⏭️  Total Q2 values skipped (no Q1): {results['total_q2_skipped']}")
        print(f"⏭️  Total Q3 values skipped (no Q2): {results['total_q3_skipped']}")
        
        total_fixed = results['total_q2_fixed'] + results['total_q3_fixed']
        total_already_fixed = results.get('total_q2_already_fixed', 0) + results.get('total_q3_already_fixed', 0)
        print(f"\n💡 Total values corrected this run: {total_fixed}")
        print(f"💡 Total values already fixed (skipped): {total_already_fixed}")
        
        if results["errors"]:
            print(f"\n⚠️  Overall errors: {len(results['errors'])}")
            if self.verbose:
                for error in results["errors"][:10]:
                    print(f"  - {error}")
                if len(results["errors"]) > 10:
                    print(f"  ... and {len(results['errors']) - 10} more errors")
        
        print("=" * 60)
    
    def _log_gross_profit_results(self, results: dict) -> None:
        """Log the results of Gross Profit calculation for a single company."""
        
        print("\n" + "=" * 60)
        print(f"💰 GROSS PROFIT CALCULATION RESULTS - {results['company_cik']}")
        print("=" * 60)
        print(f"📊 Fiscal years processed: {results['fiscal_years_processed']}")
        print(f"✅ Quarterly values inserted: {results['quarterly_values_inserted']}")
        print(f"✅ Annual values inserted: {results['annual_values_inserted']}")
        
        if results['quarterly_concepts_created'] > 0 or results['annual_concepts_created'] > 0:
            print(f"🆕 Concepts created: {results['quarterly_concepts_created']} quarterly, "
                  f"{results['annual_concepts_created']} annual")
        
        if results["skipped_periods"]:
            print(f"⏭️  Periods skipped: {len(results['skipped_periods'])}")
            if self.verbose and results["skipped_periods"]:
                print("  Skipped periods:")
                for period in results["skipped_periods"][:10]:
                    print(f"    - {period}")
                if len(results["skipped_periods"]) > 10:
                    print(f"    ... and {len(results['skipped_periods']) - 10} more")
        
        if results["errors"]:
            print(f"\n⚠️  Errors encountered: {len(results['errors'])}")
            if self.verbose:
                for error in results["errors"][:10]:
                    print(f"  - {error}")
                if len(results["errors"]) > 10:
                    print(f"  ... and {len(results['errors']) - 10} more errors")
        
        print("=" * 60)
    
    def _log_overall_gross_profit_results(self, results: dict) -> None:
        """Log the overall results of Gross Profit calculation for all companies."""
        
        print("\n" + "=" * 60)
        print("🎯 OVERALL GROSS PROFIT CALCULATION SUMMARY")
        print("=" * 60)
        print(f"📊 Companies processed: {results['companies_processed']}")
        print(f"✅ Companies successful: {results['companies_successful']}")
        print(f"❌ Companies failed: {results['companies_failed']}")
        print(f"💰 Total quarterly values: {results['total_quarterly_values']}")
        print(f"💰 Total annual values: {results['total_annual_values']}")
        print(f"🆕 Total concepts created: {results['total_concepts_created']}")
        
        total_values = results['total_quarterly_values'] + results['total_annual_values']
        print(f"\n💡 Total Gross Profit values inserted: {total_values}")
        
        if results['companies_processed'] > 0:
            success_rate = (results['companies_successful'] / results['companies_processed']) * 100
            print(f"🎯 Success rate: {success_rate:.1f}%")
        
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
  uv run app.py --calculate-q4 --all-companies                                         # Process all companies (IS + CF)
  uv run app.py --calculate-q4 --cik 0000789019                                        # Process Microsoft (IS + CF)
  uv run app.py --calculate-q4 --cik 0000789019 0000320193                             # Process Microsoft + Apple
  uv run app.py --calculate-q4 --cik 0000320193 --statement is                         # Income statement only
  uv run app.py --calculate-q4 --cik 0000320193 --statement cf                         # Cash flows only
  uv run app.py --calculate-q4 --cik 0000320193 0000789019 --statement is              # Multiple CIKs, IS only
  uv run app.py --calculate-q4 --all-companies --statement is                          # All companies, IS only
  uv run app.py --calculate-q4 --all-companies --recalculate-q4                        # Delete all Q4 and recalculate
  uv run app.py --calculate-q4 --cik 0000789019 --recalculate-q4                       # Delete and recalculate Microsoft
  uv run app.py --calculate-q4 --file process_stocks.txt                               # Process tickers from file
  uv run app.py --calculate-q4 --file process_stocks.txt --statement is                # Process tickers, IS only
  
  # Cash Flow Fix (convert cumulative Q2/Q3 to quarterly):
  uv run app.py --fix-cashflow --all-companies                    # Fix all companies (incremental)
  uv run app.py --fix-cashflow --cik 0001326801                   # Fix Meta Platforms (incremental)
  uv run app.py --fix-cashflow --cik 0001326801 --fiscal-year 2025   # Fix Meta FY 2025 only
  uv run app.py --fix-cashflow --cik 0001326801 --quarter 2       # Fix Meta Q2 only, all years
  uv run app.py --fix-cashflow --cik 0001326801 --fiscal-year 2025 --quarter 2  # Fix Meta FY2025 Q2
  uv run app.py --fix-cashflow --all-companies --verbose          # Fix all with detailed output
  uv run app.py --fix-cashflow --all-companies --force            # Re-fix ALL records (ignore cashflow_fixed flag)
  uv run app.py --fix-cashflow --cik 0001326801 --force           # Re-fix Meta (ignore cashflow_fixed flag)
  uv run app.py --fix-cashflow --file process_stocks.txt          # Fix tickers from file
  
  # Gross Profit Calculation (Gross Profit = Total Revenues - Cost of Revenues):
  uv run app.py --cal-gross-profit --all-companies                # Process all companies
  uv run app.py --cal-gross-profit --cik 0000789019               # Process Microsoft only
  uv run app.py --cal-gross-profit --all-companies --recalculate  # Recalculate existing values
  uv run app.py --cal-gross-profit --cik 0000789019 --verbose     # Process with detailed output
  uv run app.py --cal-gross-profit --file process_stocks.txt      # Process tickers from file

The Q4 system calculates Q4 using: Q4 = Annual - (Q1 + Q2 + Q3)
The --fix-cashflow process converts cumulative values: Q2 = Q2 - Q1, Q3 = Q3 - Q2
  - By default, already-fixed records are skipped (incremental processing)
  - Use --force to re-fix all records regardless of cashflow_fixed status
The --cal-gross-profit calculates: Gross Profit = Total Revenues - Cost of Revenues

Note: You must specify either --calculate-q4, --fix-cashflow, or --cal-gross-profit
Note: You must specify either --all-companies, --cik <CIK> [<CIK> ...], or --file <FILE>
Note: --file <FILE> reads ticker symbols (one per line) and resolves them to CIKs via the companies collection
Note: --statement works only with --calculate-q4  (choices: is, cf, all — default: all)
Note: --fiscal-year and --quarter work only with --fix-cashflow and a single --cik
Note: --recalculate works with --cal-gross-profit to overwrite existing values
Note: --force works with --fix-cashflow to re-fix already fixed records
        """
    )
    
    parser.add_argument(
        '--calculate-q4',
        action='store_true',
        help='Run Q4 calculation process'
    )
    
    parser.add_argument(
        '--statement',
        type=str,
        choices=['is', 'cf', 'all'],
        default='all',
        help=(
            'Which statement to calculate Q4 for. '
            '"is" = income statement only, '
            '"cf" = cash flows only, '
            '"all" = both (default). '
            'Only applies to --calculate-q4.'
        )
    )
    
    parser.add_argument(
        '--fix-cashflow',
        action='store_true',
        help='Run cash flow fix process (convert cumulative Q2/Q3 to quarterly values)'
    )
    
    parser.add_argument(
        '--cal-gross-profit',
        action='store_true',
        help='Calculate and insert Gross Profit values (Gross Profit = Total Revenues - Cost of Revenues)'
    )
    
    parser.add_argument(
        '--all-companies',
        action='store_true',
        help='Process all companies in the database'
    )
    
    parser.add_argument(
        '--cik',
        type=str,
        nargs='+',
        metavar='CIK',
        help='One or more company CIKs to process (e.g., --cik 0000789019 0000320193)'
    )
    
    parser.add_argument(
        '--file',
        type=str,
        metavar='FILE',
        help='Path to a file with ticker symbols (one per line). Resolves tickers to CIKs via the companies collection.'
    )
    
    parser.add_argument(
        '--recalculate-q4',
        action='store_true',
        help='Delete all existing Q4 values before recalculating. Use with caution! (Only with --calculate-q4)'
    )
    
    parser.add_argument(
        '--recalculate',
        action='store_true',
        help='Recalculate and overwrite existing values (works with --cal-gross-profit)'
    )
    
    parser.add_argument(
        '--fiscal-year',
        type=int,
        help='Specific fiscal year to fix (e.g., 2025). Only with --fix-cashflow and --cik. If not specified, fixes all years.'
    )
    
    parser.add_argument(
        '--quarter',
        type=int,
        choices=[2, 3],
        help='Specific quarter to fix (2 or 3). Only with --fix-cashflow and --cik. If not specified, fixes both Q2 and Q3.'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-fix already fixed records. Only with --fix-cashflow. By default, already-fixed records are skipped.'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging showing all error details'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.calculate_q4 and not args.fix_cashflow and not args.cal_gross_profit:
        parser.error("You must specify either --calculate-q4, --fix-cashflow, or --cal-gross-profit")
    
    # Check for mutually exclusive operations
    operations = sum([args.calculate_q4, args.fix_cashflow, args.cal_gross_profit])
    if operations > 1:
        parser.error("Cannot specify multiple operations. Choose one: --calculate-q4, --fix-cashflow, or --cal-gross-profit")
    
    if not args.all_companies and not args.cik and not args.file:
        parser.error("You must specify --all-companies, --cik <CIK> [<CIK> ...], or --file <FILE>")
    
    if sum([bool(args.all_companies), bool(args.cik), bool(args.file)]) > 1:
        parser.error("Cannot specify multiple target options. Choose one: --all-companies, --cik, or --file")
    
    if args.recalculate_q4 and not args.calculate_q4:
        parser.error("--recalculate-q4 can only be used with --calculate-q4")
    
    if args.statement != 'all' and not args.calculate_q4:
        parser.error("--statement can only be used with --calculate-q4")
    
    if args.recalculate and not args.cal_gross_profit:
        parser.error("--recalculate can only be used with --cal-gross-profit")
    
    # Validate --force (only for fix-cashflow)
    if args.force and not args.fix_cashflow:
        parser.error("--force can only be used with --fix-cashflow")
    
    # Validate fiscal_year and quarter (only for fix-cashflow with specific company)
    if (args.fiscal_year or args.quarter) and not args.fix_cashflow:
        parser.error("--fiscal-year and --quarter can only be used with --fix-cashflow")
    
    if (args.fiscal_year or args.quarter) and args.all_companies:
        parser.error("--fiscal-year and --quarter can only be used with --cik or --file, not --all-companies")
    
    if (args.fiscal_year or args.quarter) and args.cik and len(args.cik) > 1:
        parser.error("--fiscal-year and --quarter can only be used with a single --cik")
    
    if (args.fiscal_year or args.quarter) and args.file:
        # --file may resolve to multiple CIKs; warn but don't block — validation happens at runtime
        pass
    
    # Build the list of CIKs to process (None → all companies handled inside app methods)
    cik_list: Optional[List[str]] = args.cik if args.cik else None  # None means all-companies mode
    ticker_source: Optional[str] = None  # Track if CIKs came from a ticker file
    
    # Resolve tickers from --file to CIKs
    if args.file:
        app = Q4CalculationApp(verbose=args.verbose)
        tickers = app.read_tickers_from_file(args.file)
        if not tickers:
            print(f"❌ No ticker symbols found in {args.file}")
            sys.exit(1)
        resolution = app.resolve_tickers_to_ciks(tickers)
        cik_list = []
        not_found = []
        for ticker, cik in resolution.items():
            if cik:
                cik_list.append(cik)
            else:
                not_found.append(ticker)
        if not_found:
            print(f"⚠️  Ticker(s) not found in companies collection: {', '.join(not_found)}")
        if not cik_list:
            print("❌ No valid CIKs resolved from the ticker file")
            sys.exit(1)
        ticker_source = args.file
        if app.verbose:
            app.logger.info(f"Resolved {len(cik_list)} CIK(s) from ticker file {args.file}")
        
        # Warn if --fiscal-year/--quarter used with multiple CIKs from file
        if (args.fiscal_year or args.quarter) and len(cik_list) > 1:
            print(f"⚠️  Warning: --fiscal-year/--quarter with --file resolved to {len(cik_list)} companies; filters will be applied per-company")
    
    app = Q4CalculationApp(verbose=args.verbose)
    
    # Execute the appropriate command
    if args.cal_gross_profit:
        # Gross Profit calculation mode
        print("\n" + "=" * 60)
        print("💰 GROSS PROFIT CALCULATION MODE")
        print("=" * 60)
        print("This process will:")
        print("  • Find Total Revenues and Cost of Revenues concepts")
        print("  • Calculate: Gross Profit = Total Revenues - Cost of Revenues")
        print("  • Create Gross Profit concept (us-gaap:GrossProfit, path: 003)")
        print("  • Insert calculated values for all fiscal years and quarters")
        
        if cik_list:
            if ticker_source:
                print(f"\nTarget: {len(cik_list)} company/companies from ticker file {ticker_source}")
            else:
                print(f"\nTarget: {len(cik_list)} company/companies: {', '.join(cik_list)}")
        else:
            print("\nTarget: All companies")
        
        if args.recalculate:
            print("\n⚠️  RECALCULATE MODE: Will overwrite existing Gross Profit values")
        
        print("=" * 60 + "\n")
        
        try:
            targets = cik_list if cik_list else [None]
            for cik in targets:
                app.run_gross_profit_calculation(cik, recalculate=args.recalculate)
            print("\n✅ Gross Profit calculation completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    
    elif args.fix_cashflow:
        # Cash flow fix mode
        print("\n" + "=" * 60)
        print("🔧 CASH FLOW FIX MODE - Converting Cumulative to Quarterly Values")
        print("=" * 60)
        print("This process will:")
        print("  • Convert Q2 6-month cumulative values to 3-month: Q2 = Q2 - Q1")
        print("  • Convert Q3 9-month cumulative values to 3-month: Q3 = Q3 - Q2")
        print("  • Update values in the database")
        
        if cik_list:
            if ticker_source:
                target_parts = [f"{len(cik_list)} company/companies from ticker file {ticker_source}"]
            else:
                target_parts = [f"{len(cik_list)} company/companies: {', '.join(cik_list)}"]
            if args.fiscal_year:
                target_parts.append(f"FY {args.fiscal_year}")
            if args.quarter:
                target_parts.append(f"Q{args.quarter} only")
            if args.force:
                target_parts.append("FORCE MODE")
            print(f"\nTarget: {', '.join(target_parts)}")
        else:
            force_info = " [FORCE MODE]" if args.force else ""
            print(f"\nTarget: All companies with cash flow data{force_info}")
        
        print("=" * 60 + "\n")
        
        try:
            targets = cik_list if cik_list else [None]
            for cik in targets:
                app.run_cashflow_fix(cik, args.fiscal_year, args.quarter, args.force)
            print("\n✅ Cash flow fix completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    
    elif args.calculate_q4:
        # Q4 calculation mode
        statement_labels = {'is': 'Income Statement', 'cf': 'Cash Flows', 'all': 'Income Statement + Cash Flows'}
        statement_label = statement_labels[args.statement]

        # Display processing message
        if args.recalculate_q4:
            if cik_list:
                if ticker_source:
                    print(f"⚠️  RECALCULATE MODE: Removing existing Q4 values for {len(cik_list)} company/companies from ticker file {ticker_source}")
                else:
                    print(f"⚠️  RECALCULATE MODE: Removing existing Q4 values for: {', '.join(cik_list)}")
            else:
                print("⚠️  RECALCULATE MODE: Removing ALL existing Q4 values from database")
            print("This will delete Q4 values from income_statement and cash_flow_statement")
            print()
        
        if cik_list:
            if ticker_source:
                print(f"Processing Q4 calculations for {len(cik_list)} company/companies from ticker file {ticker_source}  [{statement_label}]")
            else:
                print(f"Processing Q4 calculations for {len(cik_list)} company/companies: {', '.join(cik_list)}  [{statement_label}]")
        else:
            print(f"Processing Q4 calculations for all companies...  [{statement_label}]")
        
        try:
            targets = cik_list if cik_list else [None]
            for cik in targets:
                app.run_q4_calculation(cik, recalculate=args.recalculate_q4, statement=args.statement)
            print("Q4 calculation completed successfully!")
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
