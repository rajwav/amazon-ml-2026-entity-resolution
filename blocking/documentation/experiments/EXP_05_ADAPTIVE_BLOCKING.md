# Experiment 05: Adaptive / Record-Quality Blocking & The Multi-Match Blindspot

| Attribute | Specification |
|:---|:---|
| **Experiment ID** | `EXP_05` |
| **Date Executed** | 2026-09-25 |
| **Author / Operator** | Entity Resolution Engineering Team |
| **Status** | **Completed & Architecturally Decisive (Hypothesis Disproven / Gate Rejected)** |
| **Source Script** | [`experiments/blocking/adaptive_blocking.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/adaptive_blocking.py) |
| **Metrics Artifact** | [`experiments/results/exp5_adaptive_metrics.json`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp5_adaptive_metrics.json) |
| **Comparison Artifact** | [`experiments/results/exp5_policy_comparison.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp5_policy_comparison.tsv) |
| **Tail Analysis Artifact** | [`experiments/results/exp5_backbone_660_analysis.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp5_backbone_660_analysis.tsv) |

---

## 1. Objective
Test whether conditionally activating Channel F based on query ($S1$) record quality and candidate yield ($k < T$, missing digits, short names) can recover the 641 Channel F tail pairs while avoiding the 20-million candidate explosion of unconstrained Channel F.

---

## 2. Hypothesis
Queries that already generate abundant candidates ($k \ge 10$ or $k \ge 20$) from exact names or address digits have already succeeded. Therefore, Channel F only needs to trigger for "under-served" or low-evidence queries ($k < T$, zero digits, short names).

---

## 3. Starting Point / Baseline Reference
- Reference Backbone ($B+C+D+E$): 98.0859% recall (660 missed), 836.11 avg candidates/S1.
- Full Unconstrained F: 99.9536% recall (16 missed), 2,865.81 avg candidates/S1.

---

## 4. Dataset & Benchmark Setup
- Standard 10k Pilot Benchmark (10,000 queries, 84,481 targets, 34,481 true pairs, intra-country partitioning).

---

## 5. Method & Implementation Details
Ten adaptive $S1$-level gating policies were tested against the $B+C+D+E$ backbone:
- **Policy A**: Trigger F only if backbone candidates $k == 0$.
- **Policy B1 - B4**: Trigger F if $k < 5$, $k < 10$, $k < 20$, or $k < 50$.
- **Policy C1 - C3**: Trigger F if name tokens $\le 1$, or (tokens $\le 1 \land \text{digits} == 0$), or name length $\le 6$.
- **Policy D1 - D3**: Hybrid evidence policies triggering F if no exact name and no digit match occurred.

---

## 6. Code & Artifact References
- **Script**: [`experiments/blocking/adaptive_blocking.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/adaptive_blocking.py)
- **Metrics JSON**: [`experiments/results/exp5_adaptive_metrics.json`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp5_adaptive_metrics.json)
- **Comparison Table**: [`experiments/results/exp5_policy_comparison.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp5_policy_comparison.tsv)
- **Error Analysis**: [`experiments/results/exp5_backbone_660_analysis.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp5_backbone_660_analysis.tsv)

---

## 7. Results & Metrics Table

| Policy ID | Gating Condition | Trigger % | Recall % | Missed | Marginal TP | Avg Cands / $S1$ | Cost / New TP | Max Cands |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Ref_Backbone** | None (No F) | 0.00% | 98.0859% | 660 | 0 | 836.11 | - | 9,012 |
| **Policy A** | $k == 0$ | 0.01% | 98.0859% | 660 | 0 | 836.22 | 0.0 | 9,012 |
| **Policy B1** | $k < 5$ | 0.31% | 98.1120% | 651 | +9 | 843.23 | 7,910.8 | 9,012 |
| **Policy B2** | $k < 10$ | 1.08% | 98.1381% | 642 | +18 | 855.93 | 11,010.5 | 9,527 |
| **Policy B3** | $k < 20$ | 2.98% | 98.1700% | 631 | +29 | 882.42 | 15,969.6 | 9,527 |
| **Policy B4** | $k < 50$ | 9.60% | 98.2976% | 587 | +73 | 954.30 | 16,189.6 | 10,780 |
| **Policy C1** | tokens $\le 1$ | 11.27% | 98.4919% | 520 | +140 | 1,143.23 | 21,937.2 | 14,083 |
| **Policy C2** | tokens $\le 1 \land \text{dig} == 0$ | 0.91% | 98.2686% | 597 | +63 | 869.25 | 5,259.5 | 10,780 |
| **Policy D2** | $k < 10 \lor \text{NoEvidence}$ | 3.02% | 98.3788% | 559 | +101 | 902.28 | 6,551.2 | 10,474 |
| **Ref_Unconstrained** | Unconstrained F | 100.0% | **99.9536%** | **16** | **+644** | **2,865.81** | 31,517.0 | 17,555 |

---

## 8. Candidate Volume & Distribution Analysis
- All adaptive policies succeeded in suppressing candidate growth (averaging 836 to 1,143 candidates).
- However, they all experienced a hard **recall ceiling at 98.49%**, failing to recover over 500 of the 644 tail pairs.

---

## 9. Recall & Recovery Analysis (The Multi-Match Blindspot)
- Deep analysis of the 660 missed pairs in [`exp5_backbone_660_analysis.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp5_backbone_660_analysis.tsv) revealed the fundamental flaw in the hypothesis:
  - **92.4% of all Channel F-recoverable pairs belong to $S1$ entities that already have at least one correctly recalled target!**
  - Because entity resolution in this dataset is a **1-to-many matching problem** (cardinality up to 17), a query $S1$ may match Target A easily via an exact name match ($k \ge 10$), causing the query-level policy to classify $S1$ as "satisfied" and suppress Channel F.
  - Meanwhile, Target B (a heavily corrupted record belonging to the same entity) was only reachable via Channel F. By suppressing Channel F for query $S1$, Target B was permanently discarded!

---

## 10. Failure / Error Analysis
- Any policy framed as:
  $$\text{if } \text{Candidates}(S1) \ge T \implies \text{Do Not Run Channel F}$$
  fundamentally destroys 1-to-many recall. Query-level gating creates an artificial blind spot that sacrifices secondary and tertiary entity matches.

---

## 11. Key Lessons Learned
1. **The Multi-Match Blindspot Principle**: In 1-to-many entity resolution, query-level success does not imply query completion.
2. **Target-Side vs Query-Side Framing**: The question is **not** *"Which $S1$ records need Channel F?"*; it is *"Which individual target records need Channel F?"*.
3. **No S1-Level Suppression**: Channel F or its tail equivalent must remain universally accessible across all queries, but the index itself must be filtered to prevent candidate explosion.

---

## 12. Architectural Decision
- **Role**: **Negative Decision Record**.
- **Decision**: **PERMANENTLY REJECT all $S1$-level candidate threshold gating ($k < T$)**. Never suppress channels based on query candidate yield.

---

## 13. Impact on Subsequent Architecture
- Shifted the entire engineering strategy from query-side filtering to **target-side filtering** and **hierarchical multi-stage retrieval** (Experiment 06 and Experiment 08).
