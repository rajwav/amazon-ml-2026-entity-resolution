# Champion Blocking Architectures Directory

This directory documents the progression, detailed technical specifications, and formal freeze record of our production candidate generation architectures.

---

## 1. Directory Structure

| File | Description |
|:---|:---|
| [`README.md`](README.md) | Navigation and overview of champion architectures. |
| [`CHAMPION_V1.md`](CHAMPION_V1.md) | Architecture, benchmark performance, and retrospective on Champion v1 (Experiment 06). |
| [`CHAMPION_V2.md`](CHAMPION_V2.md) | Architecture, scorecard, and comparative superiority of Champion v2 (Experiment 10). |
| [`CHAMPION_V2_SPEC.md`](CHAMPION_V2_SPEC.md) | Exhaustive, production-grade technical specification and implementation blueprint for Champion v2. |
| [`FREEZE_RECORD.md`](FREEZE_RECORD.md) | Formal engineering freeze declaration locking blocking code and gating transition to Phase 3. |

---

## 2. Champion Evolution Summary

| Dimension | Baseline G (Control) | Champion v1 (EXP_06) | Champion v2 Surgical (EXP_10) | Total Delta (v2 vs Base G) |
|:---|:---|:---|:---|:---|
| **True-Pair Recall** | 99.9449% | 99.9275% | **99.9855%** | **+0.0406% (+14 TP)** |
| **Missed True Pairs** | 19 | 25 | **5** | **-73.7% Miss Reduction** |
| **Average Candidates / $S1$** | 3,294.6 | 1,698.0 | **1,145.0** | **-65.25% Volume** |
| **Median Candidates / $S1$** | 2,621 | 1,135 | **609** | **-76.76% Median** |
| **P95 Candidates / $S1$** | 9,555 | 5,321 | **4,250** | **-55.52% P95** |
| **P99 Candidates / $S1$** | 12,450 | 7,386 | **6,383** | **-48.73% P99** |
| **Maximum Candidates** | 18,372 | 10,904 | **10,247** | **-44.22% Max** |
| **Zero-Candidate $S1$s** | 0 | 0 | **0** | **0.00% Zero-Cand Rate** |
| **Multi-Match Complete Recall** | 99.78% | 99.82% | **99.94%** | **Near-Perfect Completeness** |
| **Runtime (10k Batch)** | 35.57s | 8.71s | **5.34s** | **$6.7\times$ Faster** |
| **Peak RAM** | 374.5 MB | 708.6 MB | **802.5 MB** | **Bounded Memory** |
