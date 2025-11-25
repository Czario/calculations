"""Verify point-in-time exclusion logic works for all companies."""

from pymongo import MongoClient
from services.q4_calculation_service import Q4CalculationService
from repositories.financial_repository import FinancialDataRepository

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

companies = [
    {"cik": "0000320193", "name": "Apple"},
    {"cik": "0000789019", "name": "Microsoft"},
    {"cik": "0001065280", "name": "Netflix"},
    {"cik": "0001326801", "name": "Meta"}
]

# Initialize service
repository = FinancialDataRepository(db)
service = Q4CalculationService(repository)

print("=" * 80)
print("POINT-IN-TIME CONCEPT DETECTION VERIFICATION")
print("=" * 80)

for company in companies:
    print(f"\n{'='*80}")
    print(f"{company['name']} (CIK: {company['cik']})")
    print(f"{'='*80}")
    
    # Get sample concepts from this company
    concepts = list(db.normalized_concepts_quarterly.find({
        "company_cik": company["cik"]
    }).limit(50))
    
    if not concepts:
        print(f"  ⚠️ No concepts found for {company['name']}")
        continue
    
    print(f"\nTesting {len(concepts)} concepts...")
    
    # Test each concept
    point_in_time_count = 0
    flow_concept_count = 0
    point_in_time_examples = []
    flow_examples = []
    
    for concept in concepts:
        concept_name = concept.get("concept_name", "")
        label = concept.get("label", "")
        
        is_point_in_time = service._is_point_in_time_concept(concept_name, label)
        
        if is_point_in_time:
            point_in_time_count += 1
            if len(point_in_time_examples) < 5:
                point_in_time_examples.append({
                    "name": concept_name,
                    "label": label
                })
        else:
            flow_concept_count += 1
            if len(flow_examples) < 3:
                flow_examples.append({
                    "name": concept_name,
                    "label": label
                })
    
    print(f"\n  Results:")
    print(f"    ✅ Flow concepts (will calculate Q4): {flow_concept_count}")
    print(f"    🚫 Point-in-time concepts (will skip): {point_in_time_count}")
    
    if point_in_time_examples:
        print(f"\n  Point-in-time concepts found:")
        for ex in point_in_time_examples:
            print(f"    🚫 {ex['name']}")
            if ex['label']:
                print(f"       Label: {ex['label']}")
    
    if flow_examples:
        print(f"\n  Flow concepts found:")
        for ex in flow_examples:
            print(f"    ✅ {ex['name']}")
            if ex['label']:
                print(f"       Label: {ex['label']}")

# Now test with actual cash/revenue concepts if they exist
print("\n" + "=" * 80)
print("TESTING SPECIFIC CONCEPT TYPES")
print("=" * 80)

test_patterns = [
    {"pattern": "Cash", "should_skip": True, "name": "Cash balance concepts"},
    {"pattern": "Revenue", "should_skip": False, "name": "Revenue concepts"},
    {"pattern": "EndOfPeriod", "should_skip": True, "name": "End of period concepts"},
    {"pattern": "SharesOutstanding", "should_skip": True, "name": "Shares outstanding"},
]

for test in test_patterns:
    print(f"\n{test['name']} (pattern: '{test['pattern']}'):")
    
    for company in companies:
        # Find a concept matching this pattern
        concept = db.normalized_concepts_quarterly.find_one({
            "company_cik": company["cik"],
            "$or": [
                {"concept_name": {"$regex": test["pattern"], "$options": "i"}},
                {"label": {"$regex": test["pattern"], "$options": "i"}}
            ]
        })
        
        if concept:
            concept_name = concept.get("concept_name", "")
            label = concept.get("label", "")
            is_point_in_time = service._is_point_in_time_concept(concept_name, label)
            
            expected = "SKIP" if test["should_skip"] else "CALCULATE"
            actual = "SKIP" if is_point_in_time else "CALCULATE"
            status = "✅" if (is_point_in_time == test["should_skip"]) else "❌"
            
            print(f"  {status} {company['name']}: {concept_name[:60]}...")
            print(f"     Expected: {expected}, Got: {actual}")

print("\n" + "=" * 80)
print("Verification complete!")
print("=" * 80)
