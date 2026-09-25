# Candidate Generation Failure Analysis Directory

This directory contains the comprehensive error analysis, historical defect tracking, and failure taxonomy for the candidate generation (blocking) phase of the Amazon ML Challenge 2026 Business Entity Resolution project.

---

## 1. Directory Structure

| File | Description |
|:---|:---|
| [`README.md`](file:///Users/raj/Desktop/ml%202026%20amazon/blocking/documentation/failure_analysis/README.md) | This navigation document and overview of failure methodologies. |
| [`MISSED_PAIR_HISTORY.md`](file:///Users/raj/Desktop/ml%202026%20amazon/blocking/documentation/failure_analysis/MISSED_PAIR_HISTORY.md) | Chronological audit tracking missed true pairs across all 11 experimental milestones. |
| [`ROOT_CAUSE_ANALYSIS.md`](file:///Users/raj/Desktop/ml%202026%20amazon/blocking/documentation/failure_analysis/ROOT_CAUSE_ANALYSIS.md) | Exhaustive root-cause taxonomy covering all 8 observed failure modes, mechanisms, mitigations, and residue. |

---

## 2. Failure Analysis Methodology
Candidate generation in entity resolution operates under an asymmetric penalty structure: **a missed true pair at the blocking stage can never be recovered by downstream classifiers, permanently lowering Macro $F_{0.5}$ and recall**.

To ensure empirical rigor:
1. **Zero-Guessing Policy**: Every missed pair cited in these documents is extracted directly from verified benchmark runs on the 10,000 $S1$ query sample (`seed=42`).
2. **Deterministic Pair Attribution**: When a candidate generator fails to recall a pair, the raw text, normalized tokens, digits, and location tokens of both query ($S1$) and target records are programmatically compared across all active hash indexes.
3. **Marginal Cost Tracking**: Every potential fix for a missed pair is evaluated on its candidate efficiency ($\Delta \text{Candidates} / \Delta \text{True Pairs Recovered}$). Fixes exceeding 20,000 candidates per true pair are flagged as degenerative bloat and rejected.

---

## 3. High-Level Failure Evolution

```
Baseline G Control:  19 Misses (Ceiling established)
       │
Exp 02 Composites:   1,528 Misses (Conjunction fragility identified)
       │
Exp 03 Backbone:     660 Misses (Channel F necessity isolated)
       │
Exp 05 Adaptive:     520-660 Misses (Multi-Match Blindspot uncovered)
       │
Exp 06 Champion v1:  25 Misses (Target-side filtering validated)
       │
Exp 08 Rare Channel: 20 Misses (Top-2 location rarity adopted)
       │
Exp 09 Surgical Tail: 10 Misses (4 hard-tail channels deployed)
       │
Exp 10 Champion v2:  5 Misses (Final freeze; 73.7% reduction vs Baseline G)
```
