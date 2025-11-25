"""Check for point-in-time concepts in income statement and cash flow Q4 calculations."""

from config.database import DatabaseConfig, DatabaseConnection

def check_point_in_time_concepts():
    """Identify point-in-time concepts that shouldn't have Q4 calculated."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    companies = [
        ("0000320193", "Apple"),
        ("0000789019", "Microsoft"),
        ("0001065280", "Netflix"),
        ("0001326801", "Meta")
    ]
    
    # Common point-in-time concept patterns (cash balances, ending positions)
    point_in_time_patterns = [
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "EndOfYear",
        "EndOfPeriod",
        "BeginningOfYear",
        "BeginningOfPeriod",
        "Outstanding",
        "Balance"
    ]
    
    print("\n" + "="*80)
    print("CHECKING FOR POINT-IN-TIME CONCEPTS IN Q4 CALCULATIONS")
    print("="*80)
    
    for cik, name in companies:
        print(f"\n{'='*80}")
        print(f"{name} (CIK: {cik})")
        print(f"{'='*80}")
        
        # Get Q4 values for income_statement and cash_flows
        q4_values = list(db.concept_values_quarterly.find({
            "company_cik": cik,
            "reporting_period.quarter": 4,
            "statement_type": {"$in": ["income_statement", "cash_flows"]}
        }, {"concept_id": 1, "statement_type": 1}))
        
        print(f"\nTotal Q4 values: {len(q4_values)}")
        
        # Get concept details
        concept_ids = list(set([q4["concept_id"] for q4 in q4_values]))
        concepts = list(db.normalized_concepts_quarterly.find({
            "_id": {"$in": concept_ids}
        }))
        
        # Check for point-in-time patterns
        point_in_time_concepts = []
        
        for concept in concepts:
            concept_name = concept.get("concept", "")
            label = concept.get("label", "")
            
            # Check if concept name or label matches point-in-time patterns
            for pattern in point_in_time_patterns:
                if pattern.lower() in concept_name.lower() or pattern.lower() in label.lower():
                    point_in_time_concepts.append({
                        "concept": concept_name,
                        "label": label,
                        "statement_type": concept.get("statement_type"),
                        "path": concept.get("path"),
                        "_id": concept["_id"]
                    })
                    break
        
        if point_in_time_concepts:
            print(f"\n⚠️  Found {len(point_in_time_concepts)} potential point-in-time concepts:")
            
            # Group by statement type
            income_pit = [c for c in point_in_time_concepts if c["statement_type"] == "income_statement"]
            cash_pit = [c for c in point_in_time_concepts if c["statement_type"] == "cash_flows"]
            
            if income_pit:
                print(f"\n  Income Statement ({len(income_pit)} concepts):")
                for concept in income_pit[:5]:
                    q4_count = db.concept_values_quarterly.count_documents({
                        "concept_id": concept["_id"],
                        "company_cik": cik,
                        "reporting_period.quarter": 4
                    })
                    print(f"    - {concept['label']} (Q4 values: {q4_count})")
            
            if cash_pit:
                print(f"\n  Cash Flows ({len(cash_pit)} concepts):")
                for concept in cash_pit[:10]:
                    q4_count = db.concept_values_quarterly.count_documents({
                        "concept_id": concept["_id"],
                        "company_cik": cik,
                        "reporting_period.quarter": 4
                    })
                    print(f"    - {concept['label']} (Q4 values: {q4_count})")
                    
                if len(cash_pit) > 10:
                    print(f"    ... and {len(cash_pit) - 10} more")
        else:
            print("\n✅ No point-in-time concepts found")
        
        # Check breakdown
        income_q4 = db.concept_values_quarterly.count_documents({
            "company_cik": cik,
            "reporting_period.quarter": 4,
            "statement_type": "income_statement"
        })
        
        cash_q4 = db.concept_values_quarterly.count_documents({
            "company_cik": cik,
            "reporting_period.quarter": 4,
            "statement_type": "cash_flows"
        })
        
        print(f"\n  Breakdown:")
        print(f"    Income Statement Q4: {income_q4}")
        print(f"    Cash Flows Q4: {cash_q4}")
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print("\nPoint-in-time concepts (like cash balances, ending positions) should NOT")
    print("be calculated using Q4 = Annual - (Q1 + Q2 + Q3) because they represent")
    print("snapshots at specific points in time, not period flows.")
    print("\nThese should be excluded from Q4 calculations or handled differently.")

if __name__ == "__main__":
    check_point_in_time_concepts()
