# Matching Model & Feature Engineering Module

**Amazon ML Challenge 2026 — Business Entity Resolution**

---

## 1. Overview & Immediate Transition
With candidate generation officially frozen and producing `candidate_pairs.tsv` at **99.9855% recall**, the team transitions immediately to **Phase 3: Matching & Classification**.

This module ingests candidate pairs and trains machine learning models to predict true entity matches, evaluated strictly by the competition metric: **Macro-Averaged $F_{0.5}$**.

```text
candidate_pairs.tsv (from Champion v2)
          │
          ▼
Pairwise Feature Extraction (`matching/features.py`)
          │
          ▼
Pairwise Feature Matrix (Sparse / Dense)
          │
          ▼
Matching Classifiers (Baseline 1 -> LightGBM -> GBDT Ensemble)
          │
          ▼
Macro F_0.5 Threshold Tuning (`matching/evaluator.py`)
          │
          ▼
matching_results.tsv (Submission File)
```

---

## 2. Team Functional Roles in Phase 3

| Team Member | Branch | Primary Ownership in Phase 3 |
|:---|:---|:---|
| **Banamudra** | `banamudra/features-matching` | Lead Feature Engineering & Gradient Boosted Decision Tree (LightGBM/XGBoost) training. |
| **Shristi** | `shristi/data-error-analysis` | Exploratory data analysis, feature ablation, false positive vs false negative error analysis. |
| **Abhijeet** | `abhijeet/evaluation-model` | Ground truth validation splitting, Macro $F_{0.5}$ calibration, baseline threshold sweeps. |
| **Raj** | `raj/blocking` | Pipeline orchestration, memory profiling, and final integration. |

---

## 3. Real Dataset Feature Families

Based on actual dataset columns (`entity_id`, `business_name`, `business_address`, `country`), the following feature families are available:

1. **Name Similarity**:
   - `exact_core_match`: 1.0 if normalized core names match identically.
   - `token_jaccard`: Significant word token Jaccard overlap ($\ge 3$ characters).
   - `ngram_jaccard`: Character 3-gram overlap.
   - `levenshtein_name`: Normalized edit distance similarity.
   - `prefix4_match`: 4-character prefix match.
   - `cons_tri_match`: Consonant trigram prefix match.
   - `collapsed_match`: Double consonant collapsed match (`"wllrow"` $\leftrightarrow$ `"willow"`).
   - `domain_match`: URL/social handle stem equivalence (`"empirecastillo.com"` $\leftrightarrow$ `"Castillo Empire"`).
2. **Address Similarity**:
   - `exact_digits_match`: Street numbers match exactly.
   - `has_shared_digit`: At least one common street number.
   - `digit_jaccard`: Jaccard similarity of extracted street numbers.
   - `has_shared_loc`: Shared location token.
   - `loc_jaccard`: Jaccard similarity of location tokens.
   - `unit_match`: Suite/Unit number equivalence (`"4b"`, `"104a"`).
   - `state_match`: US state code agreement.
3. **Data Quality & Structural Signals**:
   - `s1_has_address` / `t_has_address`: Missingness indicators.
   - `len_diff_core`: Name length difference.

---

## 4. Modeling Roadmap

1. **Baseline 1 (Heuristic Composite)**:
   - Rule-based weighted scoring implemented in `matching/baseline_matcher.py`.
   - Grid search threshold on validation set maximizing Macro $F_{0.5}$.
2. **Baseline 2 (Tabular Classifier - LightGBM)**:
   - Fast, memory-efficient pair classification using binary logloss.
   - Extract top feature importances and error profiles.
3. **Threshold Calibration Strategy**:
   - Because $F_{0.5}$ weights precision $4\times$ more heavily than recall ($\beta^{-2} = 4$), optimal thresholds are typically shifted higher ($\approx 0.65 - 0.75$) to suppress false merges.
