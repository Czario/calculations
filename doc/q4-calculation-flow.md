simple example how q4 calculation working :
Example - Americas:

Name search fails (aapl:AmericasSegmentMember not found)
Fallback 1: Search by path 001.003.001 + label "Americas" → FOUND!
Returns us-gaap:OperatingSegmentsMember concept
Example - Greater China:

Name search fails
Fallback 1: Path 001.003.003 + label → No match (annual is at .002)
Fallback 2: Path prefix 001.003.* + label "Greater China" → FOUND! (at 001.003.002)
