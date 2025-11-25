"""Check all companies for dimensional concepts with shared paths."""

from config.database import DatabaseConfig, DatabaseConnection
from collections import defaultdict

def check_all_companies():
    """Check all companies for dimensional concepts that share paths."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    print("\n" + "="*80)
    print("CHECKING ALL COMPANIES FOR DIMENSIONAL CONCEPT PATH CONFLICTS")
    print("="*80)
    
    # Get all companies
    companies = db.normalized_concepts_quarterly.distinct("company_cik")
    print(f"\nTotal companies in database: {len(companies)}")
    
    companies_with_conflicts = []
    
    for company_cik in companies:
        # Find concepts where multiple dimensional concepts share the same path
        pipeline = [
            {
                "$match": {
                    "company_cik": company_cik,
                    "dimension_concept": True,
                    "abstract": False
                }
            },
            {
                "$group": {
                    "_id": {
                        "concept": "$concept",
                        "path": "$path",
                        "statement_type": "$statement_type"
                    },
                    "count": {"$sum": 1},
                    "labels": {"$push": "$label"},
                    "dimension_members": {"$push": "$dimensions.explicitMember"}
                }
            },
            {
                "$match": {
                    "count": {"$gt": 1}
                }
            }
        ]
        
        conflicts = list(db.normalized_concepts_quarterly.aggregate(pipeline))
        
        if conflicts:
            companies_with_conflicts.append({
                "cik": company_cik,
                "conflicts": conflicts
            })
    
    print(f"\n{'='*80}")
    print(f"Companies with dimensional concept path conflicts: {len(companies_with_conflicts)}")
    print(f"{'='*80}")
    
    if not companies_with_conflicts:
        print("\n✅ No companies have dimensional concept path conflicts!")
        return
    
    # Show details for each company
    for company_data in companies_with_conflicts[:10]:  # Show first 10
        cik = company_data["cik"]
        conflicts = company_data["conflicts"]
        
        # Get company name
        sample_concept = db.normalized_concepts_quarterly.find_one({"company_cik": cik})
        
        print(f"\n{'-'*80}")
        print(f"CIK: {cik}")
        print(f"Total concept groups with conflicts: {len(conflicts)}")
        
        for conflict in conflicts[:3]:  # Show first 3 conflicts per company
            concept_info = conflict["_id"]
            count = conflict["count"]
            labels = conflict["labels"]
            members = conflict["dimension_members"]
            
            print(f"\n  Concept: {concept_info['concept']}")
            print(f"  Path: {concept_info['path']}")
            print(f"  Statement: {concept_info['statement_type']}")
            print(f"  Count: {count} concepts sharing this path")
            print(f"  Labels:")
            for i, (label, member) in enumerate(zip(labels, members), 1):
                print(f"    {i}. {label} (Member: {member})")
        
        if len(conflicts) > 3:
            print(f"\n  ... and {len(conflicts) - 3} more conflict groups")
    
    if len(companies_with_conflicts) > 10:
        print(f"\n... and {len(companies_with_conflicts) - 10} more companies")
    
    # Summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    
    total_conflicts = sum(len(c["conflicts"]) for c in companies_with_conflicts)
    print(f"Total concept groups with conflicts: {total_conflicts}")
    
    # Check if any have Q4 values calculated
    print(f"\n{'='*80}")
    print("CHECKING Q4 CALCULATION STATUS")
    print(f"{'='*80}")
    
    for company_data in companies_with_conflicts[:5]:  # Check first 5
        cik = company_data["cik"]
        
        # Get dimensional concepts for this company
        dimensional_concepts = list(db.normalized_concepts_quarterly.find({
            "company_cik": cik,
            "dimension_concept": True,
            "abstract": False
        }, {"_id": 1}).limit(100))
        
        concept_ids = [c["_id"] for c in dimensional_concepts]
        
        # Check how many have Q4 values
        q4_count = db.concept_values_quarterly.count_documents({
            "concept_id": {"$in": concept_ids},
            "company_cik": cik,
            "reporting_period.quarter": 4
        })
        
        total_concepts = len(dimensional_concepts)
        
        print(f"\nCIK {cik}:")
        print(f"  Dimensional concepts: {total_concepts}")
        print(f"  With Q4 values: {q4_count}")
        print(f"  Potentially affected: {total_concepts - q4_count}")

if __name__ == "__main__":
    check_all_companies()
