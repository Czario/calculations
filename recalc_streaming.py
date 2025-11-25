"""Re-calculate Q4 for Netflix streaming members only."""

from config.database import DatabaseConfig, DatabaseConnection
from services.q4_calculation_service import Q4CalculationService
from repositories.financial_repository import FinancialDataRepository

def recalculate_streaming_members():
    """Delete and re-calculate Q4 for Netflix streaming member concepts."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    company_cik = "0001065280"  # Netflix
    
    print("\n" + "="*80)
    print("RE-CALCULATING NETFLIX STREAMING MEMBER Q4 VALUES")
    print("="*80)
    
    # Get all streaming member concepts
    concepts = list(db.normalized_concepts_quarterly.find({
        "company_cik": company_cik,
        "concept": "nflx:StreamingMember",
        "statement_type": "income_statement"
    }))
    
    print(f"\nFound {len(concepts)} streaming member concepts")
    
    # Delete existing Q4 values for these concepts
    for concept in concepts:
        label = concept.get('label', 'Unknown')
        concept_id = concept['_id']
        
        result = db.concept_values_quarterly.delete_many({
            "concept_id": concept_id,
            "company_cik": company_cik,
            "reporting_period.quarter": 4
        })
        print(f"  {label}: Deleted {result.deleted_count} Q4 records")
    
    # Initialize services
    repo = FinancialDataRepository(db)
    q4_service = Q4CalculationService(repo)
    
    # Get fiscal years
    fiscal_years = repo.get_fiscal_years_for_company(company_cik)
    
    print("\n" + "="*80)
    print("CALCULATING Q4 VALUES")
    print("="*80)
    
    # Calculate Q4 for each concept
    for concept in concepts:
        label = concept.get('label', 'Unknown')
        concept_name = concept.get('concept')
        concept_path = concept.get('path')
        
        print(f"\n{label}:")
        
        success_count = 0
        for fiscal_year in fiscal_years:
            result = q4_service._calculate_q4_generic(
                concept_name,
                concept_path,
                company_cik,
                fiscal_year,
                "income_statement",
                quarterly_concept=concept
            )
            
            if result["success"]:
                success_count += 1
        
        print(f"  Calculated {success_count} Q4 values")
    
    # Verify results
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    
    for concept in concepts:
        label = concept.get('label', 'Unknown')
        concept_id = concept['_id']
        
        q4_count = db.concept_values_quarterly.count_documents({
            "concept_id": concept_id,
            "company_cik": company_cik,
            "reporting_period.quarter": 4
        })
        
        # Get 2024 value
        q4_2024 = db.concept_values_quarterly.find_one({
            "concept_id": concept_id,
            "company_cik": company_cik,
            "reporting_period.fiscal_year": 2024,
            "reporting_period.quarter": 4
        })
        
        value_2024 = f"${q4_2024['value']:,.0f}" if q4_2024 else "NOT FOUND"
        
        print(f"\n{label}:")
        print(f"  Total Q4 values: {q4_count}")
        print(f"  2024 Q4 value: {value_2024}")

if __name__ == "__main__":
    recalculate_streaming_members()
