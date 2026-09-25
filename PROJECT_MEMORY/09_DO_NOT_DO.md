# 09 DO NOT DO: PERMANENT PROJECT BLACKLIST

The following practices are strictly prohibited under all circumstances:

1. **DO NOT** use Google, Bing, Maps, OpenStreetMap, geocoding APIs, or web scraping.
2. **DO NOT** use external company registers (MCA, SEC EDGAR, Sirene, OpenCorporates) or third-party ER tools.
3. **DO NOT** touch or attempt to inspect test ground truth (it does not exist; any test labels are unverified).
4. **DO NOT** hardcode country logic to only `US` and `India`. The pipeline must handle arbitrary country labels, including `France` in the test set.
5. **DO NOT** hardcode specific company names, IDs, or rule exceptions for individual businesses.
6. **DO NOT** fabricate, estimate, or extrapolate metrics without actual execution.
7. **DO NOT** silently change normalization, tokenization, or sampling parameters between experiments.
8. **DO NOT** overwrite Baseline G results or candidate caches.
9. **DO NOT** delete failed or negative experiment logs.
10. **DO NOT** optimize solely for candidate reduction while ignoring true pair recall.
11. **DO NOT** confuse candidate generation with final matching (a candidate is a candidate, not a predicted match).
12. **DO NOT** confuse true-pair recall with business-level entity recall.
13. **DO NOT** allocate millions of Python set objects or execute unvectorized pairwise loops on large tables.
14. **DO NOT** jump to full 2.2M production execution before pilot experiments are completed, validated, and compared.
