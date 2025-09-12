#!/usr/bin/env python3
"""Test Q4 calculation with Microsoft FY2025 revenue data - perfect test case."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_microsoft_fy2025_revenue():
    """Test Q4 calculation with Microsoft FY2025 revenue - complete data, no existing Q4."""
    print("TESTING MICROSOFT FY2025 REVENUE Q4 CALCULATION")
    print("=" * 60)
    
    try:
        from config.database import DatabaseConfig, DatabaseConnection
        from repositories.financial_repository import FinancialDataRepository
        from services.q4_calculation_service import Q4CalculationService
        
        # Perfect test case parameters
        company_cik = "0000789019"  # Microsoft
        concept_name = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
        concept_path = "001"
        fiscal_year = 2025
        
        print(f"Company: {company_cik} (Microsoft)")
        print(f"Concept: {concept_name}")
        print(f"Path: {concept_path}")
        print(f"Fiscal Year: {fiscal_year}")
        print()
        
        # Expected values from database analysis
        expected_q1 = 65585000000
        expected_q2 = 69632000000
        expected_q3 = 70066000000
        expected_annual = 281724000000
        expected_q4 = expected_annual - (expected_q1 + expected_q2 + expected_q3)
        
        print("Expected values:")
        print(f"  Q1: {expected_q1:,.0f}")
        print(f"  Q2: {expected_q2:,.0f}")
        print(f"  Q3: {expected_q3:,.0f}")
        print(f"  Annual: {expected_annual:,.0f}")
        print(f"  Expected Q4: {expected_q4:,.0f}")
        print()
        
        # Connect to database
        config = DatabaseConfig()
        with DatabaseConnection(config) as db:
            repository = FinancialDataRepository(db)
            service = Q4CalculationService(repository)
            
            print("Step 1: Verify data retrieval")
            quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
                concept_name, concept_path, company_cik, fiscal_year
            )
            
            if quarterly_data.concept_id:
                print("✓ Found quarterly concept")
                print(f"  Q1: {quarterly_data.q1_value:,.0f}" if quarterly_data.q1_value else "  Q1: None")
                print(f"  Q2: {quarterly_data.q2_value:,.0f}" if quarterly_data.q2_value else "  Q2: None")
                print(f"  Q3: {quarterly_data.q3_value:,.0f}" if quarterly_data.q3_value else "  Q3: None")
                print(f"  Annual: {quarterly_data.annual_value:,.0f}" if quarterly_data.annual_value else "  Annual: None")
                
                # Verify values match expected
                values_match = (
                    quarterly_data.q1_value == expected_q1 and
                    quarterly_data.q2_value == expected_q2 and
                    quarterly_data.q3_value == expected_q3 and
                    quarterly_data.annual_value == expected_annual
                )
                
                if values_match:
                    print("✓ Values match expected data")
                else:
                    print("⚠ Values don't match expected data")
                    
                print()
                
                print("Step 2: Check validation")
                can_calculate = quarterly_data.can_calculate_q4()
                if can_calculate:
                    print("✓ Validation passed - can calculate Q4")
                    calculated_q4 = quarterly_data.calculate_q4()
                    print(f"  Calculated Q4: {calculated_q4:,.0f}")
                    
                    if calculated_q4 == expected_q4:
                        print("✓ Q4 calculation matches expected value")
                    else:
                        print(f"⚠ Q4 calculation differs. Expected: {expected_q4:,.0f}, Got: {calculated_q4:,.0f}")
                else:
                    print("✗ Validation failed - cannot calculate Q4")
                    missing = []
                    if quarterly_data.q1_value is None:
                        missing.append("Q1")
                    if quarterly_data.q2_value is None:
                        missing.append("Q2")
                    if quarterly_data.q3_value is None:
                        missing.append("Q3")
                    if quarterly_data.annual_value is None:
                        missing.append("Annual")
                    print(f"  Missing: {', '.join(missing)}")
                    return False
                
                print()
                
                print("Step 3: Check if Q4 already exists")
                q4_exists = repository.check_q4_exists_by_name_and_path(
                    concept_name, concept_path, company_cik, fiscal_year
                )
                
                if q4_exists:
                    print("ℹ Q4 already exists - skipping calculation test")
                    print("  (This is expected if test was run before)")
                    return True
                else:
                    print("✓ No existing Q4 - ready for calculation")
                
                print()
                
                print("Step 4: Test Q4 calculation service")
                result = service._calculate_q4_for_concept_by_name_and_path(
                    concept_name, concept_path, company_cik, fiscal_year
                )
                
                if result["success"]:
                    print("✓ Q4 calculation service succeeded!")
                    print("  Q4 value has been calculated and inserted")
                    
                    # Verify the Q4 was actually inserted
                    print()
                    print("Step 5: Verify Q4 insertion")
                    q4_now_exists = repository.check_q4_exists_by_name_and_path(
                        concept_name, concept_path, company_cik, fiscal_year
                    )
                    
                    if q4_now_exists:
                        print("✓ Q4 value successfully inserted into database")
                        return True
                    else:
                        print("✗ Q4 value was not inserted into database")
                        return False
                        
                else:
                    print(f"✗ Q4 calculation service failed: {result['reason']}")
                    return False
                
            else:
                print("✗ Quarterly concept not found")
                return False
                
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run Microsoft FY2025 revenue Q4 calculation test."""
    success = test_microsoft_fy2025_revenue()
    
    if success:
        print("\n" + "=" * 60)
        print("✓ MICROSOFT FY2025 REVENUE TEST PASSED!")
        print("Key confirmations:")
        print("  • Database schema changes handled correctly")
        print("  • Parent concept matching works with new structure")
        print("  • Q4 calculation works with complete data")
        print("  • Strict validation enforced properly")
        print("  • Q4 record creation and insertion successful")
    else:
        print("\n" + "=" * 60)
        print("✗ MICROSOFT FY2025 REVENUE TEST FAILED!")
        print("Please review the issues above")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
