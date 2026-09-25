# 03 SYSTEM ARCHITECTURE: END-TO-END PIPELINE

## 1. High-Level Pipeline Flow

```
                      RAW TSV RECORDS (S1, S2, S3)
                                   │
                                   ▼
             ┌───────────────────────────────────────────┐
             │  PHASE 1: PREPROCESSING & NORMALIZATION   │
             │  - Unicode NFKD & ASCII accent stripping   │
             │  - Lowercase, punctuation & noise removal │
             │  - Legal suffix extraction & core naming  │
             │  - Street abbreviation standardization    │
             │  - Offline Indic transliteration (Indic2Lat)│
             └─────────────────────┬─────────────────────┘
                                   │
                                   ▼
             ┌───────────────────────────────────────────┐
             │     PHASE 2: BLOCKING / CANDIDATE GEN     │
             │  - Strict Country Partitioning            │
             │  - Compact Inverted Indexes               │
             │  - Multi-Channel Blocking (B, C, D, E, F) │
             │  - Token / IDF Frequency Pruning          │
             └─────────────────────┬─────────────────────┘
                                   │
                                   ▼
             ┌───────────────────────────────────────────┐
             │       PHASE 3: CANDIDATE BUDGETING        │
             │  - Lightweight Lexical / Jaccard Ranking  │
             │  - Top-K Candidate Cap (Top 30 / Top 50)  │
             │  - Output: candidate_pairs.tsv            │
             └─────────────────────┬─────────────────────┘
                                   │
                                   ▼
             ┌───────────────────────────────────────────┐
             │     PHASE 4: ML MATCHING / CLASSIFIER     │
             │  - Feature Engineering (Fuzzy, Phonetic)  │
             │  - GBDT / LightGBM / XGBoost Model        │
             │  - Probability Calibration                │
             └─────────────────────┬─────────────────────┘
                                   │
                                   ▼
             ┌───────────────────────────────────────────┐
             │     PHASE 5: POST-PROCESSING & SUBMIT     │
             │  - Global Disjoint 1-to-Many Assignment   │
             │  - Precision-Tuned F_0.5 Thresholding     │
             │  - Output: matching_results.tsv           │
             └───────────────────────────────────────────┘
```

## 2. Stage Boundaries & Rules

| Pipeline Stage | Allowed Operations | Forbidden Operations |
| :--- | :--- | :--- |
| **1. Preprocessing** | Unicode normalization, string regex, legal suffix parsing, address normalization, phonetic transliteration. | Dropping entire records, external geocoding, API calls. |
| **2. Blocking** | Inverted indexes by country, token filtering, composite keys, unioning channels. Target: **Recall $\ge 99.5\%$**. | Dropping candidates based on unverified heuristics, cross-country pairs. |
| **3. Candidate Budgeting** | Lightweight ranking, top-K truncation to bound downstream inference. | Random candidate dropping. |
| **4. Matching Model** | Pairwise feature engineering, tree-based classification, ensemble scoring. | Models $>8\text{B}$ params, non-permissive licensed models. |
| **5. Post-Processing** | Enforcing disjoint 1-to-many clustering, threshold tuning on validation set. | Modifying candidate generation rules retroactively. |
