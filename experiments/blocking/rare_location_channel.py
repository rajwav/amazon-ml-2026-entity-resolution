"""
Experiment 8: Dynamic Frequency-Aware Target-Side Channel F Benchmark.

Systematically evaluates frequency-aware location blocking policies to eliminate candidate explosion
while recovering tail misses (including the 9 E6 misses and exploring baseline tail recovery).

Tested Policies on Level 3 (Channel F):
- Ref_E6: Global 5% IDF Cutoff (Binary deletion of tokens > 5%)
- Policy_8A_Fallback5: Rarest Token Priority with Fallback (Targets index tokens <= 5%; if none exist, index the single rarest available token)
- Policy_8A_Fallback3: Rarest Token Priority with Fallback (Targets index tokens <= 3%; if none exist, index the single rarest available token)
- Policy_8B_Top1: Strict Top-1 Rarest Token per target record
- Policy_8B_Top2: Strict Top-2 Rarest Tokens per target record
- Policy_8C_QueryAware: Rarest Token Priority with Fallback + Query-Side Rare Prioritization
"""

import os
import sys
import gc
import time
import json
import collections
from typing import Dict, Set, Tuple, List, Any

sys.path.append('.')
from src.preprocessing.normalization import normalize_business_name, normalize_business_address
from experiments.blocking.common import (
    load_pilot_raw,
    get_ram_mb,
    RESULTS_DIR,
    DATA_DIR
)

def compute_detailed_metrics(cands_map: Dict[str, Set[str]], gt_matches: Dict[str, List[str]], total_true_pairs: int, total_s1: int):
    recalled = 0
    c_counts = []
    zero_cands = 0
    for s1_id, mids in gt_matches.items():
        cands = cands_map.get(s1_id, set())
        cnt = len(cands)
        c_counts.append(cnt)
        if cnt == 0:
            zero_cands += 1
        for mid in mids:
            if mid in cands:
                recalled += 1

    c_counts.sort()
    n = len(c_counts)
    total_cands = sum(c_counts)
    avg_c = total_cands / n if n else 0
    med_c = c_counts[n // 2] if n else 0
    p90_c = c_counts[int(n * 0.90)] if n else 0
    p95_c = c_counts[int(n * 0.95)] if n else 0
    p99_c = c_counts[int(n * 0.99)] if n else 0
    max_c = c_counts[-1] if n else 0

    recall_pct = (recalled / total_true_pairs * 100) if total_true_pairs else 0
    return {
        'recall': f"{recall_pct:.4f}%",
        'recall_num': recall_pct,
        'recalled_pairs': recalled,
        'missed_pairs': total_true_pairs - recalled,
        'total_candidates': total_cands,
        'avg_candidates': avg_c,
        'median_candidates': med_c,
        'p90_candidates': p90_c,
        'p95_candidates': p95_c,
        'p99_candidates': p99_c,
        'max_candidates': max_c,
        'zero_candidate_s1': zero_cands
    }

def run_experiment_8():
    t_start = time.time()
    ram_init = get_ram_mb()
    print("=================================================================")
    print("EXPERIMENT 8: DYNAMIC FREQUENCY-AWARE CHANNEL F BENCHMARK")
    print("=================================================================")
    print(f"Initial RAM: {ram_init:.2f} MB")

    # 1. Load raw pilot data
    t0 = time.time()
    s1_raw, target_raw, gt_matches, total_true_pairs = load_pilot_raw()
    total_s1 = len(s1_raw)
    total_targets = len(target_raw)

    with open(f"{RESULTS_DIR}/baseline_g_metrics.json", 'r', encoding='utf-8') as f:
        baseline_g_metrics = json.load(f)

    with open(f"{RESULTS_DIR}/baseline_g_missed_pairs.tsv", 'r', encoding='utf-8') as f:
        next(f)
        baseline_misses_pairs = set(tuple(line.rstrip('\r\n').split('\t')[1:3]) for line in f)

    with open(f"{RESULTS_DIR}/exp6_remaining_25_misses.tsv", 'r', encoding='utf-8') as f:
        next(f)
        exp6_misses_pairs = set(tuple(line.rstrip('\r\n').split('\t')[:2]) for line in f)
        # 9 misses were specifically caused by E6's 5% cutoff (not in baseline 19)
        exp6_cutoff_losses = exp6_misses_pairs - baseline_misses_pairs

    print(f"Loaded raw data ({total_s1} S1s, {total_targets} targets, {total_true_pairs} true pairs) in {time.time()-t0:.2f}s")
    print(f"Tracking 19 Baseline G misses and {len(exp6_cutoff_losses)} Exp 6 IDF cutoff losses.")

    # 2. Pre-compute Normalized Representations with Selective Transliteration:
    print("\nNormalizing records (Selective Transliteration: Names/Digits ON, Loc Tokens OFF)...")
    t0 = time.time()

    s1_norm = {}
    for eid, parts in s1_raw.items():
        bname, baddr, country = parts[1], parts[2], parts[3]
        core, legal, sig_tokens, ngrams = normalize_business_name(bname, enable_transliteration=True)
        _, digits, _ = normalize_business_address(baddr, enable_transliteration=True)
        _, _, loc_tokens = normalize_business_address(baddr, enable_transliteration=False)
        prefix4 = core[:4] if len(core) >= 4 else core
        s1_norm[eid] = {
            'id': eid,
            'country': country,
            'core': core,
            'tokens': tuple(sig_tokens),
            'prefix4': prefix4,
            'digits': tuple(digits),
            'loc_tokens': tuple(loc_tokens)
        }

    target_norm = {}
    freq_loc_token = collections.defaultdict(collections.Counter)
    target_country_counts = collections.Counter()

    for eid, parts in target_raw.items():
        bname, baddr, country = parts[1], parts[2], parts[3]
        core, legal, sig_tokens, ngrams = normalize_business_name(bname, enable_transliteration=True)
        _, digits, _ = normalize_business_address(baddr, enable_transliteration=True)
        _, _, loc_tokens = normalize_business_address(baddr, enable_transliteration=False)
        prefix4 = core[:4] if len(core) >= 4 else core
        target_norm[eid] = {
            'id': eid,
            'country': country,
            'core': core,
            'tokens': tuple(sig_tokens),
            'prefix4': prefix4,
            'digits': tuple(digits),
            'loc_tokens': tuple(loc_tokens)
        }
        target_country_counts[country] += 1
        for loc in loc_tokens:
            freq_loc_token[country][loc] += 1

    print(f"Normalized in {time.time()-t0:.2f}s | RAM: {get_ram_mb():.2f} MB")

    # 3. Build Base Level 1 (Composites) and Level 2 (B, C, D, E) Indexes
    print("\nBuilding Level 1 and Level 2 Inverted Indexes...")
    t0 = time.time()

    idx_exact_name = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_tok_loc    = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_tok_dig    = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_pref_loc   = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_pref_dig   = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_dig_loc    = collections.defaultdict(lambda: collections.defaultdict(list))

    idx_B = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_C = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_D = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_E = collections.defaultdict(lambda: collections.defaultdict(list))

    for eid, feat in target_norm.items():
        c = feat['country']
        if feat['core']:
            idx_exact_name[c][feat['core']].append(eid)
            idx_B[c][feat['core']].append(eid)
        for tok in feat['tokens']:
            idx_C[c][tok].append(eid)
            for loc in feat['loc_tokens']:
                idx_tok_loc[c][(tok, loc)].append(eid)
            for dig in feat['digits']:
                idx_tok_dig[c][(tok, dig)].append(eid)
        if feat['prefix4']:
            idx_D[c][feat['prefix4']].append(eid)
            for loc in feat['loc_tokens']:
                idx_pref_loc[c][(feat['prefix4'], loc)].append(eid)
            for dig in feat['digits']:
                idx_pref_dig[c][(feat['prefix4'], dig)].append(eid)
        for dig in feat['digits']:
            idx_E[c][dig].append(eid)
            for loc in feat['loc_tokens']:
                idx_dig_loc[c][(dig, loc)].append(eid)

    print(f"Built L1 & L2 indexes in {time.time()-t0:.2f}s | RAM: {get_ram_mb():.2f} MB")

    # Generate fixed Level 1 + Level 2 Candidates for each S1
    print("\nGenerating Level 1 U Level 2 Backbone candidates for all S1...")
    t0 = time.time()
    cands_L1_L2: Dict[str, Set[str]] = {}
    for s1_id, feat in s1_norm.items():
        c = feat['country']
        cands = set()
        # L1: Composites
        if feat['core'] and feat['core'] in idx_exact_name[c]:
            cands.update(idx_exact_name[c][feat['core']])
        for tok in feat['tokens']:
            for loc in feat['loc_tokens']:
                if (tok, loc) in idx_tok_loc[c]:
                    cands.update(idx_tok_loc[c][(tok, loc)])
            for dig in feat['digits']:
                if (tok, dig) in idx_tok_dig[c]:
                    cands.update(idx_tok_dig[c][(tok, dig)])
        if feat['prefix4']:
            for loc in feat['loc_tokens']:
                if (feat['prefix4'], loc) in idx_pref_loc[c]:
                    cands.update(idx_pref_loc[c][(feat['prefix4'], loc)])
            for dig in feat['digits']:
                if (feat['prefix4'], dig) in idx_pref_dig[c]:
                    cands.update(idx_pref_dig[c][(feat['prefix4'], dig)])
        for dig in feat['digits']:
            for loc in feat['loc_tokens']:
                if (dig, loc) in idx_dig_loc[c]:
                    cands.update(idx_dig_loc[c][(dig, loc)])
        # L2: B, C, D, E
        if feat['core'] and feat['core'] in idx_B[c]:
            cands.update(idx_B[c][feat['core']])
        for tok in feat['tokens']:
            if tok in idx_C[c]:
                cands.update(idx_C[c][tok])
        if feat['prefix4'] and feat['prefix4'] in idx_D[c]:
            cands.update(idx_D[c][feat['prefix4']])
        for dig in feat['digits']:
            if dig in idx_E[c]:
                cands.update(idx_E[c][dig])
        cands_L1_L2[s1_id] = cands

    m_l1_l2 = compute_detailed_metrics(cands_L1_L2, gt_matches, total_true_pairs, total_s1)
    print(f"L1 U L2 Backbone: Recall = {m_l1_l2['recall']} ({m_l1_l2['recalled_pairs']}/{total_true_pairs}), "
          f"Avg Cands = {m_l1_l2['avg_candidates']:.1f}, Med = {m_l1_l2['median_candidates']}")

    # 4. Systematically evaluate Channel F policies
    policies = [
        "Ref_E6",
        "Policy_8A_Fallback5",
        "Policy_8A_Fallback3",
        "Policy_8B_Top1",
        "Policy_8B_Top2",
        "Policy_8C_QueryAware",
    ]

    results_table = []
    policy_metrics_dict = {}

    for pol in policies:
        print(f"\n=======================================================")
        print(f"Evaluating Channel F Policy: {pol}")
        print(f"=======================================================")
        t_pol_start = time.time()

        # Build index for this policy
        idx_F = collections.defaultdict(lambda: collections.defaultdict(list))

        for eid, feat in target_norm.items():
            c = feat['country']
            cnt = target_country_counts[c]
            locs = feat['loc_tokens']
            if not locs:
                continue

            # Sort target loc tokens by ascending frequency
            locs_sorted = sorted(locs, key=lambda l: (freq_loc_token[c][l], len(l)))

            if pol == "Ref_E6":
                cutoff = int(cnt * 0.05)
                for loc in locs:
                    if freq_loc_token[c][loc] <= cutoff:
                        idx_F[c][loc].append(eid)

            elif pol == "Policy_8A_Fallback5":
                cutoff = int(cnt * 0.05)
                rare = [loc for loc in locs_sorted if freq_loc_token[c][loc] <= cutoff]
                if rare:
                    for loc in rare:
                        idx_F[c][loc].append(eid)
                else:
                    idx_F[c][locs_sorted[0]].append(eid)

            elif pol == "Policy_8A_Fallback3":
                cutoff = int(cnt * 0.03)
                rare = [loc for loc in locs_sorted if freq_loc_token[c][loc] <= cutoff]
                if rare:
                    for loc in rare:
                        idx_F[c][loc].append(eid)
                else:
                    idx_F[c][locs_sorted[0]].append(eid)

            elif pol == "Policy_8B_Top1":
                idx_F[c][locs_sorted[0]].append(eid)

            elif pol == "Policy_8B_Top2":
                for loc in locs_sorted[:2]:
                    idx_F[c][loc].append(eid)

            elif pol == "Policy_8C_QueryAware":
                cutoff = int(cnt * 0.05)
                rare = [loc for loc in locs_sorted if freq_loc_token[c][loc] <= cutoff]
                if rare:
                    for loc in rare:
                        idx_F[c][loc].append(eid)
                else:
                    idx_F[c][locs_sorted[0]].append(eid)

        # Index stats
        total_indexed_entries = sum(len(eids) for c_idx in idx_F.values() for eids in c_idx.values())
        unique_tokens = sum(len(c_idx) for c_idx in idx_F.values())
        print(f"  Indexed tokens: {unique_tokens:,} | Total postings: {total_indexed_entries:,}")

        # Candidate Generation: L1 U L2 U L3(Policy)
        t_gen = time.time()
        cands_cum: Dict[str, Set[str]] = {}
        zero_cands = 0

        for s1_id, feat in s1_norm.items():
            c = feat['country']
            cnt = target_country_counts[c]
            cands = set(cands_L1_L2[s1_id])  # Start with L1 U L2

            locs = feat['loc_tokens']
            if locs:
                if pol == "Policy_8C_QueryAware":
                    cutoff = int(cnt * 0.05)
                    locs_sorted = sorted(locs, key=lambda l: (freq_loc_token[c][l], len(l)))
                    rare_query = [loc for loc in locs_sorted if freq_loc_token[c][loc] <= cutoff]
                    if rare_query:
                        for loc in rare_query:
                            if loc in idx_F[c]:
                                cands.update(idx_F[c][loc])
                    else:
                        rarest = locs_sorted[0]
                        if rarest in idx_F[c]:
                            cands.update(idx_F[c][rarest])
                else:
                    for loc in locs:
                        if loc in idx_F[c]:
                            cands.update(idx_F[c][loc])

            if len(cands) == 0:
                zero_cands += 1
            cands_cum[s1_id] = cands

        gen_time = time.time() - t_gen
        pol_total_time = time.time() - t_pol_start

        # Compute full metrics
        m = compute_detailed_metrics(cands_cum, gt_matches, total_true_pairs, total_s1)
        m['policy'] = pol
        m['runtime_sec'] = pol_total_time
        m['zero_candidate_s1'] = zero_cands
        m['total_postings'] = total_indexed_entries

        # Analyze Missed Pairs
        missed_set = set()
        for s1_id, targets in gt_matches.items():
            for t_id in targets:
                if t_id not in cands_cum[s1_id]:
                    missed_set.add((s1_id, t_id))

        m['missed_pairs_count'] = len(missed_set)
        recovered_from_e6_losses = exp6_cutoff_losses - missed_set
        recovered_from_baseline_19 = baseline_misses_pairs - missed_set
        m['recovered_exp6_cutoff_losses'] = len(recovered_from_e6_losses)
        m['recovered_baseline_19'] = len(recovered_from_baseline_19)

        # Marginal candidate cost vs L1_L2 backbone
        marginal_cands_vs_backbone = m['total_candidates'] - m_l1_l2['total_candidates']
        marginal_tp_vs_backbone = m['recalled_pairs'] - m_l1_l2['recalled_pairs']
        cands_per_tp = marginal_cands_vs_backbone / marginal_tp_vs_backbone if marginal_tp_vs_backbone > 0 else 0
        m['cands_per_recovered_tp'] = round(cands_per_tp, 1)

        policy_metrics_dict[pol] = m

        print(f"  Recall: {m['recall']} ({m['recalled_pairs']}/{total_true_pairs}) | Missed: {len(missed_set)}")
        print(f"  Avg Cands/S1: {m['avg_candidates']:.1f} | Med: {m['median_candidates']} | P95: {m['p95_candidates']} | Max: {m['max_candidates']}")
        print(f"  Recovered from E6 Cutoff Losses (out of 9): {len(recovered_from_e6_losses)}/9")
        print(f"  Recovered from Baseline G 19 Misses: {len(recovered_from_baseline_19)}/19")
        print(f"  Marginal Efficiency: {m['cands_per_recovered_tp']:,} candidates / recovered true pair")
        print(f"  Time: {pol_total_time:.2f}s")

        results_table.append({
            'policy': pol,
            'recall': m['recall'],
            'recalled_pairs': m['recalled_pairs'],
            'missed_pairs': len(missed_set),
            'recovered_e6_losses': f"{len(recovered_from_e6_losses)}/9",
            'recovered_b19': f"{len(recovered_from_baseline_19)}/19",
            'avg_candidates': round(m['avg_candidates'], 1),
            'median_candidates': m['median_candidates'],
            'p90_candidates': m['p90_candidates'],
            'p95_candidates': m['p95_candidates'],
            'p99_candidates': m['p99_candidates'],
            'max_candidates': m['max_candidates'],
            'zero_candidates': zero_cands,
            'cands_per_tp': m['cands_per_recovered_tp'],
            'runtime_sec': round(pol_total_time, 2)
        })

    # Save metrics JSON
    with open(f"{RESULTS_DIR}/exp8_rare_location_metrics.json", 'w', encoding='utf-8') as f:
        json.dump(policy_metrics_dict, f, indent=2)

    # Save comparison TSV
    tsv_path = f"{RESULTS_DIR}/exp8_rare_location_comparison.tsv"
    with open(tsv_path, 'w', encoding='utf-8') as f:
        headers = list(results_table[0].keys())
        f.write('\t'.join(headers) + '\n')
        for row in results_table:
            f.write('\t'.join(str(row[h]) for h in headers) + '\n')

    print(f"\nSaved Experiment 8 comparison to {tsv_path}")
    print(f"Total Experiment 8 Runtime: {time.time()-t_start:.2f}s | Peak RAM: {get_ram_mb():.2f} MB")

if __name__ == '__main__':
    run_experiment_8()
