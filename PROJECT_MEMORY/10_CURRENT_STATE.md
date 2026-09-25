# 10 CURRENT STATE: LIVE PROJECT STATUS

*Last Updated: 2026-09-25 23:35:00*

## 1. Project Phase
- **Stage:** Blocking Experiments & Optimization (Pre-ML Matching).
- **Focus:** Maximizing True-Pair Recall while pruning Candidate Volume.

## 2. Active Baseline: Strategy G
- **Definition:** Multi-Channel Union: `B` (Exact Core Name) + `C` (Significant Name Tokens $\ge 3$) + `D` (4-char Prefix) + `E` (Address Digits) + `F` (Address Location Tokens).
- **Metrics on 10k Pilot:**
  - True-Pair Recall: **99.9449%** (34,462 / 34,481)
  - Missed True Pairs: **19**
  - Average Candidates / S1: **3,294.6**
  - Median Candidates / S1: **2,621**
  - P95 Candidates / S1: **9,555**
  - Max Candidates / S1: **18,372**
  - Zero-Candidate S1s: **0**
  - Runtime: **35.57s** | Peak RAM: **374.48 MB**

## 3. Completed Experiments
- **Experiment 1 (Rare Token / IDF Filtering):**
  - `E1_B` (Conservative $>5\%$ cutoff) drops candidate volume by **57.21%** (from 3,295 to 1,410 candidates/S1) while maintaining **99.9043% recall** (only 14 true pairs lost vs baseline).
- **Experiment 2 (Combined / Composite Blocking Keys):**
  - Individual composite keys suffer massive recall drops (59.97%–80.37%) and produce up to 1,689 zero-candidate S1s.
  - `C2_Union_All_Composites` (union of all 5 composite pairs + exact name) achieves **95.57% recall** with only **113.8 candidates/S1 (median: 15)**, ideal as a Level-1 filter for fallback architectures.
- **Experiment 3 (Multi-Channel Incremental Union Analysis):**
  - $B$: 39.12% recall, 1.6 cands/S1
  - $B+C$: 86.02% recall (+16,171 pairs), 347.9 cands/S1
  - $B+C+D$: 91.18% recall (+1,780 pairs), 369.2 cands/S1 (only +21.3 cands!)
  - $B+C+D+E$: **98.09% recall** (+2,380 pairs), **836.1 cands/S1** (median: 377, 1 zero-cand S1)
  - $B+C+D+E+F$ (Baseline G): 99.94% recall (+641 pairs), 3,294.6 cands/S1 (+2,458.5 cands from F alone!)
- **Experiment 4 (Indic Script Transliteration Ablation):**
  - Proved transliteration asymmetry:
    - In Core Backbone ($B+C+D+E$): Transliteration boosts recall from **97.66% to 98.09% (+155 true pairs)** with near-zero candidate cost (**+4.9 candidates/S1**, from 831.2 to 836.1). 100% of newly recovered pairs are from Name Transliteration.
    - In Location Tokens (Channel $F$): Transliterating Indic addresses generates **+4.33 million non-true candidates (+433/S1 bloat)** and loses 4 pairs due to short-token collisions.
  - Architectural conclusion: **Selective transliteration** (Names ON, generic address location tokens OFF).
- **Experiment 5 (Adaptive / Record-Quality Blocking):**
  - Benchmarked 11 gating policies for Channel F against the Selective-Transliteration Backbone.
  - Critical insight: Discovered the **Multi-Match Gating Blindspot**: 92.4% of Channel F true pairs belong to multi-match S1 queries that already matched another target in BCDE. Query-level suppression ($k < T$) cuts off Channel F prematurely, capping recall at ~98.4%. Channel F must be throttled via target-side token-frequency filtering (IDF) rather than query-level gating.
- **Experiment 6 (Hierarchical Fallback Blocking Pipeline):**
  - Integrated 3-tier cumulative union ($L1 \cup L2 \cup L3$): 99.9275% recall on 10k pilot, -48.46% candidate reduction, 99.76% multi-match integrity.
- **Experiment 7 (Scalability & Robustness Testing):**
  - Progressively benchmarked across 10k, 25k, and 50k S1s:
    - Recall stability: **99.9275%** (10k) $\rightarrow$ **99.9328%** (25k) $\rightarrow$ **99.9444%** (50k).
    - Multi-match recall: **99.93%–99.94%** across all scales.
    - Zero-candidate S1s: **0** across all scales.
    - Candidate reduction ratio: perfectly invariant at **~97.99%** across all scales.
    - Candidate volume scaling: $\text{Avg Candidates} \approx 0.0201 \times N_{\text{targets}}$.
    - Memory bounded: Streaming evaluation keeps peak RAM bounded under **725 MB** even when evaluating 422.9M candidate pairs.
  - France test split validation: 100% legal suffix extraction (`SARL`, `SAS`, `EURL`, `SA`, `SCI`), 0 zero-candidate S1s, 93.50% reduction.
- **Experiment 8 (Dynamic Frequency-Aware Channel F):**
  - Proved that indexing strictly the **Top-2 rarest location tokens per target** recovers **100% (9/9)** of all cutoff losses while slashing Channel F candidates by **67.7% vs Baseline G** (from 3,294.6 to **1,064.5 candidates/S1**, median **588**). Recall = **99.9420%**.
- **Experiment 9 (Hard-Tail Recovery Channels):**
  - Evaluated targeted channels for the 19 Baseline-G misses (2-letter abbreviations, domain/handle stems, ordinal/leading-zero address digits, consonant collapse).
  - **Surgical Tail Pipeline:** Delivers **99.9710% recall** (34,471 / 34,481, **only 10 missed pairs**) with only **1,140.7 candidates/S1** (median **606**, -65.38% vs Baseline G!).
  - **Full Tail Bound:** Pushes recall to an all-time record **99.9797% recall** (**only 7 missed pairs**) with **1,580.5 candidates/S1**.
  - 15 of the 19 Baseline-G misses (78.9%) systematically recovered.

- **Experiment 10 (Final Hard-Tail Investigation & Champion v2):**
  - Evaluated targeted micro-signals for each of the 10 remaining missed true pairs.
  - Accepted 3 ultra-efficient signals:
    1. Consonant Trigram Prefix (`cons_tri`, freq <= 50): +2 TP, efficiency 18,149 cands/TP.
    2. US State + Digits (`state, dig`, freq <= 50): +2 TP, efficiency 1,878 cands/TP.
    3. Alphanumeric Address Unit (`unit`, freq <= 100): +1 TP, efficiency 2,976 cands/TP.
  - Recovers **5 out of the 10 tail misses (50%)**, leaving only 5 unmatchable edge cases.

## 4. Active Production Champion: Champion v2 (Surgical)
- **Status:** **FROZEN (Ready for Phase 3 Feature Engineering)**
- **Components:**
  1. Level 1: `C2_Union_All` (Exact name + 5 composites)
  2. Level 2: Core Backbone ($B+C+D+E$ with selective transliteration)
  3. Level 3: Dynamic Channel F (Top-2 rarest tokens per target)
  4. Tail 1: Country-partitioned 2-letter tokens (`tokens_2char`)
  5. Tail 2: Domain stem & social handle nospace matching
  6. Tail 3: Double consonant collapse (`core_collapsed`)
  7. Tail 4: Composite enriched digits + location (`digits_enriched + loc`)
  8. Micro-Signal 1: Consonant Trigram Prefix (`cons_tri`, freq <= 50)
  9. Micro-Signal 2: US State + Digits composite (`state, dig`, freq <= 50)
  10. Micro-Signal 3: Alphanumeric address unit (`unit`, freq <= 100)
- **Champion v2 Metrics on 10k Pilot:**
  - True-Pair Recall: **99.9855%** (34,476 / 34,481)
  - Missed True Pairs: **5** (slashed from 19 in Baseline G and 25 in E6)
  - Average Candidates / S1: **1,145.0** (slashed by **-65.25%** vs Baseline G's 3,294.6)
  - Median Candidates / S1: **609** (slashed by **-76.76%** vs Baseline G's 2,621)
  - P95 Candidates / S1: **4,250** (slashed by **-55.52%** vs Baseline G's 9,555)
  - Max Candidates / S1: **10,247** (vs 18,372 in Baseline G)
  - Zero-Candidate S1s: **0**
  - Multi-Match Complete Recall: **99.90%**
  - Total Runtime: **3.73s** | Peak RAM: **802 MB**

## 5. Current Blockers & Risks
- **Blockers:** None. Blocking phase complete.
- **Risks:** Full dataset contains 2.2M S1 and 10.3M targets. Must use streaming/chunked generation to keep memory under 1 GB.

## 6. Next Planned Action
- **Phase 3: Pairwise Feature Engineering & Matcher/Ranker Training**
  - Extract fast pairwise string, token, digit, phonetic, and channel indicator features.
  - Train LightGBM model calibrated for Macro $F_{0.5}$.






