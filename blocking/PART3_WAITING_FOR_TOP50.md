# Part 3 Blocking: Top-50 Status & Uncapped Fallback Safety Assessment

**Date:** September 27, 2026 — 08:10 AM  
**Investigator:** Abhijeet (evaluation-model)  
**Status:** **TOP-50 UNAVAILABLE — FALLBACK ASSESSMENT COMPLETE**  
**Full Production Job Started:** **NO** (Halted by Disk-Space Safety Gate)

---

## 1. Upstream Top-50 Dependency Status
- **Remote Inspection:** `origin/banamudra/features-matching` remains at commit `6aaf778` (base repository commit).
- **Artifacts Missing:** `query_single_topk`, `TOP50_VALIDATION_REPORT.md`, and the Top-50 pruning logic are not yet available remotely.
- **Rule Enforced:** In accordance with the **Backup Rule**, we do not invent or substitute an unverified Top-50 algorithm.

---

## 2. Country-Partitioned Champion v2 Fallback Assessment

### 2.1 Semantics & Correctness
- **Preserved Invariant:** 100.00% exact match validated against the 10,000-S1 pilot benchmark.
- **Zero Loss / Zero Addition:** Exactly 34,476 recalled true pairs (99.9855%), exactly 5 missed, 0 cross-country leakage.

### 2.2 Memory Safety
- **RAM Footprint:** Strictly bounded at **2.38 GB peak RSS** during real test evaluation.
- **Virtual Memory:** 2.32 GB (zero pagefile thrashing, zero swap pressure).
- **Index Caching:** France index pre-built and cached in [`partitions/indexes/index_France.pkl`](file:///d:/VS%20Code%20files/Amazon_ML/amazon-ml-2026-entity-resolution/partitions/indexes/index_France.pkl) (441.7 MB).

### 2.3 Benchmarks Executed (Real Test Data)
- **100 S1 Benchmark:** Completed successfully (1,023,785 candidates in 12.59 MB output).
- **1,000 S1 Benchmark:** Completed successfully in 58.68s (15,506,579 candidates in 190.62 MB output).
- **10,000 S1 Benchmark:** Completed successfully in 389.52s (194,603,706 candidates in 2.39 GB output).

---

## 3. Critical Disk-Space Safety Gate & Output Sizing

### 3.1 Measured Drive Capacity
- **Drive D:** (Project Workspace): **47.77 GB free**
- **Drive C:** (System Drive): **130.47 GB free**

### 3.2 Output Size Projection for Full Uncapped Part 3 (433,054 S1)
- **France (64,979 queries):** Yields ~128,000 candidates/query $\rightarrow$ **~104 GB uncompressed TSV**.
- **US & India (368,075 queries):** Yields ~1,150 candidates/query $\rightarrow$ **~5.3 GB uncompressed TSV**.
- **Total Projected Uncompressed File Size:** **~109 GB to 110 GB**.

### 3.3 Safety Decision
- **Available Space on Drive D: (47.77 GB) < Projected Size (~110 GB)**.
- Running the uncapped raw TSV directly on Drive D: would cause catastrophic drive exhaustion (`OSError: [Errno 28] No space left on device`).
- In strict adherence to the mandate:
  > *"Do NOT start the full Part 3 uncapped run unless the benchmark and disk-space checks demonstrate that it is safe."*
- **The full uncapped Part 3 run has NOT been started on Drive D:.**

---

## 4. Recommended Solutions to Proceed
1. **Option A (Top-50 Pruning - Optimal):** Wait for Banamudra's Top-50 pruning. Top-50 reduces candidate volume to $\le 50$ per S1, resulting in a **~260 MB total file size** (easily fitting anywhere).
2. **Option B (Drive C: Target):** Route uncapped output to Drive C: (e.g. `C:\Amazon_ML_Candidates\candidate_pairs_part3.tsv`), where 130 GB free space is available.
3. **Option C (Gzip Stream Compression):** Write output as `candidate_pairs_part3.tsv.gz`. Gzip achieves >90% compression on repetitive IDs, shrinking ~110 GB down to **~10–12 GB** (safely fitting on Drive D:).
