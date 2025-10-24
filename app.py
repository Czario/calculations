"""Main application orchestrator for Q4 calculations."""

import logging
from typing import List, Optional
from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository
from services.q4_calculation_service import Q4CalculationService


class Q4CalculationApp:
    """Main application for Q4 calculations."""
    
    def __init__(self):
        self.config = DatabaseConfig()
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def run_q4_calculation(self, company_cik: Optional[str] = None, recalculate: bool = False) -> None:
        """Run Q4 calculation for specified company or all companies.
        
        Args:
            company_cik: Company CIK to process. If None, processes all companies.
            recalculate: If True, removes existing Q4 values before recalculating.
        """
        
        self.logger.info("Starting Q4 calculation process...")
        
        try:
            with DatabaseConnection(self.config) as db:
                repository = FinancialDataRepository(db)
                service = Q4CalculationService(repository)
                
                # Remove existing Q4 values if recalculate flag is set
                if recalculate:
                    self.logger.info("Recalculate mode: Removing existing Q4 values...")
                    deleted_count = repository.delete_all_q4_values(company_cik)
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
    
    def _process_company(self, service: Q4CalculationService, company_cik: str) -> None:
        """Process Q4 calculations for a specific company (both income statement and cash flow)."""
        
        self.logger.info(f"Processing Q4 calculations for company: {company_cik}")
        
        # Process income statement
        self.logger.info(f"Calculating income statement Q4 for {company_cik}...")
        income_results = service.calculate_q4_for_company(company_cik)
        self._log_results(company_cik, income_results)
        
        # Process cash flow statement
        self.logger.info(f"Calculating cash flow statement Q4 for {company_cik}...")
        cashflow_results = service.calculate_q4_for_cash_flow(company_cik)
        self._log_results(company_cik, cashflow_results)
    
    def _process_all_companies(
        self, 
        service: Q4CalculationService, 
        repository: FinancialDataRepository
    ) -> None:
        """Process Q4 calculations for all companies."""
        
        self.logger.info("Processing Q4 calculations for all companies...")
        
        # Get all unique company CIKs
        companies = self._get_all_companies(repository)
        
        if not companies:
            self.logger.warning("No companies found in the database")
            return
        
        self.logger.info(f"Found {len(companies)} companies to process")
        
        total_processed = 0
        total_successful = 0
        total_skipped = 0
        
        for idx, company_cik in enumerate(companies, 1):
            try:
                self.logger.info(f"Processing company {idx}/{len(companies)}: {company_cik}")
                
                # Process income statement
                self.logger.info(f"  → Income Statement Q4 calculations")
                income_results = service.calculate_q4_for_company(company_cik)
                self._log_results(company_cik, income_results)
                
                total_processed += income_results["processed_concepts"]
                total_successful += income_results["successful_calculations"]
                total_skipped += income_results["skipped_concepts"]
                
                # Process cash flow statement
                self.logger.info(f"  → Cash Flow Statement Q4 calculations")
                cashflow_results = service.calculate_q4_for_cash_flow(company_cik)
                self._log_results(company_cik, cashflow_results)
                
                total_processed += cashflow_results["processed_concepts"]
                total_successful += cashflow_results["successful_calculations"]
                total_skipped += cashflow_results["skipped_concepts"]
                
            except Exception as e:
                self.logger.error(f"Error processing company {company_cik}: {e}")
        
        # Log summary
        self.logger.info("=" * 50)
        self.logger.info("Q4 CALCULATION SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Companies processed: {len(companies)}")
        self.logger.info(f"Concepts processed: {total_processed}")
        self.logger.info(f"Successful Q4 calculations: {total_successful}")
        self.logger.info(f"Skipped concepts: {total_skipped}")
        self.logger.info("=" * 50)
    
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
        """Log the results of Q4 calculation for a company."""
        
        self.logger.info(f"Results for company {company_cik}:")
        self.logger.info(f"  - Processed concepts: {results['processed_concepts']}")
        self.logger.info(f"  - Successful calculations: {results['successful_calculations']}")
        self.logger.info(f"  - Skipped concepts: {results['skipped_concepts']}")
        
        if results["errors"]:
            self.logger.warning(f"  - Errors/Warnings: {len(results['errors'])}")
            for error in results["errors"][:5]:  # Show first 5 errors
                self.logger.warning(f"    • {error}")
            if len(results["errors"]) > 5:
                self.logger.warning(f"    ... and {len(results['errors']) - 5} more")


def main():
    """Main entry point."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Calculate Q4 values for financial statements (income statement and cash flows)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py                           # Process all companies
  python app.py --cik 0000789019          # Process Microsoft only
  python app.py --cik 0000320193          # Process Apple only
  python app.py --recalculate             # Delete all Q4 values and recalculate for all companies
  python app.py --cik 0000789019 --recalculate  # Delete and recalculate Q4 for Microsoft only

The system calculates Q4 using: Q4 = Annual - (Q1 + Q2 + Q3)
All four values (Annual, Q1, Q2, Q3) must be present for calculation.
        """
    )
    
    parser.add_argument(
        '--cik',
        type=str,
        help='Company CIK to process (e.g., 0000789019 for Microsoft). If not provided, processes all companies.'
    )
    
    parser.add_argument(
        '--recalculate',
        action='store_true',
        help='Delete all existing Q4 values before recalculating. Use with caution!'
    )
    
    args = parser.parse_args()
    
    app = Q4CalculationApp()
    
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
