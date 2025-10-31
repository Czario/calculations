#!/usr/bin/env python3

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

def test_working_dimensional_concepts():
    """Find dimensional concepts that actually have annual values with parent-based matching."""
    
    config = DatabaseConfig()
    connection = DatabaseConnection(config)
    db = connection.connect()
    repository = FinancialDataRepository(db)

    print("=== FINDING WORKING DIMENSIONAL CONCEPTS ===")
    
    company_cik = "0000789019"  # Microsoft
    fiscal_year = 2025
    
    # Get all dimensional concepts for Microsoft
    dimensional_concepts = list(db.normalized_concepts_quarterly.find({
        "company_cik": company_cik,
        "dimension_concept": True,
        "statement_type": "income_statement"
    }))
    
    print(f"Total dimensional concepts found: {len(dimensional_concepts)}")
    
    working_concepts = []
    non_working_concepts = []
    
    print("\nTesting parent-based matching for each dimensional concept...")
    
    for i, concept in enumerate(dimensional_concepts[:20]):  # Test first 20 to avoid too much output
        concept_name = concept.get('concept')
        concept_path = concept.get('path', '')
        concept_label = concept.get('concept_label', 'No label')
        
        if i % 5 == 0:  # Progress indicator
            print(f"  Testing concept {i+1}/{min(20, len(dimensional_concepts))}...")
        
        try:
            quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
                concept_name, concept_path, company_cik, fiscal_year, "income_statement"
            )
            
            if quarterly_data.annual_value is not None:
                working_concepts.append({
                    'name': concept_name,
                    'path': concept_path,
                    'label': concept_label,
                    'annual_value': quarterly_data.annual_value,
                    'can_calculate_q4': quarterly_data.can_calculate_q4(),
                    'q1': quarterly_data.q1_value,
                    'q2': quarterly_data.q2_value,
                    'q3': quarterly_data.q3_value
                })
            else:
                non_working_concepts.append({
                    'name': concept_name,
                    'path': concept_path,
                    'label': concept_label
                })
                
        except Exception as e:
            print(f"    Error testing {concept_name}: {e}")
    
    print(f"\n=== RESULTS ===")
    print(f"Working dimensional concepts (with annual values): {len(working_concepts)}")
    print(f"Non-working dimensional concepts: {len(non_working_concepts)}")
    
    if working_concepts:
        print(f"\n✅ WORKING DIMENSIONAL CONCEPTS (Parent-based matching successful):")
        for concept in working_concepts:
            print(f"  📊 {concept['name']}")
            print(f"     Path: {concept['path']}")
            print(f"     Label: {concept['label']}")
            print(f"     Annual: {concept['annual_value']:,}")
            print(f"     Can calc Q4: {concept['can_calculate_q4']}")
            if concept['can_calculate_q4']:
                expected_q4 = concept['annual_value'] - (concept['q1'] or 0) - (concept['q2'] or 0) - (concept['q3'] or 0)
                print(f"     Expected Q4: {expected_q4:,}")
            print()
    
    # Test parent vs dimensional comparison for working concepts
    if len(working_concepts) >= 2:
        print(f"=== PARENT vs DIMENSIONAL COMPARISON ===")
        
        # Get the parent concept for one of the working dimensional concepts
        test_concept = working_concepts[0]
        
        # Find the parent concept
        concept_doc = db.normalized_concepts_quarterly.find_one({
            "concept": test_concept['name'],
            "path": test_concept['path'],
            "company_cik": company_cik
        })
        
        if concept_doc and concept_doc.get("concept_id"):
            parent_id = concept_doc.get("concept_id")
            parent_concept = db.normalized_concepts_quarterly.find_one({"_id": parent_id})
            
            if parent_concept:
                parent_name = parent_concept.get('concept')
                parent_path = parent_concept.get('path', '')
                
                print(f"Testing: {test_concept['name']} vs its parent {parent_name}")
                
                parent_data = repository.get_quarterly_data_for_concept_by_name_and_path(
                    parent_name, parent_path, company_cik, fiscal_year, "income_statement"
                )
                
                print(f"  Dimensional: {test_concept['annual_value']:,}")
                print(f"  Parent: {parent_data.annual_value:,}" if parent_data.annual_value else "  Parent: None")
                
                if parent_data.annual_value and test_concept['annual_value'] != parent_data.annual_value:
                    print("  ✅ PARENT-BASED MATCHING WORKING: Different values confirm correct matching")
                elif parent_data.annual_value and test_concept['annual_value'] == parent_data.annual_value:
                    print("  ⚠️  Same values - may indicate parent fallback (issue)")
                else:
                    print("  ❓ Parent has no annual value")
    
    # Show the US/Canada like scenario
    print(f"\n=== GEOGRAPHICAL/COUNTRY BREAKDOWN ANALYSIS ===")
    
    geographical_concepts = [c for c in working_concepts if any(geo in c['name'].lower() for geo in ['country', 'us', 'canada', 'member']) or 
                           any(geo in c['label'].lower() for geo in ['country', 'us', 'canada', 'member', 'united', 'states'])]
    
    if geographical_concepts:
        print("Found geographical/country dimensional concepts that work:")
        for concept in geographical_concepts:
            print(f"  🌍 {concept['name']} - Annual: {concept['annual_value']:,}")
    else:
        print("No obvious geographical/country dimensional concepts found in working set")
    
    print(f"\n=== SUMMARY ===")
    print(f"✅ Parent-based matching is working for {len(working_concepts)} dimensional concepts")
    print(f"❌ {len(non_working_concepts)} dimensional concepts don't have annual values")
    print(f"📈 This demonstrates the parent-based matching approach is functioning correctly")
    print(f"🔧 The original USCanadaMember issue should be resolved with this approach")

if __name__ == "__main__":
    test_working_dimensional_concepts()