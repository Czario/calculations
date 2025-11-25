"""Investigate why regional Q4 values were calculated wrong."""

from pymongo import MongoClient
from repositories.financial_repository import FinancialDataRepository

client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

repository = FinancialDataRepository(db)

cik = "0001065280"  # Netflix

print("=" * 80)
print("INVESTIGATING WHY REGIONAL Q4 WAS WRONG")
print("=" * 80)

# The 4 regional streaming members all share the same path: 001.001.001
concept_name = "nflx:StreamingMember"
path = "001.001.001"

regions = [
    {"name": "UCAN", "member": "nflx:UnitedStatesAndCanadaMember"},
    {"name": "EMEA", "member": "us-gaap:EMEAMember"},
    {"name": "LATAM", "member": "srt:LatinAmericaMember"},
    {"name": "APAC", "member": "srt:AsiaPacificMember"}
]

# Get all 4 regional concepts
regional_concepts = []
for region in regions:
    concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": cik,
        "concept": concept_name,
        "path": path,
        "dimensions.explicitMember": region["member"]
    })
    if concept:
        regional_concepts.append({
            "region": region["name"],
            "member": region["member"],
            "concept": concept
        })

print(f"\nFound {len(regional_concepts)} regional concepts, all sharing:")
print(f"  Concept name: {concept_name}")
print(f"  Path: {path}")
print(f"  Company CIK: {cik}")

print("\n" + "=" * 80)
print("THE PROBLEM: Same path, different dimension members")
print("=" * 80)

for rc in regional_concepts:
    print(f"\n{rc['region']}:")
    print(f"  Member: {rc['member']}")
    print(f"  Concept ID: {rc['concept']['_id']}")
    print(f"  Path: {rc['concept']['path']}")

print("\n" + "=" * 80)
print("TESTING: What happens if we look up by name + path only?")
print("=" * 80)

# This is what the OLD code would have done - lookup without dimension member
print(f"\nLooking up quarterly concept by name={concept_name}, path={path}")

# Old method: get_quarterly_concept by name and path
quarterly_concept = repository._find_quarterly_concept(
    concept_name, path, cik, "income_statement"
)

if quarterly_concept:
    print(f"  Found concept ID: {quarterly_concept['_id']}")
    print(f"  Dimension member: {quarterly_concept.get('dimensions', {}).get('explicitMember', 'None')}")
    
    # Check which region this matches
    for rc in regional_concepts:
        if rc['concept']['_id'] == quarterly_concept['_id']:
            print(f"  ⚠️ This matches: {rc['region']}")
            break

print("\n" + "=" * 80)
print("TESTING: Finding annual concept for each region")
print("=" * 80)

fiscal_year = 2024

for rc in regional_concepts:
    print(f"\n{rc['region']} (quarterly concept ID: {rc['concept']['_id']}):")
    
    # Try to find matching annual concept using OLD method (by name and path only)
    annual_concept_old = repository._find_matching_annual_concept(
        concept_name, cik, "income_statement"
    )
    
    if annual_concept_old:
        print(f"  OLD method found annual concept:")
        print(f"    ID: {annual_concept_old['_id']}")
        print(f"    Member: {annual_concept_old.get('dimensions', {}).get('explicitMember', 'None')}")
        
        # Get annual value
        annual_value = db.concept_values_annual.find_one({
            "concept_id": annual_concept_old["_id"],
            "company_cik": cik,
            "reporting_period.fiscal_year": fiscal_year
        })
        
        if annual_value:
            print(f"    Annual value: {annual_value['value']:,.0f}")
            
            # Check if this is the WRONG annual for this quarterly
            correct_member = rc['member']
            found_member = annual_concept_old.get('dimensions', {}).get('explicitMember')
            
            if correct_member != found_member:
                print(f"    ❌ WRONG! This is {found_member}")
                print(f"    Should be: {correct_member}")
            else:
                print(f"    ✅ Correct match!")

print("\n" + "=" * 80)
print("ROOT CAUSE ANALYSIS")
print("=" * 80)

print("\n1. All 4 regions share the SAME path: 001.001.001")
print("2. They are differentiated ONLY by dimensions.explicitMember:")
for rc in regional_concepts:
    print(f"   - {rc['region']}: {rc['member']}")

print("\n3. OLD CODE: Matched quarterly to annual by name + path ONLY")
print("   Result: All 4 quarterly concepts matched to the SAME annual concept")
print("   (Whichever one was found first in the database)")

print("\n4. NEW CODE: Matches by dimension member FIRST (Priority 1)")
print("   Result: Each quarterly concept matches to its correct annual concept")

print("\n" + "=" * 80)
print("SOLUTION VERIFICATION")
print("=" * 80)

print("\nChecking _find_matching_annual_concept with dimension member matching...")

for rc in regional_concepts:
    quarterly_concept = rc['concept']
    
    # Get root parent for this quarterly concept
    root_parent_id, root_parent_name = repository._get_root_parent_concept_info(
        quarterly_concept, "normalized_concepts_quarterly"
    )
    
    # Find matching annual with NEW method (includes dimension member)
    annual_concept_new = repository._find_matching_annual_concept(
        concept_name, 
        cik, 
        "income_statement",
        quarterly_root_parent_id=root_parent_id,
        quarterly_root_parent_name=root_parent_name,
        quarterly_dimension_member=quarterly_concept.get('dimensions', {}).get('explicitMember')
    )
    
    print(f"\n{rc['region']}:")
    print(f"  Quarterly member: {rc['member']}")
    
    if annual_concept_new:
        annual_member = annual_concept_new.get('dimensions', {}).get('explicitMember')
        print(f"  Annual member: {annual_member}")
        
        if rc['member'] == annual_member:
            print(f"  ✅ CORRECT MATCH!")
        else:
            print(f"  ❌ Still wrong!")
