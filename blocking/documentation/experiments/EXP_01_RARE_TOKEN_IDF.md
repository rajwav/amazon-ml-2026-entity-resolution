# Experiment 01: Rare-Token & Global Frequency (IDF) Filtering

| Attribute | Specification |
|:---|:---|
| **Experiment ID** | `EXP_01` |
| **Date Executed** | 2026-09-25 |
| **Author / Operator** | Entity Resolution Engineering Team |
| **Status** | **Completed & Evaluated (Threshold Calibrated)** |
| **Source Script** | [`experiments/blocking/rare_token.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/rare_token.py) |
| **Metrics Artifact** | [`experiments/results/exp1_rare_token_metrics.json`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp1_rare_token_metrics.json) |
| **Lost Pairs Artifact** | [`experiments/results/exp1_newly_lost_pairs.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp1_newly_lost_pairs.tsv) |

---

## 1. Objective
Evaluate whether globally pruning frequent tokens across the target corpus using IDF/document-frequency thresholds can significantly reduce candidate volume without violating the $\ge 99.90\%$ recall threshold.

---

## 2. Hypothesis
A small percentage of highly frequent tokens (e.g., common city names, generic words like "center", "road", "enterprises") account for the vast majority of index postings and candidate pairs. Suppressing tokens exceeding document-frequency caps will slash candidate volume by over 50% while retaining nearly all true matches.

---

## 3. Starting Point / Baseline Reference
- Baseline G (`EXP_00`): 99.9449% recall, 34,462 recalled, 19 missed, 3,294.6 avg candidates/S1.

---

## 4. Dataset & Benchmark Setup
- Standard 10k Pilot Benchmark:
  - $S1$: 10,000 queries (6,000 US, 4,000 IN).
  - Target Pool: 84,481 records (50,000 US, 34,481 IN).
  - True Pairs: 34,481.
  - Partitioning: Strict country isolation.

---

## 5. Method & Implementation Details
Four frequency-cutoff configurations were evaluated across the target corpus:
1. **E1_A (No Filtering)**: Full Baseline G control (0% pruning).
2. **E1_B (Conservative)**: Drop tokens appearing in $> 5\%$ of target pool (US $> 2,500$, IN $> 1,700$).
3. **E1_C (Moderate)**: Drop tokens appearing in $> 2\%$ of target pool (US $> 1,000$, IN $> 680$).
4. **E1_D (Aggressive)**: Drop tokens appearing in $> 1\%$ of target pool (US $> 500$, IN $> 340$).

Global frequency tables were constructed across all target fields. Inverted index postings for any token whose frequency exceeded the threshold were suppressed during indexing.

---

## 6. Code & Artifact References
- **Script**: [`experiments/blocking/rare_token.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/rare_token.py)
- **Metrics JSON**: [`experiments/results/exp1_rare_token_metrics.json`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp1_rare_token_metrics.json)
- **Lost Pairs Log**: [`experiments/results/exp1_newly_lost_pairs.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp1_newly_lost_pairs.tsv)

---

## 7. Results & Metrics Table

| Configuration | Threshold | Recall % | Recalled | Missed | Newly Lost vs Base | Avg Cands / $S1$ | Median | P95 | Cand Reduction vs Base | Runtime |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **E1_A (Baseline)** | None | **99.9449%** | 34,462 | 19 | 0 | 3,294.6 | 2,621 | 9,555 | 0.00% | 19.88s |
| **E1_B (Conservative)** | **> 5%** | **99.9043%** | 34,448 | 33 | **+14** | **1,409.7** | 1,095 | 3,752 | **-57.21%** | 6.07s |
| **E1_C (Moderate)** | > 2% | 99.7738% | 34,403 | 78 | +59 | 718.5 | 618 | 1,639 | -78.19% | 4.54s |
| **E1_D (Aggressive)** | > 1% | 99.6230% | 34,351 | 130 | +111 | 445.5 | 416 | 920 | -86.48% | 7.72s |

---

## 8. Candidate Volume & Distribution Analysis
- **Conservative 5% filtering** immediately reduced average candidate count from **3,294.6 down to 1,409.7** (a massive **57.21% candidate reduction**).
- Median candidates plummeted from 2,621 to 1,095; P95 dropped from 9,555 to 3,752.
- Moderate (2%) and Aggressive (1%) cutoffs slashed candidates further (718.5 and 445.5), but breached the $\ge 99.90\%$ recall floor.

---

## 9. Recall & Recovery Analysis
- E1_B successfully retained **99.9043% recall**, holding above our safety gate of 99.90%.
- However, 14 true pairs were newly lost compared to Baseline G.
- Analysis of E1_C and E1_D demonstrated severe recall degradation: dropping to 99.77% and 99.62% respectively (+59 and +111 lost true pairs).

---

## 10. Failure / Error Analysis (The 14 Newly Lost Pairs in E1_B)
Inspection of [`exp1_newly_lost_pairs.tsv`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/results/exp1_newly_lost_pairs.tsv) showed:
- The 14 newly lost pairs relied exclusively on common geographic location tokens (e.g., large metropolitan names like "Houston", "Delhi", "Bengaluru") where the name tokens had significant spelling variation or typos that failed Channels B, C, D, and E.
- Suppressing these common tokens globally removed the only bridge connecting the query to the target.

---

## 11. Key Lessons Learned
1. **Global IDF Filtering is Highly Effective but Blunt**: A simple 5% frequency cutoff removes 57.2% of all candidate volume while maintaining 99.90% recall.
2. **Global Suppression Kills Common-City Ground Truth**: Global token blacklists permanently disconnect entities located in massive metropolitan centers when names are corrupted.
3. **Threshold Calibration**: 5% is the strict maximum threshold for safe global filtering. Cutoffs at 2% or 1% destroy recall.

---

## 12. Architectural Decision
- **Role**: **Candidate Pruning Mechanism**.
- **Decision**: Adopt the 5% frequency cutoff as a foundational filter for Channel F, but reject global suppression for core name channels. Proceed to investigate composite keys to replace coarse individual token indexes.

---

## 13. Impact on Subsequent Architecture
- Established the 5% document-frequency ceiling used in subsequent channel definitions (Experiments 05, 06, and 07).
- Led directly to **Experiment 02 (Composite Blocking Keys)** to evaluate whether multi-attribute compound keys could achieve high precision without dropping common geographic tokens.
