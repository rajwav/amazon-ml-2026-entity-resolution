# Blocking Experiments: Index & Research Overview

> **Amazon ML Challenge 2026 — Business Entity Resolution**  

---

## 1. Experimental Methodology & Rigor

All candidate generation experiments adhere to strict laboratory protocols:
1. **Identical Benchmark Data:** Evaluated on the persistent 10k S1 pilot (`pilot_s1.tsv`, `pilot_targets.tsv`, `pilot_ground_truth.tsv`), generated with `random.seed(42)`.
2. **Standardized Attribution Analysis:** Every experiment measures marginal true-pair recovery ($\Delta \text{TP}$), marginal candidate addition ($\Delta \text{Cands}$), and efficiency ($\Delta \text{Cands} / \Delta \text{TP}$).
3. **Multi-Match Integrity Checks:** Every configuration is validated against 1-to-many queries to ensure no partial recall degradation.
4. **Permanent Artifact Archival:** All code, outputs, metrics JSONs, and missed-pair lists are permanently archived in `experiments/blocking/` and `experiments/results/`.

---

## 2. Master Experiment Index

| ID | Experiment Title | Script | Primary Hypothesis / Focus | Recall | Avg Cands/S1 | Misses | Key Outcome | Status |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :--- | :---: |
| **EXP-00** | Baseline G Reproduction | `baseline_g.py` | Verify 99.94% recall reference baseline | 99.9449% | 3,294.6 | 19 | Baseline reproduced with 0 error | **BASELINE** |
| **EXP-01** | Rare Token / Target IDF | `rare_token.py` | Drop tokens >5% target pool frequency | 99.9043% | 1,409.7 | 33 | Slashed candidates by -57.2% | **ACCEPTED** |
| **EXP-02** | Composite Blocking Keys | `composite_keys.py` | Standalone composite keys vs C2 Union | 95.5686% | 113.8 | 1,528 | C2_Union achieves median 15 cands | **ACCEPTED (L1)** |
| **EXP-03** | Multi-Channel Progression | `multi_channel.py` | Incremental union attribution (B->F) | 98.0859% | 836.1 | 660 | BCDE established as core backbone | **ACCEPTED (L2)** |
| **EXP-04** | Indic Transliteration | `transliteration.py` | Transliteration ablation across scripts | 98.0859% | 836.1 | 660 | Discovered transliteration asymmetry | **ACCEPTED** |
| **EXP-05** | Adaptive Gating Policies | `adaptive_blocking.py` | Conditionally gate Channel F on S1 count | 98.3846% | 893.3 | 557 | Discovered Multi-Match Blindspot | **REJECTED** |
| **EXP-06** | Hierarchical Fallback | `hierarchical_pipeline.py` | 3-Tier cumulative pipeline (L1+L2+L3) | 99.9275% | 1,698.0 | 25 | -48.5% cands, 99.76% multi-match | **ACCEPTED** |
| **EXP-07** | Scalability & Robustness | `scalability_benchmark.py` | 10k -> 25k -> 50k scaling & France test | 99.9444% | 8,459.2 | 96 | Proved linear scaling, bounded RAM | **ACCEPTED** |
| **EXP-08** | Dynamic Frequency F | `rare_location_channel.py` | Target-side Top-2 rarest tokens | 99.9420% | 1,064.5 | 20 | Recovers 100% cutoff losses, -67.7% cands | **ACCEPTED (L3)** |
| **EXP-09** | Hard-Tail Recovery | `tail_recovery_channels.py` | 2-char tokens, domain stems, ordinals | 99.9710% | 1,140.7 | 10 | Recovered 12 baseline misses (-65.4% cands) | **CHAMPION V1** |
| **EXP-10** | Final Tail Investigation | `final_tail_investigation.py` | Consonant trigram, state digits, units | **99.9855%** | **1,145.0** | **5** | Slashed misses by 74%, 5 misses left | **CHAMPION V2** |
