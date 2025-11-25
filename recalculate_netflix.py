"""Re-calculate Q4 values for Netflix with fixed dimensional matching logic."""

from config.database import DatabaseConfig, DatabaseConnection
from services.q4_calculation_service import Q4CalculationService
from repositories.financial_repository import FinancialDataRepository

def recalculate_netflix_q4():
    """Delete and re-calculate all Q4 values for Netflix."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    company_cik = "0001065280"  # Netflix
    
    print("\n" + "="*80)
    print("RE-CALCULATING NETFLIX Q4 VALUES")
    print("="*80)
    
    # Check current state
    current_q4 = db.concept_values_quarterly.count_documents({
        "company_cik": company_cik,
        "reporting_period.quarter": 4
    })
    print(f"\nCurrent Q4 values in database: {current_q4}")
    
    # Delete existing Q4 values
    print("\nDeleting existing Q4 values...")
    result = db.concept_values_quarterly.delete_many({
        "company_cik": company_cik,
        "reporting_period.quarter": 4
    })
    print(f"Deleted {result.deleted_count} Q4 records")
    
    # Initialize services
    repo = FinancialDataRepository(db)
    q4_service = Q4CalculationService(repo)
    
    # Re-calculate Q4 for income statement
    print("\n" + "="*80)
    print("CALCULATING Q4 FOR INCOME STATEMENT")
    print("="*80)
    income_q4_count = q4_service.calculate_q4_for_company(company_cik)
    print(f"\nCalculated {income_q4_count} Q4 values for income statement")
    
    # Re-calculate Q4 for cash flows
    print("\n" + "="*80)
    print("CALCULATING Q4 FOR CASH FLOWS")
    print("="*80)
    cash_q4_count = q4_service.calculate_q4_for_cash_flow(company_cik)
    print(f"\nCalculated {cash_q4_count} Q4 values for cash flows")
    
    # Check new state
    new_q4 = db.concept_values_quarterly.count_documents({
        "company_cik": company_cik,
        "reporting_period.quarter": 4
    })
    print("\n" + "="*80)
    print(f"New Q4 values in database: {new_q4}")
    print(f"Total Q4 values calculated: {income_q4_count + cash_q4_count}")
    print("="*80)
    
    # Verify no negative values
    negative_q4 = list(db.concept_values_quarterly.find({
        "company_cik": company_cik,
        "reporting_period.quarter": 4,
        "value": {"$lt": 0}
    }))
    
    if negative_q4:
        print(f"\n⚠️ WARNING: Found {len(negative_q4)} negative Q4 values:")
        for record in negative_q4[:10]:  # Show first 10
            concept_id = record.get("concept_id")
            concept = db.normalized_concepts_quarterly.find_one({"_id": concept_id})
            concept_name = concept.get("concept") if concept else "Unknown"
            concept_label = concept.get("label") if concept else "Unknown"
            value = record.get("value", 0)
            year = record.get("reporting_period", {}).get("fiscal_year")
            print(f"  - {concept_name} ({concept_label}) | Year: {year} | Value: {value:,.0f}")
    else:
        print("\n✅ No negative Q4 values found!")
    
    # Test specific dimensional concept
    print("\n" + "="*80)
    print("VERIFYING UCAN STREAMING MEMBER Q4 (2024)")
    print("="*80)
    
    # Find UCAN streaming member concept
    ucan_concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": company_cik,
        "concept": "nflx:StreamingMember",
        "statement_type": "income_statement",
        "label": "United States and Canada (UCAN)"
    })
    
    if ucan_concept:
        ucan_q4 = db.concept_values_quarterly.find_one({
            "concept_id": ucan_concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": 2024,
            "reporting_period.quarter": 4
        })
        
        if ucan_q4:
            print(f"UCAN Q4 2024 Value: ${ucan_q4['value']:,.0f}")
            print(f"Expected: $4,517,018,000")
            if abs(ucan_q4['value'] - 4517018000) < 1000:  # Within $1000
                print("✅ CORRECT!")
            else:
                print("❌ STILL WRONG!")
        else:
            print("❌ Q4 value not found!")
    else:
        print("❌ UCAN concept not found!")
    
    print("\n" + "="*80)
    print("RE-CALCULATION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    recalculate_netflix_q4()
