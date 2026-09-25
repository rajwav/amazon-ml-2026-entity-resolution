# 01 Dataset & Ground Truth: Statistical Architecture & Structural Invariants

> **Amazon ML Challenge 2026 — Business Entity Resolution**  

---

## 1. Complete File Inventory

The dataset comprises 7 primary TSV files totaling **26.4 million rows** and **2.43 GB** on disk:

| Split | File Name | Size (MB) | Exact Rows | Primary Key | Missing Values | Country Breakdown |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **Train** | `train_source1.tsv` | 200.34 MB | 2,206,821 | `entity_id` | `business_address`: 0 (0.0%) | US: 1,323,633 (60.0%)<br>India: 883,188 (40.0%) |
| **Train** | `train_source2.tsv` | 466.63 MB | 5,034,616 | `entity_id` | `business_address`: 168,967 (3.36%) | US: 3,016,817 (59.9%)<br>India: 2,017,799 (40.1%) |
| **Train** | `train_source3.tsv` | 480.37 MB | 5,285,603 | `entity_id` | `business_address`: 175,916 (3.33%) | US: 3,170,056 (60.0%)<br>India: 2,115,547 (40.0%) |
| **Train** | `train_ground_truth.tsv`| 121.13 MB | 2,206,821 | `entity_id` | `matched_entity_ids`: 123,247 (5.58%) | N/A |
| **Test** | `test_source1.tsv` | 166.91 MB | 1,732,544 | `entity_id` | `business_address`: 0 (0.0%) | India: 809,986 (46.8%)<br>US: 663,106 (38.3%)<br>France: 259,452 (15.0%) |
| **Test** | `test_source2.tsv` | 485.86 MB | 4,887,273 | `entity_id` | `business_address`: 129,408 (2.65%) | India: 2,312,565 (47.3%)<br>US: 1,871,330 (38.3%)<br>France: 703,378 (14.4%) |
| **Test** | `test_source3.tsv` | 482.56 MB | 5,082,316 | `entity_id` | `business_address`: 136,098 (2.68%) | India: 2,405,000 (47.3%)<br>US: 1,945,701 (38.3%)<br>France: 731,615 (14.4%) |

---

## 2. Schema and Entity ID Taxonomy

Each record possesses 4 core tab-separated fields:
1. `entity_id` (string): Unique identifier prefixed by source.
   - `S1-XXXXXXXXX` (e.g. `S1-326626722`)
   - `S2-XXXXXXXXX` (e.g. `S2-927342266`)
   - `S3-XXXXXXXXX` (e.g. `S3-630258153`)
2. `business_name` (string): Raw corporate or commercial trade name.
3. `business_address` (string): Raw address string (may be empty or formatted as string `"null"`).
4. `country` (string): Country name (`United States`, `US`, `India`, or `France`).

In `train_ground_truth.tsv`:
- Column 1: `entity_id` (Source 1 anchor ID).
- Column 2: `matched_entity_ids` (comma-separated list of matching Source 2 and Source 3 IDs, or empty for singletons).

---

## 3. Structural Invariants & Statistical Facts

### 3.1 Total Ground-Truth True Pairs
The training ground truth contains exactly **7,638,365 true pairs**:
- $S1 \leftrightarrow S2$ matches: **3,693,619 pairs** (48.36%).
- $S1 \leftrightarrow S3$ matches: **3,944,746 pairs** (51.64%).

### 3.2 Match Cardinality Distribution (1-to-Many Architecture)
Unlike standard 1-to-1 bipartite record linkage problems, this challenge represents a **1-to-Many mapping**:

| Match Count ($k$) | Number of S1 Entities | Percentage of S1 | Total True Pairs Involved |
| :---: | :---: | :---: | :---: |
| **0 matches (Singletons)** | 123,247 | 5.58% | 0 |
| **1 match** | 119,157 | 5.40% | 119,157 |
| **2 matches** | 375,212 | 17.00% | 750,424 |
| **3 matches** | 530,841 | 24.05% | 1,592,523 |
| **4 matches** | 484,115 | 21.94% | 1,936,460 |
| **5 matches** | 321,957 | 14.59% | 1,609,785 |
| **6 matches** | 164,868 | 7.47% | 989,208 |
| **7 matches** | 63,968 | 2.90% | 447,776 |
| **$\ge 8$ matches** | 23,456 | 1.06% | 193,032 |
| **Total** | **2,206,821** | **100.00%** | **7,638,365** |

> [!IMPORTANT]
> **Why Multi-Match Cardinality Dictates Blocking Architecture:**
> Exactly **89.02% of all $S1$ entities match multiple external records** across $S2$ and $S3$.
> In Experiment 5, we discovered the **Multi-Match Gating Blindspot**: If an $S1$ query matches one easy target via exact name ($BCDE$), an adaptive policy that suppresses broad channels (like Channel $F$) based on "query already has candidates" prematurely drops remaining true matches, capping recall at ~98.4%. Therefore, blocking channels must be throttled via **Target-Side Token Filtering**, never query-level suppression.

### 3.3 Target Record Exclusivity Invariant
- Every $S2$ record maps to **at most one** $S1$ anchor business.
- Every $S3$ record maps to **at most one** $S1$ anchor business.
- **Distractor Records (Unmatched Targets):**
  - $S2$: 1,340,997 records (26.64% of $S2$) are unmatchable distractors.
  - $S3$: 1,340,857 records (25.37% of $S3$) are unmatchable distractors.

### 3.4 100% Intra-Country Invariant
Across all 7,638,365 training ground-truth pairs:
- **Cross-country true matches: EXACTLY ZERO (0).**
- True matches are 100.0% intra-country.
- **Architectural Consequence:** Every inverted index and candidate channel is partitioned strictly by country:
  $$\text{Candidates}(S1) \subseteq \text{Targets}_{\text{Country}(S1)}$$
  This cuts the active Cartesian search space immediately by ~40%–60% without any recall loss.

---

## 4. The Persistent 10,000-S1 Pilot Benchmark

To enable fast, reproducible iteration without training-set leakage or memory crashes, we generated a fixed, persistent pilot dataset (`experiments/blocking/setup_pilot_data.py`, seed=42):
- **Source 1 Pilot:** Exactly **10,000** records (`experiments/data/pilot_s1.tsv`):
  - 6,000 US entities: 335 singletons (0-match), 324 1-match, 5,341 multi-match.
  - 4,000 India entities: 223 singletons (0-match), 216 1-match, 3,561 multi-match.
- **Ground-Truth True Pairs:** Exactly **34,481 true pairs** (`pilot_ground_truth.tsv`).
- **Target Search Pool:** Exactly **84,481 records** (`pilot_targets.tsv`):
  - 34,481 true matched targets (100% recall reference).
  - 50,000 hard distractors: 25,000 unmatched records from $S2$, 25,000 unmatched records from $S3$.
- **Target Pool by Country:** US = 50,522; India = 33,959.
- **Cartesian Candidate Space:** $10,000 \times 84,481 = \mathbf{844,810,000\text{ possible pairs}}$.

All 11 experiments in this project were evaluated strictly against this exact pilot benchmark.
