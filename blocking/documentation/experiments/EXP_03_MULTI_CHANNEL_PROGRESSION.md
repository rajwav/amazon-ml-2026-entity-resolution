# Experiment 03: Incremental Multi-Channel Progression & Channel Attribution

| Attribute | Specification |
|:---|:---|
| **Experiment ID** | `EXP_03` |
| **Date Executed** | 2026-09-25 |
| **Author / Operator** | Entity Resolution Engineering Team |
| **Status** | **Completed & Verified (Definitive Channel Decomposition)** |
| **Source Script** | [`experiments/blocking/multi_channel.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/multi_channel.py) |
| **Metrics Artifact** | [`experiments/results/exp3_incremental_union_metrics.json`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp3_incremental_union_metrics.json) |

---

## 1. Objective
Measure the exact marginal utility, cumulative recall, candidate volume growth, and candidate cost-per-pair for each individual channel in Baseline G ($B \to B+C \to B+C+D \to B+C+D+E \to B+C+D+E+F$).

---

## 2. Hypothesis
Candidate volume will exhibit severe non-linear growth with the addition of Channel F (location), whereas Channels B, C, D, and E will deliver the vast majority of true entity pairs ($>98\%$) at a fraction of the total candidate cost.

---

## 3. Starting Point / Baseline Reference
- Baseline G (`EXP_00`): Full union ($B+C+D+E+F$) at 99.9449% recall, 3,294.6 avg candidates/S1.

---

## 4. Dataset & Benchmark Setup
- Standard 10k Pilot Benchmark:
  - $S1$: 10,000 queries. Target Pool: 84,481 records. Ground Truth: 34,481 pairs.
  - Intra-country isolation (`US`, `IN`).

---

## 5. Method & Implementation Details
Channels were activated cumulatively in 5 successive stages:
1. **Step 1 ($B$)**: Exact core name index.
2. **Step 2 ($B+C$)**: Add significant name token index.
3. **Step 3 ($B+C+D$)**: Add 4-character name prefix index.
4. **Step 4 ($B+C+D+E$)**: Add address digits index (The "Backbone").
5. **Step 5 ($B+C+D+E+F$)**: Add broad location tokens index (Full Baseline G).

For each step, marginal newly recalled pairs ($\Delta \text{TP}$) and marginal candidates per newly recovered pair ($\Delta \text{Cands} / \Delta \text{TP}$) were tracked.

---

## 6. Code & Artifact References
- **Script**: [`experiments/blocking/multi_channel.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/multi_channel.py)
- **Metrics JSON**: [`experiments/results/exp3_incremental_union_metrics.json`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp3_incremental_union_metrics.json)

---

## 7. Results & Metrics Table

| Stage | Added Channel | Recall % | Recalled | Missed | Marginal TP ($\Delta$) | Avg Cands / $S1$ | Marginal Cands ($\Delta$) | Efficiency ($\Delta \text{Cands}/\Delta \text{TP}$) | Runtime |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Step 1** | **B** (Exact Core) | 39.12% | 13,490 | 20,991 | +13,490 | 1.6 | 15,850 | **1.2 cands / TP** | 0.02s |
| **Step 2** | **+ C** (Tokens) | 86.02% | 29,661 | 4,820 | +16,171 | 347.9 | 3,462,668 | **214.1 cands / TP** | 0.52s |
| **Step 3** | **+ D** (Prefix-4) | 91.18% | 31,441 | 3,040 | +1,780 | 369.2 | 212,990 | **119.7 cands / TP** | 1.58s |
| **Step 4** | **+ E** (Address Dig) | **98.09%** | **33,821** | **660** | **+2,380** | **836.1** | 4,669,623 | **1,962.0 cands / TP** | 2.32s |
| **Step 5** | **+ F** (Location) | **99.94%** | **34,462** | **19** | **+641** | **3,294.6** | 24,585,244 | **38,354.5 cands / TP** | 7.28s |

---

## 8. Candidate Volume & Distribution Analysis
- **Steps 1 through 4 ($B+C+D+E$)**: Generates **836.1 candidates per query** and captures **98.09% of true pairs** ($33,821 / 34,481$).
- **Step 5 (+ Channel F)**: Increases candidates by **2,458.5 candidates per query** (+294%) while recovering only **641 additional pairs** (+1.86% recall).
- Channel F requires an astonishing **38,355 candidate comparisons for every single additional true pair recovered**!

---

## 9. Recall & Recovery Analysis
- Channel B alone captures 39.12% of pairs with near-zero noise (1.6 cands/query).
- Significant tokens (Channel C) contribute the largest single recall jump (+16,171 pairs, 46.9% of ground truth).
- Address digits (Channel E) recover an essential 2,380 pairs (6.9% of ground truth).
- $B+C+D+E$ serves as a rock-solid, high-efficiency **Core Backbone**, missing only 660 pairs out of 34,481.

---

## 10. Failure / Error Analysis (The 660 Tail Pairs Missed by $B+C+D+E$)
- The 660 tail pairs represent the "hard tail" of entity resolution:
  - 641 of them have valid location tokens and are successfully recovered by Channel F in Step 5.
  - 19 of them fail even Channel F (the Baseline G misses).
- The central dilemma: How to capture the 641 Channel F pairs without paying the massive 24.58 million candidate penalty of unfiltered Channel F.

---

## 11. Key Lessons Learned
1. **$B+C+D+E$ is the Architectural Backbone**: Delivering 98.09% recall at 836 cands/S1, this combination forms the ideal core candidate generator.
2. **Channel F is Highly Inefficient in Aggregate**: 38,355 candidate evaluations per recovered match is economically unviable if applied uniformly.
3. **Surgical Location Retrieval is Required**: Rather than querying all location tokens for all entities, location matching must be constrained or prioritized dynamically.

---

## 12. Architectural Decision
- **Role**: **Core Candidate Backbone Definition**.
- **Decision**: Designate $B+C+D+E$ as Level-2 (Core Backbone). Isolate Channel F as a secondary/fallback tier that must undergo radical candidate optimization. Proceed to Experiment 04 to investigate transliteration.

---

## 13. Impact on Subsequent Architecture
- The "660 Tail Misses" became the explicit optimization benchmark for Experiments 04, 05, 06, 08, 09, and 10.
- Established the fundamental candidate efficiency metric ($\Delta \text{Cands} / \Delta \text{TP}$) used in all subsequent channel evaluations.
