# EXPERIMENT INDEX: COMPLETE MATRIX OF BLOCKING EXPERIMENTS

> **Amazon ML Challenge 2026 — Business Entity Resolution**  

---

## 1. Matrix of Experiments

| Experiment ID | Script File | Benchmark Split | Recall (%) | Recalled Pairs | Missed Pairs | Avg Cands / S1 | Median | P95 | Max | Zero Cands | Marginal Cands / TP | Decision |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **EXP-00: Baseline G** | `baseline_g.py` | 10k Pilot | 99.9449% | 34,462 | 19 | 3,294.6 | 2,621 | 9,555 | 18,372 | 0 | Baseline | **BASELINE** |
| **EXP-01: IDF Filtering (E1_B)** | `rare_token.py` | 10k Pilot | 99.9043% | 34,448 | 33 | 1,409.7 | 967 | 4,524 | 9,844 | 0 | -18.8M cands / -14 TP | **ACCEPTED** |
| **EXP-02: Composite Keys (C2)** | `composite_keys.py` | 10k Pilot | 95.5686% | 32,953 | 1,528 | 113.8 | 15 | 637 | 3,115 | 116 | 31.6 cands / TP | **ACCEPTED (L1)** |
| **EXP-03: Backbone (BCDE)** | `multi_channel.py` | 10k Pilot | 98.0859% | 33,821 | 660 | 836.1 | 377 | 3,594 | 8,976 | 1 | 8,630.9 cands / TP | **ACCEPTED (L2)** |
| **EXP-04: Selective Translit** | `transliteration.py` | 10k Pilot | 98.0859% | 33,821 | 660 | 836.1 | 377 | 3,594 | 8,976 | 1 | +4.9 cands / +155 TP | **ACCEPTED** |
| **EXP-05: Adaptive Gating** | `adaptive_blocking.py` | 10k Pilot | 98.3846% | 33,924 | 557 | 893.3 | 412 | 3,820 | 9,145 | 0 | Multi-match capped | **REJECTED** |
| **EXP-06: 3-Tier Pipeline** | `hierarchical_pipeline.py` | 10k Pilot | 99.9275% | 34,456 | 25 | 1,698.0 | 1,135 | 5,321 | 10,904 | 0 | 13,572.5 cands / TP | **ACCEPTED** |
| **EXP-07: Scalability (50k)** | `scalability_benchmark.py` | 50k Sample | 99.9444% | 172,636 | 96 | 8,459.2 | 5,581 | 26,625 | 58,359 | 0 | Linear scaling law | **ACCEPTED** |
| **EXP-08: Dynamic F (Top-2)** | `rare_location_channel.py` | 10k Pilot | 99.9420% | 34,461 | 20 | 1,064.5 | 588 | 3,949 | 9,239 | 0 | 3,568.6 cands / TP | **ACCEPTED (L3)** |
| **EXP-09: Champion v1** | `tail_recovery_channels.py` | 10k Pilot | 99.9710% | 34,471 | 10 | 1,140.7 | 606 | 4,245 | 10,247 | 0 | 76,214.5 cands / TP | **CHAMPION V1** |
| **EXP-10: Champion v2** | `final_tail_investigation.py` | 10k Pilot | **99.9855%** | **34,476** | **5** | **1,145.0** | **609** | **4,250** | **10,247** | **0** | **8,605.0 cands / TP** | **CHAMPION V2** |

---

## 2. Cross-Experiment Chronological Links

1. **Baseline G $\rightarrow$ Exp 1:** Identified that Channel F was responsible for 74.6% of candidate bloat; tested global IDF thresholds.
2. **Exp 1 $\rightarrow$ Exp 2:** Recognized that individual channels were either too broad or too narrow; explored composite keys ($C2$).
3. **Exp 2 $\rightarrow$ Exp 3:** Deconstructed full multi-channel union to establish $BCDE$ backbone.
4. **Exp 3 $\rightarrow$ Exp 4:** Discovered Indic script loss in names; implemented and ablated native transliteration.
5. **Exp 4 $\rightarrow$ Exp 5:** Attempted query-level candidate suppression to control Channel F; discovered Multi-Match Blindspot.
6. **Exp 5 $\rightarrow$ Exp 6:** Formulated 3-Tier Cumulative Union ($L1 \cup L2 \cup L3$) with unsuppressed query evaluation.
7. **Exp 6 $\rightarrow$ Exp 7:** Scaled 3-tier pipeline from 10k to 50k and French test data; discovered memory limit and instituted streaming evaluation.
8. **Exp 7 $\rightarrow$ Exp 8:** Addressed the 9 IDF cutoff losses from Exp 6 by inventing Target-Side Top-2 Rarest Token Indexing.
9. **Exp 8 $\rightarrow$ Exp 9:** Solved the 19 Baseline-G misses by introducing 2-letter tokens, domain stems, and ordinal normalization.
10. **Exp 9 $\rightarrow$ Exp 10:** Conducted root-cause autopsy on final 10 misses; added consonant trigrams, state digits, and units to achieve Champion v2.
