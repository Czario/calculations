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
    
    def run_q4_calculation(self, company_cik: Optional[str] = None) -> None:
        """Run Q4 calculation for specified company or all companies."""
        
        self.logger.info("Starting Q4 calculation process...")
        
        try:
            with DatabaseConnection(self.config) as db:
                repository = FinancialDataRepository(db)
                service = Q4CalculationService(repository)
                
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
        """Process Q4 calculations for a specific company."""
        
        self.logger.info(f"Processing Q4 calculations for company: {company_cik}")
        
        results = service.calculate_q4_for_company(company_cik)
        self._log_results(company_cik, results)
    
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
        
        for company_cik in companies:
            try:
                self.logger.info(f"Processing company {total_processed + 1}/{len(companies)}: {company_cik}")
                
                results = service.calculate_q4_for_company(company_cik)
                self._log_results(company_cik, results)
                
                total_processed += results["processed_concepts"]
                total_successful += results["successful_calculations"]
                total_skipped += results["skipped_concepts"]
                
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
    
    app = Q4CalculationApp()
    
    # Check for company CIK argument
    company_cik = None
    if len(sys.argv) > 1:
        company_cik = sys.argv[1]
        print(f"Processing Q4 calculations for company: {company_cik}")
    else:
        print("Processing Q4 calculations for all companies...")
    
    try:
        app.run_q4_calculation(company_cik)
        print("Q4 calculation completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
