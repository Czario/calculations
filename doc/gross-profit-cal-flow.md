The flow is EXACTLY as you specified:
For EACH label in the formula ("Total Revenues" and "Cost of Revenues"):
standardlabels collection

Search: {standard_label: "Total Revenues", statement_type: "income_statement"}
Get: _id (standard_label_id)
concepts_standard_mapping collection

Search: {standard_label_id: <id from step 1>}
Get: concept_ids (array of concept IDs)
us_gaap_taxonomy collection

For EACH concept_id in the array:
Search: {_id: <concept_id>}
Get: concept (e.g., "us-gaap:Revenues", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax")
normalized_concepts_quarterly AND normalized_concepts_annual collections

For EACH concept found:
Search: {concept: <concept>, company_cik: <cik>, statement_type: "income_statement"}
Get: concept document with concept_id
Returns the FIRST matching concept found
Calculate Gross Profit:

Formula: Gross Profit = Total Revenues - Cost of Revenues
Gets values from concept_values_quarterly and concept_values_annual using the concept_ids found above
Insert calculated values:

Into: concept_values_quarterly (for Q1, Q2, Q3, Q4)
Into: concept_values_annual (for FY)
Links to Gross Profit concept created in normalized_concepts_quarterly and normalized_concepts_annual
The implementation correctly:

✅ Looks up BOTH labels ("Total Revenues" and "Cost of Revenues")
✅ Follows the complete flow through all 5 collections
✅ Tries ALL mapped concepts from us_gaap_taxonomy
✅ Searches in BOTH quarterly and annual collections separately
✅ Inserts values in BOTH concept_values_quarterly and concept_values_annual