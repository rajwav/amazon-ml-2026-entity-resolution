# BLOCKING PHASE MASTER: COMPREHENSIVE HISTORICAL & TECHNICAL RECORD

```text
========================================================================================
BLOCKING STATUS: FROZEN
CHAMPION: Champion v2 (Surgical Pipeline)
BENCHMARK: 10,000 S1 Stratified Pilot (seed=42), 84,481 Targets, 34,481 True Pairs
TRUE-PAIR RECALL: 99.9855% (34,476 / 34,481)
MISSED TRUE PAIRS: 5 (out of 34,481 ground truth matches)
AVERAGE CANDIDATES / S1: 1,145.0 (slashed by -65.25% vs Baseline G's 3,294.6)
MEDIAN CANDIDATES / S1: 609 (slashed by -76.76% vs Baseline G's 2,621)
P95 CANDIDATES / S1: 4,250 (slashed by -55.52% vs Baseline G's 9,555)
MAX CANDIDATES / S1: 10,247 (slashed by -44.22% vs Baseline G's 18,372)
ZERO-CANDIDATE S1s: 0 (100% query coverage preserved)
MULTI-MATCH COMPLETE RECALL: 99.90% (8,893 / 8,902 entities with all targets found)
TOTAL RUNTIME: 3.73 seconds (10k S1)
PEAK RAM: 802.46 MB (<1 GB physical RAM ceiling strictly honored)
NEXT PHASE: Phase 3 — Pairwise Feature Engineering & Classification (LightGBM)
========================================================================================
```

---

## 1. Executive Summary

This document presents the definitive technical and experimental history of the **Candidate Generation (Blocking)** phase for the Amazon ML Challenge 2026 Business Entity Resolution project.

In Business Entity Resolution, an anchor catalog of clean businesses (Source 1) must be matched against two highly corrupted external data sources (Source 2 and Source 3). The ultimate competition metric is **Macro $F_{0.5}$**, which places double the weight on precision over recall:
$$F_{0.5} = (1 + 0.5^2) \frac{\text{Precision} \times \text{Recall}}{0.5^2 \times \text{Precision} + \text{Recall}} = \frac{1.25 \times P \times R}{0.25 \times P + R}$$

However, in the candidate generation stage, **Recall is the hard, non-negotiable prerequisite**:
$$\text{Recall}_{\text{End-to-End}} = \text{Recall}_{\text{Blocking}} \times \text{Recall}_{\text{Classification}}$$
If a true matching business record is excluded during blocking, no downstream ranking model or neural classifier can ever recover it, imposing a hard mathematical ceiling on precision, recall, and Macro $F_{0.5}$.

Our objective was to construct a blocker that achieves **$\ge 99.9\%$ true-pair recall** while slashing candidate volume by over 50% compared to our initial Baseline G, keeping candidate generation memory-safe (<1 GB RAM) and computationally scalable across millions of entities.

Through an evidence-driven sequence of 11 benchmark experiments, we achieved:
- Recall elevated from **99.9449%** (Baseline G) to an all-time record **99.9855%** (Champion v2).
- Missed true pairs reduced by **-73.68%** (from 19 down to **ONLY 5 misses**).
- Average candidates per query slashed by **-65.25%** (from 3,294.6 to **1,145.0**).
- Median candidate count dropped by **-76.76%** (from 2,621 to **609**).
- Absolute immunity against zero-candidate queries (**0 zero-candidate S1s**).
- Perfect memory safety (**<805 MB RAM** across all runs).

With all 10 remaining tail misses analyzed and 5 recovered at an ultra-low marginal cost of **8,605 candidates per recovered true pair**, the blocking problem has reached empirical saturation. The architecture is officially **FROZEN**.

---

## 2. Challenge Context & Rules

### 2.1 The Entity Resolution Challenge
We are tasked with entity resolution across three corporate datasets:
- **Source 1 ($S1$):** Anchor reference catalog containing standardized business records (`entity_id`, `business_name`, `business_address`, `country`).
- **Source 2 ($S2$):** Highly noisy external business directory with typographical errors, abbreviations, missing addresses, legal entity re-orderings, and web domains.
- **Source 3 ($S3$):** Second noisy directory featuring heavy native Indic scripts (Devanagari, Tamil, Telugu, Kannada, Bengali) in India records, missing fields, and formatting noise.

### 2.2 Strict Constraints & Operating Envelope
1. **Zero External Lookups:** The competition strictly prohibits external network access, web scraping, geocoding APIs (e.g. Google Maps), corporate registries, or external LLM APIs. All feature extraction, transliteration, and matching must be 100% self-contained and offline.
2. **Physical Hardware Bounds:** The production evaluation environment is constrained to standard compute with strict memory limits (8 GB physical RAM). Memory leaks or monolithic in-memory matrix materialization result in fatal process crashes.
3. **Multilingual and Multi-Country Scope:** Training data covers the United States and India. The unseen test set introduces **France** (`FR`), requiring the blocker to be language-agnostic and country-independent without hardcoded geographical assumptions.
4. **Disjoint Target Assignment Invariant:** In the ground truth, every noisy target record ($S2$ or $S3$) belongs to **at most one** $S1$ anchor business. True matches never cross country boundaries (**100.0% intra-country**).

---

## 3. Dataset Architecture & Ground Truth Facts

### 3.1 Dataset Sizes and Field Properties

| Dataset Split | File | Size | Exact Rows | Missing Addresses | Country Distribution |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Train** | `train_source1.tsv` | 200.3 MB | 2,206,821 | 0 (0.00%) | US: 60.0% (1,323,633) \| India: 40.0% (883,188) |
| **Train** | `train_source2.tsv` | 466.6 MB | 5,034,616 | 168,967 (3.36%) | US: 59.9% (3,016,817) \| India: 40.1% (2,017,799) |
| **Train** | `train_source3.tsv` | 480.4 MB | 5,285,603 | 175,916 (3.33%) | US: 60.0% (3,170,056) \| India: 40.0% (2,115,547) |
| **Train** | `train_ground_truth.tsv` | 121.1 MB | 2,206,821 | 123,247 (5.58% unmatched) | Exactly 7,638,365 true pairs (S2: 3.69M, S3: 3.94M) |
| **Test** | `test_source1.tsv` | 166.9 MB | 1,732,544 | 0 (0.00%) | India: 46.8% \| US: 38.3% \| France: 15.0% (259,452) |
| **Test** | `test_source2.tsv` | 485.9 MB | 4,887,273 | 129,408 (2.65%) | India: 47.3% \| US: 38.3% \| France: 14.4% (703,378) |
| **Test** | `test_source3.tsv` | 482.6 MB | 5,082,316 | 136,098 (2.68%) | India: 47.3% \| US: 38.3% \| France: 14.4% (731,615) |

### 3.2 Match Cardinality Distribution
In the training ground truth:
- **Zero-match queries (Singletons):** 123,247 $S1$ entities (5.58%) have 0 matching targets in $S2/S3$.
- **1-match queries:** 119,157 $S1$ entities (5.40%).
- **Multi-match queries ($\ge 2$ matches):** **89.02% of all $S1$ entities** have between 2 and 11 true targets across $S2$ and $S3$.
- **Target Invariant:** Exactly **0** targets in $S2$ or $S3$ match more than one $S1$ anchor business.

### 3.3 The Controlled 10,000-S1 Pilot Benchmark
To ensure reproducible, mathematically rigorous experimentation without data leakage, we created a fixed pilot benchmark (`experiments/blocking/setup_pilot_data.py`, seed=42):
- **$S1$ Queries:** Exactly **10,000** records (`pilot_s1.tsv`): 6,000 US, 4,000 India.
- **Target Pool:** Exactly **84,481** records (`pilot_targets.tsv`):
  - 34,481 true matched targets (100% of ground-truth matches for the 10k $S1$).
  - 50,000 hard distractor records (25,000 randomly selected unmatched records from $S2$, 25,000 from $S3$).
- **Ground Truth Matches:** Exactly **34,481 true pairs** (`pilot_ground_truth.tsv`).
- **Cartesian Search Space:** $10,000 \times 84,481 = \mathbf{844,810,000\text{ potential pairs}}$.

All experimental results are evaluated strictly against this identical 10k pilot benchmark.

---

## 4. The Blocking Problem & Baseline G

### 4.1 Why Blocking is Mandatory
Evaluating all pairs using pairwise machine learning models requires computing complex string distance and semantic features across $N \times M$ pairs.
- At full scale: $2,206,821 \times 10,320,219 = \mathbf{22,774,874,271,899\text{ pairs}}$ (22.7 trillion pairs).
- Computing pairwise features at 10 microseconds per pair would require **7.2 years** of continuous CPU execution and petabytes of memory.
- An effective blocker acts as an ultra-fast, high-recall sieve that reduces candidate pairs from billions down to thousands per query while retaining $\ge 99.9\%$ of all true matches.

### 4.2 Initial Starting Baseline: Strategy G
Baseline G was defined as the multi-channel union of 5 distinct inverted index channels partitioned strictly by country:
- **Channel B (Exact Core Name):** Strips legal suffixes (`LLC`, `Inc`, `Pvt Ltd`), punctuation, and lowercase whitespace. Matches exact core name string.
- **Channel C (Significant Name Tokens):** Inverted index of significant words in core name (length $\ge 3$, excluding standard stop-words).
- **Channel D (4-Character Name Prefix):** First 4 characters of core name string.
- **Channel E (Address Digits):** Exact integer digit sequences extracted from address (house numbers, ward numbers, postal codes).
- **Channel F (Address Location Tokens):** Words in address (length $\ge 3$) excluding generic road words (`street`, `road`, `avenue`).

### 4.3 Baseline G Reproduction Verification
Running `experiments/blocking/baseline_g.py` verified Strategy G with zero discrepancy:
- **True-Pair Recall:** **99.9449%** (34,462 / 34,481 true pairs recalled).
- **Missed True Pairs:** **19 pairs** (logged in `baseline_g_missed_pairs.tsv`).
- **Average Candidates / $S1$:** **3,294.6** (Total generated: 32,946,375 candidate pairs).
- **Median Candidates / $S1$:** **2,621** | **P95:** **9,555** | **Max:** **18,372**.
- **Zero-Candidate $S1$s:** **0**.
- **Candidate Reduction vs Cartesian:** **96.10%**.
- **Runtime / RAM:** 35.57s / 374.48 MB.

**Baseline Diagnostic:** While Baseline G achieved excellent recall (99.94%), candidate volume was bloated (3,295 candidates per query). Channel F alone contributed over 74% of all candidates due to high-frequency geographical tokens.

---

## 5. Complete Chronological Evolution of Blocking

```
[Phase 1: Baseline Establishment]
   └── Baseline G Reproduction (99.94% recall | 3,294.6 cands/S1 | 19 misses)
              │
[Phase 2: Candidate Volume Optimization]
   ├── Exp 1: Target-Side IDF Filtering (E1-B 5% cutoff -> -57.2% candidates | 99.90% recall)
   ├── Exp 2: Composite Blocking Keys (C2_Union_All -> 113.8 cands/S1 | 95.57% recall)
   └── Exp 3: Multi-Channel Incremental Union (Established BCDE Backbone: 836.1 cands | 98.09% recall)
              │
[Phase 3: Domain Specialization & Gating]
   ├── Exp 4: Indic Script Transliteration (Transliteration Asymmetry -> Names ON, Loc OFF)
   ├── Exp 5: Quality-Aware Gating (Discovered Multi-Match Gating Blindspot -> S1 gating rejected)
   └── Exp 6: 3-Tier Cumulative Fallback Pipeline (L1 U L2 U L3 -> 1,698 cands/S1 | 99.93% recall)
              │
[Phase 4: Scalability & Dynamic Frequency Control]
   ├── Exp 7: Scalability Benchmark (10k -> 25k -> 50k linear scaling & France test validation)
   └── Exp 8: Dynamic Frequency-Aware Channel F (Top-2 Rarest Tokens -> 1,064 cands/S1 | 99.94% recall)
              │
[Phase 5: Hard-Tail Recovery & Saturation]
   ├── Exp 9: Surgical Tail Recovery Pipeline (2-letter tokens, domain stems -> 1,140 cands/S1 | 99.97% recall)
   └── Exp 10: Final 10-Miss Autopsy & Micro-Signals (Consonant Tri + State Digits + Units)
              │
              ▼
   [CHAMPION V2 SURGICAL FROZEN]
   Recall: 99.9855% | 1,145.0 cands/S1 | Median: 609 | Misses: 5 | RAM: 802 MB
```

---

## 6. Experiment-by-Experiment Analysis

### Experiment 1: Rare Token & Target IDF Filtering
- **Script:** [`experiments/blocking/rare_token.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/rare_token.py)
- **Objective:** Measure whether dropping high-frequency address tokens from Channel F could curb candidate explosion without sacrificing true matches.
- **Configurations:**
  - `E1_A` (No filtering / Baseline G): 99.9449% recall, 3,294.6 cands/S1.
  - `E1_B` (Conservative >5% Target Pool Cutoff): **99.9043% recall**, **1,409.7 cands/S1** (-57.21% candidate reduction, only 14 pairs lost).
  - `E1_C` (Moderate >2% Cutoff): 99.7825% recall, 988.4 cands/S1 (56 pairs lost).
  - `E1_D` (Aggressive >1% Cutoff): 99.5302% recall, 770.8 cands/S1 (143 pairs lost).
- **Decision:** **ACCEPTED** `E1_B` threshold (>5% country pool) as our primary candidate-pruning mechanism.

### Experiment 2: Composite Blocking Keys
- **Script:** [`experiments/blocking/composite_keys.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/composite_keys.py)
- **Objective:** Test whether multi-attribute composite keys (e.g. `(token, location)`, `(digit, location)`) could replace broad single-attribute channels.
- **Findings:** Standalone composite keys suffered severe recall drops (59.97%–80.37%) and created up to 1,689 zero-candidate queries because noisy records frequently have one corrupted field.
- **Breakthrough:** Combining all 5 composite keys plus exact core name into `C2_Union_All` achieved **95.57% recall** with only **113.8 candidates/S1 (median: 15)**.
- **Decision:** `C2_Union_All` was **ACCEPTED** as our ultra-compact **Level 1 Sieve** for hierarchical blocking.

### Experiment 3: Multi-Channel Incremental Union Analysis
- **Script:** [`experiments/blocking/multi_channel.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/multi_channel.py)
- **Objective:** Deconstruct Baseline G channel by channel ($B \rightarrow B+C \rightarrow B+C+D \rightarrow B+C+D+E \rightarrow B+C+D+E+F$) to isolate exact marginal recall and candidate bloat.
- **Key Findings:**
  - $B$ (Exact Name): 39.12% recall, 1.6 cands/S1.
  - $B+C$ (Significant Tokens): 86.02% recall (+16,171 TP), 347.9 cands/S1.
  - $B+C+D$ (4-char Prefix): 91.18% recall (+1,780 TP), 369.2 cands/S1 (only +21.3 cands!).
  - $B+C+D+E$ (Address Digits): **98.09% recall** (+2,380 TP), **836.1 cands/S1** (median: 377).
  - $B+C+D+E+F$ (Location Tokens): 99.94% recall (+641 TP), 3,294.6 cands/S1 (+2,458.5 cands from F alone!).
- **Decision:** Adopted $B+C+D+E$ as our **Core High-Efficiency Backbone** (Level 2).

### Experiment 4: Indic Script Transliteration Ablation
- **Script:** [`experiments/blocking/transliteration.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/transliteration.py)
- **Objective:** Determine the exact impact of offline Indic script transliteration across Devanagari, Tamil, Telugu, Kannada, and Bengali.
- **Discovery (Transliteration Asymmetry):**
  - **In Names ($B, C, D$):** Transliteration recovered **155 genuine true pairs** across 6 Indic scripts with virtually zero candidate overhead (**+4.9 candidates/S1**, from 831.2 to 836.1). 100% of newly recovered pairs were attributed to name transliteration.
  - **In Locations ($F$):** Transliterating non-Latin addresses generated **+4.33 million non-match candidates** (+433 cands/S1 bloat) and lost 4 pairs due to short-token collisions.
- **Decision:** **Selective Transliteration** officially adopted: *Transliteration ON for Names and Digits; OFF for generic address location tokens.*

### Experiment 5: Adaptive / Record-Quality Blocking
- **Script:** [`experiments/blocking/adaptive_blocking.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/adaptive_blocking.py)
- **Objective:** Evaluate whether Channel F could be conditionally gated based on $S1$ candidate count ($k < T$) or record completeness.
- **Discovery (Multi-Match Gating Blindspot):**
  - Analysis of the 660 backbone misses revealed that **92.4% of all Channel F true pairs belonged to multi-match $S1$ entities that had already recalled another target in $BCDE$**.
  - Query-level gating suppressed Channel F for multi-match queries, permanently capping recall at ~98.4%.
- **Decision:** **REJECTED** query-level candidate count suppression. Channel F bloat must be controlled strictly via **Target-Side Filtering**.

### Experiment 6: Hierarchical Fallback Blocking Pipeline
- **Script:** [`experiments/blocking/hierarchical_pipeline.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/hierarchical_pipeline.py)
- **Objective:** Integrate Level 1 (Composite Sieve), Level 2 (Core Backbone), and Level 3 (Target-side 5% IDF-filtered Channel F) into a unified cumulative union ($L1 \cup L2 \cup L3$).
- **Results:**
  - True-Pair Recall: **99.9275%** (34,456 / 34,481).
  - Average candidates/S1: **1,698.0** (-48.46% reduction vs Baseline G's 3,294.6).
  - Median candidates/S1: **1,135** (vs 2,621 in Baseline G).
  - Multi-match integrity: 99.76% of multi-match queries had 100% of true targets recalled.
- **Decision:** Adopted as baseline production blocker.

### Experiment 7: Scalability & Robustness Benchmark
- **Script:** [`experiments/blocking/scalability_benchmark.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/scalability_benchmark.py)
- **Objective:** Validate recall stability, candidate volume scaling, and memory boundedness across 10k, 25k, 50k $S1$ samples and French test data.
- **Key Findings:**
  - **Recall Invariance:** Rock-solid at 99.9275% (10k) $\rightarrow$ 99.9328% (25k) $\rightarrow$ **99.9444%** (50k).
  - **Candidate Scaling Law:** Average candidates/S1 scale strictly linearly with target pool size:
    $$\text{Avg Candidates}(S1) \approx 0.0201 \times N_{\text{targets}}$$
  - **Memory Boundedness:** Discovered candidate materialization memory limit; solved permanently by **streaming evaluation**, keeping peak RAM bounded below **725 MB** for 422.9M candidates.
  - **France Out-of-Domain Robustness:** Extracted 100% of French legal suffixes (`SARL`, `SAS`, `EURL`, `SA`, `SCI`), achieving 0 zero-candidate queries and 93.50% candidate reduction.

### Experiment 8: Dynamic Frequency-Aware Channel F
- **Script:** [`experiments/blocking/rare_location_channel.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/rare_location_channel.py)
- **Objective:** Eliminate common-token target starvation (where records with only Mumbai/Delhi had 0 tokens indexed under static 5% cutoff) without causing candidate explosion.
- **Breakthrough (`Policy_8B_Top2`):** Sorting each target's location tokens by frequency and indexing strictly its **Top-2 rarest tokens** recovered **100% (9/9) of all cutoff losses**, while slashing Channel F candidates by **67.7% vs Baseline G** (from 3,294.6 to **1,064.5 candidates/S1**, median **588**). Recall = **99.9420%**.
- **Decision:** `Policy_8B_Top2` **ACCEPTED** into production.

### Experiment 9: Targeted Hard-Tail Recovery Channels
- **Script:** [`experiments/blocking/tail_recovery_channels.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/tail_recovery_channels.py)
- **Objective:** Systematically address the root causes of the 19 Baseline-G misses.
- **Discoveries:**
  - **2-Letter Word Channel:** `length >= 3` rule had discarded business acronyms (`TY`, `DK`, `TB`, `XF`, `JD`, `AL`, `IT`). Adding country-partitioned 2-letter tokens recovered all 7 misses for only **+1.4 candidates/S1** (efficiency: 1,998 cands/TP).
  - **Domain / Handle Stemming:** Stripping URLs (`tristatefoundation.com`) and social handles (`@SIBYLSBAKERY`) to clean alphanumeric word stems recovered 3 misses for +16 candidates total.
  - **Double Consonant Collapse:** Collapsing repeated consonants (`ll` $\rightarrow$ `l`) recovered `Malone` vs `Mallone` for +6 candidates total.
  - **Address Ordinal Normalization:** Normalizing `54th` $\rightarrow$ `54` and `001711` $\rightarrow$ `1711` allowed composite matching on alias/DBA pairs.
- **Result (`Surgical_Tail_Pipeline`):** **99.9710% recall** (only 10 misses) with **1,140.7 candidates/S1** (-65.38% vs Baseline G).

### Experiment 10: Final 10-Miss Autopsy & Champion v2 Validation
- **Script:** [`experiments/blocking/final_tail_investigation.py`](file:///Users/raj/Desktop/ml%202026%20amazon/experiments/blocking/final_tail_investigation.py)
- **Objective:** Final investigation of the 10 remaining missed true pairs to reach empirical saturation.
- **Micro-Signals Tested:**
  - Consonant Trigram Prefix (`cons_tri`, freq $\le 50$): **+2 TP** (`Willow` vs `Wllrow`, `X & W Flexible` vs `X W & Fceeixble`), efficiency 18,150 cands/TP. **ACCEPTED**.
  - US State + Digits (`state, dig`, freq $\le 50$): **+2 TP** (`Straight Edge` vs `Deltazeta` at AZ-54, `Castillo Empire` vs MN-1711), efficiency 1,878 cands/TP. **ACCEPTED**.
  - Alphanumeric Unit (`unit`, freq $\le 100$): **+1 TP** (`My Consultancy` vs Kannada target at No.3A), efficiency 2,976 cands/TP. **ACCEPTED**.
  - Top-4 Location: +3 TP for +5.65M candidates (1.88M cands/TP). **REJECTED**.
- **Result (`Champion_v2_Surgical`):** **99.9855% recall (34,476 / 34,481, ONLY 5 MISSES)** with **1,145.0 candidates/S1** (median **609**, P95 **4,250**).

---

## 7. Comprehensive Failure Analysis

### 7.1 Missed Pair Progression Across Milestones

| Milestone | Total Misses | Misses from Baseline G (out of 19) | New Cutoff Losses | Dominant Failure Modes |
| :--- | :---: | :---: | :---: | :--- |
| **Baseline G** | 19 | 19 | 0 | 2-letter names (7), URLs/handles (4), aliases (3), typos (2) |
| **Exp 1: IDF Cutoff** | 33 | 19 | 14 | Frequent city tokens dropped (Mumbai, Delhi) |
| **Exp 6: 3-Tier Pipeline** | 25 | 16 | 9 | 5% global cutoff starved targets with only city tokens |
| **Exp 8: Dynamic F (Top-2)** | 20 | 16 | 0 | 100% of cutoff losses recovered; 4 rank exceedances |
| **Exp 9: Surgical Tail** | 10 | 7 | 0 | 12 baseline misses recovered by 2-letter tokens, domains, ordinals |
| **Exp 10: Champion v2** | **5** | **2** | 0 | **14 of 19 baseline misses recovered (73.7%)** |

### 7.2 Autopsy of the Final 5 Unmatchable Misses
The remaining 5 missed true pairs represent fundamental data limits:
1. `S1-602029172` (`F+ Blockchain LLC` vs `F+ LLC Center`): Target address is empty; stripping legal suffixes leaves ONLY the single letter `F`. Connecting them deterministically would require matching every business starting with `F`, adding >3,000 candidates per query.
2. `S1-599869526` (`Decarlo Heritage Electric LLC` vs `Fayeyuma`): Complete DBA alias (zero name overlap) located at disjoint street numbers (`8418 Ii` vs `8400 1/2 Ii`).
3. `S1-650519043` (`Supreme Creative Canary Inc` vs `Ccsupreme.Com`): Target domain has `cc` prefix (`ccsupreme`); address has OCR split (`Gastoni Acity`), pushing `sunset` to 3rd rank.
4. `S1-252340060` (`Vision Care Limited` vs `विजन केयर लिमिटेड`): Cross-lingual target with heavy OCR typos in locality (`bhendarar` for `bhendarkar`, `lakhandul` for `lakhandur`), masking shared tokens.
5. `S1-501450329` (`East All Estate Private Limited` vs Bengali target): Transliteration phonetic divergence (`east` vs `ist`).

Forcing recall on these 5 edge cases would require unconstrained single-letter blocking or Cartesian address matching, triggering catastrophic candidate explosion.

---

## 8. Champion v2 (Surgical) Architecture Specification

```
                                  S1 Anchor Query
                                         │
               ┌─────────────────────────┼─────────────────────────┐
               │                         │                         │
               ▼                         ▼                         ▼
        [Level 1: Sieve]         [Level 2: Backbone]        [Level 3: Dynamic F]
         C2_Union_All               B + C + D + E             Top-2 Rarest Loc
       (Exact + 5 Composites)    (Selective Translit)      (Per-Target Bounded)
       Median: 15 cands          Median: 377 cands          Median: 588 cands
       Recall: 95.57%            Recall: 98.09%             Recall: 99.94%
               │                         │                         │
               └─────────────────────────┼─────────────────────────┘
                                         │
                                         ▼
                             [Surgical Tail Channels]
           ┌─────────────────────────────┼─────────────────────────────┐
           │                             │                             │
           ▼                             ▼                             ▼
    [Tail 1: Short Names]       [Tail 2: Web & Social]     [Tail 3: Normalization]
    Country 2-Char Tokens       Domain / Handle Stems      Consonant Collapse (ll->l)
    (TY, DK, TB, XF, etc.)      (nospace concatenation)    Enriched Digits + Loc
           │                             │                             │
           └─────────────────────────────┼─────────────────────────────┘
                                         │
                                         ▼
                            [Targeted Micro-Signals]
           ┌─────────────────────────────┼─────────────────────────────┐
           │                             │                             │
           ▼                             ▼                             ▼
   Consonant Trigram             US State + Digits             Alphanumeric Unit
   Prefix (freq <= 50)           Composite (freq <= 50)        Token (freq <= 100)
   (kwl, xwf)                    (AZ-54, MN-1711)              (3a, 104b)
           │                             │                             │
           └─────────────────────────────┼─────────────────────────────┘
                                         │
                                         ▼
                             CUMULATIVE UNION & DEDUP
                                         │
                                         ▼
                       Candidate Pairs (1,145.0 avg / S1)
                       Recall: 99.9855% | Misses: 5 | 0-Cands: 0
```

---

## 9. Final Benchmark Comparison

| Metric | Cartesian | Baseline G | Exp 6 Pipeline | **Champion v2 (Surgical)** | Net Impact vs Baseline G |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **True-Pair Recall** | 100.0% | 99.9449% | 99.9275% | **99.9855%** | **+0.0406% (+14 true pairs)** |
| **Missed True Pairs** | 0 | 19 | 25 | **5** | **-73.68% (slashed by 3/4)** |
| **Average Candidates / S1** | 84,481.0 | 3,294.6 | 1,698.0 | **1,145.0** | **-65.25% (-2,149.6 cands/S1)** |
| **Median Candidates / S1** | 84,481 | 2,621 | 1,135 | **609** | **-76.76% (-2,012 cands/S1)** |
| **P90 Candidates / S1** | 84,481 | 7,723 | 4,155 | **2,864** | **-62.92% (-4,859 cands/S1)** |
| **P95 Candidates / S1** | 84,481 | 9,555 | 5,321 | **4,250** | **-55.52% (-5,305 cands/S1)** |
| **Max Candidates / S1** | 84,481 | 18,372 | 10,904 | **10,247** | **-44.22% (-8,125 cands/S1)** |
| **Zero-Candidate S1s** | 0 | 0 | 0 | **0** | **Perfect 0 maintained** |
| **Multi-Match Complete Recall** | 100.0% | 99.76% | 99.76% | **99.90%** | **Near-perfect multi-match** |
| **Candidate Reduction Ratio** | 0.00% | 96.10% | 97.99% | **98.64%** | **Search space cut by 98.6%** |
| **Evaluation Runtime** | - | 35.57s | 8.71s | **3.73s** | **$9.5\times$ faster execution** |
| **Peak Memory Consumption** | OOM | 374 MB | 708 MB | **802 MB** | **Bounded under 1 GB RAM** |

---

## 10. Handoff to Phase 3: Machine Learning Matcher

Candidate generation is complete and officially frozen. The candidate universe output by Champion v2 now feeds into **Phase 3 (Pairwise Feature Engineering & Classification)**:

1. **Vectorized Pairwise Features:**
   - **Name Similarities:** Exact match flag, Jaro-Winkler distance, Levenshtein ratio, token Jaccard similarity, shared significant token count, character 3-gram cosine similarity.
   - **Address Similarities:** Exact house number match flag, postal/PIN code equality, location token Jaccard similarity, string edit distance on street name.
   - **Structural & Provenance Indicators:** Boolean match flags for Level 1 (`C2_Union`), Level 2 Backbone, Level 3 Channel F, 2-letter token match, and domain handle stem match.
   - **Legal Suffix Flags:** Exact legal type agreement (`pvt_ltd` vs `pvt_ltd`), legal conflict flag (`inc` vs `llc`), missing suffix indicator.
2. **Gradient-Boosted Tree Classifier:**
   - Train a fast LightGBM or CatBoost binary classifier on pairwise features with stratified 5-fold cross-validation.
3. **Threshold Calibration for Macro $F_{0.5}$:**
   - Optimize prediction probability cutoffs specifically to maximize Macro $F_{0.5}$ (weighting precision twice as heavily as recall).
4. **Disjoint 1-to-Many Assignment:**
   - Apply stable bipartite matching or greedy target assignment so each $S2$ and $S3$ record is assigned to at most one $S1$ query, satisfying the ground-truth target exclusivity invariant.
