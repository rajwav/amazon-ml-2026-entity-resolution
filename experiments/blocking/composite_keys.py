"""
Experiment 2: Combined / Composite Blocking Keys Benchmark.
Evaluates composite multi-attribute blocking keys (e.g., name_token + location,
name_token + digit, prefix + digit, digit + location) on the identical 10k pilot.
Measures recall vs. candidate volume tradeoffs against Baseline G.
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

def run_experiment_2():
    t_start = time.time()
    ram_init = get_ram_mb()
    print("=================================================================")
    print("EXPERIMENT 2: COMBINED / COMPOSITE BLOCKING KEYS BENCHMARK")
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

    # 3. Build Inverted Indexes for Single and Composite Keys
    print("\nBuilding Inverted Indexes for Composite Keys...")
    t0 = time.time()

    # Composite indexes: Country -> (Key1, Key2) -> list of IDs
    idx_exact_name   = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_sig_token    = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_prefix4      = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_digits       = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_loc_token    = collections.defaultdict(lambda: collections.defaultdict(list))

    idx_tok_loc      = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_tok_dig      = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_pref_loc     = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_pref_dig     = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_dig_loc      = collections.defaultdict(lambda: collections.defaultdict(list))

    for eid, feat in target_norm.items():
        c = feat['country']

        # Single keys
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

        # Composite keys:
        # A: (token, location)
        for tok in feat['tokens']:
            for loc in feat['loc_tokens']:
                idx_tok_loc[c][(tok, loc)].append(eid)

        # B: (token, digit)
        for tok in feat['tokens']:
            for dig in feat['digits']:
                idx_tok_dig[c][(tok, dig)].append(eid)

        # C: (prefix4, location)
        if feat['prefix4']:
            for loc in feat['loc_tokens']:
                idx_pref_loc[c][(feat['prefix4'], loc)].append(eid)

        # D: (prefix4, digit)
        if feat['prefix4']:
            for dig in feat['digits']:
                idx_pref_dig[c][(feat['prefix4'], dig)].append(eid)

        # E: (digit, location)
        for dig in feat['digits']:
            for loc in feat['loc_tokens']:
                idx_dig_loc[c][(dig, loc)].append(eid)

    print(f"Built composite indexes in {time.time()-t0:.2f}s | RAM: {get_ram_mb():.2f} MB")

    # 4. Define Composite Configurations to Benchmark
    composite_configs = [
        {
            'id': 'C2_A_Tok_Loc',
            'desc': 'Composite: Country + (Name Token & Location Token)',
            'keys': ['tok_loc']
        },
        {
            'id': 'C2_B_Tok_Dig',
            'desc': 'Composite: Country + (Name Token & Address Digit)',
            'keys': ['tok_dig']
        },
        {
            'id': 'C2_C_Pref_Loc',
            'desc': 'Composite: Country + (Name Prefix4 & Location Token)',
            'keys': ['pref_loc']
        },
        {
            'id': 'C2_D_Pref_Dig',
            'desc': 'Composite: Country + (Name Prefix4 & Address Digit)',
            'keys': ['pref_dig']
        },
        {
            'id': 'C2_E_Dig_Loc',
            'desc': 'Composite: Country + (Address Digit & Location Token)',
            'keys': ['dig_loc']
        },
        {
            'id': 'C2_Union_Name_Address_Composites',
            'desc': 'Composite Union: (Exact Name) + (Tok & Loc) + (Tok & Dig) + (Pref & Dig)',
            'keys': ['exact_name', 'tok_loc', 'tok_dig', 'pref_dig']
        },
        {
            'id': 'C2_Union_All_Composites',
            'desc': 'Composite Union: (Exact Name) + (Tok & Loc) + (Tok & Dig) + (Pref & Loc) + (Pref & Dig) + (Dig & Loc)',
            'keys': ['exact_name', 'tok_loc', 'tok_dig', 'pref_loc', 'pref_dig', 'dig_loc']
        },
        {
            'id': 'C2_High_Precision_Union',
            'desc': 'High-Precision Union: (Exact Name) + (Tok & Loc) + (Tok & Dig) + (Sig Token)',
            'keys': ['exact_name', 'tok_loc', 'tok_dig', 'sig_token']
        }
    ]

    exp_results = []
    all_lost_pairs = {}

    for cfg in composite_configs:
        t_cfg_start = time.time()
        print(f"\nEvaluating {cfg['id']}: {cfg['desc']}...")
        keys = set(cfg['keys'])

        s1_candidates = {}
        for s1_id, feat in s1_norm.items():
            c = feat['country']
            cands = set()

            # Exact Name
            if 'exact_name' in keys and feat['core'] and feat['core'] in idx_exact_name[c]:
                cands.update(idx_exact_name[c][feat['core']])

            # Sig token standalone
            if 'sig_token' in keys:
                for tok in feat['tokens']:
                    if tok in idx_sig_token[c]:
                        cands.update(idx_sig_token[c][tok])

            # Tok & Loc
            if 'tok_loc' in keys:
                for tok in feat['tokens']:
                    for loc in feat['loc_tokens']:
                        pair = (tok, loc)
                        if pair in idx_tok_loc[c]:
                            cands.update(idx_tok_loc[c][pair])

            # Tok & Dig
            if 'tok_dig' in keys:
                for tok in feat['tokens']:
                    for dig in feat['digits']:
                        pair = (tok, dig)
                        if pair in idx_tok_dig[c]:
                            cands.update(idx_tok_dig[c][pair])

            # Pref & Loc
            if 'pref_loc' in keys and feat['prefix4']:
                p = feat['prefix4']
                for loc in feat['loc_tokens']:
                    pair = (p, loc)
                    if pair in idx_pref_loc[c]:
                        cands.update(idx_pref_loc[c][pair])

            # Pref & Dig
            if 'pref_dig' in keys and feat['prefix4']:
                p = feat['prefix4']
                for dig in feat['digits']:
                    pair = (p, dig)
                    if pair in idx_pref_dig[c]:
                        cands.update(idx_pref_dig[c][pair])

            # Dig & Loc
            if 'dig_loc' in keys:
                for dig in feat['digits']:
                    for loc in feat['loc_tokens']:
                        pair = (dig, loc)
                        if pair in idx_dig_loc[c]:
                            cands.update(idx_dig_loc[c][pair])

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

        # Compare with Baseline G
        current_recalled_set = set()
        for s1_id, true_mids in gt_matches.items():
            cands = s1_candidates.get(s1_id, set())
            for m in true_mids:
                if m in cands:
                    current_recalled_set.add((s1_id, m))

        newly_lost = baseline_recalled_set - current_recalled_set
        recalled_baseline_pairs = len(current_recalled_set & baseline_recalled_set)
        newly_recovered = current_recalled_set - baseline_recalled_set

        metrics['retained_from_baseline'] = recalled_baseline_pairs
        metrics['newly_lost_vs_baseline'] = len(newly_lost)
        metrics['newly_recovered_vs_baseline'] = len(newly_recovered)
        metrics['cand_reduction_vs_baseline_pct'] = (1.0 - (metrics['avg_candidates'] / baseline_metrics['avg_candidates'])) * 100

        all_lost_pairs[cfg['id']] = list(newly_lost)
        exp_results.append(metrics)

        print(f"  Recall:                 {metrics['recall']} ({metrics['recalled_pairs']}/{total_true_pairs})")
        print(f"  Newly Lost vs Baseline: {len(newly_lost)} | Newly Recovered: {len(newly_recovered)}")
        print(f"  Avg Candidates/S1:      {metrics['avg_candidates']:.1f} (vs Baseline: {baseline_metrics['avg_candidates']:.1f}, reduction: {metrics['cand_reduction_vs_baseline_pct']:.2f}%)")
        print(f"  P50 / P95 / Max Cands:  {metrics['median_candidates']} / {metrics['p95_candidates']} / {metrics['max_candidates']}")
        print(f"  Zero Candidate S1:      {metrics['zero_candidate_s1']}")
        print(f"  Runtime:                {dt_cfg:.2f}s | RAM: {peak_ram:.2f} MB")

    # 5. Save Experiment 2 Results
    print("\nSaving Experiment 2 metrics to experiments/results/exp2_composite_keys_metrics.json...")
    with open(f"{RESULTS_DIR}/exp2_composite_keys_metrics.json", 'w', encoding='utf-8') as f:
        json.dump(exp_results, f, indent=2)

    # Save newly lost pairs to TSV
    lost_tsv_path = f"{RESULTS_DIR}/exp2_newly_lost_pairs.tsv"
    with open(lost_tsv_path, 'w', encoding='utf-8') as f:
        f.write("experiment_id\ts1_entity_id\ttarget_entity_id\ts1_name\ttarget_name\ts1_address\ttarget_address\n")
        for exp_id, lost_list in all_lost_pairs.items():
            for s1_id, mid in lost_list[:50]:
                s1_p = s1_raw[s1_id]
                t_p = target_raw[mid]
                f.write(f"{exp_id}\t{s1_id}\t{mid}\t{s1_p[1]}\t{t_p[1]}\t{s1_p[2]}\t{t_p[2]}\n")

    return exp_results

if __name__ == '__main__':
    run_experiment_2()
