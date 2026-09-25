# Experiment 06: Hierarchical Multi-Stage Blocking Pipeline (Champion v1)

| Attribute | Specification |
|:---|:---|
| **Experiment ID** | `EXP_06` |
| **Date Executed** | 2026-09-25 |
| **Author / Operator** | Entity Resolution Engineering Team |
| **Status** | **Completed & Validated (Champion v1 Baseline Architecture)** |
| **Source Script** | [`experiments/blocking/hierarchical_pipeline.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/hierarchical_pipeline.py) |
| **Metrics Artifact** | [`experiments/results/exp6_hierarchical_pipeline_metrics.json`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp6_hierarchical_pipeline_metrics.json) |
| **Comparison Artifact** | [`experiments/results/exp6_pipeline_comparison.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp6_pipeline_comparison.tsv) |
| **Remaining Misses Artifact** | [`experiments/results/exp6_remaining_25_misses.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp6_remaining_25_misses.tsv) |

---

## 1. Objective
Design, build, and benchmark an end-to-end 3-tier hierarchical blocking pipeline that combines:
1. Fast Level 1 composite sieve (`C2_Union_All`).
2. Robust Level 2 backbone ($B+C+D+E$ with selective name transliteration).
3. Target-side 5% IDF-filtered Level 3 Channel F, operating without any $S1$-level suppression.

---

## 2. Hypothesis
A multi-tier architecture where early fast tiers capture 95.6% of matches and the fallback tiers contribute target-side filtered candidates without query-level gating will break the 98.49% recall plateau, delivering $>99.90\%$ recall while cutting candidate volume by nearly 50% relative to Baseline G.

---

## 3. Starting Point / Baseline Reference
- Baseline G (`EXP_00`): 99.9449% recall, 3,294.6 avg candidates/S1.
- Experiment 05 Finding: Never use query-side suppression ($k < T$); filter on the target index instead.

---

## 4. Dataset & Benchmark Setup
- Standard 10k Pilot Benchmark (10,000 queries, 84,481 targets, 34,481 true pairs, intra-country partitioning).

---

## 5. Method & Implementation Details
The 3-tier hierarchical candidate generator operates as follows:
- **Level 1 (High Precision Sieve)**:
  - Exact normalized name.
  - 5 Composite keys: `(tok, loc)`, `(tok, dig)`, `(pref, loc)`, `(pref, dig)`, `(dig, loc)`.
- **Level 2 (Core Backbone)**:
  - Channels $B+C+D+E$.
  - Selective transliteration: Enabled on names and digits, disabled on location tokens.
- **Level 3 (Filtered Safety Net - Channel F)**:
  - Location token index filtered at target indexing time by dropping tokens appearing in $> 5\%$ of the target pool (US $> 2,500$, IN $> 1,700$).
  - Crucially: Evaluated for **all queries**, guaranteeing no multi-match blindspots.

Total candidate set:
$$\text{Candidates}(S1) = \text{L1}(S1) \cup \text{L2}(S1) \cup \text{L3}(S1)$$

---

## 6. Code & Artifact References
- **Script**: [`experiments/blocking/hierarchical_pipeline.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/hierarchical_pipeline.py)
- **Metrics JSON**: [`experiments/results/exp6_hierarchical_pipeline_metrics.json`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp6_hierarchical_pipeline_metrics.json)
- **Comparison TSV**: [`experiments/results/exp6_pipeline_comparison.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp6_pipeline_comparison.tsv)
- **Missed Pairs Log**: [`experiments/results/exp6_remaining_25_misses.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp6_remaining_25_misses.tsv)

---

## 7. Results & Metrics Table

| Pipeline Tier | Recall % | Recalled | Missed | Avg Cands / $S1$ | Median | P90 | P95 | P99 | Max | Zero $S1$ | Runtime |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Level 1 Only** | 95.63% | 32,973 | 1,508 | **104.2** | 10 | 325 | 604 | 1,207 | 3,564 | 135 | 0.41s |
| **Level 1 $\cup$ Level 2** | 98.09% | 33,821 | 660 | **836.1** | 377 | 2,251 | 3,559 | 5,539 | 9,012 | 1 | 1.75s |
| **L1 $\cup$ L2 $\cup$ L3 (Final)** | **99.9275%** | **34,456** | **25** | **1,698.0** | **1,135** | **4,155** | **5,321** | **7,386** | **10,904** | **0** | **8.71s** |
| **Baseline G (Control)** | 99.9449% | 34,462 | 19 | 3,294.6 | 2,621 | 8,012 | 9,555 | 12,450 | 18,372 | 0 | 35.57s |

---

## 8. Candidate Volume & Distribution Analysis
- Relative to Baseline G (3,294.6 candidates), the Hierarchical Pipeline generates **1,698.0 candidates per query**—a **48.46% reduction in candidate volume** ($16.98\text{M}$ candidates vs $32.95\text{M}$).
- Median candidates dropped by **56.7%** (from 2,621 down to 1,135).
- P95 dropped by **44.3%** (from 9,555 down to 5,321); Maximum dropped from 18,372 to 10,904.

---

## 9. Recall & Recovery Analysis
- Recovers **99.9275% of true pairs** (34,456 / 34,481), comfortably clearing the $\ge 99.90\%$ safety threshold.
- Successfully overcomes the 98.49% multi-match blindspot from Experiment 05 by evaluating Level 3 target-side filtered location tokens universally.
- Only 25 pairs missed across the entire 10,000 query benchmark (compared to 19 in Baseline G).

---

## 10. Failure / Error Analysis (The 25 Remaining Misses)
Inspection of [`exp6_remaining_25_misses.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp6_remaining_25_misses.tsv) revealed:
- **19 Baseline G Overlaps**: 19 of the 25 misses were the exact same hard-tail misses present in Baseline G (acronyms like "TB", domain handles like `empirecastillo.com`, missing address records).
- **6 Newly Lost in Level 3**: 6 pairs were lost due to the 5% IDF cutoff on Channel F in metropolitan areas where names were corrupted (e.g., `S1-683744230` `"AS Solution Limited"` vs `"assolution.com"` in Mumbai).

---

## 11. Key Lessons Learned
1. **Target-Side Filtering Rescues Multi-Match Recall**: By filtering the index at index-time rather than skipping queries at query-time, 1-to-many recall is completely preserved.
2. **First Champion Architecture**: Experiment 06 establishes our first fully validated candidate generation champion (**Champion v1**), cutting candidates in half while maintaining $>99.9\%$ recall.
3. **Target for Tail Recovery**: To push recall toward 100%, we must develop surgical channels specifically targeting the 25 residual misses.

---

## 12. Architectural Decision
- **Role**: **Champion Architecture Version 1 (`Champion_v1`)**.
- **Decision**: Formally crown this 3-tier architecture as Champion v1. Proceed immediately to Experiment 07 to verify scalability up to 100,000 queries before engineering further tail improvements.

---

## 13. Impact on Subsequent Architecture
- Served as the foundation for the scalability benchmark in Experiment 07.
- Defined the target candidate volume floor (~1,700 cands) that Experiment 08 subsequently optimized down to 1,141 cands.
