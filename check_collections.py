from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017/')['normalize_data']

print('Collections:')
for coll in ['concept_values_quarterly', 'concept_values_annual', 'normalized_concepts_quarterly', 'normalized_concepts_annual']:
    count = db[coll].count_documents({})
    print(f'  {coll}: {count} documents')

print('\nSample Q1-Q3 values:')
for period in ['Q1', 'Q2', 'Q3']:
    count = db.concept_values_quarterly.count_documents({'fiscal_period': period})
    print(f'  {period}: {count}')
