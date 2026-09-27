# Experiment 02: Composite Blocking Keys & Complement Analysis

| Attribute | Specification |
|:---|:---|
| **Experiment ID** | `EXP_02` |
| **Date Executed** | 2026-09-25 |
| **Author / Operator** | Entity Resolution Engineering Team |
| **Status** | **Completed & Architecture Selected (Adopted as Level 1)** |
| **Source Script** | [`experiments/blocking/composite_keys.py`](../../../experiments/blocking/composite_keys.py) |
| **Analysis Script** | [`experiments/blocking/analyze_exp2_complement.py`](../../../experiments/blocking/analyze_exp2_complement.py) |
| **Metrics Artifact** | [`experiments/results/exp2_composite_keys_metrics.json`](../../../experiments/results/exp2_composite_keys_metrics.json) |
| **Error / Complement Artifact** | [`experiments/results/exp2_complement_analysis.tsv`](../../../experiments/results/exp2_complement_analysis.tsv) |

---

## 1. Objective
Evaluate whether multi-attribute composite blocking keys (pairing name tokens, prefixes, digits, and location tokens) can generate high precision, ultra-compact candidate pools, and analyze the exact 1,528 failure cases missed by the composite union.

---

## 2. Hypothesis
Pairing two distinct entity signals into a conjunction key (e.g., `Name Token + City` or `Prefix + Street Digit`) will drastically restrict inverted index posting lists to a tiny fraction of single-attribute lists ($<120$ candidates/query), while their union will capture $>95\%$ of true pairs.

---

## 3. Starting Point / Baseline Reference
- Baseline G (`EXP_00`): 99.9449% recall, 34,462 recalled, 19 missed, 3,294.6 avg candidates/S1.

---

## 4. Dataset & Benchmark Setup
- Standard 10k Pilot Benchmark:
  - $S1$: 10,000 queries. Target Pool: 84,481 records. Ground Truth: 34,481 pairs.
  - Strict intra-country partitioning (`US`, `IN`).

---

## 5. Method & Implementation Details
Evaluated 5 individual composite channels and 3 composite unions:
1. **C2_A (Tok & Loc)**: `(country, token, location_token)`
2. **C2_B (Tok & Dig)**: `(country, token, address_digit)`
3. **C2_C (Pref & Loc)**: `(country, prefix_4, location_token)`
4. **C2_D (Pref & Dig)**: `(country, prefix_4, address_digit)`
5. **C2_E (Dig & Loc)**: `(country, address_digit, location_token)`
6. **C2_Union_All_Composites**: Union of exact normalized name plus all 5 composite keys (A through E).

Following execution, an automated complement analysis (`analyze_exp2_complement.py`) cross-referenced every missed pair against Baseline G channels.

---

## 6. Code & Artifact References
- **Script**: [`experiments/blocking/composite_keys.py`](../../../experiments/blocking/composite_keys.py)
- **Complement Analysis Script**: [`experiments/blocking/analyze_exp2_complement.py`](../../../experiments/blocking/analyze_exp2_complement.py)
- **Metrics JSON**: [`experiments/results/exp2_composite_keys_metrics.json`](../../../experiments/results/exp2_composite_keys_metrics.json)
- **Complement Analysis TSV**: [`experiments/results/exp2_complement_analysis.tsv`](../../../experiments/results/exp2_complement_analysis.tsv)

---

## 7. Results & Metrics Table

| Key Configuration | Recall % | Recalled | Missed | Avg Cands / $S1$ | Median | P95 | Zero-Cand $S1$ | Reduction vs Base | Runtime |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **C2_A (Tok & Loc)** | 80.37% | 27,712 | 6,769 | 28.0 | 7 | 118 | 233 | -99.15% | 0.44s |
| **C2_B (Tok & Dig)** | 64.88% | 22,370 | 12,111 | 6.8 | 3 | 29 | 1,408 | -99.79% | 0.13s |
| **C2_C (Pref & Loc)** | 74.74% | 25,770 | 8,711 | 7.7 | 4 | 25 | 472 | -99.77% | 0.12s |
| **C2_D (Pref & Dig)** | 59.97% | 20,677 | 13,804 | 2.9 | 2 | 7 | 1,689 | -99.91% | 0.05s |
| **C2_E (Dig & Loc)** | 74.53% | 25,698 | 8,783 | 83.0 | 4 | 553 | 1,102 | -97.48% | 0.53s |
| **C2_Union_Name_Address** | 87.63% | 30,216 | 4,265 | 32.5 | 8 | 135 | 157 | -99.01% | 0.42s |
| **C2_Union_All_Composites** | **95.5686%** | **32,953** | **1,528** | **113.8** | **15** | **637** | **116** | **-96.55%** | **0.91s** |
| **C2_High_Precision_Union**| 86.02% | 29,661 | 4,820 | 347.9 | 231 | 1,655 | 14 | -89.44% | 1.98s |

---

## 8. Candidate Volume & Distribution Analysis
- `C2_Union_All_Composites` generated only **113.8 candidates per query** (median 15, P95 637).
- Relative to Baseline G (3,294.6 candidates), this represents an astonishing **96.55% candidate reduction** and runs in sub-second time (0.91 seconds for 10,000 queries).
- However, 116 queries generated 0 candidates due to missing conjunction attributes.

---

## 9. Recall & Recovery Analysis
- While `C2_Union_All` captured 32,953 true pairs, its recall was **95.57%**, missing **1,528 true pairs**.
- In the Amazon ML Challenge, where recall is the hard upper bound on model performance, a 4.43% recall loss is strictly disqualifying for a standalone blocker.

---

## 10. Complement Analysis (The 1,528 Missed Pairs)
Detailed diagnostic in [`exp2_complement_analysis.tsv`](../../../experiments/results/exp2_complement_analysis.tsv) revealed:
1. **Baseline G Recovery**: Baseline G recovered **1,509 of the 1,528 missed pairs** (98.76%).
2. **Channel Recovery Attribution**:
   - **Channel F (Location)** alone recovered **1,412 pairs** (92.4%).
   - Channel C (Name Tokens) recovered 74 pairs.
   - Channel D (Address Digits) recovered 23 pairs.
3. **Failure Category Breakdown**:
   - **Missing Target Address / Missing Digits**: 68.2% of misses lacked valid address digits on either query or target, rendering conjunctions `Tok & Dig`, `Pref & Dig`, and `Dig & Loc` impossible.
   - **Non-Overlapping Normalized Location**: City/state was spelled differently or missing, breaking `Tok & Loc` and `Pref & Loc`.
   - **Only Shared Signal Was Location**: 24.3% of true pairs had distinct names (e.g., parent/child subsidiaries, DBA aliases) and only co-occurred in Channel F.

---

## 11. Key Lessons Learned
1. **Never Use Composite Keys as Standalone Blocker**: Composites are conjunctions ($A \land B$). If either field is missing or corrupted, the true pair vanishes.
2. **Composites Are Ideal for Fast Tier-1 Retrieval**: Capturing 95.57% of ground truth at only 113.8 candidates/S1 makes `C2_Union_All` the perfect first tier in a multi-stage architecture.
3. **Channel F is Essential for the Tail**: Over 92% of the tail missed by composites requires broad location-based candidate retrieval.

---

## 12. Architectural Decision
- **Role**: **Tier-1 Fast Filter (`L1_Blocker`)**.
- **Decision**: Adopt `C2_Union_All_Composites` as Level-1 in a hierarchical architecture. Reject `C2_Union_All` as a standalone solution. Proceed to multi-channel progression testing in Experiment 03.

---

## 13. Impact on Subsequent Architecture
- Established Level 1 of the Champion architecture, which instantly resolves $>95.5\%$ of true matches with extreme efficiency.
- Defined the explicit requirement for a fallback Level 2 and Level 3 to catch the 1,528 tail misses.
