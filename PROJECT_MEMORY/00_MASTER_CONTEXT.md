# 00 MASTER CONTEXT: AMAZON ML CHALLENGE 2026

## 1. Challenge Objective
Solve large-scale Cross-Source Business Entity Resolution (ER):
- **Reference / Query Source (Source 1):** Clean, deduplicated anchor businesses (`S1-*`).
- **Target Sources (Source 2 & Source 3):** Noisy, administrative/web-scraped datasets (`S2-*`, `S3-*`).
- **Task:** For every Source 1 entity, identify all corresponding matching entities from Source 2 and Source 3 that refer to the same real-world business entity.
- An S1 entity may match **zero (singleton)**, **one**, or **multiple** records from S2 and S3.

## 2. Evaluation Metric & Objective Separation
- **Leaderboard Metric:** Macro-averaged **$F_{0.5}$ score** across all Source 1 entities:
  $$F_{0.5} = \frac{1.25 \times \text{Precision} \times \text{Recall}}{0.25 \times \text{Precision} + \text{Recall}}$$
  Precision is weighted **2× as heavily as recall**. Merging two distinct businesses (false positive) severely degrades the score. Correctly predicting empty for singletons earns a full 1.0.
- **Critical Phase Objective Separation:**
  - **Blocking / Candidate Generation Phase (CURRENT STAGE):** Prioritize **HIGH TRUE-PAIR RECALL** while systematically reducing candidate volume. If a true match is omitted during blocking, the downstream matching model can never recover it.
  - **Matching / Classification Phase:** Prioritize **HIGH PRECISION** by filtering out non-matches, handling singletons, and thresholding probabilities to maximize macro $F_{0.5}$.

## 3. Dataset Scale & Invariants
- **Training Set:** 2,206,821 S1 entities; 5,034,616 S2 entities; 5,285,603 S3 entities. Total true pairs: 7,638,365.
- **Test Set:** 1,732,544 S1 entities; 4,887,273 S2 entities; 5,082,316 S3 entities.
- **Invariants:**
  - True matches are **100.00% strictly intra-country** (zero cross-country matches).
  - Every S2 and S3 entity belongs to **at most one** S1 entity (1-to-many disjoint clustering).
  - Countries in Train: `US`, `India`.
  - Countries in Test: `US`, `India`, and **`France`** (zero-shot country, ~15% of test data).

## 4. Hardware Constraints
- **RAM:** Local machine has ~8 GB physical RAM.
- **Constraint:** Processing must be strictly country-partitioned, streaming, or chunked with compact inverted index structures. No massive in-memory Python object graphs or uncontrolled Cartesian joins.

## 5. Current Progress & Stage
- **Phase:** Systematic Blocking Experiments.
- **Pilot Dataset:** Stratified 10,000 S1 entities (6,000 US, 4,000 India; 34,481 true pairs; 84,481 target records).
- **Current Baseline:** Strategy G (Recall: 99.9449%, Avg Cands: 3,294.6).
- **Latest Completed Experiment:** Experiment 1 (Rare Token / IDF Filtering: E1-B achieves 57.21% candidate reduction with only 14 lost pairs).
- **Next Stage:** Experiment 2 (Combined / Composite Blocking Keys).
