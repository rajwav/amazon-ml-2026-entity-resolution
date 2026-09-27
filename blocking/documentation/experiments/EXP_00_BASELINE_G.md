# Experiment 00: Baseline G (Unfiltered Control)

| Attribute | Specification |
|:---|:---|
| **Experiment ID** | `EXP_00` / `Baseline_G` |
| **Date Executed** | 2026-09-25 |
| **Author / Operator** | Entity Resolution Engineering Team |
| **Status** | **Completed & Verified (Benchmark Baseline Reference)** |
| **Source Script** | [`experiments/blocking/baseline_g.py`](../../../experiments/blocking/baseline_g.py) |
| **Metrics Artifact** | [`experiments/results/baseline_g_metrics.json`](../../../experiments/results/baseline_g_metrics.json) |
| **Missed Pairs Artifact** | [`experiments/results/baseline_g_missed_pairs.tsv`](../../../experiments/results/baseline_g_missed_pairs.tsv) |

---

## 1. Objective
Establish the gold-standard upper bound for candidate generation recall and candidate volume on a representative 10,000 $S1$ query sample by running an unfiltered union of 5 distinct blocking channels (Channels B, C, D, E, and F) partitioned strictly by country.

---

## 2. Hypothesis
By taking the multi-channel union of exact normalized names (B), token-level name matches (C), address digit co-occurrences (D), name prefix + digit composites (E), and all shared location tokens (F), we can capture virtually all true matching entity pairs ($>99.9\%$), setting a definitive ceiling against which all candidate reduction strategies must be evaluated.

---

## 3. Starting Point / Baseline Reference
- This experiment serves as the foundational **Control / Benchmark Reference**. Prior to this experiment, no systematic multi-channel baseline had been measured with microsecond timing and memory tracking on the unified benchmark.

---

## 4. Dataset & Benchmark Setup
- **$S1$ Sample Size**: 10,000 records.
  - US Queries: 6,000 records (60%).
  - India Queries: 4,000 records (40%).
  - Sampling Seed: `seed=42` (`setup_pilot_data.py`).
- **Target Record Pool**: 84,481 records.
  - 34,481 true positive targets matching the 10,000 $S1$ entities (cardinality: $1 \le k \le 17$).
  - 50,000 random distractor records sampled from the remaining corpus.
- **Ground Truth Pairs**: 34,481 true pairs.
- **Partitioning**: Strict country isolation (`country_s1 == country_target`). Cross-country blocking is strictly prohibited due to zero cross-border matches in ground truth.

---

## 5. Method & Implementation Details
Candidate generation utilizes inverted hash indexes partitioned by country code (`US`, `IN`):

1. **Channel B (Exact Name)**:
   - Index Key: `norm_name` (lowercase, punctuation stripped, normalized whitespace).
2. **Channel C (Significant Name Tokens)**:
   - Index Key: Individual alphanumeric tokens extracted from `norm_name` with stopword and common entity designation filtering (e.g., `llc`, `inc`, `pvt`, `ltd`).
3. **Channel D (Address Digits)**:
   - Index Key: Digits extracted from the address field (`re.findall(r'\d+', address)`).
4. **Channel E (Prefix-3 + Digits Composite)**:
   - Index Key: Tuple `(prefix_3, digit)` where `prefix_3` is the first 3 characters of `norm_name`.
5. **Channel F (Location Tokens - Unfiltered)**:
   - Index Key: All individual location tokens parsed from the address field (city, locality, region).

For each $S1$ record, candidate targets are gathered as:
$$\text{Candidates}(S1) = \bigcup_{k \in \{B, C, D, E, F\}} \text{Index}_k(S1)$$

---

## 6. Code & Artifact References
- **Script**: [`experiments/blocking/baseline_g.py`](../../../experiments/blocking/baseline_g.py)
- **Data Generator**: [`experiments/blocking/setup_pilot_data.py`](../../../experiments/blocking/setup_pilot_data.py)
- **Metrics JSON**: [`experiments/results/baseline_g_metrics.json`](../../../experiments/results/baseline_g_metrics.json)
- **Error Log**: [`experiments/results/baseline_g_missed_pairs.tsv`](../../../experiments/results/baseline_g_missed_pairs.tsv)

---

## 7. Results & Metrics Table

| Metric | Measured Value | Notes / Significance |
|:---|:---|:---|
| **True Pairs** | 34,481 | Benchmark constant |
| **Recalled Pairs** | 34,462 | 99.9449% Recall |
| **Missed Pairs** | **19** | Hard-tail ceiling misses |
| **Recall %** | **99.9449%** | Gold standard benchmark |
| **Total Candidates** | 32,946,375 | Cross-product union |
| **Average Candidates / $S1$** | **3,294.6** | High computational cost |
| **Median Candidates / $S1$** | **2,621** | Heavy median load |
| **P95 Candidates / $S1$** | **9,555** | Extreme tail query cost |
| **Maximum Candidates** | **18,372** | Worst-case query volume |
| **Zero-Candidate $S1$s** | **0** | Perfect query coverage (0.00%) |
| **Candidate Reduction Ratio** | 96.1001% | Relative to full cartesian product |
| **Runtime** | 35.57 s | Single-threaded in-memory execution |
| **Peak RAM** | 374.48 MB | Inverted index hash maps |

---

## 8. Candidate Volume & Distribution Analysis
- While Baseline G captures nearly all true pairs, generating **3,294.6 candidates per query** represents an intolerable bottleneck for downstream feature extraction, cross-encoders, and gradient boosting classifiers ($32.95\text{M}$ candidate comparisons per 10k batch).
- The P95 of 9,555 candidates indicates that dense metropolitan areas (e.g., "New York", "Mumbai") or common business tokens trigger catastrophic index fan-out.
- Channel F (unfiltered location) was identified as the primary source of bloat ($>85\%$ of candidate edges originate from Channel F alone).

---

## 9. Recall & Recovery Analysis
- Baseline G achieves **99.9449% recall**, capturing 34,462 out of 34,481 true pairs.
- Multi-match performance was high, but 19 true entity pairs were completely missed.
- The 19 missed pairs demonstrate that even an unfiltered 5-channel union has blind spots when both names and addresses undergo severe semantic drift, script changes, or missing data.

---

## 10. Failure / Error Analysis (The 19 Missed Pairs)
The 19 missed pairs in [`baseline_g_missed_pairs.tsv`](../../../experiments/results/baseline_g_missed_pairs.tsv) were systematically analyzed:
1. **Script Discrepancy (Devanagari vs Latin)**: Entity names written in native Hindi script vs Latin transliteration (e.g., "पतंजलि" vs "Patanjali") where neither Channel B nor Channel C could match.
2. **Extreme Short Names**: 2-character acronyms (e.g., "OM", "BK", "JB") where standard tokenization stripped the tokens or digits were absent.
3. **Severe Spelling & Phonetic Drift**: Substantial consonant substitutions (e.g., "Empire Castillo" vs `empirecastillo.com`, or `@SIBYLSBAKERY`).
4. **Completely Missing Address Data**: Records where the target record had `None` or whitespace for address, neutralizing Channels D, E, and F.

---

## 11. Key Lessons Learned
1. **Recall Ceiling Established**: 99.94% is attainable, but at the cost of 3,295 candidates per query.
2. **Channel F is an Unchecked Floodgate**: Unfiltered location tokens generate millions of non-viable candidate pairs while contributing marginal unique recall over B+C+D+E.
3. **19 Misses Are Highly Structured**: The missed pairs are not random noise; they belong to specific semantic categories (script variation, missing address, short names, web handles) that require dedicated surgical channels rather than general token loosening.

---

## 12. Architectural Decision
- **Role**: **Formal Benchmark Control**.
- **Decision**: Adopt Baseline G as the permanent ground truth reference. All candidate reduction mechanisms must measure candidate savings relative to Baseline G's 3,294.6 avg candidates while maintaining recall $\ge 99.90\%$.

---

## 13. Impact on Subsequent Architecture
- Directly motivated **Experiment 1 (Rare-Token IDF Filtering)** to test whether aggressive thresholding on Channel F and Channel C could reduce the 3,295 candidate average without dropping recall.
- Established the benchmark suite used identically across Experiments 01 through 10.
