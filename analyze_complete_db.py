"""Comprehensive database analysis script for normalize_data database."""

from config.database import DatabaseConfig, DatabaseConnection
import json
from datetime import datetime
from bson import ObjectId


def serialize_doc(doc):
    """Convert MongoDB document to JSON-serializable format."""
    if isinstance(doc, dict):
        return {k: serialize_doc(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, datetime):
        return doc.isoformat()
    else:
        return doc


def analyze_collection_structure(db, collection_name, sample_size=3):
    """Analyze structure of a collection."""
    print(f"\n{'='*80}")
    print(f"COLLECTION: {collection_name}")
    print(f"{'='*80}")
    
    collection = db[collection_name]
    total_count = collection.count_documents({})
    print(f"Total documents: {total_count:,}")
    
    if total_count == 0:
        print("  [EMPTY COLLECTION]")
        return
    
    # Get sample documents
    samples = list(collection.find().limit(sample_size))
    
    # Analyze field structure from all samples
    all_fields = set()
    field_types = {}
    field_null_counts = {}
    
    # Scan more documents for field analysis
    scan_size = min(100, total_count)
    docs_to_scan = list(collection.find().limit(scan_size))
    
    for doc in docs_to_scan:
        for key, value in doc.items():
            all_fields.add(key)
            if key not in field_types:
                field_types[key] = set()
            field_types[key].add(type(value).__name__)
            
            if value is None:
                field_null_counts[key] = field_null_counts.get(key, 0) + 1
    
    print(f"\nFields found (from {scan_size} documents):")
    for field in sorted(all_fields):
        types = ', '.join(sorted(field_types[field]))
        null_count = field_null_counts.get(field, 0)
        null_pct = (null_count / scan_size) * 100
        print(f"  • {field}: {types}", end="")
        if null_count > 0:
            print(f" (NULL in {null_count}/{scan_size} = {null_pct:.1f}%)")
        else:
            print()
    
    # Show sample documents
    print(f"\nSample documents (first {len(samples)}):")
    for i, doc in enumerate(samples, 1):
        print(f"\n--- Sample {i} ---")
        serialized = serialize_doc(doc)
        print(json.dumps(serialized, indent=2, default=str))
    
    return {
        'total_count': total_count,
        'fields': list(all_fields),
        'field_types': {k: list(v) for k, v in field_types.items()},
        'field_null_counts': field_null_counts
    }


def analyze_cik_specific(db, cik):
    """Analyze data for specific CIK across all collections."""
    print(f"\n{'='*80}")
    print(f"CIK-SPECIFIC ANALYSIS: {cik}")
    print(f"{'='*80}")
    
    collections_to_check = [
        'normalized_concepts_quarterly',
        'normalized_concepts_annual',
        'normalized_values_quarterly',
        'normalized_values_annual',
        'concept_values',
        'sec_api_raw'
    ]
    
    for coll_name in collections_to_check:
        if coll_name not in db.list_collection_names():
            continue
            
        collection = db[coll_name]
        count = collection.count_documents({"company_cik": cik})
        print(f"\n{coll_name}: {count} records")
        
        if count > 0:
            # Show a few samples
            samples = list(collection.find({"company_cik": cik}).limit(2))
            for i, doc in enumerate(samples, 1):
                print(f"  Sample {i}:")
                # Show key fields
                if 'concept' in doc:
                    print(f"    concept: {doc.get('concept')}")
                if 'fiscal_year' in doc:
                    print(f"    fiscal_year: {doc.get('fiscal_year')}")
                if 'quarter' in doc:
                    print(f"    quarter: {doc.get('quarter')}")
                if 'value' in doc:
                    print(f"    value: {doc.get('value')}")
                if 'statement_type' in doc:
                    print(f"    statement_type: {doc.get('statement_type')}")
                if 'company_name' in doc:
                    print(f"    company_name: {doc.get('company_name')}")
                if 'form_type' in doc:
                    print(f"    form_type: {doc.get('form_type')}")
                if 'dimension_concept' in doc:
                    print(f"    dimension_concept: {doc.get('dimension_concept')}")


def analyze_database(target_cik=None):
    """Main database analysis function."""
    print("="*80)
    print("DATABASE ANALYSIS - normalize_data")
    print("="*80)
    print(f"Analysis started at: {datetime.now().isoformat()}")
    
    config = DatabaseConfig()
    conn = DatabaseConnection(config)
    db = conn.connect()
    
    print(f"\nConnected to database: {db.name}")
    
    # List all collections
    collections = db.list_collection_names()
    print(f"\nTotal collections: {len(collections)}")
    print("Collections:", ", ".join(collections))
    
    # Analyze each collection
    collection_stats = {}
    for coll_name in sorted(collections):
        try:
            stats = analyze_collection_structure(db, coll_name, sample_size=2)
            collection_stats[coll_name] = stats
        except Exception as e:
            print(f"Error analyzing {coll_name}: {e}")
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    for coll_name in sorted(collections):
        if coll_name in collection_stats and collection_stats[coll_name]:
            count = collection_stats[coll_name]['total_count']
            fields = len(collection_stats[coll_name]['fields'])
            print(f"{coll_name:45s} {count:>10,} docs, {fields:>3} fields")
    
    # CIK-specific analysis if provided
    if target_cik:
        analyze_cik_specific(db, target_cik)
    
    # Close connection
    conn.close()
    print(f"\n{'='*80}")
    print("Analysis complete!")
    print(f"{'='*80}")


if __name__ == "__main__":
    import sys
    
    # Get CIK from command line if provided
    target_cik = sys.argv[1] if len(sys.argv) > 1 else None
    
    if target_cik:
        print(f"Analyzing database with focus on CIK: {target_cik}")
    else:
        print("Analyzing entire database (provide CIK as argument for specific analysis)")
    
    analyze_database(target_cik)
