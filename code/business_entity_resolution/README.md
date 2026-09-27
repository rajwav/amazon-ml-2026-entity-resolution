# Business Entity Resolution — Solution Pipeline
Amazon ML Challenge 2026

## 1. Overview
This pipeline implements an end-to-end, high-precision Business Entity Resolution system designed to match Source 1 entities against Source 2 and Source 3 target entities across 11+ million records.

### Architecture
1. **Surgical Multi-Channel Blocking**:
   - Channel 1: Exact normalized name `(country, clean_name)`
   - Channel 2: Prefix-5 + first digit `(country, clean_name[:5], first_digit)`
   - Channel 3: Significant token + first digit `(country, token, first_digit)`
   - Strict bucket capping $\le 20$ to eliminate combinatorial explosions.
2. **LightGBM Classifier**:
   - 11 lightweight pairwise signals capturing exact name identity, token Jaccard, address token overlap, digit matching, prefix identity, length difference/ratio, and character bigram Dice similarity.
   - Decision threshold calibrated directly on the official competition metric (**Macro $F_{0.5}$** with $2\times$ weight on precision).

---

## 2. Requirements & Installation
Install the required dependencies:
```bash
pip install -r requirements.txt
```

---

## 3. End-to-End Reproduction

### Run Inference on Test Data:
To reproduce `matching_results.tsv` and `candidate_pairs.tsv`:
```bash
python3 src/run_inference.py \
  --test-dir student_resource/dataset/test \
  --output-dir output
```
This produces:
- `output/matching_results.tsv`: Final predicted matches for each test S1 entity.
- `output/candidate_pairs.tsv`: Final candidate set evaluated immediately prior to ML scoring.

### (Optional) Retrain Model:
```bash
python3 src/train.py
```
This fits LightGBM on the labeled dataset and calibrates the threshold for optimal Macro $F_{0.5}$.

---

## 4. Verification
Run the official competition validator:
```bash
python3 student_resource/utils/validate_submission.py \
  --matching output/matching_results.tsv \
  --candidate output/candidate_pairs.tsv \
  --test-dir student_resource/dataset/test \
  --check-ids
```
Output:
`PASS — no blocking issues found. Safe to submit.`
