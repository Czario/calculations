#!/usr/bin/env python3

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository
from services.q4_calculation_service import Q4CalculationService

def test_parent_based_with_recalculation():
    """Test parent-based matching with forced recalculation to see actual Q4 values."""
    
    config = DatabaseConfig()
    connection = DatabaseConnection(config)
    db = connection.connect()
    repository = FinancialDataRepository(db)
    service = Q4CalculationService(repository)

    print("=== TESTING PARENT-BASED MATCHING WITH FORCED RECALCULATION ===")
    
    company_cik = "0000789019"  # Microsoft
    fiscal_year = 2025  # Use FY2025 for testing
    
    # First, let's check if Q4 exists and delete it to force recalculation
    concepts_to_test = [
        ("msft:GamingMember", "001.001", "Gaming Member"),
        ("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "001", "Total Revenue"),
        ("msft:IntelligentCloudMember", "001.002", "Intelligent Cloud"),
        ("msft:ProductivityAndBusinessProcessesMember", "001.001", "Productivity & Business Processes")
    ]
    
    for concept_name, concept_path, friendly_name in concepts_to_test:
        print(f"\n=== {friendly_name} ===")
        
        # First, delete any existing Q4 to force recalculation
        delete_result = db.concept_values_quarterly.delete_many({
            "company_cik": company_cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": 4,
            "calculated": True
        })
        
        if delete_result.deleted_count > 0:
            print(f"   Deleted {delete_result.deleted_count} existing Q4 records for clean test")
        
        # Get quarterly data to see what we're working with
        quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
            concept_name, concept_path, company_cik, fiscal_year, "income_statement"
        )
        
        print(f"   Concept: {concept_name}")
        print(f"   Path: {concept_path}")
        print(f"   Found quarterly concept: {quarterly_data.concept_id is not None}")
        
        if quarterly_data.concept_id:
            print(f"   Q1: {quarterly_data.q1_value:,}" if quarterly_data.q1_value else "   Q1: None")
            print(f"   Q2: {quarterly_data.q2_value:,}" if quarterly_data.q2_value else "   Q2: None")
            print(f"   Q3: {quarterly_data.q3_value:,}" if quarterly_data.q3_value else "   Q3: None")
            print(f"   Annual: {quarterly_data.annual_value:,}" if quarterly_data.annual_value else "   Annual: None")
            print(f"   Can calculate Q4: {quarterly_data.can_calculate_q4()}")
            
            if quarterly_data.can_calculate_q4():
                expected_q4 = quarterly_data.calculate_q4()
                print(f"   Expected Q4: {expected_q4:,}")
                
                # Now test the Q4 calculation with parent-based matching
                result = service._calculate_q4_generic(
                    concept_name, concept_path, company_cik, fiscal_year, "income_statement"
                )
                
                print(f"   Calculation result: {result}")
                
                if result["success"]:
                    print(f"   ✅ Q4 calculation successful!")
                    
                    # Verify the Q4 was actually created
                    q4_check = repository.check_q4_exists_by_name_and_path(
                        concept_name, concept_path, company_cik, fiscal_year, "income_statement"
                    )
                    print(f"   Q4 exists in database: {q4_check}")
                else:
                    print(f"   ❌ Q4 calculation failed: {result.get('reason')}")
            else:
                missing_values = []
                if quarterly_data.q1_value is None:
                    missing_values.append("Q1")
                if quarterly_data.q2_value is None:
                    missing_values.append("Q2")
                if quarterly_data.q3_value is None:
                    missing_values.append("Q3")
                if quarterly_data.annual_value is None:
                    missing_values.append("Annual")
                print(f"   ❌ Cannot calculate Q4 - Missing: {', '.join(missing_values)}")
        else:
            print("   ❌ Quarterly concept not found")
    
    print("\n=== VERIFICATION: Parent-Based vs Path-Based Results ===")
    
    # Compare Gaming Member (dimensional) vs Total Revenue (parent)
    gaming_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        "msft:GamingMember", "001.001", company_cik, fiscal_year, "income_statement"
    )
    
    total_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "001", company_cik, fiscal_year, "income_statement"
    )
    
    if gaming_data.annual_value and total_data.annual_value:
        print(f"Gaming Member annual: {gaming_data.annual_value:,}")
        print(f"Total Revenue annual: {total_data.annual_value:,}")
        
        if gaming_data.annual_value != total_data.annual_value:
            print("✅ Parent-based matching working: Dimensional concept uses its own annual value")
        else:
            print("⚠️  Values are identical - may indicate fallback to parent")
            
        # Calculate expected Q4s
        if gaming_data.can_calculate_q4() and total_data.can_calculate_q4():
            gaming_q4 = gaming_data.calculate_q4()
            total_q4 = total_data.calculate_q4()
            
            print(f"Gaming Member expected Q4: {gaming_q4:,}")
            print(f"Total Revenue expected Q4: {total_q4:,}")
            
            if gaming_q4 != total_q4:
                print("✅ Q4 calculations are different - parent-based matching prevents incorrect fallback")
            else:
                print("⚠️  Q4 calculations are identical - may need investigation")

if __name__ == "__main__":
    test_parent_based_with_recalculation()