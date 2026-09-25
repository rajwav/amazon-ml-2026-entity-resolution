"""
Experiment 1: Rare Token / IDF Filtering Benchmark.
Evaluates progressive frequency filtering thresholds on the 10,000 S1 pilot.
Measures recall retention vs. candidate reduction against Baseline G.
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

def run_experiment_1():
    t_start = time.time()
    ram_init = get_ram_mb()
    print("=================================================================")
    print("EXPERIMENT 1: RARE TOKEN / IDF FILTERING BENCHMARK")
    print("=================================================================")
    print(f"Initial RAM: {ram_init:.2f} MB")

    # 1. Load pilot records and baseline G candidates
    t0 = time.time()
    s1_raw, target_raw, gt_matches, total_true_pairs = load_pilot_raw()
    
    with open(f"{DATA_DIR}/baseline_g_candidates.json", 'r', encoding='utf-8') as f:
        baseline_candidates = {k: set(v) for k, v in json.load(f).items()}

    with open(f"{RESULTS_DIR}/baseline_g_metrics.json", 'r', encoding='utf-8') as f:
        baseline_metrics = json.load(f)

    baseline_recalled_set = set()
    for s1_id, true_mids in gt_matches.items():
        base_cands = baseline_candidates.get(s1_id, set())
        for m in true_mids:
            if m in base_cands:
                baseline_recalled_set.add((s1_id, m))
    assert len(baseline_recalled_set) == 34462

    print(f"Loaded pilot data and baseline in {time.time()-t0:.2f}s (Baseline recalled pairs: {len(baseline_recalled_set)})")

    # 2. Normalize records
    s1_norm, target_norm = get_normalized_records(s1_raw, target_raw)

    # 3. Analyze Token Frequencies across Target Pool by Country
    # Target pool sizes: US=50,522, India=33,959
    freq_sig_token = collections.defaultdict(collections.Counter)
    freq_prefix4   = collections.defaultdict(collections.Counter)
    freq_digits    = collections.defaultdict(collections.Counter)
    freq_loc_token = collections.defaultdict(collections.Counter)

    for eid, feat in target_norm.items():
        c = feat['country']
        for tok in feat['tokens']: freq_sig_token[c][tok] += 1
        if feat['prefix4']: freq_prefix4[c][feat['prefix4']] += 1
        for dig in feat['digits']: freq_digits[c][dig] += 1
        for loc in feat['loc_tokens']: freq_loc_token[c][loc] += 1

    print("\nTop 5 most frequent tokens in Target Pool:")
    for c in ['US', 'India']:
        print(f"  [{c}] Top Name Tokens:     {freq_sig_token[c].most_common(5)}")
        print(f"  [{c}] Top 4-char Prefixes: {freq_prefix4[c].most_common(5)}")
        print(f"  [{c}] Top Address Digits:  {freq_digits[c].most_common(5)}")
        print(f"  [{c}] Top Loc Tokens:      {freq_loc_token[c].most_common(5)}")

    # 4. Define Progressive Filtering Configurations
    # Thresholds define the MAX frequency allowed for a token to be used as a blocking key.
    # We test:
    # E1-A: No filtering (exact Baseline G)
    # E1-B: Conservative filtering (drop extreme outliers > 5% of target pool, e.g. US > 2500, India > 1700)
    # E1-C: Moderate filtering (drop tokens > 2% of target pool, e.g. US > 1000, India > 680)
    # E1-D: Aggressive filtering (drop tokens > 1% of target pool, e.g. US > 500, India > 340)

    configs = [
        {
            'id': 'E1_A_No_Filtering',
            'desc': 'No filtering (Baseline G)',
            'max_pct': 1.0,
            'max_freq_us': 999999,
            'max_freq_in': 999999
        },
        {
            'id': 'E1_B_Conservative',
            'desc': 'Conservative filtering (Drop tokens > 5% of target pool: US > 2500, IN > 1700)',
            'max_pct': 0.05,
            'max_freq_us': 2500,
            'max_freq_in': 1700
        },
        {
            'id': 'E1_C_Moderate',
            'desc': 'Moderate filtering (Drop tokens > 2% of target pool: US > 1000, IN > 680)',
            'max_pct': 0.02,
            'max_freq_us': 1000,
            'max_freq_in': 680
        },
        {
            'id': 'E1_D_Aggressive',
            'desc': 'Aggressive filtering (Drop tokens > 1% of target pool: US > 500, IN > 340)',
            'max_pct': 0.01,
            'max_freq_us': 500,
            'max_freq_in': 340
        }
    ]

    exp_results = []
    all_lost_pairs_by_cfg = {}

    for cfg in configs:
        t_cfg_start = time.time()
        print(f"\nEvaluating {cfg['id']}: {cfg['desc']}...")
        
        limit_us = cfg['max_freq_us']
        limit_in = cfg['max_freq_in']

        # Build Inverted Indexes excluding tokens above threshold
        idx_exact_name = collections.defaultdict(lambda: collections.defaultdict(list))
        idx_sig_token  = collections.defaultdict(lambda: collections.defaultdict(list))
        idx_prefix4    = collections.defaultdict(lambda: collections.defaultdict(list))
        idx_digits     = collections.defaultdict(lambda: collections.defaultdict(list))
        idx_loc_token  = collections.defaultdict(lambda: collections.defaultdict(list))

        filtered_tokens_count = collections.defaultdict(int)

        for eid, feat in target_norm.items():
            c = feat['country']
            limit = limit_us if c == 'US' else limit_in

            # Channel B: Exact name (never filtered)
            if feat['core']:
                idx_exact_name[c][feat['core']].append(eid)

            # Channel C: Sig tokens
            for tok in feat['tokens']:
                if freq_sig_token[c][tok] <= limit:
                    idx_sig_token[c][tok].append(eid)
                else:
                    filtered_tokens_count[f"{c}_token"] += 1

            # Channel D: 4-char prefix
            if feat['prefix4']:
                if freq_prefix4[c][feat['prefix4']] <= limit:
                    idx_prefix4[c][feat['prefix4']].append(eid)
                else:
                    filtered_tokens_count[f"{c}_prefix"] += 1

            # Channel E: Digits
            for dig in feat['digits']:
                if freq_digits[c][dig] <= limit:
                    idx_digits[c][dig].append(eid)
                else:
                    filtered_tokens_count[f"{c}_digit"] += 1

            # Channel F: Location tokens
            for loc in feat['loc_tokens']:
                if freq_loc_token[c][loc] <= limit:
                    idx_loc_token[c][loc].append(eid)
                else:
                    filtered_tokens_count[f"{c}_loc"] += 1

        print(f"  Filtered postings count: {dict(filtered_tokens_count)}")

        # Generate candidates per S1
        s1_candidates = {}
        for s1_id, feat in s1_norm.items():
            c = feat['country']
            limit = limit_us if c == 'US' else limit_in
            cands = set()

            # B: Exact core name
            if feat['core'] and feat['core'] in idx_exact_name[c]:
                cands.update(idx_exact_name[c][feat['core']])

            # C: Sig tokens
            for tok in feat['tokens']:
                if freq_sig_token[c][tok] <= limit and tok in idx_sig_token[c]:
                    cands.update(idx_sig_token[c][tok])

            # D: Prefix
            if feat['prefix4'] and freq_prefix4[c][feat['prefix4']] <= limit and feat['prefix4'] in idx_prefix4[c]:
                cands.update(idx_prefix4[c][feat['prefix4']])

            # E: Digits
            for dig in feat['digits']:
                if freq_digits[c][dig] <= limit and dig in idx_digits[c]:
                    cands.update(idx_digits[c][dig])

            # F: Location tokens
            for loc in feat['loc_tokens']:
                if freq_loc_token[c][loc] <= limit and loc in idx_loc_token[c]:
                    cands.update(idx_loc_token[c][loc])

            s1_candidates[s1_id] = cands

        dt_cfg = time.time() - t_cfg_start
        peak_ram = get_ram_mb()

        # Evaluate metrics
        metrics, missed_pairs = evaluate_blocking_candidates(
            experiment_id=cfg['id'],
            description=cfg['desc'],
            s1_candidates=s1_candidates,
            gt_matches=gt_matches,
            total_true_pairs=total_true_pairs,
            total_target_pool=len(target_norm),
            runtime_sec=dt_cfg,
            peak_ram_mb=peak_ram,
            s1_norm=s1_norm,
            target_norm=target_norm
        )

        # Calculate exact delta compared to Baseline G
        current_recalled_set = set()
        for s1_id, true_mids in gt_matches.items():
            cands = s1_candidates.get(s1_id, set())
            for m in true_mids:
                if m in cands:
                    current_recalled_set.add((s1_id, m))

        retained_from_base = len(current_recalled_set & baseline_recalled_set)
        newly_lost_pairs = baseline_recalled_set - current_recalled_set

        metrics['retained_from_baseline'] = retained_from_base
        metrics['newly_lost_vs_baseline'] = len(newly_lost_pairs)
        metrics['cand_reduction_vs_baseline_pct'] = (1.0 - (metrics['avg_candidates'] / baseline_metrics['avg_candidates'])) * 100

        all_lost_pairs_by_cfg[cfg['id']] = list(newly_lost_pairs)
        exp_results.append(metrics)

        print(f"  Recall:                 {metrics['recall']} ({metrics['recalled_pairs']}/{total_true_pairs})")
        print(f"  Newly Lost vs Baseline: {len(newly_lost_pairs)}")
        print(f"  Avg Candidates/S1:      {metrics['avg_candidates']:.1f} (vs Baseline: {baseline_metrics['avg_candidates']:.1f}, reduction: {metrics['cand_reduction_vs_baseline_pct']:.2f}%)")
        print(f"  P50 / P95 / Max Cands:  {metrics['median_candidates']} / {metrics['p95_candidates']} / {metrics['max_candidates']}")
        print(f"  Zero Candidate S1:      {metrics['zero_candidate_s1']}")
        print(f"  Runtime:                {dt_cfg:.2f}s | RAM: {peak_ram:.2f} MB")

    # 5. Save Experiment 1 Results
    print("\nSaving Experiment 1 metrics to experiments/results/exp1_rare_token_metrics.json...")
    with open(f"{RESULTS_DIR}/exp1_rare_token_metrics.json", 'w', encoding='utf-8') as f:
        json.dump(exp_results, f, indent=2)

    # Save newly lost pairs to TSV
    lost_tsv_path = f"{RESULTS_DIR}/exp1_newly_lost_pairs.tsv"
    with open(lost_tsv_path, 'w', encoding='utf-8') as f:
        f.write("experiment_id\ts1_entity_id\ttarget_entity_id\ts1_name\ttarget_name\ts1_address\ttarget_address\n")
        for exp_id, lost_list in all_lost_pairs_by_cfg.items():
            for s1_id, mid in lost_list[:50]: # log first 50
                s1_p = s1_raw[s1_id]
                t_p = target_raw[mid]
                f.write(f"{exp_id}\t{s1_id}\t{mid}\t{s1_p[1]}\t{t_p[1]}\t{s1_p[2]}\t{t_p[2]}\n")

    return exp_results, all_lost_pairs_by_cfg

if __name__ == '__main__':
    run_experiment_1()
