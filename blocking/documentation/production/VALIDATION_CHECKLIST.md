# Candidate Generation Validation & Quality Checklist

This checklist enforces data integrity, recall assurance, and sanity audits across candidate generation runs.

---

## 1. Pre-Flight Checklist (Run Before Execution)

- [ ] **Environment Integrity**:
  - Python $\ge 3.10$ installed and active in `.venv`.
  - Packages installed: `indic-transliteration`, `pyarrow`, `pandas`, `polars`, `psutil`.
- [ ] **Input File Verification**:
  - Query datasets ($S1$) exist and have valid MD5/SHA256 checksums.
  - Target corpus datasets exist and have valid checksums.
  - Columns verified: `id`, `name`, `address`, `country`.
- [ ] **Country Isolation Check**:
  - Verify zero records with null or unmapped `country` values.
  - Ensure index builder only pairs `IN` with `IN` and `US` with `US`.
- [ ] **Benchmark Sanity Regression**:
  - Execute `python3 experiments/blocking/final_tail_investigation.py`.
  - Confirm benchmark outputs: Recall $= 99.9855\%$, Misses $= 5$, Avg Cands $= 1,145.0$.

---

## 2. In-Flight Telemetry Checklist

- [ ] **RAM Consumption Bounds**:
  - India partition index construction: RAM $\le 1.8\text{ GB}$.
  - US partition index construction: RAM $\le 3.2\text{ GB}$.
  - Streaming query execution: RAM remains stable (no memory leaks).
- [ ] **Throughput Rate**:
  - Processing rate $\ge 1,200\text{ queries/sec}$.
- [ ] **Zero-Candidate Monitoring**:
  - Zero-candidate query count must remain exactly **0 (0.00%)**.

---

## 3. Post-Run Verification Checklist

- [ ] **Output Artifact Integrity**:
  - All partition Parquet/TSV shards present and non-empty.
  - Row count equals total queries $\times$ candidate count.
  - No corrupted or unclosed Parquet footers.
- [ ] **Duplicate Candidate Elimination**:
  - Assert that within each query $S1$, all `target_id` entries are unique (`len(candidates) == len(set(candidates))`).
- [ ] **Ground Truth Recall Audit (on Evaluation / Benchmark Split)**:
  - Calculate true-pair recall on ground truth subset:
    $$\text{Recall} = \frac{\text{True Pairs Recalled}}{\text{Total Ground Truth Pairs}} \ge 99.95\%$$
- [ ] **Candidate Volume Distribution Audit**:
  - Average candidates per query: $1,100 \le \mu \le 1,200$.
  - Median candidates per query: $550 \le \text{Median} \le 650$.
  - P95 candidates per query: $\le 4,500$.
  - Maximum query candidates: $\le 12,000$.
- [ ] **Phase 3 Hand-off Sign-off**:
  - Candidate files registered in data registry and made accessible to Feature Engineering pipeline.
