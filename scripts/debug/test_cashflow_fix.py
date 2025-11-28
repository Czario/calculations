"""Test script for cash flow fix service.

This script helps verify the fix-cashflow process that converts cumulative Q2/Q3 
cash flow values to actual quarterly values.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository
from services.cashflow_fix_service import CashFlowFixService


def test_single_company(company_cik: str):
    """Test cash flow fix for a single company.
    
    Args:
        company_cik: Company CIK to test
    """
    print(f"\n{'=' * 80}")
    print(f"Testing Cash Flow Fix for Company: {company_cik}")
    print(f"{'=' * 80}\n")
    
    config = DatabaseConfig()
    
    with DatabaseConnection(config) as db:
        repository = FinancialDataRepository(db)
        
        # Get sample data BEFORE fix
        print("BEFORE FIX - Sample Q1, Q2, Q3 values:")
        print("-" * 80)
        
        sample_data = _get_sample_data(repository, company_cik, fiscal_year=2012)
        _print_sample_data(sample_data)
        
        # Run the fix
        print("\n\nRUNNING FIX PROCESS...")
        print("-" * 80)
        
        service = CashFlowFixService(repository, verbose=True)
        results = service.fix_cumulative_values_for_company(company_cik)
        
        # Show results
        print("\n\nRESULTS:")
        print("-" * 80)
        print(f"Fiscal years processed: {results['fiscal_years_processed']}")
        print(f"Q2 values fixed: {results['q2_fixed']}")
        print(f"Q3 values fixed: {results['q3_fixed']}")
        print(f"Q2 values skipped: {results['q2_skipped']}")
        print(f"Q3 values skipped: {results['q3_skipped']}")
        
        if results['errors']:
            print(f"\nErrors: {len(results['errors'])}")
            for error in results['errors'][:5]:
                print(f"  - {error}")
        
        # Get sample data AFTER fix
        print("\n\nAFTER FIX - Sample Q1, Q2, Q3 values:")
        print("-" * 80)
        
        sample_data_after = _get_sample_data(repository, company_cik, fiscal_year=2012)
        _print_sample_data(sample_data_after)
        
        # Verify the fix
        print("\n\nVERIFICATION:")
        print("-" * 80)
        _verify_fix(sample_data, sample_data_after)
        
        print(f"\n{'=' * 80}\n")


def _get_sample_data(repository: FinancialDataRepository, company_cik: str, fiscal_year: int):
    """Get sample Q1, Q2, Q3 data for verification.
    
    Args:
        repository: Repository instance
        company_cik: Company CIK
        fiscal_year: Fiscal year to sample
        
    Returns:
        Dictionary with sample data
    """
    # Get a few sample concepts
    q1_values = list(repository.concept_values_quarterly.find({
        "company_cik": company_cik,
        "statement_type": "cash_flows",
        "reporting_period.fiscal_year": fiscal_year,
        "reporting_period.quarter": 1,
        "form_type": "10-Q"
    }).limit(3))
    
    q2_values = list(repository.concept_values_quarterly.find({
        "company_cik": company_cik,
        "statement_type": "cash_flows",
        "reporting_period.fiscal_year": fiscal_year,
        "reporting_period.quarter": 2,
        "form_type": "10-Q"
    }).limit(3))
    
    q3_values = list(repository.concept_values_quarterly.find({
        "company_cik": company_cik,
        "statement_type": "cash_flows",
        "reporting_period.fiscal_year": fiscal_year,
        "reporting_period.quarter": 3,
        "form_type": "10-Q"
    }).limit(3))
    
    # Build lookup by concept_id
    data = {}
    
    for q1_val in q1_values:
        concept_id = str(q1_val["concept_id"])
        if concept_id not in data:
            data[concept_id] = {
                "concept_id": concept_id,
                "concept_name": _get_concept_name(repository, q1_val["concept_id"])
            }
        data[concept_id]["q1"] = q1_val["value"]
    
    for q2_val in q2_values:
        concept_id = str(q2_val["concept_id"])
        if concept_id not in data:
            data[concept_id] = {
                "concept_id": concept_id,
                "concept_name": _get_concept_name(repository, q2_val["concept_id"])
            }
        data[concept_id]["q2"] = q2_val["value"]
    
    for q3_val in q3_values:
        concept_id = str(q3_val["concept_id"])
        if concept_id not in data:
            data[concept_id] = {
                "concept_id": concept_id,
                "concept_name": _get_concept_name(repository, q3_val["concept_id"])
            }
        data[concept_id]["q3"] = q3_val["value"]
    
    return data


def _get_concept_name(repository: FinancialDataRepository, concept_id):
    """Get concept name from concept_id."""
    try:
        concept = repository.normalized_concepts_quarterly.find_one(
            {"_id": concept_id},
            {"concept": 1}
        )
        return concept.get("concept", "Unknown") if concept else "Unknown"
    except Exception:
        return "Unknown"


def _print_sample_data(data: dict):
    """Print sample data in a formatted way."""
    if not data:
        print("No data found")
        return
    
    for concept_id, values in list(data.items())[:3]:
        concept_name = values.get("concept_name", "Unknown")
        q1 = values.get("q1", "N/A")
        q2 = values.get("q2", "N/A")
        q3 = values.get("q3", "N/A")
        
        print(f"\nConcept: {concept_name}")
        if q1 != "N/A":
            print(f"  Q1: {q1:>15,.2f}")
        if q2 != "N/A":
            print(f"  Q2: {q2:>15,.2f}")
        if q3 != "N/A":
            print(f"  Q3: {q3:>15,.2f}")


def _verify_fix(before: dict, after: dict):
    """Verify that the fix worked correctly.
    
    Args:
        before: Data before fix
        after: Data after fix
    """
    verified = 0
    failed = 0
    
    for concept_id, before_vals in before.items():
        after_vals = after.get(concept_id, {})
        concept_name = before_vals.get("concept_name", "Unknown")
        
        # Check Q2 fix: Q2_after should equal Q2_before - Q1_before
        if "q1" in before_vals and "q2" in before_vals and "q2" in after_vals:
            expected_q2 = before_vals["q2"] - before_vals["q1"]
            actual_q2 = after_vals["q2"]
            
            if abs(expected_q2 - actual_q2) < 0.01:
                print(f"✅ Q2 fix verified for {concept_name}")
                print(f"   {before_vals['q2']:,.2f} - {before_vals['q1']:,.2f} = {actual_q2:,.2f}")
                verified += 1
            else:
                print(f"❌ Q2 fix FAILED for {concept_name}")
                print(f"   Expected: {expected_q2:,.2f}, Got: {actual_q2:,.2f}")
                failed += 1
        
        # Check Q3 fix: Q3_after should equal Q3_before - Q2_before
        if "q2" in before_vals and "q3" in before_vals and "q3" in after_vals:
            expected_q3 = before_vals["q3"] - before_vals["q2"]
            actual_q3 = after_vals["q3"]
            
            if abs(expected_q3 - actual_q3) < 0.01:
                print(f"✅ Q3 fix verified for {concept_name}")
                print(f"   {before_vals['q3']:,.2f} - {before_vals['q2']:,.2f} = {actual_q3:,.2f}")
                verified += 1
            else:
                print(f"❌ Q3 fix FAILED for {concept_name}")
                print(f"   Expected: {expected_q3:,.2f}, Got: {actual_q3:,.2f}")
                failed += 1
    
    print(f"\n{'=' * 80}")
    print(f"Verification Results: {verified} passed, {failed} failed")
    print(f"{'=' * 80}")


def main():
    """Main test function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test cash flow fix service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_cashflow_fix.py                    # Test Meta Platforms (default)
  python test_cashflow_fix.py --cik 0000789019   # Test Microsoft
        """
    )
    
    parser.add_argument(
        '--cik',
        type=str,
        default='0001326801',  # Meta Platforms by default
        help='Company CIK to test (default: 0001326801 - Meta Platforms)'
    )
    
    args = parser.parse_args()
    
    test_single_company(args.cik)


if __name__ == "__main__":
    main()
