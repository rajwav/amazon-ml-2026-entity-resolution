# Formal Candidate Generation Freeze Record

| Attribute | Specification |
|:---|:---|
| **Freeze Target** | Candidate Generation / Blocking Pipeline |
| **Approved Architecture** | **Champion v2 Surgical** |
| **Date of Freeze** | 2026-09-25 |
| **Status** | **LOCKED, SIGNED OFF & IMMUTABLE** |
| **Next Phase** | Phase 3: Feature Engineering, Fast Pre-Ranking & Classification |

---

## 1. Declaration of Architecture Freeze
Effective as of the completion and verification of Experiment 10 ([`experiments/blocking/final_tail_investigation.py`](../../../experiments/blocking/final_tail_investigation.py)), the candidate generation (blocking) architecture for the Amazon ML Challenge 2026 Business Entity Resolution project is **OFFICIALLY FROZEN**.

No further modifications, additions, deletions, or hyperparameter adjustments shall be made to the candidate generation channels, tokenizers, normalizers, or inverted indexes without an explicit, formal Architectural Change Request accompanied by statistical proof of superiority.

---

## 2. Quantitative Freeze Sign-Off Criteria

The blocking phase has satisfied every pre-established engineering criterion:

| Requirement / Gate | Target Threshold | Achieved by Champion v2 | Status |
|:---|:---|:---|:---|
| **Benchmark Recall Floor** | $\ge 99.90\%$ | **99.9855%** (34,476 / 34,481) | **PASSED (Exceeded by +0.0855%)** |
| **Missed Pair Count** | $\le 10$ pairs | **5 pairs** | **PASSED (Slashed by 73.7% vs Control)** |
| **Average Candidates / $S1$** | $< 1,500$ | **1,145.0 candidates** | **PASSED (-65.25% vs Control)** |
| **Median Candidates / $S1$** | $< 1,000$ | **609 candidates** | **PASSED (-76.76% vs Control)** |
| **Zero-Candidate $S1$ Defect Rate** | $0.00\%$ | **0 queries (0.00%)** | **PASSED (100% Query Coverage)** |
| **Multi-Match Complete Recall** | $\ge 99.5\%$ | **99.94%** | **PASSED (Multi-Match Preserved)** |
| **Memory Constraint** | $< 2.0\text{ GB}$ | **802.5 MB** | **PASSED (Sub-Gigabyte Footprint)** |
| **Execution Throughput** | $> 1,000\text{ queries/sec}$ | **1,873 queries/sec** (5.34s / 10k) | **PASSED (Production Viable)** |

---

## 3. Justification for Freezing & Halting Further Blocking Experiments
Further attempts to recover the remaining 5 missed pairs were empirically investigated in Experiment 10:
- Recovering 3 of the remaining 5 pairs required Signal S1 (Top-4 location tokens), which added **5.65 million candidate pairs** at an efficiency cost of **1,884,418 candidates per true pair recovered**.
- The remaining missed pairs represent either:
  1. Complete legal pseudonym renames (`"Straight Edge Barbershop"` $\leftrightarrow$ `"Deltazeta"`),
  2. Severe label corruption / blank target addresses (`""`), or
  3. Parent-subsidiary mappings sharing zero lexical overlap.
- Continuing to loosen candidate thresholds to chase the final 5 pairs would flood downstream classifiers with millions of false positive pairs, degrading precision, increasing false positive rates, and destroying Macro $F_{0.5}$.
- The optimal engineering decision is to freeze blocking at 99.9855% recall and direct engineering resources to downstream feature engineering and scoring.

---

## 4. Verification Checksums & Artifact Signatures

- **Source Implementation Script**: [`experiments/blocking/final_tail_investigation.py`](../../../experiments/blocking/final_tail_investigation.py)
- **Primary Metrics JSON**: [`experiments/results/exp10_final_tail_metrics.json`](../../../experiments/results/exp10_final_tail_metrics.json)
- **Detailed Evaluation TSV**: [`experiments/results/exp10_final_tail_investigation.tsv`](../../../experiments/results/exp10_final_tail_investigation.tsv)
- **Benchmark Seed**: `seed=42`
- **Benchmark Sample**: 10,000 $S1$ records, 84,481 target records, 34,481 ground truth pairs.

---

## 5. Transition to Phase 3
All subsequent development now proceeds to **Phase 3: Matching & Classification**:
1. Feature extraction across query-target pairs (string distances, token containment, digit matching, TF-IDF cosine, embedding similarity).
2. Fast pre-ranking / candidate truncation (reducing 1,145 candidates down to top-50 for heavy models).
3. Gradient Boosted Decision Tree (LightGBM/XGBoost/CatBoost) and neural cross-encoder training.
4. Threshold tuning optimized directly for Macro $F_{0.5}$.
