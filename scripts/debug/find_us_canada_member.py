#!/usr/bin/env python3

from config.database import DatabaseConfig, DatabaseConnection

def find_us_canada_concepts():
    config = DatabaseConfig()
    connection = DatabaseConnection(config)
    db = connection.connect()
    
    print("=== SEARCHING FOR US/CANADA CONCEPTS ===")
    
    # Search for USCanadaMember or similar US/Canada concepts
    search_patterns = [
        {"concept_label": {"$regex": ".*US.*Canada.*", "$options": "i"}},
        {"concept_label": {"$regex": ".*United States.*Canada.*", "$options": "i"}},
        {"concept_label": {"$regex": ".*USCanada.*", "$options": "i"}},
        {"concept_path": {"$regex": ".*USCanada.*", "$options": "i"}},
        {"concept_path": {"$regex": "001.001.001", "$options": "i"}},
    ]
    
    # Check quarterly data
    print("=== QUARTERLY DATA ===")
    for pattern in search_patterns:
        concepts = list(db.normalized_concepts_quarterly.find(pattern))
        if concepts:
            for concept in concepts:
                print(f"Found quarterly concept: {concept.get('concept_label')}")
                print(f"  Path: {concept.get('concept_path')}")
                print(f"  Dimension: {concept.get('dimension_concept')}")
                print(f"  Parent: {concept.get('parent_concept')}")
                print(f"  Company: {concept.get('company_cik')}")
                print()
    
    # Check annual data
    print("=== ANNUAL DATA ===")
    for pattern in search_patterns:
        concepts = list(db.normalized_concepts_annual.find(pattern))
        if concepts:
            for concept in concepts:
                print(f"Found annual concept: {concept.get('concept_label')}")
                print(f"  Path: {concept.get('concept_path')}")
                print(f"  Dimension: {concept.get('dimension_concept')}")
                print(f"  Parent: {concept.get('parent_concept')}")
                print(f"  Company: {concept.get('company_cik')}")
                print()
    
    # Also search for any concept with path 001.001.001
    print("=== CONCEPTS WITH PATH 001.001.001 ===")
    path_concepts = list(db.normalized_concepts_quarterly.find({"concept_path": "001.001.001"}))
    for concept in path_concepts:
        print(f"Path 001.001.001 concept: {concept.get('concept_label')}")
        print(f"  Dimension: {concept.get('dimension_concept')}")
        print(f"  Parent: {concept.get('parent_concept')}")
        print(f"  Company: {concept.get('company_cik')}")
        print()
    
    # Check for values in concept_values collections
    print("=== CHECKING CONCEPT VALUES ===")
    # Find any values with the problematic pattern
    quarterly_values = list(db.concept_values_quarterly.find({
        "$or": [
            {"concept_path": "001.001.001"},
            {"concept_path": {"$regex": ".*USCanada.*", "$options": "i"}}
        ]
    }).limit(5))
    
    if quarterly_values:
        print("Found quarterly values with problematic paths:")
        for value in quarterly_values:
            print(f"  Value: {value.get('value')}")
            print(f"  Path: {value.get('concept_path')}")
            print(f"  Company: {value.get('company_cik')}")
            print(f"  Period: {value.get('reporting_period', {}).get('end_date')}")
            print()

if __name__ == "__main__":
    find_us_canada_concepts()