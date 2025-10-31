#!/usr/bin/env python3

from config.database import DatabaseConfig, DatabaseConnection

def analyze_dimensional_concepts():
    config = DatabaseConfig()
    connection = DatabaseConnection(config)
    db = connection.connect()
    
    print("=== ANALYZING DIMENSIONAL CONCEPTS ===")
    
    # Get all dimensional concepts (non-parent concepts)
    dimensional_concepts = list(db.normalized_concepts_quarterly.find({
        "dimension_concept": True
    }).limit(20))
    
    print(f"Found {len(dimensional_concepts)} dimensional concepts (showing first 20):")
    for concept in dimensional_concepts:
        print(f"  Label: {concept.get('concept_label')}")
        print(f"  Path: {concept.get('concept_path')}")
        print(f"  Parent: {concept.get('parent_concept')}")
        print(f"  Company: {concept.get('company_cik')}")
        print()
    
    # Check for any concept with deep nesting (like 001.001.001)
    print("=== CONCEPTS WITH DEEP PATHS ===")
    deep_path_concepts = list(db.normalized_concepts_quarterly.find({
        "concept_path": {"$regex": r".*\..*\..*"}  # 3+ levels
    }))
    
    for concept in deep_path_concepts:
        print(f"Deep path: {concept.get('concept_path')}")
        print(f"  Label: {concept.get('concept_label')}")
        print(f"  Company: {concept.get('company_cik')}")
        print()
    
    # Check what values exist in concept_values_quarterly for dimensional data
    print("=== DIMENSIONAL VALUES IN QUARTERLY DATA ===")
    dim_values = list(db.concept_values_quarterly.find({
        "concept_path": {"$regex": r".*\..*"}  # Any path with dots
    }).limit(10))
    
    for value in dim_values:
        print(f"Value: {value.get('value')}")
        print(f"Path: {value.get('concept_path')}")
        print(f"Company: {value.get('company_cik')}")
        print(f"Period: {value.get('reporting_period', {}).get('end_date')}")
        print(f"Concept ID: {value.get('concept_id')}")
        print()
    
    # Look for revenue-related dimensional concepts specifically
    print("=== REVENUE-RELATED DIMENSIONAL CONCEPTS ===")
    revenue_dims = list(db.normalized_concepts_quarterly.find({
        "$and": [
            {"dimension_concept": True},
            {"parent_concept": {"$regex": ".*Revenue.*", "$options": "i"}}
        ]
    }))
    
    for concept in revenue_dims:
        print(f"Revenue dimension: {concept.get('concept_label')}")
        print(f"  Path: {concept.get('concept_path')}")
        print(f"  Parent: {concept.get('parent_concept')}")
        print(f"  Company: {concept.get('company_cik')}")
        
        # Find values for this concept
        values = list(db.concept_values_quarterly.find({
            "concept_id": concept.get("_id")
        }))
        
        if values:
            print(f"  Values found: {len(values)}")
            for v in values[:3]:  # Show first 3 values
                print(f"    {v.get('value')} ({v.get('reporting_period', {}).get('end_date')})")
        print()

if __name__ == "__main__":
    analyze_dimensional_concepts()