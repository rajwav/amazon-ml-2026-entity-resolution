# 08 VALIDATION PROTOCOL: EXPERIMENTAL ACCEPTANCE GATE

Before any experiment result is accepted into the project memory or reported as an improvement, it must pass this 10-point checklist:

```
[ ] 1. Identical Dataset: Reads exactly experiments/data/pilot_s1.tsv (10,000 S1 records).
[ ] 2. Identical Search Pool: Evaluates against experiments/data/pilot_targets.tsv (84,481 target records).
[ ] 3. Identical Ground Truth: Evaluates against experiments/data/pilot_ground_truth.tsv (34,481 true pairs).
[ ] 4. Zero Data Leakage: Evaluates using only training files; zero test ground truth or external lookup.
[ ] 5. Baseline Grounding: Compares directly against the exact baseline_g_candidates.json.
[ ] 6. True-Pair Metric: Recall is computed strictly as (recalled_true_pairs / 34,481).
[ ] 7. Candidate Deduplication: Candidate counts per S1 entity are deduplicated (set union) before counting.
[ ] 8. Performance Profiled: Exact execution runtime and peak RAM are logged.
[ ] 9. Missed Pairs Analyzed: Newly lost true pairs compared to Baseline G are logged with root-cause categorization.
[ ] 10. Reproducibility: Re-running the script produces identical metrics.
```

If any check fails, the experiment is invalid.
