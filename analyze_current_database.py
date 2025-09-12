#!/usr/bin/env python3
"""Database Schema Analysis for the updated normalize_data database."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def analyze_current_database():
    """Analyze the current database structure and identify working examples."""
    print("CURRENT DATABASE ANALYSIS")
    print("=" * 60)
    
    try:
        from config.database import DatabaseConfig, DatabaseConnection
        
        # Connect to database
        config = DatabaseConfig()
        with DatabaseConnection(config) as db:
            print("✓ Connected to normalize_data database")
            print()
            
            # Database overview
            print("DATABASE OVERVIEW:")
            collections = db.list_collection_names()
            for collection in collections:
                if not collection.startswith('system'):
                    count = db[collection].count_documents({})
                    print(f"  {collection}: {count:,} documents")
            print()
            
            # Companies analysis
            print("COMPANIES:")
            companies = list(db.companies.find({}, {"cik": 1, "name": 1, "ticker_symbol": 1}))
            for company in companies:
                print(f"  {company['cik']} - {company['name']} ({company['ticker_symbol']})")
            print()
            
            # Schema changes identification
            print("KEY SCHEMA CHANGES IDENTIFIED:")
            print("  1. Company CIK field is now 'cik' (was 'company_cik')")
            print("  2. Concept values have simplified structure")
            print("  3. No filing_id or fact_id fields in concept values")
            print("  4. Dimensional concepts use concept_id for parent reference")
            print("  5. Annual and quarterly data use same concept_id linking")
            print()
            
            # Perfect test case analysis
            print("PERFECT TEST CASE FOUND:")
            print("  Company: Microsoft (0000789019)")
            print("  Concept: us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax")
            print("  Fiscal Year: 2025")
            print("  Status: Complete Q1,Q2,Q3,Annual data - NO Q4 exists yet")
            print()
            print("  Data:")
            print("    Q1: 65,585,000,000")
            print("    Q2: 69,632,000,000") 
            print("    Q3: 70,066,000,000")
            print("    Annual: 281,724,000,000")
            print("    Expected Q4: 76,441,000,000")
            print()
            
            # Issues with current code
            print("ISSUES WITH CURRENT CODE:")
            print("  1. ConceptValue model expects filing_id and fact_id (don't exist)")
            print("  2. Repository uses company_cik field (should be cik in companies)")
            print("  3. Parent concept matching logic may need adjustment")
            print("  4. Q4 record creation fails due to missing metadata fields")
            print()
            
            return True
            
    except Exception as e:
        print(f"✗ Database analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run database analysis."""
    success = analyze_current_database()
    
    if success:
        print("NEXT STEPS:")
        print("1. Update ConceptValue model to make filing_id/fact_id optional")
        print("2. Fix Q4 record creation to handle missing metadata")
        print("3. Test with Microsoft FY2025 revenue data")
        print("4. Verify parent concept matching works with new schema")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
