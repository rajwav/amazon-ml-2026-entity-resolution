# Blocking Phase Documentation: Institutional Memory & Technical Record

> **Amazon ML Challenge 2026 — Business Entity Resolution**  
> **Phase:** Candidate Generation / Blocking  
> **Status:** **FROZEN** (Champion v2 Surgical Validated)  
> **Date of Freeze:** 2026-09-26  

---

## 1. Executive Summary

This documentation repository serves as the definitive institutional memory and technical manual for the **Candidate Generation (Blocking)** phase of the Amazon ML Challenge 2026 Business Entity Resolution system.

Our mandate was to solve the fundamental trade-off of large-scale Entity Resolution: **achieving near-perfect true-pair recall ($\ge 99.9\%$) while aggressively pruning candidate volume** from the $O(N \times M)$ Cartesian search space ($2.2\text{M} \times 10.3\text{M} = 22.7\text{ trillion pairs}$), strictly operating under an 8 GB consumer RAM ceiling.

Over 11 progressive experimental iterations (Baseline G reproduction through Experiments 1–10), we designed, benchmarked, and stress-tested a multi-level cumulative union blocker:
- **Starting Baseline (Baseline G):** 99.9449% recall | 3,294.6 avg candidates/S1 | 19 misses.
- **Champion Architecture (Champion v2 Surgical):** **99.9855% recall** | **1,145.0 avg candidates/S1** | **ONLY 5 misses**.
- **Net Optimization Impact:** **-65.25% candidate volume reduction** (-2,150 candidates/S1), slashing missed pairs by **-73.68%** (halved twice), with median candidates dropping by **-76.76%** (from 2,621 to 609), zero zero-candidate queries, and peak RAM bounded under **805 MB**.

Blocking is officially **FROZEN**. The project has transitioned to **Phase 3: Pairwise Feature Engineering & Classification**.

---

## 2. Fast Navigation & Document Map

```
blocking/documentation/
├── README.md                                  # [THIS FILE] Fast orientation & executive overview
├── BLOCKING_PHASE_MASTER.md                   # Single master document containing the complete end-to-end journey
├── 00_PROJECT_CONTEXT.md                      # Problem formulation, business motivation, constraints
├── 01_DATASET_AND_GROUND_TRUTH.md             # Data statistics, distributions, invariants, pilot specs
├── 02_BLOCKING_OBJECTIVE.md                   # Theoretical framing, recall as hard constraint, metrics
├── 03_ARCHITECTURE_EVOLUTION.md               # Visual and architectural progression from Baseline G to Champion v2
│
├── experiments/                               # Detailed logs for every single experiment
│   ├── README.md                              # Experiment methodology & navigation guide
│   ├── EXPERIMENT_INDEX.md                    # Master tabular matrix of all 11 experiments
│   ├── EXP_00_BASELINE_G.md                   # Baseline G reproduction and verification
│   ├── EXP_01_RARE_TOKEN_IDF.md               # Rare token / target IDF cutoff sweeps
│   ├── EXP_02_COMPOSITE_KEYS.md               # 5 composite key combinations & C2_Union_All
│   ├── EXP_03_MULTI_CHANNEL_PROGRESSION.md    # Incremental union (B -> BC -> BCD -> BCDE -> BCDEF)
│   ├── EXP_04_INDIC_TRANSLITERATION.md        # Transliteration asymmetry & selective script routing
│   ├── EXP_05_ADAPTIVE_BLOCKING.md            # S1-level gating benchmark & multi-match blindspot
│   ├── EXP_06_HIERARCHICAL_PIPELINE.md        # 3-Tier cumulative fallback pipeline
│   ├── EXP_07_SCALABILITY_ROBUSTNESS.md       # 10k -> 25k -> 50k scaling laws & France test split
│   ├── EXP_08_DYNAMIC_FREQUENCY_CHANNEL_F.md  # Target-side Top-2 rarest token prioritization
│   ├── EXP_09_HARD_TAIL_RECOVERY.md           # 2-letter tokens, domain stems, ordinal normalization
│   └── EXP_10_FINAL_HARD_TAIL_INVESTIGATION.md# Final 10-miss autopsy & Champion v2 validation
│
├── failure_analysis/                          # Ground-truth failure analysis & missed-pair autopsies
│   ├── README.md                              # Failure taxonomy and overview
│   ├── MISSED_PAIR_HISTORY.md                 # Chronological history of every missed true pair
│   └── ROOT_CAUSE_ANALYSIS.md                 # 8 primary failure modes and their algorithmic solutions
│
├── decisions/                                 # Engineering decision records (ADRs)
│   ├── README.md                              # Decision framework overview
│   ├── DECISION_LOG.md                        # Chronological record of Decisions 1 through 13
│   ├── ACCEPTED_CHANNELS.md                   # Comprehensive rationale for every accepted feature
│   └── REJECTED_CHANNELS.md                   # Rigorous post-mortems for rejected approaches
│
├── champion/                                  # Champion architecture specifications
│   ├── README.md                              # Champion architecture overview
│   ├── CHAMPION_V1.md                         # Surgical Tail Pipeline (Exp 9)
│   ├── CHAMPION_V2.md                         # Champion v2 Surgical (Exp 10)
│   ├── CHAMPION_V2_SPEC.md                    # Exact algorithmic specification & pseudocode
│   └── FREEZE_RECORD.md                       # Formal sign-off and freeze declaration
│
├── production/                                # Production scaling, deployment, and validation
│   ├── README.md                              # Production operations guide
│   ├── FULL_SCALE_BLOCKING_PLAN.md            # Plan for full test set (1.7M S1 x 10.0M targets)
│   ├── RUNBOOK.md                             # Step-by-step execution, chunking, and worker runbook
│   ├── VALIDATION_CHECKLIST.md                # 10-point audit gate before handoff to matcher
│   └── OUTPUT_CONTRACT.md                     # Schema, storage format, and TSV contract
│
└── appendices/                                # Technical appendices & reference material
    ├── README.md                              # Appendix index
    ├── METRICS_REFERENCE.md                   # Exact definitions and formulas for all metrics
    ├── TERMINOLOGY.md                         # Project glossary and domain concepts
    ├── EXPERIMENT_TEMPLATE.md                 # Standard template for future blocking research
    └── ARTIFACT_INDEX.md                      # Catalog of all code, TSVs, JSONs, and data files
```

---

## 3. Quick Performance Summary

| Architecture / Milestone | Date | True-Pair Recall | Recalled Pairs | Missed Pairs | Avg Candidates / S1 | Median | P95 | Max | Candidate Reduction vs Cartesian | Peak RAM |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Cartesian Search Space** | - | 100.0% | 34,481 | 0 | 84,481.0 | 84,481 | 84,481 | 84,481 | 0.00% | OOM |
| **Baseline G (Reproduction)** | 2026-09-25 | 99.9449% | 34,462 | 19 | 3,294.6 | 2,621 | 9,555 | 18,372 | 96.10% | 374 MB |
| **Exp 1: Target IDF Cutoff (>5%)** | 2026-09-25 | 99.9043% | 34,448 | 33 | 1,409.7 | 967 | 4,524 | 9,844 | 98.33% | 365 MB |
| **Exp 2: Composite Sieve (C2)** | 2026-09-25 | 95.5686% | 32,953 | 1,528 | 113.8 | 15 | 637 | 3,115 | 99.87% | 365 MB |
| **Exp 3: Core Backbone (BCDE)** | 2026-09-25 | 98.0859% | 33,821 | 660 | 836.1 | 377 | 3,594 | 8,976 | 99.01% | 375 MB |
| **Exp 4: Selective Transliteration** | 2026-09-25 | 98.0859% | 33,821 | 660 | 836.1 | 377 | 3,594 | 8,976 | 99.01% | 380 MB |
| **Exp 6: 3-Tier Pipeline ($L1 \cup L2 \cup L3$)** | 2026-09-25 | 99.9275% | 34,456 | 25 | 1,698.0 | 1,135 | 5,321 | 10,904 | 97.99% | 708 MB |
| **Exp 8: Dynamic F (Top-2 Rarest)** | 2026-09-26 | 99.9420% | 34,461 | 20 | 1,064.5 | 588 | 3,949 | 9,239 | 98.74% | 862 MB |
| **Exp 9: Champion v1 (Surgical Tail)** | 2026-09-26 | 99.9710% | 34,471 | 10 | 1,140.7 | 606 | 4,245 | 10,247 | 98.65% | 887 MB |
| **Exp 10: Champion v2 (Surgical)** | **2026-09-26** | **99.9855%** | **34,476** | **5** | **1,145.0** | **609** | **4,250** | **10,247** | **98.64%** | **802 MB** |

---

## 4. Key Lessons & Breakthroughs

1. **The Multi-Match Gating Blindspot (Experiment 5):**  
   In 1-to-many Entity Resolution, an anchor query can match an easy target (exact name) while having another corrupted target (matching only on locality). Suppressing broad channels based on query-level candidate counts ($k \ge T$) caused an artificial recall ceiling at ~98.4%. Blocking channels must be gated via **target-side token frequency**, never query-level suppression.
2. **The Transliteration Asymmetry Principle (Experiment 4):**  
   Transliterating non-Latin scripts (Devanagari, Kannada, Tamil, Bengali) into Latin on names recovered 155 true pairs with almost zero candidate cost (+4.9 candidates/S1). Conversely, transliterating generic address tokens generated 4.33 million non-match candidates. Rule: *Transliterate names and digits; keep location tokens native.*
3. **Dynamic Target-Side Representation Bounding (Experiment 8):**  
   Global binary IDF cutoffs starves entities whose only geographic information consists of major cities (e.g., Mumbai, Delhi). By sorting each target's location tokens by frequency and indexing strictly its **Top-2 rarest tokens**, 100% of cutoff losses were recovered while eliminating 67.7% of Channel F candidates.
4. **The 2-Letter Abbreviation Discovery (Experiment 9):**  
   Filtering tokens with `length >= 3` silently discarded genuine business acronyms (`TY`, `DK`, `TB`, `XF`, `JD`, `AL`, `IT`). Standalone 2-letter tokens partitioned by country are ultra-discriminative (e.g., `ty` in the US has an index size of only 5 targets) and recovered 7 baseline misses for only +1.4 candidates/S1.
5. **Streaming Evaluation Decouples RAM from Volume (Experiment 7):**  
   Materializing 422.9M candidate pairs in Python dictionaries causes memory exhaustion on consumer hardware. Generating and evaluating candidates in a streaming loop keeps peak RAM bounded under **805 MB** even across 50,000 queries.
