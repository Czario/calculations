"""Test the dimensional concept matching fix."""

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

config = DatabaseConfig()
conn = DatabaseConnection(config)
db = conn.connect()

repository = FinancialDataRepository(db)

cik = '0001065280'
fiscal_year = 2024

print('='*80)
print('TESTING DIMENSIONAL CONCEPT MATCHING FIX')
print('='*80)

# Test case: nflx:StreamingMember (UCAN)
concept_name = 'nflx:StreamingMember'
concept_path = '001.001.001'  # UCAN path
statement_type = 'income_statement'

print(f'\nTest Case: {concept_name}')
print(f'Path: {concept_path}')
print(f'Expected Label: United States and Canada (UCAN)')

# Get quarterly data using the fixed method
quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
    concept_name,
    concept_path,
    cik,
    fiscal_year,
    statement_type
)

print(f'\nQuarterly Values Retrieved:')
print(f'  Q1: {quarterly_data.q1_value:>15,.0f}' if quarterly_data.q1_value else '  Q1: None')
print(f'  Q2: {quarterly_data.q2_value:>15,.0f}' if quarterly_data.q2_value else '  Q2: None')
print(f'  Q3: {quarterly_data.q3_value:>15,.0f}' if quarterly_data.q3_value else '  Q3: None')
print(f'  Annual: {quarterly_data.annual_value:>11,.0f}' if quarterly_data.annual_value else '  Annual: None')

if quarterly_data.can_calculate_q4():
    q4_value = quarterly_data.calculate_q4()
    sum_all = quarterly_data.q1_value + quarterly_data.q2_value + quarterly_data.q3_value + q4_value
    
    print(f'\nCalculated Q4:')
    print(f'  Q4 = {quarterly_data.annual_value:,.0f} - ({quarterly_data.q1_value:,.0f} + {quarterly_data.q2_value:,.0f} + {quarterly_data.q3_value:,.0f})')
    print(f'  Q4 = {q4_value:,.0f}')
    
    print(f'\nVerification:')
    print(f'  Sum of all quarters: {sum_all:,.0f}')
    print(f'  Annual value:        {quarterly_data.annual_value:,.0f}')
    print(f'  Match: {"✅ CORRECT" if abs(sum_all - quarterly_data.annual_value) < 1 else "❌ WRONG"}')
    
    # Expected values from user data
    expected_annual = 17359369000  # UCAN annual 2024
    expected_q4 = expected_annual - (4224315000 + 4295560000 + 4322476000)
    
    print(f'\nExpected vs Actual:')
    print(f'  Expected Annual: {expected_annual:,.0f}')
    print(f'  Actual Annual:   {quarterly_data.annual_value:,.0f}')
    print(f'  Match: {"✅" if abs(quarterly_data.annual_value - expected_annual) < 1 else "❌"}')
    print(f'\n  Expected Q4: {expected_q4:,.0f}')
    print(f'  Actual Q4:   {q4_value:,.0f}')
    print(f'  Match: {"✅" if abs(q4_value - expected_q4) < 1 else "❌"}')
else:
    print('\n❌ Cannot calculate Q4 - missing values')

# Test other regions too
print(f'\n{"="*80}')
print('TESTING ALL REGIONS')
print(f'{"="*80}')

regions = [
    ('001.001.001', 'United States and Canada (UCAN)', 17359369000),
    ('001.001.002', 'Europe, Middle East, and Africa (EMEA)', 12387035000),
    ('001.001.003', 'Latin America (LATAM)', 4839816000),
    ('001.001.004', 'Asia-Pacific (APAC)', 4414746000)
]

for path, expected_label, expected_annual in regions:
    quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        concept_name, path, cik, fiscal_year, statement_type
    )
    
    print(f'\nPath: {path} - {expected_label}')
    if quarterly_data.annual_value:
        match = "✅" if abs(quarterly_data.annual_value - expected_annual) < 1 else "❌"
        print(f'  Annual: {quarterly_data.annual_value:>14,.0f} (expected: {expected_annual:,.0f}) {match}')
    else:
        print(f'  Annual: None ❌')

conn.close()

print(f'\n{"="*80}')
print('TEST COMPLETE')
print(f'{"="*80}')
