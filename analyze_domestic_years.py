"""Analyze which years have data for DomesticStreamingMember."""

from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

cik = "0001065280"  # Netflix

print("=" * 80)
print("DOMESTIC STREAMING MEMBER - YEAR-BY-YEAR ANALYSIS")
print("=" * 80)

# Get one of the DomesticStreamingMember concepts
concept = db.normalized_concepts_quarterly.find_one({
    "company_cik": cik,
    "dimensions.explicitMember": "nflx:DomesticStreamingMember",
    "path": "002.001"
})

if concept:
    print(f"\nAnalyzing: {concept.get('concept', 'N/A')}")
    print(f"Path: {concept.get('path', 'N/A')}")
    print(f"Concept ID: {concept['_id']}")
    
    # Get all values grouped by year and quarter
    values = list(db.concept_values_quarterly.find({
        "concept_id": concept["_id"],
        "company_cik": cik
    }).sort([("reporting_period.fiscal_year", 1), ("reporting_period.quarter", 1)]))
    
    print(f"\nTotal values: {len(values)}")
    
    # Group by year
    by_year = {}
    for val in values:
        year = val["reporting_period"]["fiscal_year"]
        quarter = val["reporting_period"]["quarter"]
        
        if year not in by_year:
            by_year[year] = {}
        by_year[year][f"Q{quarter}"] = val["value"]
    
    # Check annual values
    annual_concept = db.normalized_concepts_annual.find_one({
        "company_cik": cik,
        "concept": concept.get("concept"),
        "dimensions.explicitMember": "nflx:DomesticStreamingMember"
    })
    
    annual_values = {}
    if annual_concept:
        print(f"\nAnnual concept found: {annual_concept['_id']}")
        annuals = list(db.concept_values_annual.find({
            "concept_id": annual_concept["_id"],
            "company_cik": cik
        }))
        
        for ann in annuals:
            year = ann["reporting_period"]["fiscal_year"]
            annual_values[year] = ann["value"]
    
    # Display year by year
    print(f"\n{'Year':<6} {'Q1':>15} {'Q2':>15} {'Q3':>15} {'Q4':>15} {'Annual':>15} {'Can Calc Q4?':>15}")
    print("-" * 105)
    
    all_years = sorted(set(list(by_year.keys()) + list(annual_values.keys())))
    
    for year in all_years:
        q1 = by_year.get(year, {}).get("Q1", None)
        q2 = by_year.get(year, {}).get("Q2", None)
        q3 = by_year.get(year, {}).get("Q3", None)
        q4 = by_year.get(year, {}).get("Q4", None)
        annual = annual_values.get(year, None)
        
        can_calc = "Yes" if (q1 is not None and q2 is not None and q3 is not None and annual is not None) else "No"
        
        q1_str = f"{q1:,.0f}" if q1 is not None else "-"
        q2_str = f"{q2:,.0f}" if q2 is not None else "-"
        q3_str = f"{q3:,.0f}" if q3 is not None else "-"
        q4_str = f"{q4:,.0f}" if q4 is not None else "MISSING"
        annual_str = f"{annual:,.0f}" if annual is not None else "-"
        
        # Highlight years where Q4 should exist but doesn't
        if can_calc == "Yes" and q4 is None:
            year_marker = f"{year} ⚠️"
        else:
            year_marker = str(year)
        
        print(f"{year_marker:<6} {q1_str:>15} {q2_str:>15} {q3_str:>15} {q4_str:>15} {annual_str:>15} {can_calc:>15}")
    
    # Summary
    print("\n" + "=" * 105)
    print("SUMMARY")
    print("=" * 105)
    
    missing_q4 = []
    for year in all_years:
        q1 = by_year.get(year, {}).get("Q1", None)
        q2 = by_year.get(year, {}).get("Q2", None)
        q3 = by_year.get(year, {}).get("Q3", None)
        q4 = by_year.get(year, {}).get("Q4", None)
        annual = annual_values.get(year, None)
        
        if q1 is not None and q2 is not None and q3 is not None and annual is not None and q4 is None:
            missing_q4.append(year)
    
    if missing_q4:
        print(f"\n❌ Years with all data (Q1, Q2, Q3, Annual) but MISSING Q4: {missing_q4}")
        print(f"   These {len(missing_q4)} Q4 values should be calculated!")
    else:
        print(f"\n✅ All years that can have Q4 calculated already have Q4 values")
    
    # Check if 2024-2025 simply don't have quarterly data yet
    recent_years = [2024, 2025]
    no_data_years = []
    for year in recent_years:
        if year not in by_year or not by_year[year]:
            no_data_years.append(year)
    
    if no_data_years:
        print(f"\nℹ️  Years with no quarterly data at all: {no_data_years}")
        print(f"   (Data may not be available yet or Netflix changed reporting)")
