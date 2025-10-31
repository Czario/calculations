#!/usr/bin/env python3

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

def test_us_canada_member_scenario():
    """Test the specific USCanadaMember scenario mentioned in the original issue."""
    
    config = DatabaseConfig()
    connection = DatabaseConnection(config)
    db = connection.connect()
    repository = FinancialDataRepository(db)

    print("=== TESTING US/CANADA MEMBER SCENARIO ===")
    
    # Look for any concepts that might represent US/Canada geographical breakdown
    print("\n1. Searching for US/Canada related concepts...")
    
    # Search for concepts with US/Canada patterns
    us_concepts = list(db.normalized_concepts_quarterly.find({
        "$or": [
            {"concept": {"$regex": ".*US.*", "$options": "i"}},
            {"concept": {"$regex": ".*United.*States.*", "$options": "i"}},
            {"concept_label": {"$regex": ".*US.*", "$options": "i"}},
            {"concept_label": {"$regex": ".*United.*States.*", "$options": "i"}}
        ]
    }).limit(10))
    
    canada_concepts = list(db.normalized_concepts_quarterly.find({
        "$or": [
            {"concept": {"$regex": ".*Canada.*", "$options": "i"}},
            {"concept_label": {"$regex": ".*Canada.*", "$options": "i"}}
        ]
    }).limit(10))
    
    print(f"Found {len(us_concepts)} US-related concepts")
    print(f"Found {len(canada_concepts)} Canada-related concepts")
    
    # Look for country-based dimensional concepts
    country_concepts = list(db.normalized_concepts_quarterly.find({
        "$or": [
            {"concept": {"$regex": "country:.*", "$options": "i"}},
            {"concept": {"$regex": ".*Country.*", "$options": "i"}},
            {"concept_label": {"$regex": ".*Country.*", "$options": "i"}}
        ]
    }))
    
    print(f"Found {len(country_concepts)} country-related concepts")
    
    if country_concepts:
        print("\nCountry-related concepts found:")
        for concept in country_concepts[:5]:  # Show first 5
            print(f"  - {concept.get('concept')} (Path: {concept.get('path')}) - {concept.get('concept_label')}")
    
    # Test with the specific pattern mentioned: "001.001.001"
    print("\n2. Testing concepts with deep paths (like 001.001.001)...")
    
    deep_path_concepts = list(db.normalized_concepts_quarterly.find({
        "path": {"$regex": r".*\..*\..*"}  # At least 3 levels
    }))
    
    print(f"Found {len(deep_path_concepts)} concepts with deep paths")
    
    # Test the parent-based matching with a dimensional concept we know exists
    print("\n3. Testing parent-based matching with known dimensional concept...")
    
    company_cik = "0000789019"  # Microsoft
    fiscal_year = 2025
    
    # Test a concept that has geographical breakdown
    us_member_concepts = list(db.normalized_concepts_quarterly.find({
        "concept": {"$regex": ".*US.*Member", "$options": "i"},
        "company_cik": company_cik
    }))
    
    if us_member_concepts:
        print("Found US Member concepts:")
        for concept in us_member_concepts[:3]:
            print(f"  - {concept.get('concept')} (Path: {concept.get('path')})")
            
            # Test parent-based matching for this concept
            quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
                concept.get('concept'), concept.get('path', ''), company_cik, fiscal_year, "income_statement"
            )
            
            print(f"    Annual value: {quarterly_data.annual_value:,}" if quarterly_data.annual_value else "    Annual value: None")
            
            # Find the parent concept
            if quarterly_data.concept_id:
                quarterly_concept_doc = db.normalized_concepts_quarterly.find_one({"_id": quarterly_data.concept_id})
                if quarterly_concept_doc and quarterly_concept_doc.get("concept_id"):
                    parent_id = quarterly_concept_doc.get("concept_id")
                    parent_concept = db.normalized_concepts_quarterly.find_one({"_id": parent_id})
                    if parent_concept:
                        print(f"    Parent concept: {parent_concept.get('concept')}")
                        
                        # Get parent's annual value
                        parent_data = repository.get_quarterly_data_for_concept_by_name_and_path(
                            parent_concept.get('concept'), parent_concept.get('path', ''), 
                            company_cik, fiscal_year, "income_statement"
                        )
                        
                        print(f"    Parent annual value: {parent_data.annual_value:,}" if parent_data.annual_value else "    Parent annual value: None")
                        
                        # Verify they're different (proving parent-based matching works)
                        if quarterly_data.annual_value and parent_data.annual_value:
                            if quarterly_data.annual_value != parent_data.annual_value:
                                print("    ✅ Dimensional concept uses its own value (parent-based matching working)")
                            else:
                                print("    ⚠️  Same as parent value")
    
    # Test the specific scenario: path "001.001.001"
    print("\n4. Testing specific path scenario (001.001.001)...")
    
    specific_path_concepts = list(db.normalized_concepts_quarterly.find({
        "path": "001.001.001",
        "company_cik": company_cik
    }))
    
    if specific_path_concepts:
        print("Found concepts with path 001.001.001:")
        for concept in specific_path_concepts:
            print(f"  - {concept.get('concept')} - {concept.get('concept_label')}")
    else:
        print("No concepts found with exact path 001.001.001")
    
    # Test with a simulated US/Canada scenario
    print("\n5. Testing simulated US/Canada member scenario...")
    
    # Find any geographical dimensional concepts
    geo_concepts = list(db.normalized_concepts_quarterly.find({
        "$and": [
            {"company_cik": company_cik},
            {"dimension_concept": True},
            {"$or": [
                {"concept": {"$regex": "country:", "$options": "i"}},
                {"concept": {"$regex": ".*Member", "$options": "i"}},
                {"concept_label": {"$regex": ".*Member.*", "$options": "i"}}
            ]}
        ]
    }))
    
    print(f"Found {len(geo_concepts)} geographical/member dimensional concepts")
    
    for concept in geo_concepts[:3]:  # Test first 3
        concept_name = concept.get('concept')
        concept_path = concept.get('path', '')
        
        print(f"\nTesting: {concept_name} (Path: {concept_path})")
        
        quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
            concept_name, concept_path, company_cik, fiscal_year, "income_statement"
        )
        
        if quarterly_data.annual_value:
            print(f"  Annual value: {quarterly_data.annual_value:,}")
            print("  ✅ Parent-based matching found annual value")
        else:
            print("  ❌ No annual value found")

if __name__ == "__main__":
    test_us_canada_member_scenario()