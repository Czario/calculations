#!/usr/bin/env python3
"""Test script to verify the Q4 calculation setup."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        from config.database import DatabaseConfig, DatabaseConnection
        print("✓ Database config imports successful")
    except ImportError as e:
        print(f"✗ Database config import failed: {e}")
        return False
    
    try:
        from models.financial_data import QuarterlyData, ConceptValue, ReportingPeriod
        print("✓ Financial data models imports successful")
    except ImportError as e:
        print(f"✗ Financial data models import failed: {e}")
        return False
    
    try:
        from repositories.financial_repository import FinancialDataRepository
        print("✓ Financial repository imports successful")
    except ImportError as e:
        print(f"✗ Financial repository import failed: {e}")
        return False
    
    try:
        from services.q4_calculation_service import Q4CalculationService
        print("✓ Q4 calculation service imports successful")
    except ImportError as e:
        print(f"✗ Q4 calculation service import failed: {e}")
        return False
    
    try:
        from app import Q4CalculationApp
        print("✓ Main app imports successful")
    except ImportError as e:
        print(f"✗ Main app import failed: {e}")
        return False
    
    return True

def test_database_config():
    """Test database configuration."""
    print("\nTesting database configuration...")
    
    try:
        from config.database import DatabaseConfig
        config = DatabaseConfig()
        
        print(f"✓ MongoDB URI: {config.get_connection_string()}")
        print(f"✓ Database Name: {config.get_database_name()}")
        return True
        
    except Exception as e:
        print(f"✗ Database config test failed: {e}")
        return False

def test_quarterly_data_model():
    """Test the QuarterlyData model."""
    print("\nTesting QuarterlyData model...")
    
    try:
        from models.financial_data import QuarterlyData
        from bson import ObjectId
        
        # Create test data
        quarterly_data = QuarterlyData(
            concept_id=ObjectId(),
            company_cik="0000320193",
            fiscal_year=2024,
            q1_value=100.0,
            q2_value=150.0,
            q3_value=200.0,
            annual_value=500.0
        )
        
        # Test calculations
        assert quarterly_data.has_complete_quarterly_data() == True
        assert quarterly_data.has_annual_value() == True
        assert quarterly_data.can_calculate_q4() == True
        
        q4_value = quarterly_data.calculate_q4()
        expected_q4 = 500.0 - (100.0 + 150.0 + 200.0)  # 50.0
        assert q4_value == expected_q4
        
        print(f"✓ Q4 calculation test passed: {q4_value}")
        return True
        
    except Exception as e:
        print(f"✗ QuarterlyData model test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Q4 Calculation Setup Test")
    print("=" * 40)
    
    tests_passed = 0
    total_tests = 3
    
    if test_imports():
        tests_passed += 1
    
    if test_database_config():
        tests_passed += 1
    
    if test_quarterly_data_model():
        tests_passed += 1
    
    print("\n" + "=" * 40)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✓ All tests passed! Setup is ready.")
        print("\nTo run the Q4 calculation:")
        print("  python app.py                    # Process all companies")
        print("  python app.py 0000320193        # Process specific company (Apple)")
        return True
    else:
        print("✗ Some tests failed. Please check the setup.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
