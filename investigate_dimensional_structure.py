"""Investigate the structure of dimensional values for Netflix."""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database name from config
db_name = os.getenv("TARGET_DB_NAME", "normalize_data")

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client[db_name]

netflix_cik = "0001065280"

print("=" * 80)
print(f"INVESTIGATING NETFLIX DIMENSIONAL DATA")
print("=" * 80)

# Get a sample dimensional value
print("\n📋 Sample dimensional quarterly value:")
sample = db.concept_values_quarterly.find_one({
    "company_cik": netflix_cik,
    "dimension_value": True
})

if sample:
    print("\nFull sample document:")
    for key, value in sample.items():
        if key != "_id":
            print(f"  {key}: {value}")
    
    # Try to find the concept
    print(f"\n📋 Looking up concept with ID: {sample['concept_id']}")
    concept = db.normalized_concepts_quarterly.find_one({"_id": sample["concept_id"]})
    
    if concept:
        print("\nConcept found:")
        for key, value in concept.items():
            if key != "_id":
                print(f"  {key}: {value}")
    else:
        print("\n⚠️  Concept not found in normalized_concepts_quarterly!")
        
        # Check if there's a dimensional_concept_id field
        if "dimensional_concept_id" in sample:
            print(f"\n📋 Checking dimensional_concept_id: {sample['dimensional_concept_id']}")
            dim_concept = db.normalized_concepts_quarterly.find_one({"_id": sample["dimensional_concept_id"]})
            if dim_concept:
                print("\nDimensional concept found:")
                for key, value in dim_concept.items():
                    if key != "_id":
                        print(f"  {key}: {value}")

# Get more samples to see the pattern
print("\n\n" + "=" * 80)
print("SAMPLING MORE DIMENSIONAL VALUES")
print("=" * 80)

samples = list(db.concept_values_quarterly.find({
    "company_cik": netflix_cik,
    "dimension_value": True
}).limit(10))

print(f"\nFound {len(samples)} sample dimensional values")

for i, s in enumerate(samples, 1):
    concept = db.normalized_concepts_quarterly.find_one({"_id": s["concept_id"]})
    dim_concept = None
    if "dimensional_concept_id" in s:
        dim_concept = db.normalized_concepts_quarterly.find_one({"_id": s["dimensional_concept_id"]})
    
    print(f"\n{i}. FY{s['reporting_period']['fiscal_year']} Q{s['reporting_period']['quarter']}: {s['value']:,.2f}")
    
    # Use 'concept' field instead of 'name' for dimensional concepts
    concept_name = concept.get('concept', concept.get('name', 'NOT FOUND')) if concept else 'NOT FOUND'
    print(f"   concept_id points to: {concept_name}")
    
    if dim_concept:
        dim_concept_name = dim_concept.get('concept', dim_concept.get('name', 'N/A'))
        print(f"   dimensional_concept_id points to: {dim_concept_name}")
    
    print(f"   Label: {concept.get('label', 'N/A') if concept else 'N/A'}")
    print(f"   Path: {s.get('statement_type', 'N/A')} | {concept.get('path', 'N/A') if concept else 'N/A'}")
    print(f"   Calculated: {s.get('calculated', False)}")

print("\n" + "=" * 80)
