# 04 EXPERIMENT LOG: COMPLETE BENCHMARK REGISTRY

*Rule: Never overwrite an experiment. Append all runs with exact parameters, measured metrics, and conclusions.*

---

## Experiment 0: Baseline G Reproduction
- **ID:** `Baseline_G`
- **Date:** 2026-09-25 22:46:00
- **Hypothesis:** Exact replication of Strategy G on the identical 10,000 S1 pilot dataset will yield 34,462 recalled true pairs (99.94% recall), 19 missed pairs, and ~3,294.6 avg candidates/S1.
- **Dataset:** 10,000 S1 pilot, 84,481 target pool, 34,481 true pairs (`experiments/data/`).
- **Configuration:** Channels B (Exact Core Name) + C (Sig Name Tokens $\ge 3$) + D (4-char prefix) + E (Address Digits) + F (Address Location Tokens). No filtering.
- **Results:**
  - True Pairs Recalled: **34,462** / 34,481
  - True Pairs Missed: **19**
  - Recall: **99.9449%**
  - Avg Candidates/S1: **3,294.6**
  - Median Candidates/S1: **2,621**
  - P95 Candidates/S1: **9,555**
  - Max Candidates/S1: **18,372**
  - Zero-Candidate S1s: **0**
  - Reduction Ratio: **96.1001%**
  - Runtime: **35.57s** | Peak RAM: **374.48 MB**
- **Conclusion:** Control baseline reproduced with 100% precision. Candidate sets saved to `experiments/data/baseline_g_candidates.json`.

---

## Experiment 1: Rare Token / IDF Frequency Filtering
- **ID:** `E1` (`E1_A`, `E1_B`, `E1_C`, `E1_D`)
- **Date:** 2026-09-25 23:16:00
- **Hypothesis:** Filtering out hyper-frequent stopwords and common tokens from target inverted indexes will drastically reduce candidate volume without harming true-pair recall.
- **Configurations:**
  - `E1_A`: No filtering (Baseline G control).
  - `E1_B`: Conservative cutoff (tokens appearing in $>5\%$ of target pool: US $>2500$, India $>1700$).
  - `E1_C`: Moderate cutoff (tokens appearing in $>2\%$ of target pool: US $>1000$, India $>680$).
  - `E1_D`: Aggressive cutoff (tokens appearing in $>1\%$ of target pool: US $>500$, India $>340$).
- **Results:**
  - `E1_A`: Recall: 99.9449% | Recalled: 34,462 | Lost vs Base: 0 | Avg Cands: 3,294.6 | P95: 9,555 | Max: 18,372 | Zero: 0 | Time: 19.88s
  - `E1_B`: Recall: 99.9043% | Recalled: 34,448 | Lost vs Base: **14** | Avg Cands: **1,409.7** (-57.21%) | P95: 3,752 | Max: 6,807 | Zero: 0 | Time: 6.07s
  - `E1_C`: Recall: 99.7738% | Recalled: 34,403 | Lost vs Base: **59** | Avg Cands: **718.5** (-78.19%) | P95: 1,639 | Max: 3,425 | Zero: 0 | Time: 4.54s
  - `E1_D`: Recall: 99.6230% | Recalled: 34,351 | Lost vs Base: **111** | Avg Cands: **445.5** (-86.48%) | P95: 920 | Max: 1,675 | Zero: 0 | Time: 7.72s
- **Conclusion:** `E1_B` is a massive breakthrough for candidate reduction: slashes average candidate volume by **57.21%** (from 3,295 to 1,410) and cuts P95 candidate bloat by **60.7%** (from 9,555 to 3,752) while retaining **99.904% recall** (only 14 pairs newly lost).

---

## Experiment 2: Combined / Composite Blocking Keys
- **ID:** `E2` (`C2_A` through `C2_E`, `C2_Union_All_Composites`, `C2_Union_Name_Address`, `C2_High_Precision`)
- **Date:** 2026-09-25 23:45:00
- **Hypothesis:** Compounding blocking attributes (e.g. name token + location token, prefix + digit) will drastically reduce candidate volume by creating highly selective conjunctions ($A \land B$).
- **Configurations:**
  - `C2_A_Tok_Loc`: Country + (Name Token & Loc Token)
  - `C2_B_Tok_Dig`: Country + (Name Token & Address Digit)
  - `C2_C_Pref_Loc`: Country + (Name 4-Char Prefix & Loc Token)
  - `C2_D_Pref_Dig`: Country + (Name 4-Char Prefix & Address Digit)
  - `C2_E_Dig_Loc`: Country + (Address Digit & Loc Token)
  - `C2_Union_All_Composites`: Union of Exact Name + all 5 composite pairs
- **Results:**
  - `C2_A_Tok_Loc`: Recall: 80.37% | Recalled: 27,712 | Lost vs Base: 6,750 | Avg Cands: 28.0 (-99.15%) | Med: 7 | P95: 118 | Max: 678 | Zero: 233
  - `C2_B_Tok_Dig`: Recall: 64.88% | Recalled: 22,370 | Lost vs Base: 12,092 | Avg Cands: 6.8 (-99.79%) | Med: 3 | P95: 29 | Max: 406 | Zero: 1,408
  - `C2_C_Pref_Loc`: Recall: 74.74% | Recalled: 25,770 | Lost vs Base: 8,692 | Avg Cands: 7.7 (-99.77%) | Med: 4 | P95: 25 | Max: 165 | Zero: 472
  - `C2_D_Pref_Dig`: Recall: 59.97% | Recalled: 20,677 | Lost vs Base: 13,785 | Avg Cands: 2.9 (-99.91%) | Med: 2 | P95: 7 | Max: 81 | Zero: 1,689
  - `C2_E_Dig_Loc`: Recall: 74.53% | Recalled: 25,698 | Lost vs Base: 8,764 | Avg Cands: 83.0 (-97.48%) | Med: 4 | P95: 553 | Max: 3,727 | Zero: 1,102
  - `C2_Union_All_Composites`: Recall: **95.57%** | Recalled: 32,953 | Lost vs Base: 1,509 | Avg Cands: **113.8** (-96.55%) | Med: **15** | P95: 637 | Max: 3,820 | Zero: 116
- **Conclusion:** Standalone composite keys suffer severe recall drops (59%–80%) and produce hundreds of zero-candidate S1s because noisy records frequently lack address digits or have corrupted tokens. However, the **Union of All Composites** (`C2_Union_All_Composites`) achieves **95.57% recall with only 113.8 candidates on average (median 15)**, making it a premier candidate for the Level 1 tier in hierarchical fallback blocking.

---

## Experiment 3: Multi-Channel Incremental Union Analysis
- **ID:** `E3` (`E3_Step1_B`, `E3_Step2_BC`, `E3_Step3_BCD`, `E3_Step4_BCDE`, `E3_Step5_BCDEF`)
- **Date:** 2026-09-25 23:55:00
- **Hypothesis:** Incrementally evaluating $B \rightarrow B+C \rightarrow B+C+D \rightarrow B+C+D+E \rightarrow B+C+D+E+F$ will quantify the exact marginal true-pair recovery and candidate cost added by each channel.
- **Results:**
  - `B` (Exact Name): Recall: **39.12%** | Recalled: 13,490 | Missed: 20,991 | Avg Cands: **1.6** | Med: 1 | P95: 4 | Zero: 2,534
  - `B + C` (+ Sig Token): Recall: **86.02%** (+46.90%) | Recalled: 29,661 | Marginal Pairs: **+16,171** | Missed: 4,820 | Avg Cands: **347.9** | Med: 231 | P95: 1,655 | Zero: 14
  - `B + C + D` (+ 4-Char Prefix): Recall: **91.18%** (+5.16%) | Recalled: 31,441 | Marginal Pairs: **+1,780** | Missed: 3,040 | Avg Cands: **369.2** (+21.3) | Med: 247 | P95: 1,698 | Zero: 5
  - `B + C + D + E` (+ Address Digits): Recall: **98.09%** (+6.91%) | Recalled: 33,821 | Marginal Pairs: **+2,380** | Missed: 660 | Avg Cands: **836.1** (+466.9) | Med: 377 | P95: 3,559 | Zero: 1
  - `B + C + D + E + F` (+ Loc Tokens = Base G): Recall: **99.94%** (+1.85%) | Recalled: 34,462 | Marginal Pairs: **+641** | Missed: 19 | Avg Cands: **3,294.6** (+2,458.5) | Med: 2,621 | P95: 9,555 | Zero: 0
- **Conclusion:** Channel C is the core recovery workhorse (+16,171 pairs). Channel D has the highest efficiency (+1,780 pairs for only +21 cands). Channel E pushes recall over 98% with under 840 candidates. Channel F recovers the final +641 pairs but accounts for **74.6% of the total candidate volume** (+2,458 candidates/S1).

---

## Experiment 4: Indic Script Transliteration Ablation Benchmark
- **ID:** `E4` (`1_BCDE_translit_OFF`, `2_BCDE_translit_ON`, `3_BCDEF_translit_OFF`, `4_BCDEF_translit_ON` / Baseline G)
- **Date:** 2026-09-25 23:57:00
- **Hypothesis:** Offline Indic-to-Latin transliteration will recover cross-script true pairs (where S1 is in Latin and S2/S3 is in native Indic script like Devanagari, Kannada, Tamil, Gujarati, Bengali) with minimal candidate volume penalty.
- **Configurations Tested on identical 10k pilot:**
  1. `1_BCDE_translit_OFF`: B+C+D+E, transliteration disabled.
  2. `2_BCDE_translit_ON`: B+C+D+E, transliteration enabled.
  3. `3_BCDEF_translit_OFF`: B+C+D+E+F, transliteration disabled.
  4. `4_BCDEF_translit_ON`: B+C+D+E+F, transliteration enabled (Baseline G control).
- **Results:**
  - `1_BCDE_translit_OFF`: Recall: **97.6625%** | Recalled: 33,675 | Missed: 806 | Avg Cands: **831.2** | Med: 370 | P95: 3,556 | Max: 9,012 | Zero: 1 | Time: 1.54s | RAM: 600.7 MB
  - `2_BCDE_translit_ON`: Recall: **98.0859%** (+0.4234%) | Recalled: 33,821 | Missed: 660 | Marginal Pairs: **+146 net (+155 new, -9 lost)** | Avg Cands: **836.1** (+4.9 cands/S1) | Med: 377 | P95: 3,559 | Max: 9,012 | Zero: 1 | Time: 1.54s | RAM: 826.9 MB
  - `3_BCDEF_translit_OFF`: Recall: **99.9565%** | Recalled: 34,466 | Missed: 15 | Avg Cands: **2,861.6** | Med: 1,495 | P95: 9,067 | Max: 17,555 | Zero: 0 | Time: 6.44s | RAM: 637.2 MB
  - `4_BCDEF_translit_ON` (Baseline G): Recall: **99.9449%** | Recalled: 34,462 | Missed: 19 | Avg Cands: **3,294.6** (+433.0 cands/S1) | Med: 2,621 | P95: 9,555 | Max: 18,372 | Zero: 0 | Time: 9.06s | RAM: 815.9 MB
- **Attribution Analysis:**
  - **Source Classification for Recovered Pairs:** Exactly **100.0% (155/155)** of newly recovered pairs in BCDE were driven purely by **Name Transliteration**. Address transliteration caused 0 recoveries.
  - **Marginal Efficiency in Core Backbone (BCDE):** Adding transliteration in BCDE introduced only **+4.9 candidates/S1** (+61,463 newly added, -12,071 dropped) to gain **+155 true pairs** (1 true pair gained per 395 non-true candidates, marginal gain ratio 0.00252).
  - **Channel F (Location Token) Transliteration Toxicity:** In BCDEF, turning transliteration ON in address location tokens bloated candidate volume by **+4,330,186 candidates (+433.0 candidates/S1)** while actually losing 4 true pairs (from 34,466 to 34,462) due to noisy short-syllable collisions.
  - **Baseline G 19 Misses:** None of the 19 Baseline G misses were recovered by transliteration (since Baseline G already ran with transliteration ON).
- **Conclusion:** Transliteration is essential and highly effective for **business names** (recovering 155 genuine Indic script pairs across Devanagari, Kannada, Tamil, Gujarati, Bengali, Malayalam with virtually zero candidate overhead). However, transliteration should be **disabled on Channel F location tokens** to avoid 4.3 million useless candidates.

---

## Experiment 5: Adaptive / Record-Quality Blocking Benchmark
- **ID:** `E5` (`Ref_Backbone_No_F`, `Policy_A_k0`, `Policy_B1_k5`–`B4_k50`, `Policy_C1`–`C3`, `Policy_D1`–`D3`, `Ref_Unconstrained_F`)
- **Date:** 2026-09-26 00:04:00
- **Hypothesis:** Selective activation of Channel F based on S1 record-quality features (evidence strength, address digits, token counts, candidate set evidence) can recover the tail of true pairs missed by the $B+C+D+E$ backbone without incurring the massive candidate bloat of unconstrained Channel F.
- **Reference Backbone:** $B+C+D+E$ with selective transliteration (ON for names B/C/D and digits E; OFF for location tokens F).
  - Recall: **98.0859%** (33,821 / 34,481), Missed: **660**, Avg Candidates: **836.1**, Median: 377, P95: 3,559, Zero-Cand S1: 1.
- **Master Policy Benchmark Results (10k Pilot):**
  - `Ref_Backbone_No_F`: Recall: **98.0859%** | Recalled: 33,821 | Missed: 660 | +TP: 0 | Trig S1: 0.0% | Avg Cands: **836.1** | P50: 377 | P95: 3,559 | P99: 5,539 | Max: 9,012
  - `Policy_A_k0` (F if k==0): Recall: **98.0859%** | Recalled: 33,821 | Missed: 660 | +TP: 0 | Trig S1: 0.01% (1 S1) | Avg Cands: 836.2 | P50: 377 | P95: 3,559 | P99: 5,539 | Max: 9,012
  - `Policy_B1_k5` (F if k<5): Recall: **98.1120%** | Recalled: 33,830 | Missed: 651 | +TP: **+9** | Trig S1: 0.31% (31 S1) | Avg Cands: **843.2** | P50: 381 | P95: 3,570 | P99: 5,555 | Max: 9,012 | Eff: 7,910.8 cands/TP
  - `Policy_B2_k10` (F if k<10): Recall: **98.1381%** | Recalled: 33,839 | Missed: 642 | +TP: **+18** | Trig S1: 1.08% (108 S1) | Avg Cands: **855.9** | P50: 385 | P95: 3,594 | P99: 5,690 | Max: 9,527 | Eff: 11,010.5 cands/TP
  - `Policy_B3_k20` (F if k<20): Recall: **98.1700%** | Recalled: 33,850 | Missed: 631 | +TP: **+29** | Trig S1: 2.98% (298 S1) | Avg Cands: **882.4** | P50: 396 | P95: 3,637 | P99: 5,826 | Max: 9,527 | Eff: 15,969.6 cands/TP
  - `Policy_B4_k50` (F if k<50): Recall: **98.2976%** | Recalled: 33,894 | Missed: 587 | +TP: **+73** | Trig S1: 9.60% (960 S1) | Avg Cands: **954.3** | P50: 423 | P95: 3,737 | P99: 6,154 | Max: 10,780 | Eff: 16,189.6 cands/TP
  - `Policy_C1_Tokens1` (tokens<=1 & has loc): Recall: **98.4919%** | Recalled: 33,961 | Missed: 520 | +TP: **+140** | Trig S1: 11.27% (1,127 S1) | Avg Cands: **1,143.2** | P50: 428 | P95: 4,849 | P99: 8,506 | Max: 14,083 | Eff: 21,937.2 cands/TP
  - `Policy_C2_Tokens1_NoDig` (tokens<=1 & digits==0 & has loc): Recall: **98.2686%** | Recalled: 33,884 | Missed: 597 | +TP: **+63** | Trig S1: 0.91% (91 S1) | Avg Cands: **869.2** (+33.1) | P50: 387 | P95: 3,634 | P99: 5,837 | Max: 10,780 | Eff: **5,259.5 cands/TP**
  - `Policy_C3_ShortName` (core<=6 & has loc): Recall: **98.1352%** | Recalled: 33,838 | Missed: 643 | +TP: **+17** | Trig S1: 1.54% (154 S1) | Avg Cands: 852.6 | P50: 384 | P95: 3,593 | P99: 5,652 | Max: 10,706 | Eff: 9,727.5 cands/TP
  - `Policy_D1_NoExact_NoDigMatch` (No exact & No dig match & has loc): Recall: **98.3324%** | Recalled: 33,906 | Missed: 575 | +TP: **+85** | Trig S1: 2.09% (209 S1) | Avg Cands: **885.3** (+49.2) | P50: 391 | P95: 3,656 | P99: 5,869 | Max: 10,474 | Eff: **5,782.9 cands/TP**
  - `Policy_D2_Hybrid` (k<10 OR NoExact&NoDigMatch): Recall: **98.3788%** | Recalled: 33,922 | Missed: 559 | +TP: **+101** | Trig S1: 3.02% (302 S1) | Avg Cands: **902.3** (+66.2) | P50: 397 | P95: 3,695 | P99: 5,963 | Max: 10,474 | Eff: **6,551.2 cands/TP**
  - `Policy_D3_Hybrid` (k<20 OR (NoExact & Digs==0)): Recall: **98.4020%** | Recalled: 33,930 | Missed: 551 | +TP: **+109** | Trig S1: 4.33% (433 S1) | Avg Cands: **923.6** (+87.5) | P50: 405 | P95: 3,725 | P99: 6,123 | Max: 10,474 | Eff: **8,023.1 cands/TP**
  - `Ref_Unconstrained_F` (All S1s): Recall: **99.9536%** | Recalled: 34,465 | Missed: 16 | +TP: **+644** | Trig S1: 100.0% | Avg Cands: **2,865.8** (+2,029.7) | P50: 1,494 | P95: 9,082 | P99: 11,499 | Max: 17,555 | Eff: 31,517.0 cands/TP
- **Critical Error & Tail Analysis on the 660 Backbone Misses:**
  - **Recoverability:** 644 / 660 (97.58%) are recoverable by Channel F. Only 16 / 660 (2.42%) are unrecoverable.
  - **Multi-Match Asymmetry (The Key Architectural Discovery):**
    - 635 / 644 (98.6%) of the F-recoverable pairs belong to **multi-match S1 entities**.
    - **595 / 644 (92.4%)** belong to S1 entities where the S1 **ALREADY had another true match successfully recalled by BCDE**.
    - Because S1 already found one or more targets via name or digits, S1 generated candidates ($k \ge 50$ or $k \ge 100$), causing candidate-count gating policies ($k < T$) to suppress Channel F, even though S1 still had another corrupted target (e.g. `Veozephgild`) that could ONLY be found via street/city location tokens!
  - **Target Quality Breakdown:**
    - 397 / 644 (61.6%) of targets missed by BCDE have **zero address digits** (Channel E impossible).
    - 644 / 644 (100.0%) of targets missed by BCDE have **zero name overlap** with S1 (Channels B, C, D impossible due to synthetic noise names or concatenated domains).
  - **Baseline G 19 Misses Tracking:**
    - 16 of the 19 Baseline G misses remain unrecoverable by any channel (including F). The remaining 3 were recovered because transliteration OFF on F eliminated 4 false-collision losses.

---

## Experiment 6: Hierarchical Fallback Blocking Pipeline Integration Benchmark
- **ID:** `E6` (`1_Baseline_G`, `2_Backbone_BCDE`, `3_L1_Only`, `4_L1_U_L2`, `5_L1_U_L2_U_L3`)
- **Date:** 2026-09-26 00:09:00
- **Hypothesis:** Combining Level 1 (Composite Sieve), Level 2 (Core Backbone B+C+D+E with selective transliteration), and Level 3 (Target-side E1-B filtered Channel F with unsuppressed query evaluation) as a cumulative deduplicated union ($L1 \cup L2 \cup L3$) will achieve $\ge 99.9\%$ true-pair recall while slashing candidate volume by nearly 50% compared to Baseline G.
- **Master Benchmark Comparison (10,000 S1 Pilot):**
  - `1_Baseline_G`: Recall: **99.9449%** (34,462 / 34,481) | Missed: 19 | Avg Cands: **3,294.6** | Med: 2,621 | P90: 8,012 | P95: 9,555 | P99: 12,450 | Max: 18,372 | Zero: 0 | Total Cands: 32,946,375 | Reduct: 96.10% | Time: 35.57s
  - `2_Backbone_BCDE`: Recall: **98.0859%** (33,821 / 34,481) | Missed: 660 | Avg Cands: **836.1** | Med: 377 | P90: 2,251 | P95: 3,559 | P99: 5,539 | Max: 9,012 | Zero: 1 | Total Cands: 8,361,131 | Reduct: 99.01% | Time: 2.12s
  - `3_L1_Only`: Recall: **95.6266%** (32,973 / 34,481) | Missed: 1,508 | Avg Cands: **104.2** | Med: **10** | P90: 325 | P95: 604 | P99: 1,207 | Max: 3,564 | Zero: 135 | Total Cands: 1,042,142 | Reduct: 99.88% | Time: 1.15s
  - `4_L1_U_L2`: Recall: **98.0859%** (33,821 / 34,481) | Missed: 660 | Avg Cands: **836.1** | Med: 377 | P90: 2,251 | P95: 3,559 | P99: 5,539 | Max: 9,012 | Zero: 1 | Total Cands: 8,361,131 | Reduct: 99.01% | Time: 3.27s
  - `5_L1_U_L2_U_L3`: Recall: **99.9275%** (34,456 / 34,481) | Missed: **25** | Avg Cands: **1,698.0** (-48.46%) | Med: **1,135** (-56.7%) | P90: 4,155 | P95: **5,321** (-44.3%) | P99: 7,386 | Max: **10,904** (-40.6%) | Zero: **0** | Total Cands: **16,979,677** | Reduct: **97.99%** | Time: 8.71s
- **Marginal Set-Difference Analysis:**
  - `Level 1 (Composite Sieve)`: **32,973 TP** (95.63% recall) | 1,042,142 cands (104.2/S1) | Efficiency: **31.6 cands/TP**
  - `Level 2 (Core Backbone)`: **+848 marginal TP** (+2.46% recall $\rightarrow$ 98.09% cumulative) | +7,318,989 marginal cands (+731.9/S1) | Efficiency: **8,630.9 cands/TP**
  - `Level 3 (Filtered Channel F)`: **+635 marginal TP** (+1.84% recall $\rightarrow$ 99.93% cumulative) | +8,618,546 marginal cands (+861.9/S1) | Efficiency: **13,572.5 cands/TP** (vs 31,517 for unconstrained F)
- **660-Tail Recovery Tracking:**
  - Total Backbone Misses: 660
  - Recovered by Level 3 (Filtered Channel F): **635 pairs (96.21%)**
  - Remaining Unrecovered: **25 pairs (3.79%)**
  - Baseline G 19-Misses Overlap: 16 of the 19 Baseline G misses remain unrecovered; 9 new misses were introduced by the 5% IDF cutoff in exchange for eliminating 16 million candidate pairs.
- **1-to-Many Multi-Match Integrity Validation:**
  - Multi-Match S1 queries ($N \ge 2$): 8,902 entities (89.0% of pilot) representing 33,941 ground-truth pairs.
  - Recalled pairs: **33,917 (99.9293%)**.
  - S1s with 100% true targets recalled: **8,881 (99.76%)**.
  - S1s with partial matches: **21 (0.24%)**.
  - S1s with 0 matches recalled: **0 (0.00%)**.
  - Proves conclusively that query-level unsuppressed F preserves multi-match recall.
- **Candidate Universe Integrity Audit:**
  - Every candidate pair has valid S1 ID and valid S2/S3 Target ID: **PASSED [x]**
  - Every predicted match is a strict subset of Candidate Universe: **PASSED [x]**
  - Candidate reduction vs Baseline G: **-48.46%** (15,966,698 candidate pairs eliminated).

---

## Experiment 7: Scalability & Robustness Testing Benchmark (10k, 25k, 50k, and France)
- **ID:** `E7` (`10k_S1`, `25k_S1`, `50k_S1`, `France_Test_Sample`)
- **Date:** 2026-09-26 00:41:00
- **Hypothesis:** The Experiment 6 hierarchical blocker will maintain stable recall ($\ge 99.9\%$), bounded memory (<1 GB), and predictable linear candidate scaling as dataset size expands.
- **Scaling Results Summary:**
  - `10k_S1` (10,000 S1, 84,481 targets, 34,481 true pairs):
    - L1 Recall: **95.6266%** | L2 Recall: **98.0859%** | L3 Final Recall: **99.9275%** (25 missed)
    - Avg Candidates: **1,698.0** | Med: 1,135 | P90: 4,155 | P95: 5,321 | P99: 7,386 | Max: 10,904 | 0-Cand: **0**
    - Total Candidates: 16,979,677 | Reduction: **97.9901%** | Total Time: **8.71s** | RAM: **708.59 MB**
  - `25k_S1` (25,000 S1, 211,205 targets, 86,264 true pairs, seed=42):
    - L1 Recall: **95.6587%** | L2 Recall: **98.1128%** | L3 Final Recall: **99.9328%** (58 missed)
    - Avg Candidates: **4,338.4** | Med: 2,842 | P90: 10,741 | P95: 13,757 | P99: 19,006 | Max: 28,864 | 0-Cand: **0**
    - Total Candidates: 108,461,169 | Reduction: **97.9459%** | Total Time: **84.95s** | RAM: **720.72 MB**
    - Multi-Match Recall: **99.9329%** (Partials: 51 / 22,255 = 0.23%)
  - `50k_S1` (50,000 S1, 421,542 targets, 172,732 true pairs, seed=42):
    - L1 Recall: **95.6667%** | L2 Recall: **98.0704%** | L3 Final Recall: **99.9444%** (96 missed)
    - Avg Candidates: **8,459.2** | Med: 5,581 | P90: 20,706 | P95: 26,625 | P99: 37,041 | Max: 58,359 | 0-Cand: **0**
    - Total Candidates: 422,958,074 | Reduction: **97.9933%** | Total Time: **205.82s** | RAM: **637.88 MB**
    - Multi-Match Recall: **99.9435%** (Partials: 84 / 44,510 = 0.19%)
  - `France_Test_Sample` (5,000 S1, 50,000 targets from `test_source*.tsv`):
    - Detected legal suffixes: `sarl` (1,389), `sas` (1,020), `eurl` (338), `sa` (222), `sci` (168).
    - Avg Candidates: **3,247.9** | Med: 2,875 | P95: 7,099 | Max: 11,750 | 0-Cand: **0** | Reduction: **93.5042%**
- **Scaling Laws & Structural Observations:**
  - **Recall Stability:** Recall is remarkably stable across scales: L1 is consistently 95.63%–95.67%, L2 is 98.07%–98.11%, and Final L3 recall is **99.93%–99.94%**.
  - **Candidate Scaling Law:** Average candidates/S1 scale strictly linearly with the size of the target search space: $\text{Avg Candidates} \approx 0.0201 \times N_{\text{targets}}$. The candidate reduction ratio remains constant at **~97.99%**.
  - **Memory Boundedness:** Materializing all candidate sets in memory simultaneously causes heap exhaustion at 50k; however, **streaming evaluation (S1 by S1)** decouples memory from candidate volume, keeping peak RAM strictly bounded below **750 MB** regardless of scale.
  - **Zero-Candidate Queries:** Exactly 0 across all scales and splits.

---

## Experiment 8: Dynamic Frequency-Aware Channel F Benchmark
- **ID:** `E8` (`rare_location_channel.py`)
- **Date:** 2026-09-26 01:23:00
- **Hypothesis:** Replacing static binary 5% token deletion on Channel F with dynamic target-side rarity prioritization will prevent target starvation (recovering true pairs lost when records only possess city tokens like Mumbai or Delhi) while slashing candidate bloat.
- **Configurations Evaluated:**
  - `Ref_E6` (Static 5% IDF Cutoff): Recall **99.9275%** (25 missed) | Avg Cands: **1,698.0** | Med: 1,135 | P95: 5,321 | Recov E6 Cutoff: 0/9
  - `Policy_8A_Fallback5` (Tokens $\le 5\%$ or Rarest Fallback): Recall **99.9507%** (17 missed) | Avg Cands: **1,719.7** | Med: 1,149 | P95: 5,377 | Recov E6 Cutoff: **8/9**
  - `Policy_8A_Fallback3` (Tokens $\le 3\%$ or Rarest Fallback): Recall **99.9449%** (19 missed) | Avg Cands: **1,424.8** | Med: 971 | P95: 4,558 | Recov E6 Cutoff: **8/9**
  - `Policy_8B_Top1` (Strict Top-1 Rarest Token per Target): Recall **99.7883%** (73 missed) | Avg Cands: **899.7** | Med: 434 | P95: 3,695 | Recov E6 Cutoff: **8/9**
  - `Policy_8B_Top2` (Strict Top-2 Rarest Tokens per Target): Recall **99.9420%** (20 missed) | Avg Cands: **1,064.5** | Med: **588** | P95: **3,949** | Recov E6 Cutoff: **9/9 (100%)**
  - `Policy_8C_QueryAware`: Recall **99.9275%** (25 missed) | Avg Cands: **1,698.0** | Med: 1,135 | Recov E6 Cutoff: 0/9
- **Key Discoveries:**
  - `Policy_8B_Top2` delivers the ultimate Pareto frontier for Channel F: slashes candidate volume by **67.7% vs Baseline G** (from 3,294.6 down to **1,064.5 candidates/S1**, median **588**) while recovering **100% (9/9)** of all cutoff losses, trailing Baseline G by only a single true pair (34,461 vs 34,462).
  - Efficiency ratio for Top-2 is **3,568.6 candidates / recovered true pair** (vs 13,572 for E6 and 31,517 for unconstrained F).

---

## Experiment 9: Hard-Tail Recovery Channels Benchmark
- **ID:** `E9` (`tail_recovery_channels.py`)
- **Date:** 2026-09-26 01:28:00
- **Hypothesis:** Targeted architectural channels (2-letter business abbreviations, domain/handle stems, ordinal/leading-zero address normalization, and consonant collapse) will systematically recover the 19 Baseline-G misses without candidate explosion.
- **Configurations Evaluated:**
  - `E8_Top2_Base`: Recall **99.9420%** (20 missed) | Avg Cands: **1,064.5** | Med: 588 | Recov B19: 3/19
  - `+Enriched_Digits` (Ordinals & Leading Zeros): Recall **99.9565%** (15 missed) | Avg Cands: **1,579.1** | Med: 652 | Recov B19: 7/19
  - `+ShortNames_2Char` (Country-partitioned 2-letter tokens): Recall **99.9768%** (8 missed) | Avg Cands: **1,580.5** | Med: 654 | Recov B19: **14/19** (+7 TP for only +1.4 cands/S1, efficiency: 1,998 cands/TP!)
  - `+Domain_Nospace` (Domain stems, handles, nospace): Recall **99.9768%** (8 missed) | Avg Cands: **1,580.5** (+16 candidates total across whole dataset!)
  - `+Consonant_Collapse` (Double consonant collapse): Recall **99.9797%** (7 missed) | Avg Cands: **1,580.5** (+6 candidates total, recovers `Malone` vs `Mallone`!)
  - `Full_Tail_Recovery_Pipeline`: Recall **99.9797%** (34,474 / 34,481, **ONLY 7 MISSED**) | Avg Cands: **1,580.5** | Med: 654 | P95: 6,182 | Recov B19: **15/19 (78.9%)**
  - `Surgical_Tail_Pipeline` (Composite Enriched Digits + Loc): Recall **99.9710%** (34,471 / 34,481, **ONLY 10 MISSED**) | Avg Cands: **1,140.7** | Med: **606** | P95: **4,245** | Max: 10,247 | Recov B19: **12/19 (63.2%)**
- **Key Discoveries:**
  - **Surgical Tail Masterpiece:** `Surgical_Tail_Pipeline` achieves **99.9710% recall** with only **1,140.7 candidates/S1** (median **606**), cutting misses nearly in half vs Baseline G (10 vs 19) while slashing candidates by **-65.38%**!
  - **Full Tail Bound:** `Full_Tail_Recovery_Pipeline` pushes recall to an all-time record of **99.9797%** (34,474 / 34,481, only 7 missed pairs in the entire pilot dataset) with **1,580.5 candidates/S1** (-52.0% vs Baseline G).
  - **The 2-Letter Token Discovery:** S1 abbreviations like `TY`, `DK`, `TB`, `XF`, `JD`, `AL`, `IT` were completely dropped by the `length >= 3` rule. Adding country-partitioned 2-letter non-stopword tokens recovered all 7 true pairs for a negligible +1.4 candidates/S1.

---

## Experiment 10: Final Hard-Tail Blocking Investigation & Champion v2 Validation
- **ID:** `E10` (`final_tail_investigation.py`)
- **Date:** 2026-09-26 01:38:00
- **Hypothesis:** By analyzing the exact failure modes of the remaining 10 missed true pairs, ultra-targeted micro-signals (Consonant Trigram Prefix, US State + Digits, Alphanumeric Address Units) can recover additional true pairs with negligible candidate overhead.
- **Micro-Signals Evaluated:**
  - `Champion_v1_Base` (Surgical Tail Baseline): Recall **99.9710%** (10 missed) | Avg Cands: **1,140.7** | Med: 606 | P95: 4,245
  - `Signal_S1_Top4_Loc` (Channel F Top-4 rarest): Recall **99.9797%** (7 missed) | Avg Cands: **1,706.0** | +3 TP for +5.65M cands (**REJECTED**: 1.88M cands/TP bloat)
  - `Signal_S2_Consonant_Tri` (Consonant trigram prefix, freq <= 50): Recall **99.9768%** (8 missed) | Avg Cands: **1,144.3** | +2 TP for +36,299 cands (**ACCEPTED**: 18,149 cands/TP, recovers `Willow` vs `Wllrow` and `X & W Flexible` vs `X W & Fceeixble`)
  - `Signal_S3_Domain_Subwords` (Sorted tokens in domain stem): Recall **99.9710%** | Avg Cands: **1,140.7** | +0 TP (**REJECTED**)
  - `Signal_S4_State_Digit` (US State + Digits composite, freq <= 50): Recall **99.9768%** (8 missed) | Avg Cands: **1,141.1** | +2 TP for +3,756 cands (**ACCEPTED**: 1,878 cands/TP, recovers `Straight Edge` vs `Deltazeta` and `Castillo Empire` vs `empirecastillo.com`)
  - `Signal_S5_Alphanumeric_Unit` (Unit tokens like `3a`, freq <= 100): Recall **99.9739%** (9 missed) | Avg Cands: **1,141.0** | +1 TP for +2,976 cands (**ACCEPTED**: 2,976 cands/TP, recovers `My Consultancy` vs Kannada name at No.3A)
  - `Signal_S6_Short_Street_State` (2-char street + state): Recall **99.9710%** | +0 TP (**REJECTED**)
  - **`Champion_v2_Surgical` (Champion v1 + S2 + S4 + S5):**
    - Recall: **99.9855%** (34,476 / 34,481, **ONLY 5 MISSED PAIRS**)
    - Recovers **5 out of the 10 target misses (50%)**
    - Average Candidates / S1: **1,145.0** (slashed by **-65.25%** vs Baseline G's 3,294.6)
    - Median Candidates / S1: **609** (vs 2,621 in Baseline G)
    - P95 Candidates / S1: **4,250** (vs 9,555 in Baseline G)
    - Zero-Candidate S1s: **0**
    - Multi-match complete recall: **99.90%**
    - Marginal efficiency: **8,605.0 candidates per recovered true pair** (+5 TP for only +43,025 candidates total, +4.3 cands/S1).
- **Architectural Conclusion:**
  - With recall reaching **99.9855%** and candidate volume pruned by **65.25%**, the blocking problem is solved to statistical saturation. The remaining 5 misses consist of unmatchable edge cases (1-letter name with 0 address digits or complete cross-lingual mismatch). Blocking architecture is officially **FROZEN**.






