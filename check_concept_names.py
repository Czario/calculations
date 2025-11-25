from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017/')['normalize_data']

# Find cash concepts
print("Cash concepts in Netflix:")
cash_concepts = list(db.normalized_concepts_quarterly.find({
    'company_cik': '0001065280',
    'label': 'Cash'
}).limit(3))

for concept in cash_concepts:
    print(f"  Concept name: {concept.get('concept_name', 'N/A')}")
    print(f"  Label: {concept.get('label', 'N/A')}")
    print()

# Find shares outstanding concepts
print("\nShares outstanding in Meta:")
shares = list(db.normalized_concepts_quarterly.find({
    'company_cik': '0001326801',
    'concept_name': {'$regex': 'SharesOutstanding', '$options': 'i'}
}).limit(3))

for concept in shares:
    print(f"  Concept name: {concept.get('concept_name', 'N/A')}")
    print(f"  Label: {concept.get('label', 'N/A')}")
    print()

# Check if concept_name field is empty
print("\nChecking concept_name field:")
sample = db.normalized_concepts_quarterly.find_one({'company_cik': '0001065280'})
print(f"Keys: {list(sample.keys())}")
print(f"concept_name value: '{sample.get('concept_name', 'MISSING')}'")
print(f"concept value: '{sample.get('concept', 'MISSING')}'")
