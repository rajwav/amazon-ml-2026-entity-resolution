"""
Step 1: Reproduce Strategy G Baseline.
Validates exact replication of the control baseline:
- Recall ≈ 99.94%
- Recalled pairs = 34,462
- Missed pairs = 19
- Avg candidates/S1 ≈ 3,294.6
- Median ≈ 2,621
- P95 ≈ 9,555
- Max ≈ 18,372
- Zero-candidate S1 = 0
Saves candidate sets to experiments/data/baseline_g_candidates.json.
"""

import os
import sys
import time
import json
import collections
from typing import Dict, Set

sys.path.append('.')
from experiments.blocking.common import (
    load_pilot_raw,
    get_normalized_records,
    evaluate_blocking_candidates,
    get_ram_mb,
    RESULTS_DIR,
    DATA_DIR
)

def run_baseline_g():
    t_start = time.time()
    ram_init = get_ram_mb()
    print("=================================================================")
    print("STEP 1: REPRODUCING STRATEGY G BASELINE")
    print("=================================================================")
    print(f"Initial RAM: {ram_init:.2f} MB")

    # 1. Load pre-cached pilot data
    t0 = time.time()
    s1_raw, target_raw, gt_matches, total_true_pairs = load_pilot_raw()
    print(f"Loaded raw pilot data in {time.time()-t0:.2f}s: {len(s1_raw)} S1s, {len(target_raw)} Targets, {total_true_pairs} True Pairs")

    # 2. Normalize records
    t0 = time.time()
    s1_norm, target_norm = get_normalized_records(s1_raw, target_raw)
    print(f"Normalized records in {time.time()-t0:.2f}s: {len(s1_norm)} S1s, {len(target_norm)} Targets")
    print(f"RAM after normalization: {get_ram_mb():.2f} MB")

    # 3. Build Inverted Indexes for Strategy G
    t0 = time.time()
    idx_exact_name = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_sig_token  = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_prefix4    = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_digits     = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_loc_token  = collections.defaultdict(lambda: collections.defaultdict(list))

    for eid, feat in target_norm.items():
        c = feat['country']
        if feat['core']:
            idx_exact_name[c][feat['core']].append(eid)
        for tok in feat['tokens']:
            idx_sig_token[c][tok].append(eid)
        if feat['prefix4']:
            idx_prefix4[c][feat['prefix4']].append(eid)
        for dig in feat['digits']:
            idx_digits[c][dig].append(eid)
        for loc in feat['loc_tokens']:
            idx_loc_token[c][loc].append(eid)

    print(f"Built inverted indexes in {time.time()-t0:.2f}s")
    print(f"RAM after indexing: {get_ram_mb():.2f} MB")

    # 4. Generate Candidates per S1 (Strategy G = B + C + D + E + F)
    t0 = time.time()
    s1_candidates: Dict[str, Set[str]] = {}

    for s1_id, feat in s1_norm.items():
        c = feat['country']
        cands = set()

        # B: Exact core name
        if feat['core'] and feat['core'] in idx_exact_name[c]:
            cands.update(idx_exact_name[c][feat['core']])

        # C: Significant name tokens
        for tok in feat['tokens']:
            if tok in idx_sig_token[c]:
                cands.update(idx_sig_token[c][tok])

        # D: 4-char prefix
        if feat['prefix4'] and feat['prefix4'] in idx_prefix4[c]:
            cands.update(idx_prefix4[c][feat['prefix4']])

        # E: Address digits
        for dig in feat['digits']:
            if dig in idx_digits[c]:
                cands.update(idx_digits[c][dig])

        # F: Address location tokens
        for loc in feat['loc_tokens']:
            if loc in idx_loc_token[c]:
                cands.update(idx_loc_token[c][loc])

        s1_candidates[s1_id] = cands

    runtime_gen = time.time() - t0
    total_runtime = time.time() - t_start
    peak_ram = get_ram_mb()
    print(f"Generated and deduplicated candidates for 10,000 S1s in {runtime_gen:.2f}s")
    print(f"Peak RAM: {peak_ram:.2f} MB")

    # 5. Evaluate Metrics
    metrics, missed_pairs = evaluate_blocking_candidates(
        experiment_id="Baseline_G",
        description="Strategy G (B + C + D + E + F) Unfiltered Control",
        s1_candidates=s1_candidates,
        gt_matches=gt_matches,
        total_true_pairs=total_true_pairs,
        total_target_pool=len(target_norm),
        runtime_sec=total_runtime,
        peak_ram_mb=peak_ram,
        s1_norm=s1_norm,
        target_norm=target_norm
    )

    # 6. Save Candidate Sets & Missed Pairs
    print("Saving baseline candidates to experiments/data/baseline_g_candidates.json...")
    with open(f"{DATA_DIR}/baseline_g_candidates.json", 'w', encoding='utf-8') as f:
        # Save as list for JSON serialization
        json.dump({k: list(v) for k, v in s1_candidates.items()}, f)

    print("Saving missed pairs to experiments/results/baseline_g_missed_pairs.tsv...")
    with open(f"{RESULTS_DIR}/baseline_g_missed_pairs.tsv", 'w', encoding='utf-8') as f:
        f.write("experiment\ts1_entity_id\ttarget_entity_id\tsource\ts1_name\ttarget_name\ts1_address\ttarget_address\treason\n")
        for m in missed_pairs:
            s1_p = s1_raw[m['s1_entity_id']]
            t_p = target_raw[m['target_entity_id']]
            f.write(f"{m['experiment']}\t{m['s1_entity_id']}\t{m['target_entity_id']}\t{m['source']}\t{s1_p[1]}\t{t_p[1]}\t{s1_p[2]}\t{t_p[2]}\t{m['reason']}\n")

    # Save summary metrics
    with open(f"{RESULTS_DIR}/baseline_g_metrics.json", 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2)

    print("\n=================================================================")
    print("BASELINE REPRODUCTION VERIFICATION REPORT")
    print("=================================================================")
    print(f"Total S1 records:           {len(s1_candidates)}")
    print(f"Total true pairs:           {metrics['true_pairs']}")
    print(f"True pairs recalled:        {metrics['recalled_pairs']}")
    print(f"True pairs missed:          {metrics['missed_pairs']}")
    print(f"Recall:                     {metrics['recall']}")
    print(f"Average candidates/S1:      {metrics['avg_candidates']:.1f}")
    print(f"Median candidates/S1:       {metrics['median_candidates']}")
    print(f"P95 candidates/S1:          {metrics['p95_candidates']}")
    print(f"Maximum candidates/S1:      {metrics['max_candidates']}")
    print(f"Zero-candidate S1 count:    {metrics['zero_candidate_s1']}")
    print(f"Candidate reduction ratio:  {metrics['candidate_reduction_ratio']}")
    print(f"Runtime:                    {metrics['runtime_seconds']:.2f} seconds")
    print(f"Peak RAM:                   {metrics['peak_memory_mb']:.2f} MB")

    # Check against expected baseline
    exp_recall = 99.94
    exp_recalled = 34462
    exp_missed = 19
    exp_avg = 3294.6
    exp_med = 2621
    exp_p95 = 9555
    exp_max = 18372

    print("\n--- DISCREPANCY AUDIT ---")
    print(f"Recall:    Actual = {metrics['recall_pct']:.4f}% | Expected = {exp_recall:.2f}% | Delta = {metrics['recall_pct'] - exp_recall:+.4f}%")
    print(f"Recalled:  Actual = {metrics['recalled_pairs']} | Expected = {exp_recalled} | Delta = {metrics['recalled_pairs'] - exp_recalled}")
    print(f"Missed:    Actual = {metrics['missed_pairs']} | Expected = {exp_missed} | Delta = {metrics['missed_pairs'] - exp_missed}")
    print(f"Avg Cands: Actual = {metrics['avg_candidates']:.1f} | Expected = {exp_avg:.1f} | Delta = {metrics['avg_candidates'] - exp_avg:+.1f}")
    print(f"Median:    Actual = {metrics['median_candidates']} | Expected = {exp_med} | Delta = {metrics['median_candidates'] - exp_med}")
    print(f"P95:       Actual = {metrics['p95_candidates']} | Expected = {exp_p95} | Delta = {metrics['p95_candidates'] - exp_p95}")
    print(f"Max:       Actual = {metrics['max_candidates']} | Expected = {exp_max} | Delta = {metrics['max_candidates'] - exp_max}")

    # Print the 19 missed true pairs
    print(f"\n--- THE {len(missed_pairs)} MISSED TRUE PAIRS ---")
    for i, m in enumerate(missed_pairs, 1):
        s1_p = s1_raw[m['s1_entity_id']]
        t_p = target_raw[m['target_entity_id']]
        print(f"{i:2d}. S1: {m['s1_entity_id']} ({s1_p[3]}) | '{s1_p[1]}' | '{s1_p[2]}'")
        print(f"    Target: {m['target_entity_id']} ({m['source']}) | '{t_p[1]}' | '{t_p[2]}'")
        print(f"    Diagnosed Reason: {m['reason']}")
        print()

    return metrics, missed_pairs

if __name__ == '__main__':
    run_baseline_g()
