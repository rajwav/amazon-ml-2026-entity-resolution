# 01 PROJECT RULES: INVIOLABLE OPERATIONAL MANDATES

These rules govern all engineering, modeling, and experimental behavior. They are absolute.

## 1. Scientific & Grounding Discipline
1. **NEVER invent experimental results.** All reported metrics, recalls, candidate counts, runtimes, and RAM footprints must come directly from executed code output.
2. **NEVER claim something was tested if it was not.** If a parameter or approach was not executed, mark it clearly as "Untested Hypothesis".
3. **NEVER assume an improvement without measured evidence.** Do not claim a candidate count reduction is beneficial if true pair recall was not simultaneously verified.
4. **ALWAYS report uncertainty.** If a failure cause or trend is ambiguous, state "Unknown — needs verification."

## 2. Integrity & Competition Fair Play
5. **NEVER use external data.** No Google Maps, geocoding APIs, commercial ER tools, corporate registries (MCA, EDGAR, Sirene), internet lookups, or web scraping. Use ONLY the provided dataset.
6. **NEVER use test ground truth.** All validation, training, and threshold tuning must be performed on the training set. The test pipeline must run strictly blind.
7. **NEVER hardcode countries or entities.** Code must operate generically by country label. French entities in the test set must be supported by the same country-agnostic logic as US and India.

## 3. Experimental Reproducibility & Baseline Protection
8. **NEVER silently modify the baseline.** Strategy G (`B + C + D + E + F`) is the verified control baseline. Any modification must be created as a new experiment ID (`E1`, `E2`, etc.).
9. **NEVER overwrite successful experiments or delete failed runs.** Negative results are critical data that prevent circular mistakes.
10. **ALWAYS preserve reproducibility.** Every benchmark must record:
    - Exact sample / seed (`random.seed(42)`)
    - Exact true-pair universe
    - Normalization code version
    - Execution configuration
    - Runtime and peak memory

## 4. Evaluation Semantics
11. **Evaluate recall strictly as True-Pair Recall:**
    $$\text{Recall} = \frac{\text{Recalled True Pairs}}{\text{Total True Pairs}}$$
    Do NOT compute recall as matched businesses over total businesses.
12. **Candidate $\neq$ Predicted Match.** A candidate is a plausible link fed to the matching model. Do NOT compute blocking precision as if every candidate were a final prediction.
