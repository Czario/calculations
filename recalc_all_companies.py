"""Recalculate Q4 for all companies with dimensional concept conflicts."""

from config.database import DatabaseConfig, DatabaseConnection
from services.q4_calculation_service import Q4CalculationService
from repositories.financial_repository import FinancialDataRepository

def recalculate_all_companies():
    """Recalculate Q4 values for all companies with conflicts."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    # Initialize services
    repo = FinancialDataRepository(db)
    q4_service = Q4CalculationService(repo)
    
    # Companies with conflicts
    companies = [
        ("0000320193", "Apple"),
        ("0000789019", "Microsoft"),
        ("0001065280", "Netflix"),
        ("0001326801", "Meta")
    ]
    
    print("\n" + "="*80)
    print("RECALCULATING Q4 FOR ALL COMPANIES")
    print("="*80)
    
    for cik, name in companies:
        print(f"\n{'='*80}")
        print(f"{name} (CIK: {cik})")
        print(f"{'='*80}")
        
        # Get current Q4 count
        before_count = db.concept_values_quarterly.count_documents({
            "company_cik": cik,
            "reporting_period.quarter": 4
        })
        
        print(f"\nQ4 values before: {before_count}")
        
        # Delete existing Q4 values to recalculate
        delete_result = db.concept_values_quarterly.delete_many({
            "company_cik": cik,
            "reporting_period.quarter": 4
        })
        print(f"Deleted: {delete_result.deleted_count} Q4 records")
        
        # Recalculate income statement Q4
        print("\nCalculating income statement Q4...")
        income_result = q4_service.calculate_q4_for_company(cik)
        print(f"  Processed: {income_result.get('processed_concepts', 0)} concepts")
        print(f"  Success: {income_result.get('successful_calculations', 0)}")
        print(f"  Skipped: {income_result.get('skipped_concepts', 0)}")
        
        # Recalculate cash flows Q4
        print("\nCalculating cash flows Q4...")
        cash_result = q4_service.calculate_q4_for_cash_flow(cik)
        print(f"  Processed: {cash_result.get('processed_concepts', 0)} concepts")
        print(f"  Success: {cash_result.get('successful_calculations', 0)}")
        print(f"  Skipped: {cash_result.get('skipped_concepts', 0)}")
        
        # Get new Q4 count
        after_count = db.concept_values_quarterly.count_documents({
            "company_cik": cik,
            "reporting_period.quarter": 4
        })
        
        print(f"\nQ4 values after: {after_count}")
        print(f"Net change: {after_count - before_count:+d}")
        
        # Check negative values
        negative_count = db.concept_values_quarterly.count_documents({
            "company_cik": cik,
            "reporting_period.quarter": 4,
            "value": {"$lt": 0}
        })
        
        if negative_count > 0:
            print(f"⚠️  Negative Q4 values: {negative_count}")
        else:
            print(f"✅ No negative Q4 values")
    
    print(f"\n{'='*80}")
    print("RECALCULATION COMPLETE FOR ALL COMPANIES")
    print(f"{'='*80}")

if __name__ == "__main__":
    recalculate_all_companies()
