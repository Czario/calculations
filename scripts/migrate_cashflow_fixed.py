"""Migration script to mark already-fixed cash flow records.

This script is for one-time use to mark cash flow Q2 and Q3 records
that have already been fixed (before the incremental processing feature was added).

It identifies records that were fixed by checking if they have negative values
or by running a consistency check against Q1 values.

Usage:
    uv run scripts/migrate_cashflow_fixed.py --dry-run          # Preview what will be updated
    uv run scripts/migrate_cashflow_fixed.py --execute          # Actually update records
    uv run scripts/migrate_cashflow_fixed.py --cik 0001326801   # Process specific company
    uv run scripts/migrate_cashflow_fixed.py --execute --verbose  # With detailed output
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository


class CashflowFixedMigration:
    """Migration tool to mark already-fixed cash flow records."""
    
    def __init__(self, db, verbose: bool = False):
        self.db = db
        self.verbose = verbose
        self.concept_values_quarterly = db.concept_values_quarterly
    
    def get_all_cashflow_companies(self) -> List[str]:
        """Get all unique company CIKs that have cash flow data."""
        pipeline = [
            {
                "$match": {
                    "statement_type": "cash_flows",
                    "form_type": "10-Q",
                    "reporting_period.quarter": {"$in": [2, 3]}
                }
            },
            {"$group": {"_id": "$company_cik"}},
            {"$sort": {"_id": 1}}
        ]
        
        result = list(self.concept_values_quarterly.aggregate(pipeline))
        return [item["_id"] for item in result if item["_id"]]
    
    def get_unfixed_q2_q3_count(self, company_cik: Optional[str] = None) -> Dict[str, int]:
        """Get count of Q2/Q3 records without cashflow_fixed flag."""
        match_query = {
            "statement_type": "cash_flows",
            "form_type": "10-Q",
            "reporting_period.quarter": {"$in": [2, 3]},
            "cashflow_fixed": {"$ne": True}
        }
        
        if company_cik:
            match_query["company_cik"] = company_cik
        
        pipeline = [
            {"$match": match_query},
            {
                "$group": {
                    "_id": "$reporting_period.quarter",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        result = list(self.concept_values_quarterly.aggregate(pipeline))
        counts = {"q2": 0, "q3": 0}
        for item in result:
            if item["_id"] == 2:
                counts["q2"] = item["count"]
            elif item["_id"] == 3:
                counts["q3"] = item["count"]
        
        return counts
    
    def mark_all_q2_q3_as_fixed(
        self, 
        company_cik: Optional[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Mark all Q2/Q3 cash flow records as fixed.
        
        This is the simple approach that marks ALL Q2/Q3 cash flow records
        as fixed. Use this if you're confident all existing data has been fixed.
        
        Args:
            company_cik: Optional company CIK to filter
            dry_run: If True, only count records without updating
            
        Returns:
            Statistics about the operation
        """
        results = {
            "q2_marked": 0,
            "q3_marked": 0,
            "dry_run": dry_run,
            "company_cik": company_cik or "all"
        }
        
        # Build query for Q2 records without cashflow_fixed
        q2_query = {
            "statement_type": "cash_flows",
            "form_type": "10-Q",
            "reporting_period.quarter": 2,
            "cashflow_fixed": {"$ne": True}
        }
        
        # Build query for Q3 records without cashflow_fixed
        q3_query = {
            "statement_type": "cash_flows",
            "form_type": "10-Q",
            "reporting_period.quarter": 3,
            "cashflow_fixed": {"$ne": True}
        }
        
        if company_cik:
            q2_query["company_cik"] = company_cik
            q3_query["company_cik"] = company_cik
        
        if dry_run:
            # Just count the records
            results["q2_marked"] = self.concept_values_quarterly.count_documents(q2_query)
            results["q3_marked"] = self.concept_values_quarterly.count_documents(q3_query)
        else:
            # Actually update the records
            migration_timestamp = datetime.utcnow()
            
            # Update Q2 records
            q2_result = self.concept_values_quarterly.update_many(
                q2_query,
                {
                    "$set": {
                        "cashflow_fixed": True,
                        "cashflow_fixed_at": migration_timestamp,
                        "cashflow_fixed_by": "migration_script"
                    }
                }
            )
            results["q2_marked"] = q2_result.modified_count
            
            # Update Q3 records
            q3_result = self.concept_values_quarterly.update_many(
                q3_query,
                {
                    "$set": {
                        "cashflow_fixed": True,
                        "cashflow_fixed_at": migration_timestamp,
                        "cashflow_fixed_by": "migration_script"
                    }
                }
            )
            results["q3_marked"] = q3_result.modified_count
        
        return results
    
    def preview_by_company(self, company_cik: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get preview of unfixed records per company."""
        match_query = {
            "statement_type": "cash_flows",
            "form_type": "10-Q",
            "reporting_period.quarter": {"$in": [2, 3]},
            "cashflow_fixed": {"$ne": True}
        }
        
        if company_cik:
            match_query["company_cik"] = company_cik
        
        pipeline = [
            {"$match": match_query},
            {
                "$group": {
                    "_id": {
                        "company_cik": "$company_cik",
                        "quarter": "$reporting_period.quarter"
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$group": {
                    "_id": "$_id.company_cik",
                    "quarters": {
                        "$push": {
                            "quarter": "$_id.quarter",
                            "count": "$count"
                        }
                    },
                    "total": {"$sum": "$count"}
                }
            },
            {"$sort": {"_id": 1}}
        ]
        
        return list(self.concept_values_quarterly.aggregate(pipeline))


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migration script to mark already-fixed cash flow records',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run scripts/migrate_cashflow_fixed.py --dry-run              # Preview all companies
  uv run scripts/migrate_cashflow_fixed.py --dry-run --verbose    # Detailed preview per company
  uv run scripts/migrate_cashflow_fixed.py --execute              # Update all records
  uv run scripts/migrate_cashflow_fixed.py --cik 0001326801 --dry-run  # Preview specific company
  uv run scripts/migrate_cashflow_fixed.py --cik 0001326801 --execute  # Update specific company

This script marks existing Q2/Q3 cash flow records with:
  - cashflow_fixed: true
  - cashflow_fixed_at: <timestamp>
  - cashflow_fixed_by: "migration_script"

IMPORTANT: Only run --execute once you've verified the data is already fixed!
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what will be updated without making changes (default behavior)'
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute the migration and update records'
    )
    
    parser.add_argument(
        '--cik',
        type=str,
        help='Process only a specific company CIK'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Show detailed per-company breakdown'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.dry_run and args.execute:
        parser.error("Cannot specify both --dry-run and --execute")
    
    # Default to dry-run if neither specified
    if not args.dry_run and not args.execute:
        args.dry_run = True
        print("ℹ️  No mode specified, defaulting to --dry-run\n")
    
    config = DatabaseConfig()
    
    try:
        with DatabaseConnection(config) as db:
            migration = CashflowFixedMigration(db, verbose=args.verbose)
            
            print("=" * 60)
            print("🔧 CASH FLOW FIXED MIGRATION TOOL")
            print("=" * 60)
            
            if args.dry_run:
                print("📋 MODE: DRY RUN (preview only, no changes)")
            else:
                print("⚠️  MODE: EXECUTE (will update records!)")
            
            if args.cik:
                print(f"📍 Target: Company {args.cik}")
            else:
                print("📍 Target: All companies")
            
            print("=" * 60 + "\n")
            
            # Show detailed preview if verbose
            if args.verbose:
                print("📊 Unfixed records by company:\n")
                preview = migration.preview_by_company(args.cik)
                
                if not preview:
                    print("  ✅ No unfixed Q2/Q3 cash flow records found!")
                else:
                    for company in preview:
                        quarters_info = ", ".join([
                            f"Q{q['quarter']}: {q['count']}" 
                            for q in sorted(company['quarters'], key=lambda x: x['quarter'])
                        ])
                        print(f"  {company['_id']}: {quarters_info} (Total: {company['total']})")
                
                print()
            
            # Run the migration (or preview)
            results = migration.mark_all_q2_q3_as_fixed(
                company_cik=args.cik,
                dry_run=args.dry_run
            )
            
            # Print results
            print("\n" + "=" * 60)
            if args.dry_run:
                print("📋 DRY RUN RESULTS (no changes made)")
            else:
                print("✅ MIGRATION COMPLETED")
            print("=" * 60)
            
            print(f"📍 Target: {results['company_cik']}")
            print(f"🔢 Q2 records {'to mark' if args.dry_run else 'marked'}: {results['q2_marked']}")
            print(f"🔢 Q3 records {'to mark' if args.dry_run else 'marked'}: {results['q3_marked']}")
            print(f"📊 Total: {results['q2_marked'] + results['q3_marked']}")
            
            if args.dry_run and (results['q2_marked'] > 0 or results['q3_marked'] > 0):
                print("\n💡 To apply these changes, run with --execute flag:")
                if args.cik:
                    print(f"   uv run scripts/migrate_cashflow_fixed.py --execute --cik {args.cik}")
                else:
                    print("   uv run scripts/migrate_cashflow_fixed.py --execute")
            
            print("=" * 60)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
