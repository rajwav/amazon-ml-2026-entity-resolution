# Complete Project Artifact & Repository Inventory

This index registers all code scripts, metric JSON files, evaluation TSVs, and documentation artifacts comprising the candidate generation phase.

---

## 1. Source Code Scripts (`experiments/blocking/`)

| Script Path | Description / Purpose |
|:---|:---|
| [`common.py`](../../../experiments/blocking/common.py) | Core normalization functions, Indic transliteration pipeline, metrics evaluators, and timers. |
| [`setup_pilot_data.py`](../../../experiments/blocking/setup_pilot_data.py) | Generates the stratified 10k $S1$ benchmark pilot with 84,481 target records and 34,481 ground truth pairs (`seed=42`). |
| [`baseline_g.py`](../../../experiments/blocking/baseline_g.py) | Evaluates Baseline G (unfiltered 5-channel union control). |
| [`rare_token.py`](../../../experiments/blocking/rare_token.py) | Evaluates Experiment 01 (global IDF / rare-token filtering thresholds). |
| [`composite_keys.py`](../../../experiments/blocking/composite_keys.py) | Evaluates Experiment 02 (composite conjunction blocking keys and composite unions). |
| [`analyze_exp2_complement.py`](../../../experiments/blocking/analyze_exp2_complement.py) | Automated error attribution script analyzing the 1,528 pairs missed by composite keys. |
| [`multi_channel.py`](../../../experiments/blocking/multi_channel.py) | Evaluates Experiment 03 (5-step incremental channel progression: $B \to B+C \dots \to B+C+D+E+F$). |
| [`transliteration.py`](../../../experiments/blocking/transliteration.py) | Evaluates Experiment 04 ($2 \times 2$ factorial Indic script transliteration ablation). |
| [`adaptive_blocking.py`](../../../experiments/blocking/adaptive_blocking.py) | Evaluates Experiment 05 (10 adaptive $S1$-level candidate volume gating policies). |
| [`hierarchical_pipeline.py`](../../../experiments/blocking/hierarchical_pipeline.py) | Evaluates Experiment 06 (3-tier hierarchical multi-stage candidate generator / Champion v1). |
| [`scalability_benchmark.py`](../../../experiments/blocking/scalability_benchmark.py) | Evaluates Experiment 07 (progressive scale benchmark: 10k $\to$ 25k $\to$ 50k queries). |
| [`rare_location_channel.py`](../../../experiments/blocking/rare_location_channel.py) | Evaluates Experiment 08 (dynamic target-side frequency and Top-2 rarest location tokens). |
| [`tail_recovery_channels.py`](../../../experiments/blocking/tail_recovery_channels.py) | Evaluates Experiment 09 (four surgical tail channels for hard-tail recovery). |
| [`final_tail_investigation.py`](../../../experiments/blocking/final_tail_investigation.py) | Evaluates Experiment 10 (micro-signals S1 through S6, crowns Champion v2 Surgical). |

---

## 2. Experimental Metric JSON Files (`experiments/results/`)

| Metric JSON Path | Experiment / Description |
|:---|:---|
| [`baseline_g_metrics.json`](../../../experiments/results/baseline_g_metrics.json) | Baseline G control metrics (99.9449% recall, 3,294.6 cands). |
| [`exp1_rare_token_metrics.json`](../../../experiments/results/exp1_rare_token_metrics.json) | Rare token IDF cutoff evaluations (No filtering vs 5% vs 2% vs 1%). |
| [`exp2_composite_keys_metrics.json`](../../../experiments/results/exp2_composite_keys_metrics.json) | Performance of 5 individual composite keys and 3 composite unions. |
| [`exp3_incremental_union_metrics.json`](../../../experiments/results/exp3_incremental_union_metrics.json) | Cumulative 5-stage channel progression and marginal true pair counts. |
| [`exp4_transliteration_metrics.json`](../../../experiments/results/exp4_transliteration_metrics.json) | Factorial metrics for Indic transliteration on/off across backbone and full baseline. |
| [`exp5_adaptive_metrics.json`](../../../experiments/results/exp5_adaptive_metrics.json) | Metrics for 10 adaptive query gating policies (Policies A, B1-B4, C1-C3, D1-D3). |
| [`exp6_hierarchical_pipeline_metrics.json`](../../../experiments/results/exp6_hierarchical_pipeline_metrics.json) | Performance of 3-tier hierarchical pipeline tiers (Level 1, L1 $\cup$ L2, L1 $\cup$ L2 $\cup$ L3). |
| [`exp7_scalability_metrics.json`](../../../experiments/results/exp7_scalability_metrics.json) | Scalability metrics across 10k, 25k, and 50k query benchmarks. |
| [`exp8_rare_location_metrics.json`](../../../experiments/results/exp8_rare_location_metrics.json) | Dynamic location Channel F evaluations (Top-1, Top-2, Fallback-3, Fallback-5). |
| [`exp9_tail_recovery_metrics.json`](../../../experiments/results/exp9_tail_recovery_metrics.json) | Hard-tail recovery metrics across individual channels and surgical pipeline. |
| [`exp10_final_tail_metrics.json`](../../../experiments/results/exp10_final_tail_metrics.json) | Micro-signal metrics (S1-S6) and official Champion v2 Surgical benchmark. |

---

## 3. Evaluation & Diagnostic TSV Files (`experiments/results/`)

| TSV Artifact Path | Description |
|:---|:---|
| [`baseline_g_missed_pairs.tsv`](../../../experiments/results/baseline_g_missed_pairs.tsv) | Full record dump of the 19 historic missed true pairs in Baseline G. |
| [`exp1_newly_lost_pairs.tsv`](../../../experiments/results/exp1_newly_lost_pairs.tsv) | 14 true pairs newly lost when applying 5% IDF cutoff in Experiment 01. |
| [`exp2_complement_analysis.tsv`](../../../experiments/results/exp2_complement_analysis.tsv) | Deep complement analysis of the 1,528 pairs missed by composite keys. |
| [`exp4_transliteration_recovered_pairs.tsv`](../../../experiments/results/exp4_transliteration_recovered_pairs.tsv) | 146 Indian entity pairs recovered by Indic script transliteration. |
| [`exp5_policy_comparison.tsv`](../../../experiments/results/exp5_policy_comparison.tsv) | Tabular comparison of all 10 adaptive gating policies in Experiment 05. |
| [`exp5_backbone_660_analysis.tsv`](../../../experiments/results/exp5_backbone_660_analysis.tsv) | Forensic failure breakdown of the 660 tail pairs missed by $B+C+D+E$. |
| [`exp6_pipeline_comparison.tsv`](../../../experiments/results/exp6_pipeline_comparison.tsv) | Tabular comparison of Champion v1 hierarchical tiers. |
| [`exp6_remaining_25_misses.tsv`](../../../experiments/results/exp6_remaining_25_misses.tsv) | Full record dump of the 25 pairs missed by Champion v1. |
| [`exp7_scalability_comparison.tsv`](../../../experiments/results/exp7_scalability_comparison.tsv) | Scaling comparison across 10k, 25k, and 50k queries. |
| [`exp8_rare_location_comparison.tsv`](../../../experiments/results/exp8_rare_location_comparison.tsv) | Comparison of dynamic location policies in Experiment 08. |
| [`exp9_tail_recovery_comparison.tsv`](../../../experiments/results/exp9_tail_recovery_comparison.tsv) | Channel comparison for tail recovery in Experiment 09. |
| [`exp9_final_missed_pairs.tsv`](../../../experiments/results/exp9_final_missed_pairs.tsv) | Record dump of the 10 pairs remaining missed after Experiment 09. |
| [`exp10_final_tail_investigation.tsv`](../../../experiments/results/exp10_final_tail_investigation.tsv) | Forensic evaluation of micro-signals against the 10 stubborn misses. |

---

## 4. Documentation Suite (`blocking/documentation/`)

| Document | Primary Content |
|:---|:---|
| [`README.md`](../README.md) | Documentation suite homepage, navigation, and executive scorecard. |
| [`BLOCKING_PHASE_MASTER.md`](../BLOCKING_PHASE_MASTER.md) | Definitive 21-section master technical document synthesizing the entire phase. |
| [`00_PROJECT_CONTEXT.md`](../00_PROJECT_CONTEXT.md) | Business problem, constraints, evaluation metric, and phase hand-off. |
| [`01_DATASET_AND_GROUND_TRUTH.md`](../01_DATASET_AND_GROUND_TRUTH.md) | Dataset inventory (26.4M rows), 1-to-many cardinality, intra-country invariant. |
| [`02_BLOCKING_OBJECTIVE.md`](../02_BLOCKING_OBJECTIVE.md) | Mathematical framing, recall as hard constraint, trade-off optimization. |
| [`03_ARCHITECTURE_EVOLUTION.md`](../03_ARCHITECTURE_EVOLUTION.md) | Five-epoch architectural progression from Baseline G to Champion v2. |
| [`experiments/`](../experiments) | Complete directory of all 11 individual experiment reports (`EXP_00` to `EXP_10`). |
| [`failure_analysis/`](../failure_analysis) | Historical missed pair trace and 8-part root cause taxonomy. |
| [`decisions/`](../decisions) | ADR log (ADR-01 to ADR-13), accepted channel catalog, and rejected proposals catalog. |
| [`champion/`](../champion) | Champion v1 retrospective, Champion v2 overview, technical specification, and freeze record. |
| [`production/`](../production) | Full-scale blocking plan (2.23M queries), runbook, validation checklist, and output contract. |
| [`appendices/`](.) | Mathematical metrics reference, terminology glossary, experiment template, and artifact index. |
