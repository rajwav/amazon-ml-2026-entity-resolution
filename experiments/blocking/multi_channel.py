"""
Experiment 3: Multi-Channel Incremental Union Benchmark.
Evaluates cumulative additions of blocking channels:
B -> B+C -> B+C+D -> B+C+D+E -> B+C+D+E+F (Baseline G)
Measures the exact marginal true pairs recovered and candidate cost added by each channel.
"""

import os
import sys
import time
import json
import collections
from typing import Dict, Set, Tuple, List

sys.path.append('.')
from experiments.blocking.common import (
    load_pilot_raw,
    get_normalized_records,
    evaluate_blocking_candidates,
    get_ram_mb,
    RESULTS_DIR,
    DATA_DIR
)

def run_experiment_3():
    t_start = time.time()
    ram_init = get_ram_mb()
    print("=================================================================")
    print("EXPERIMENT 3: MULTI-CHANNEL INCREMENTAL UNION BENCHMARK")
    print("=================================================================")
    print(f"Initial RAM: {ram_init:.2f} MB")

    # 1. Load data
    t0 = time.time()
    s1_raw, target_raw, gt_matches, total_true_pairs = load_pilot_raw()
    s1_norm, target_norm = get_normalized_records(s1_raw, target_raw)
    print(f"Loaded and normalized data in {time.time()-t0:.2f}s")

    # 2. Build Inverted Indexes for Single Channels B, C, D, E, F
    t0 = time.time()
    idx_B_exact_name = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_C_sig_token  = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_D_prefix4    = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_E_digits     = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_F_loc_token  = collections.defaultdict(lambda: collections.defaultdict(list))

    for eid, feat in target_norm.items():
        c = feat['country']
        if feat['core']: idx_B_exact_name[c][feat['core']].append(eid)
        for tok in feat['tokens']: idx_C_sig_token[c][tok].append(eid)
        if feat['prefix4']: idx_D_prefix4[c][feat['prefix4']].append(eid)
        for dig in feat['digits']: idx_E_digits[c][dig].append(eid)
        for loc in feat['loc_tokens']: idx_F_loc_token[c][loc].append(eid)

    print(f"Built single channel inverted indexes in {time.time()-t0:.2f}s | RAM: {get_ram_mb():.2f} MB")

    # 3. Define Incremental Cumulative Steps
    incremental_steps = [
        {
            'id': 'E3_Step1_B',
            'name': 'B (Exact Core Name)',
            'added_channel': 'B',
            'channels': ['B']
        },
        {
            'id': 'E3_Step2_BC',
            'name': 'B + C (+ Significant Name Token)',
            'added_channel': 'C',
            'channels': ['B', 'C']
        },
        {
            'id': 'E3_Step3_BCD',
            'name': 'B + C + D (+ 4-Char Prefix)',
            'added_channel': 'D',
            'channels': ['B', 'C', 'D']
        },
        {
            'id': 'E3_Step4_BCDE',
            'name': 'B + C + D + E (+ Address Digits)',
            'added_channel': 'E',
            'channels': ['B', 'C', 'D', 'E']
        },
        {
            'id': 'E3_Step5_BCDEF',
            'name': 'B + C + D + E + F (Baseline G)',
            'added_channel': 'F',
            'channels': ['B', 'C', 'D', 'E', 'F']
        }
    ]

    exp_results = []
    previous_recalled_pairs_set = set()

    for step in incremental_steps:
        t_step_start = time.time()
        print(f"\nEvaluating {step['id']}: {step['name']}...")
        channels = set(step['channels'])

        s1_candidates: Dict[str, Set[str]] = {}

        for s1_id, feat in s1_norm.items():
            c = feat['country']
            cands = set()

            # B
            if 'B' in channels and feat['core'] and feat['core'] in idx_B_exact_name[c]:
                cands.update(idx_B_exact_name[c][feat['core']])

            # C
            if 'C' in channels:
                for tok in feat['tokens']:
                    if tok in idx_C_sig_token[c]:
                        cands.update(idx_C_sig_token[c][tok])

            # D
            if 'D' in channels and feat['prefix4'] and feat['prefix4'] in idx_D_prefix4[c]:
                cands.update(idx_D_prefix4[c][feat['prefix4']])

            # E
            if 'E' in channels:
                for dig in feat['digits']:
                    if dig in idx_E_digits[c]:
                        cands.update(idx_E_digits[c][dig])

            # F
            if 'F' in channels:
                for loc in feat['loc_tokens']:
                    if loc in idx_F_loc_token[c]:
                        cands.update(idx_F_loc_token[c][loc])

            s1_candidates[s1_id] = cands

        dt_step = time.time() - t_step_start
        peak_ram = get_ram_mb()

        # Compute metrics
        metrics, missed_pairs = evaluate_blocking_candidates(
            experiment_id=step['id'],
            description=step['name'],
            s1_candidates=s1_candidates,
            gt_matches=gt_matches,
            total_true_pairs=total_true_pairs,
            total_target_pool=len(target_norm),
            runtime_sec=dt_step,
            peak_ram_mb=peak_ram,
            s1_norm=s1_norm,
            target_norm=target_norm
        )

        # Set of recalled pairs
        current_recalled_set = set()
        for s1_id, true_mids in gt_matches.items():
            cands = s1_candidates.get(s1_id, set())
            for m in true_mids:
                if m in cands:
                    current_recalled_set.add((s1_id, m))

        marginal_new_pairs = len(current_recalled_set - previous_recalled_pairs_set)
        metrics['added_channel'] = step['added_channel']
        metrics['marginal_new_pairs'] = marginal_new_pairs
        metrics['recalled_pairs_count'] = len(current_recalled_set)

        previous_recalled_pairs_set = current_recalled_set
        exp_results.append(metrics)

        print(f"  Recall:                 {metrics['recall']} ({metrics['recalled_pairs']}/{total_true_pairs})")
        print(f"  Marginal True Pairs:    +{marginal_new_pairs:5d} new true pairs added by channel {step['added_channel']}")
        print(f"  True Pairs Missed:      {metrics['missed_pairs']}")
        print(f"  Avg Candidates/S1:      {metrics['avg_candidates']:.1f}")
        print(f"  P50 / P95 / Max Cands:  {metrics['median_candidates']} / {metrics['p95_candidates']} / {metrics['max_candidates']}")
        print(f"  Zero Candidate S1:      {metrics['zero_candidate_s1']}")
        print(f"  Runtime:                {dt_step:.2f}s | RAM: {peak_ram:.2f} MB")

    # 4. Save results
    print("\nSaving Experiment 3 metrics to experiments/results/exp3_incremental_union_metrics.json...")
    with open(f"{RESULTS_DIR}/exp3_incremental_union_metrics.json", 'w', encoding='utf-8') as f:
        json.dump(exp_results, f, indent=2)

    return exp_results

if __name__ == '__main__':
    run_experiment_3()
