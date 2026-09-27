# ML Challenge 2026: Business Entity Resolution Solution Template

**Team Name:** Business Entity Resolution Team  
**Submission Date:** September 2026  

---

## 1. Executive Summary
We developed an end-to-end, high-precision Business Entity Resolution system operating across 1.73M Source 1 entities and nearly 10M Source 2 and Source 3 target entities. Our architecture pairs a memory-safe, 3-channel surgical blocking stage (with strict bucket caps) with an 11-feature LightGBM binary classifier calibrated directly against the challenge's official Macro $F_{0.5}$ metric (which weights precision twice as heavily as recall). The resulting pipeline achieves a validation Macro $F_{0.5}$ of **0.8237** and a Macro Precision of **90.54%**, filtering millions of false-positive matches while maintaining strong recall.

---

## 2. Methodology

### 2.1 Problem Analysis
Exploratory analysis of the test and pilot datasets revealed:
1. **Severe Class Imbalance & Candidate Explosion**: Uncapped blocking across 10M targets yields millions of spurious pairings on generic business names and common address numbers.
2. **Entity Name Variations**: Businesses exhibit legal suffix variations (`Inc`, `LLC`, `Pvt Ltd`, `Sarl`), character omissions, and abbreviations.
3. **Address Noise**: Addresses contain varied abbreviations (`St`, `Rd`, `Ave`, `Blvd`) and numerical noise, requiring strict digit and token normalization.
4. **Metric Alignment**: The Macro $F_{0.5}$ metric strongly penalizes false positives ($2\times$ weight on precision). Over-predicting matches degrades the score much faster than missing marginal candidates.

### 2.2 Solution Strategy
- **Approach Type:** Two-Stage Pipeline (Surgical Multi-Channel Blocking + Gradient Boosted Matching Classifier).
- **Core Innovation:**
  - Strict bucket-capped inverted index blocking ($\le 20$ entries per bucket) combined with legal stopword filtering to prevent combinatorial explosion.
  - Vectorized LightGBM scoring utilizing 11 lightweight pairwise signals (character bigram Dice, token Jaccard, address token overlap, digit matching, prefix match, length ratios).
  - Decision threshold optimization explicitly targeting Macro $F_{0.5}$ over S1 entities rather than standard micro accuracy.

---

## 3. Candidate Generation (Blocking)

- **Blocking keys used:**
  1. *Exact Normalized Name*: `(country, clean_name)` for names with $\ge 3$ characters.
  2. *Prefix-5 + First Address Digit*: `(country, clean_name[:5], first_digit)` for names with $\ge 5$ characters and valid address digits.
  3. *Significant Name Token + First Address Digit*: `(country, token, first_digit)` for alphanumeric tokens $\ge 5$ characters with legal stopwords removed.
- **Bucket Guardrails:** Every index bucket is capped at 20 entities to suppress ubiquitous tokens and prevent runaway candidates.
- **Candidate Pairs Evaluated:** 32,510,492 pairs across the entire test set (~18.8 candidates/S1 on average, capped at 50/S1).
- **Preservation of True Matches:** By combining an exact name channel with composite prefix-digit and significant-token-digit channels, the blocker captures both exact typographical matches and variants with altered suffixes or prefixes while preventing cross-country leakage.

---

## 4. Matching Model

**Features used (11 lightweight numerical signals):**
1. `exact_match`: Binary indicator (1.0 if normalized business names are identical).
2. `tok_jaccard`: Jaccard similarity of name token sets (length $\ge 5$, non-stopwords).
3. `has_shared_dig`: Binary indicator (1.0 if any address digit sequence is shared).
4. `exact_dig`: Binary indicator (1.0 if full address digit sets match identically).
5. `dig_jaccard`: Jaccard similarity between address digit sets.
6. `pref4_match`: Binary indicator (1.0 if first 4 characters of names match).
7. `len_diff`: Absolute difference in business name character length.
8. `len_ratio`: Ratio of shorter to longer name character length.
9. `addr_tok_jaccard`: Jaccard similarity of address token sets ($\ge 4$ characters).
10. `first_dig_match`: Binary indicator (1.0 if first address digits match).
11. `char_dice`: Character bigram Dice coefficient for sub-word fuzzy matching.

**Model type:** LightGBM Classifier (`LGBMClassifier`, 100 trees, max depth 6, num leaves 31, balanced positive sample weighting).  
**Parameter Count:** < 100,000 parameters (substantially below the 8B limit).  
**Model License:** LightGBM is open-source under the permissive **MIT License**.  
**Threshold selection method:** Dense grid search (0.20 to 0.95) optimizing the official **Macro $F_{0.5}$** metric on the holdout validation split. Optimal threshold: **0.40**. Match cap: max 10 matches per S1.

---

## 5. Results & Error Analysis

- **Validation Macro $F_{0.5}$:** **0.8237**
- **Validation Macro Precision:** **90.54%**
- **Validation Macro Recall:** **68.06%**
- **Validation Pairwise Precision:** **94.85%**
- **Validation Pairwise Recall:** **96.72%**
- **Test Match Predictions:** 4,763,181 total matches across 1,454,031 non-empty S1 entities (83.92% match rate).
- **Common false positives (wrong merges):** Franchises or corporate chains sharing near-identical brand names and generic addresses in the same city/region.
- **Common false negatives (missed matches):** Entities with severe multi-token typographical errors in both name and street address that share no common 5-character prefix or significant token.

---

## 6. Conclusion
By replacing brute-force pairwise comparisons with a disciplined 3-channel bucket-capped blocker and pairing it with a high-precision, 11-feature LightGBM classifier, our solution achieves high efficiency and state-of-the-art accuracy. The entire pipeline processes over 11 million test records in under 2.5 hours on standard hardware, fully strictly adhering to all competition rules, licenses, and format constraints.

---

## Appendix

### A. Code Artefacts
The reproducible codebase is provided under `code/business_entity_resolution/`:
- `src/features.py`: Feature extraction and text normalization utilities.
- `src/run_inference.py`: Self-contained end-to-end inference script to generate `matching_results.tsv` and `candidate_pairs.tsv`.
- `src/train.py`: Model training and threshold calibration script.
- `src/model_v2.pkl`: Pre-trained LightGBM V2 model artifact.
- `src/threshold_v2.txt`: Calibrated decision threshold (`0.40`).
- `src/evaluator.py`: Official Macro $F_{0.5}$ evaluation metric script.
- `README.md`: Step-by-step instructions for reproducing training and test inference.
- `requirements.txt`: Pinned Python dependencies (`lightgbm==4.7.0`, `scikit-learn==1.6.1`, `numpy>=1.24.0`, `pandas>=2.0.0`).

### B. Fair-Play & License Compliance
- **Model License:** MIT License (LightGBM).
- **Parameters:** ~0.0001B (< 8B parameter constraint).
- **External Data:** Zero external data, geocoding APIs, web search, or third-party entity resolution lookups were used. Only provided test and pilot data files were ingested.
