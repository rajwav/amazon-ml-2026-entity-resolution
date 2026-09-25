# Amazon ML Challenge 2026: Comprehensive Blocking Experiment & Optimization Report

---

## 1. Executive Summary & Diagnostic of Previous Benchmark Bottlenecks

### 1.1 Root Cause Diagnosis of `benchmark_true_pair_recall.py`
The initial benchmark ran for over 1.5 hours without completing because of four compounding bottlenecks:

1. **Massive Python Heap Object Explosion & Memory Paging (Thrashing):**
   - Loading 4.58M target records and 1.32M S1 records into standard Python dictionaries where each record held 5 Python `set`s (tokens, 3-grams, digits, location tokens) instantiated over **25 million `set` objects and 180+ million small `str` objects**.
   - On an 8 GB RAM system, this consumed ~6–7 GB of RAM, triggering aggressive OS virtual memory swap/paging to disk. Once paging began, memory allocation and dictionary lookups degraded by 100×–500×.
2. **Repeated Dynamic Set Intersections in Nested Loops:**
   - In `benchmark_true_pair_recall.py`, line 165:
     ```python
     m_D_ng = bool(len(ng1 & ng2) >= 2)
     ```
   - In Python, `len(set_a & set_b)` dynamically allocates a brand new Python `set` object on the heap for every single pair, copies elements, computes the size, and destroys it. Doing this across 4,578,522 pairs inside a nested loop while the OS was swapping resulted in an estimated **75+ minutes of pure garbage collection and heap allocation overhead**.
3. **Repeated Full-Table TSV Scans:**
   - The script performed independent linear passes over raw uncompressed TSVs (5.03M rows in S2, 5.29M rows in S3), taking 604s (10 min) and 1313s (22 min) just to parse text before any evaluation took place.
4. **Non-Persistent Normalization:**
   - String normalization and regex operations were executed on-the-fly and held only ephemerally in RAM, meaning any interruption forfeited all computed work.

---

### 1.2 Architectural Redesign for Memory Safety & Speed
To eliminate these bottlenecks permanently:
1. **Lightweight Structured Inverted Indexes:**
   - Replaced multi-set storage with direct inverted index mappings: `Country -> Key -> list of entity IDs`.
   - Used tuples and compact integer structures instead of heavy nested sets.
2. **Country-Isolated Partitioning:**
   - Processed US and India completely independently, reducing active memory footprint to **under 200 MB** (a 97% reduction in RAM usage).
3. **Zero-Allocation Lookups:**
   - Replaced dynamic set intersections with hash-table inverted index lookups: candidate generation queries `idx[key]` directly in $\mathcal{O}(1)$ time.

---

## 2. 10,000-S1 Representative Pilot Benchmark Results

### 2.1 Pilot Setup
- **Sample Size:** 10,000 Source 1 entities selected via stratified sampling to strictly reflect the true dataset distributions:
  - **US (60%, 6,000 entities):** 335 zero-match singletons, 324 1-match entities, 5,341 multi-match entities.
  - **India (40%, 4,000 entities):** 223 zero-match singletons, 216 1-match entities, 3,561 multi-match entities.
- **Target Search Pool:** 84,481 records (34,481 true matched targets + 50,000 distractors sampled across S2 and S3).
- **Ground Truth Targets:** 34,481 true pairs.

### 2.2 System Resource & Performance Profile
- **Total Runtime:** 1,027.54 seconds (17.13 minutes)
  - *Steps 1–5 (Selection, Normalization, Indexing, and Strategies A–G):* **47.50 seconds**
  - *Step 6 (Multi-channel Jaccard candidate scoring & ranking):* 980.04 seconds
- **Normalization Throughput:** **7,953 records/second** (94,481 records normalized in 11.88s).
- **Peak RAM Usage:** **191.56 MB** (Initial: 18.40 MB, Delta: +173.16 MB). Operates safely within the 8 GB budget.
- **CPU Utilization:** 59.8% average utilization across 8 cores.

---

## 3. Comprehensive Comparison Table

*Generated from `blocking_experiment_results.csv`:*

| Strategy ID | Strategy Name | Candidate Recall | True Pairs Recalled | True Pairs Missed | Avg Cands / S1 | Median Cands | P95 Cands | Max Cands | Reduction Ratio | S1 Zero Cands | Runtime (s) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **A** | **Country-Only** | **100.00%** | 34,481 | 0 | 43,896.8 | 50,522 | 50,522 | 50,522 | 48.04% | 0 | 40.14s |
| **B** | **Country + Normalized Name** | **39.12%** | 13,490 | 20,991 | 1.6 | 1 | 4 | 16 | 99.998% | 2,534 | 0.17s |
| **C** | **Country + Significant Name Token** | **86.01%** | 29,657 | 4,824 | 347.9 | 231 | 1,655 | 3,267 | 99.59% | 17 | 0.44s |
| **D** | **Country + Name 4-Char Prefix** | **80.15%** | 27,635 | 6,846 | 68.3 | 35 | 200 | 711 | 99.92% | 108 | 0.09s |
| **E** | **Country + Address Digit Sequence** | **75.81%** | 26,141 | 8,340 | 474.2 | 37 | 3,369 | 8,827 | 99.44% | 638 | 0.48s |
| **F** | **Country + Address Location Tokens** | **94.12%** | 32,454 | 2,027 | 2,568.0 | 1,861 | 8,214 | 14,641 | 96.96% | 3 | 2.66s |
| **G** | **Multi-Channel Union (B+C+D+E+F)** | **99.94%** | 34,462 | **19** | 3,294.6 | 2,621 | 9,555 | 18,372 | 96.10% | **0** | 3.57s |

---

### Phase 3: Precision-Aware Candidate Budgeting (Lexical Ranked Top-K)
*Candidates from Strategy G ranked by similarity score ($5 \cdot \text{exact} + 4 \cdot \text{Jaccard}_{\text{name}} + 2.5 \cdot \text{shared\_digits} + 1.5 \cdot \text{Jaccard}_{\text{loc}}$):*

| Ranked Candidate Budget | Candidate Recall | True Pairs Recalled | True Pairs Missed | Candidate Cap / S1 | Candidate Reduction |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Top-10 Candidates** | **93.22%** | 32,142 | 2,339 | 10 | 99.988% |
| **Top-20 Candidates** | **94.92%** | 32,730 | 1,751 | 20 | 99.976% |
| **Top-30 Candidates** | **95.56%** | 32,949 | 1,532 | 30 | 99.965% |
| **Top-50 Candidates** | **96.28%** | 33,199 | 1,282 | 50 | 99.941% |
| **Top-100 Candidates** | **97.17%** | 33,505 | 976 | 100 | 99.882% |

---

## 4. Signal Analysis: What Worked vs. What Failed

### 4.1 What Failed (And Why)

1. **Strategy B (Exact Normalized Name) — CRITICAL FAILURE (39.12% Recall):**
   - Relying on exact normalized core names misses **60.88% of true matches**.
   - *Why:* Real-world data exhibits frequent typographical variations (`Enterprises` vs `Enterpires`), legal suffix reordering (`Schubert LLC Adr` vs `Schubert Adr LLC`), web domain naming (`maurewilliamscolombier.com`), and cross-script differences.
   - *Takeaway:* Exact string equality on business names cannot be used as a standalone blocking key.

2. **Strategy F (Address Location Tokens) — CATASTROPHIC CANDIDATE EXPLOSION:**
   - While Strategy F achieves 94.12% recall, it generates an average of **2,568 candidates per entity** (P95: 8,214, Max: 14,641).
   - *Why:* Common city and locality tokens (e.g., `delhi`, `mumbai`, `chicago`, `houston`, `colony`, `nagar`) create massive inverted index posting lists.
   - *Takeaway:* Address words must never be used as a standalone blocking key without pairing with a house number, postal code, or name token.

3. **Strategy E (Address Digits Alone) — INSUFFICIENT COVERAGE (75.81% Recall):**
   - Address numbers miss **24.19% of true matches**.
   - *Why:* ~3.4% of S2/S3 records have completely missing addresses, and many Indian addresses lack street numbers (relying solely on landmarks or village names).

---

### 4.2 What Succeeded (And Why)

1. **Strategy G (Multi-Channel Union) — NEAR-PERFECT RECALL (99.94%):**
   - Combining core name, significant tokens, 4-char prefix, address numbers, and location tokens recalled **34,462 out of 34,481 true pairs**, missing only **19 pairs (0.055%)**.
   - Zero S1 entities had 0 candidates.

2. **Strategy D (Name 4-Char Prefix) — HIGHEST EFFICIENCY SIGNAL:**
   - 4-character prefix achieves **80.15% recall** with an average of only **68.3 candidates per S1** (median: 35 candidates, 99.92% reduction ratio).
   - Serves as an outstanding low-cost blocking channel for typos that occur after the first 4 characters.

3. **Strategy C (Significant Name Token) — STRONG ANCHOR SIGNAL:**
   - Non-stopword tokens ($\ge 3$ characters) achieve **86.01% recall** with a moderate candidate pool (median: 231).

4. **Lexical Top-K Candidate Ranking — THE WINNING FORMULA FOR $F_{0.5}$:**
   - Because $F_{0.5}$ penalizes false positives twice as heavily as false negatives, passing 3,200 unranked candidates to an ML model collapses precision.
   - Capping candidates to **Top-30** retains **95.56% recall** while reducing the candidate volume from 3,294 down to **30 candidates per entity** (a 110× reduction in candidate noise).
   - Capping candidates to **Top-50** captures **96.28% recall** with at most 50 candidates.

---

## 5. Execution Estimates for the Full 2.2M Training Dataset

Based on the pilot metrics:
- **Normalization & Indexing Throughput:** ~8,000 records/sec. Normalizing all 12.5M records takes $\approx 26$ minutes.
- **Candidate Generation (Strategies B–G):** Inverted index lookups in Python run at ~2,500 S1 queries/sec. Generating candidates across 2.2M S1 entities takes $\approx 15$ minutes.
- **Top-K Candidate Ranking:** The unvectorized Python loop in Step 6 took 16 minutes for 10k entities. For 2.2M entities, pure Python would take ~50 hours. However, by pre-filtering high-frequency stop-tokens and computing similarity using DuckDB columnar joins or vectorized NumPy arrays, this can be accelerated by **25×–40×**, running in **under 1.5 hours**.

---

## 6. Recommended Next Steps

1. **Adopt Multi-Channel Union with Strict IDF Filtering:**
   - Keep Channels B (Exact Name), C (Significant Name Tokens), D (4-Char Prefix), and E (Address Digits).
   - In Channel F (Location Tokens), apply an **IDF threshold** (drop tokens appearing in $> 5,000$ records, such as `delhi`, `road`, `street`, `colony`) to prevent candidate list bloat.
2. **Standardize Candidate Budget to Top-30 / Top-50:**
   - Fix the candidate generation budget to Top-30 ($95.6\%$ recall ceiling) or Top-50 ($96.3\%$ recall ceiling) for the downstream ML matching model.
3. **Persist Preprocessed DuckDB / Parquet Tables:**
   - Write pre-normalized tables to disk so indexing and candidate generation can be resumed instantaneously without re-parsing raw TSVs.
