# 11 SESSION HANDOFF & CONTINUITY BRIEF

*Purpose: Enables any agent, engineer, or new session to instantly resume work with zero state loss or hallucination.*

## 1. What Has Been Completed
- **Dataset Exploration:** All 7 files (26.4M rows, 2.4 GB) profiled. Intra-country invariant (100.0%) and 1-to-many disjoint mapping invariant verified.
- **Preprocessing Module:** Built `src/preprocessing/normalization.py` with country-independent cleaning, legal suffix extraction, address standardization, and offline Indic transliteration.
- **Benchmark Data Setup:** Created persistent 10k S1 pilot in `experiments/data/` (`pilot_s1.tsv`, `pilot_targets.tsv`, `pilot_ground_truth.tsv`, `pilot_metadata.json`).
- **Baseline G Reproduction:** `Baseline_G` reproduced with 0 discrepancy: **99.9449% recall** (34,462/34,481), **19 missed**, **3,294.6 avg candidates**, **0 zero-candidate S1s**. Candidate sets saved to `experiments/data/baseline_g_candidates.json`.
- **Experiment 1 (Rare Token / IDF Filtering):** Slashed candidates by 57.2% with 99.90% recall (`E1_B` 5% IDF cutoff).
- **Experiment 2 (Composite Keys):** Evaluated 5 composite keys. Discovered `C2_Union_All` provides an ultra-compact first-tier sieve (**95.57% recall, median 15 candidates**).
- **Experiment 3 (Multi-Channel Incremental Union):** Identified $B+C+D+E$ as the core high-efficiency backbone (**98.09% recall, 836.1 cands/S1**).
- **Experiment 4 (Indic Script Transliteration Ablation):** Established **Selective Transliteration** (Names/Digits ON recovers 155 genuine true pairs with +4.9 cands/S1; location tokens OFF avoids 4.3M candidate bloat).
- **Experiment 5 (Adaptive / Record-Quality Blocking):** Discovered the **Multi-Match Gating Blindspot** (92.4% of Channel F true pairs belong to multi-match queries where S1 already found another target in BCDE; query-level candidate suppression caps recall at ~98.4%).
- **Experiment 6 (Hierarchical Fallback Blocking Pipeline):** Integrated 3-Tier Cumulative Union ($L1 \cup L2 \cup L3$): 99.9275% recall, -48.46% candidate reduction, 99.76% multi-match integrity.
- **Experiment 7 (Scalability & Robustness Testing):** Progressively benchmarked across 10k, 25k, and 50k S1 queries and French test records:
  - Validated rock-solid recall stability: **99.93% to 99.94%** across all scales.
  - Confirmed 0 zero-candidate S1s.
  - Proved streaming evaluation decouples RAM from candidate count, keeping peak memory strictly bounded below **725 MB** for 422.9M candidates.
  - Validated French legal suffix extraction and zero-candidate immunity on actual test data.

## 2. Directory Tree of Verified Artifacts
```
experiments/
├── blocking/
│   ├── setup_pilot_data.py               # Generates stratified 10k pilot
│   ├── common.py                         # Reusable metrics, loader, evaluation
│   ├── baseline_g.py                     # Baseline G control
│   ├── rare_token.py                     # Exp 1 IDF filtering
│   ├── composite_keys.py                 # Exp 2 Composite keys
│   ├── analyze_exp2_complement.py        # Exp 2 error/complement analysis
│   ├── multi_channel.py                  # Exp 3 Channel progression
│   ├── transliteration.py                # Exp 4 Transliteration ablation
│   ├── adaptive_blocking.py              # Exp 5 Quality-aware gating
│   ├── hierarchical_pipeline.py          # Exp 6 Integrated 3-tier pipeline
│   ├── scalability_benchmark.py          # Exp 7 Progressive scaling benchmark
│   ├── rare_location_channel.py          # Exp 8 Dynamic frequency-aware Channel F
│   ├── tail_recovery_channels.py         # Exp 9 Hard-tail recovery channels
│   └── final_tail_investigation.py       # Exp 10 Final hard-tail & Champion v2
├── data/
│   ├── pilot_s1.tsv                      # 10,000 S1 records
│   ├── pilot_targets.tsv                 # 84,481 target records
│   ├── pilot_ground_truth.tsv            # 34,481 true pairs
│   ├── pilot_metadata.json               # Pilot dataset specs
│   └── baseline_g_candidates.json        # Exact Baseline G candidate sets
└── results/
    ├── baseline_g_metrics.json           # Baseline G metrics
    ├── baseline_g_missed_pairs.tsv       # The 19 baseline missed pairs
    ├── exp1_rare_token_metrics.json      # Exp 1 IDF cutoff metrics
    ├── exp2_composite_metrics.json       # Exp 2 metrics
    ├── exp2_complement_analysis.tsv      # Exp 2 complement analysis
    ├── exp3_multichannel_metrics.json    # Exp 3 metrics
    ├── exp4_transliteration_metrics.json # Exp 4 metrics
    ├── exp4_transliteration_recovered_pairs.tsv # Exp 4 cross-script recoveries
    ├── exp5_adaptive_metrics.json        # Exp 5 metrics
    ├── exp5_policy_comparison.tsv        # Exp 5 policy comparison table
    ├── exp5_backbone_660_analysis.tsv    # Exp 5 660-miss breakdown
    ├── exp6_hierarchical_pipeline_metrics.json # Exp 6 3-tier pipeline metrics
    ├── exp6_pipeline_comparison.tsv      # Exp 6 comparison table
    ├── exp6_remaining_25_misses.tsv      # Exp 6 remaining 25 misses
    ├── exp7_scalability_metrics.json     # Exp 7 scaling metrics (10k, 25k, 50k, FR)
    ├── exp7_scalability_comparison.tsv   # Exp 7 scaling comparison TSV
    ├── exp8_rare_location_metrics.json   # Exp 8 dynamic Channel F metrics
    ├── exp8_rare_location_comparison.tsv # Exp 8 comparison TSV
    ├── exp9_tail_recovery_metrics.json   # Exp 9 tail recovery metrics
    ├── exp9_tail_recovery_comparison.tsv # Exp 9 comparison TSV
    ├── exp9_final_missed_pairs.tsv       # 10 remaining misses
    ├── exp10_final_tail_investigation.tsv # Exp 10 micro-signal evaluation
    └── exp10_final_tail_metrics.json     # Exp 10 metrics
```

## 3. What Must NOT Be Changed
- The 10,000 S1 pilot entities in `experiments/data/pilot_s1.tsv`.
- The target records in `experiments/data/pilot_targets.tsv`.
- The ground-truth true pairs in `experiments/data/pilot_ground_truth.tsv`.
- Baseline G candidates in `experiments/data/baseline_g_candidates.json`.

## 4. Next Immediate Action
- Move to **Phase 3: Feature Engineering & Model Training (Ranking/Matching)**. Build fast pairwise similarity features on the generated candidates to prepare for precision-heavy $F_{0.5}$ classification.

