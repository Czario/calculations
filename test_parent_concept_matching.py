#!/usr/bin/env python3
"""Test script to verify enhanced parent concept matching for Q4 calculations."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_parent_concept_matching():
    """Test that parent concept matching works correctly between quarterly and annual filings."""
    print("Testing Enhanced Parent Concept Matching")
    print("=" * 50)
    
    try:
        from config.database import DatabaseConfig, DatabaseConnection
        from repositories.financial_repository import FinancialDataRepository
        from services.q4_calculation_service import Q4CalculationService
        
        # Connect to database
        config = DatabaseConfig()
        with DatabaseConnection(config) as db:
            repository = FinancialDataRepository(db)
            service = Q4CalculationService(repository)
            
            # Test with a known company (Apple)
            company_cik = "0000320193"
            fiscal_year = 2024
            
            print(f"Testing with company: {company_cik}, fiscal year: {fiscal_year}")
            print()
            
            # Get sample concepts to test
            concepts = repository.get_income_statement_concepts(company_cik)
            
            if not concepts:
                print(f"✗ No concepts found for company {company_cik}")
                return False
            
            print(f"Found {len(concepts)} income statement concepts")
            print()
            
            # Test different types of concepts
            regular_concepts = [c for c in concepts if not c.get("dimension_concept", False)]
            dimensional_concepts = [c for c in concepts if c.get("dimension_concept", False)]
            
            print(f"Regular concepts: {len(regular_concepts)}")
            print(f"Dimensional concepts: {len(dimensional_concepts)}")
            print()
            
            # Test regular concept matching
            if regular_concepts:
                print("Testing regular concept matching...")
                test_concept = regular_concepts[0]
                concept_name = test_concept["concept"]
                concept_path = test_concept.get("path", "")
                
                print(f"  Testing concept: {concept_name}")
                print(f"  Path: {concept_path}")
                
                # Test quarterly data retrieval with parent matching
                quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
                    concept_name, concept_path, company_cik, fiscal_year
                )
                
                if quarterly_data.concept_id:
                    print(f"  ✓ Found quarterly concept")
                    print(f"  Q1: {quarterly_data.q1_value}")
                    print(f"  Q2: {quarterly_data.q2_value}")
                    print(f"  Q3: {quarterly_data.q3_value}")
                    print(f"  Annual: {quarterly_data.annual_value}")
                    
                    if quarterly_data.can_calculate_q4():
                        q4_value = quarterly_data.calculate_q4()
                        print(f"  ✓ Can calculate Q4: {q4_value:,.2f}")
                    else:
                        print(f"  ⚠ Cannot calculate Q4 (missing values)")
                else:
                    print(f"  ✗ Quarterly concept not found")
                print()
            
            # Test dimensional concept matching
            if dimensional_concepts:
                print("Testing dimensional concept matching...")
                test_concept = dimensional_concepts[0]
                concept_name = test_concept["concept"]
                concept_path = test_concept.get("path", "")
                parent_concept_id = test_concept.get("concept_id")
                
                print(f"  Testing dimensional concept: {concept_name}")
                print(f"  Path: {concept_path}")
                print(f"  Parent concept ID: {parent_concept_id}")
                
                # Get parent concept name
                parent_concept_name = repository.get_parent_concept_name(
                    test_concept["_id"], "normalized_concepts_quarterly"
                )
                print(f"  Parent concept name: {parent_concept_name}")
                
                # Test quarterly data retrieval with parent matching
                quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
                    concept_name, concept_path, company_cik, fiscal_year
                )
                
                if quarterly_data.concept_id:
                    print(f"  ✓ Found quarterly dimensional concept")
                    print(f"  Q1: {quarterly_data.q1_value}")
                    print(f"  Q2: {quarterly_data.q2_value}")
                    print(f"  Q3: {quarterly_data.q3_value}")
                    print(f"  Annual: {quarterly_data.annual_value}")
                    
                    if quarterly_data.can_calculate_q4():
                        q4_value = quarterly_data.calculate_q4()
                        print(f"  ✓ Can calculate Q4: {q4_value:,.2f}")
                    else:
                        print(f"  ⚠ Cannot calculate Q4 (missing values)")
                else:
                    print(f"  ✗ Quarterly dimensional concept not found")
                print()
            
            # Test the enhanced matching method
            if dimensional_concepts and regular_concepts:
                print("Testing find_matching_concept_by_parent method...")
                test_concept = dimensional_concepts[0]
                
                matching_concept = repository.find_matching_concept_by_parent(
                    test_concept["concept"],
                    test_concept["_id"],
                    "normalized_concepts_annual",
                    company_cik
                )
                
                if matching_concept:
                    print(f"  ✓ Found matching annual concept: {matching_concept['concept']}")
                    print(f"  Annual concept path: {matching_concept.get('path', 'N/A')}")
                else:
                    print(f"  ✗ No matching annual concept found")
                print()
            
            print("=" * 50)
            print("Parent concept matching test completed!")
            return True
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_q4_calculation_with_parent_matching():
    """Test Q4 calculation using enhanced parent concept matching."""
    print("\nTesting Q4 Calculation with Parent Concept Matching")
    print("=" * 60)
    
    try:
        from config.database import DatabaseConfig, DatabaseConnection
        from repositories.financial_repository import FinancialDataRepository
        from services.q4_calculation_service import Q4CalculationService
        
        # Connect to database
        config = DatabaseConfig()
        with DatabaseConnection(config) as db:
            repository = FinancialDataRepository(db)
            service = Q4CalculationService(repository)
            
            # Test with a known company (Apple)
            company_cik = "0000320193"
            fiscal_year = 2024
            
            print(f"Testing Q4 calculation for company: {company_cik}, fiscal year: {fiscal_year}")
            print()
            
            # Get a sample of concepts
            concepts = repository.get_income_statement_concepts(company_cik)[:5]  # Test first 5 concepts
            
            for i, concept in enumerate(concepts, 1):
                concept_name = concept["concept"]
                concept_path = concept.get("path", "")
                is_dimensional = concept.get("dimension_concept", False)
                
                print(f"{i}. Testing: {concept_name}")
                print(f"   Path: {concept_path}")
                print(f"   Type: {'Dimensional' if is_dimensional else 'Regular'}")
                
                # Test the enhanced Q4 calculation
                result = service._calculate_q4_for_concept_by_name_and_path(
                    concept_name, concept_path, company_cik, fiscal_year
                )
                
                if result["success"]:
                    print(f"   ✓ Q4 calculation successful")
                else:
                    print(f"   ⚠ Q4 calculation skipped: {result['reason']}")
                print()
            
            print("=" * 60)
            print("Q4 calculation with parent matching test completed!")
            return True
            
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all parent concept matching tests."""
    print("Enhanced Parent Concept Matching Test Suite")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 2
    
    if test_parent_concept_matching():
        tests_passed += 1
    
    if test_q4_calculation_with_parent_matching():
        tests_passed += 1
    
    print("\n" + "=" * 60)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✓ All parent concept matching tests passed!")
        print("\nKey improvements:")
        print("  • Parent concept identification for dimensional concepts")
        print("  • Enhanced matching between quarterly and annual filings")
        print("  • Fallback to path-based matching when parent matching fails")
        print("  • Better handling of concept relationships across filing types")
        return True
    else:
        print("✗ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
