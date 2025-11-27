"""Find what CIKs are actually in the database - using correct DB name."""

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

print("=" * 80)
print(f"CHECKING DATABASE: {db_name}")
print("=" * 80)

# Get unique CIKs from concept_values_quarterly
print("\n📋 CIKs in concept_values_quarterly:")
ciks = db.concept_values_quarterly.distinct("company_cik")
print(f"Found {len(ciks)} unique CIKs")
print(f"Sample CIKs: {ciks[:10]}")

# Check if Netflix is in there with different format
netflix_ciks = [c for c in ciks if "1065280" in c]
print(f"\nCIKs containing '1065280' (Netflix): {netflix_ciks}")

# Check META/Facebook
meta_ciks = [c for c in ciks if "1326801" in c]
print(f"CIKs containing '1326801' (Meta): {meta_ciks}")

# If we found Netflix, check for streaming members
if netflix_ciks:
    netflix_cik = netflix_ciks[0]
    print(f"\n{'=' * 80}")
    print(f"CHECKING NETFLIX DATA (CIK: {netflix_cik})")
    print("=" * 80)
    
    # Check for dimensional values
    dim_count = db.concept_values_quarterly.count_documents({
        "company_cik": netflix_cik,
        "dimension_value": True
    })
    print(f"\nDimensional quarterly values: {dim_count}")
    
    if dim_count > 0:
        # Get unique dimensional concept names
        pipeline = [
            {
                "$match": {
                    "company_cik": netflix_cik,
                    "dimension_value": True
                }
            },
            {
                "$lookup": {
                    "from": "normalized_concepts_quarterly",
                    "localField": "concept_id",
                    "foreignField": "_id",
                    "as": "concept"
                }
            },
            {
                "$unwind": "$concept"
            },
            {
                "$group": {
                    "_id": "$concept.name",
                    "path": {"$first": "$concept.path"},
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        
        results = list(db.concept_values_quarterly.aggregate(pipeline))
        print(f"\nUnique dimensional concepts: {len(results)}")
        
        # Print all results first to see what we have
        print("\nAll dimensional concepts:")
        for r in results:
            print(f"  - {r['_id']} (path: {r['path']}, {r['count']} values)")
        
        # Find streaming members
        streaming = [r for r in results if r["_id"] and "streaming" in r["_id"].lower()]
        print(f"\nStreaming-related concepts: {len(streaming)}")
        for s in streaming:
            print(f"  - {s['_id']} (path: {s['path']}, {s['count']} values)")
        
        # Find domestic members
        domestic = [r for r in results if r["_id"] and "domestic" in r["_id"].lower()]
        print(f"\nDomestic-related concepts: {len(domestic)}")
        for d in domestic:
            print(f"  - {d['_id']} (path: {d['path']}, {d['count']} values)")

print("\n" + "=" * 80)
