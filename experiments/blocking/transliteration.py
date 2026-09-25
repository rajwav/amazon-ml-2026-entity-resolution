"""
Experiment 4: Indic Script Transliteration Ablation Benchmark.
Evaluates 4 configurations on the identical 10k pilot:
1. BCDE - transliteration OFF
2. BCDE - transliteration ON
3. BCDEF - transliteration OFF
4. BCDEF - transliteration ON (Baseline G)

Performs detailed attribution analysis:
- Exact candidate set comparison with/without transliteration
- Identifies every true pair newly recovered because of transliteration
- Separately classifies recovery from name transliteration, address transliteration, or both
- Checks specifically whether transliteration recovers any of the 19 Baseline-G misses
- Reports non-true candidate bloat vs marginal true-pair gain
- Calculates marginal recall gain / marginal candidate increase
"""

import os
import sys
import gc
import time
import json
import collections
from typing import Dict, Set, Tuple, List

sys.path.append('.')
from src.preprocessing.normalization import normalize_business_name, normalize_business_address
from experiments.blocking.common import (
    load_pilot_raw,
    evaluate_blocking_candidates,
    get_ram_mb,
    RESULTS_DIR,
    DATA_DIR
)

def run_experiment_4():
    t_start = time.time()
    ram_init = get_ram_mb()
    print("=================================================================")
    print("EXPERIMENT 4: INDIC SCRIPT TRANSLITERATION ABLATION BENCHMARK")
    print("=================================================================")
    print(f"Initial RAM: {ram_init:.2f} MB")

    # 1. Load raw pilot data
    t0 = time.time()
    s1_raw, target_raw, gt_matches, total_true_pairs = load_pilot_raw()

    # Load baseline metrics to verify
    with open(f"{RESULTS_DIR}/baseline_g_metrics.json", 'r', encoding='utf-8') as f:
        baseline_metrics = json.load(f)
    print(f"Loaded raw data ({len(s1_raw)} S1s, {len(target_raw)} targets, {total_true_pairs} true pairs) in {time.time()-t0:.2f}s")

    # 2. Pre-compute Normalized Representations: ON vs OFF
    print("\nNormalizing records with Transliteration ON and OFF...")
    t0 = time.time()

    def normalize_corpus(enable_translit: bool):
        s1_map = {}
        for eid, parts in s1_raw.items():
            bname, baddr, country = parts[1], parts[2], parts[3]
            core, legal, sig_tokens, ngrams = normalize_business_name(bname, enable_transliteration=enable_translit)
            norm_addr, digits, loc_tokens = normalize_business_address(baddr, enable_transliteration=enable_translit)
            prefix4 = core[:4] if len(core) >= 4 else core
            s1_map[eid] = {
                'id': eid,
                'country': country,
                'core': core,
                'tokens': tuple(sig_tokens),
                'prefix4': prefix4,
                'digits': tuple(digits),
                'loc_tokens': tuple(loc_tokens)
            }

        target_map = {}
        for eid, parts in target_raw.items():
            bname, baddr, country = parts[1], parts[2], parts[3]
            core, legal, sig_tokens, ngrams = normalize_business_name(bname, enable_transliteration=enable_translit)
            norm_addr, digits, loc_tokens = normalize_business_address(baddr, enable_transliteration=enable_translit)
            prefix4 = core[:4] if len(core) >= 4 else core
            target_map[eid] = {
                'id': eid,
                'country': country,
                'core': core,
                'tokens': tuple(sig_tokens),
                'prefix4': prefix4,
                'digits': tuple(digits),
                'loc_tokens': tuple(loc_tokens)
            }
        return s1_map, target_map

    s1_norm_on, target_norm_on = normalize_corpus(enable_translit=True)
    s1_norm_off, target_norm_off = normalize_corpus(enable_translit=False)
    print(f"Normalized ON and OFF variants in {time.time()-t0:.2f}s | RAM: {get_ram_mb():.2f} MB")

    # 3. Build Inverted Index Builder Function
    def build_indexes(target_map):
        idx_B = collections.defaultdict(lambda: collections.defaultdict(list))
        idx_C = collections.defaultdict(lambda: collections.defaultdict(list))
        idx_D = collections.defaultdict(lambda: collections.defaultdict(list))
        idx_E = collections.defaultdict(lambda: collections.defaultdict(list))
        idx_F = collections.defaultdict(lambda: collections.defaultdict(list))

        for eid, feat in target_map.items():
            c = feat['country']
            if feat['core']: idx_B[c][feat['core']].append(eid)
            for tok in feat['tokens']: idx_C[c][tok].append(eid)
            if feat['prefix4']: idx_D[c][feat['prefix4']].append(eid)
            for dig in feat['digits']: idx_E[c][dig].append(eid)
            for loc in feat['loc_tokens']: idx_F[c][loc].append(eid)
        return idx_B, idx_C, idx_D, idx_E, idx_F

    idx_on = build_indexes(target_norm_on)
    idx_off = build_indexes(target_norm_off)

    def generate_candidates(s1_map, indexes, channels):
        idx_B, idx_C, idx_D, idx_E, idx_F = indexes
        s1_candidates = {}
        for s1_id, feat in s1_map.items():
            c = feat['country']
            cands = set()

            if 'B' in channels and feat['core'] and feat['core'] in idx_B[c]:
                cands.update(idx_B[c][feat['core']])
            if 'C' in channels:
                for tok in feat['tokens']:
                    if tok in idx_C[c]: cands.update(idx_C[c][tok])
            if 'D' in channels and feat['prefix4'] and feat['prefix4'] in idx_D[c]:
                cands.update(idx_D[c][feat['prefix4']])
            if 'E' in channels:
                for dig in feat['digits']:
                    if dig in idx_E[c]: cands.update(idx_E[c][dig])
            if 'F' in channels:
                for loc in feat['loc_tokens']:
                    if loc in idx_F[c]: cands.update(idx_F[c][loc])

            s1_candidates[s1_id] = cands
        return s1_candidates

    # 4. Generate Candidate Sets and Evaluate
    configs = [
        ('1_BCDE_translit_OFF', 'B+C+D+E (Transliteration OFF)', False, ['B', 'C', 'D', 'E']),
        ('2_BCDE_translit_ON',  'B+C+D+E (Transliteration ON)',  True,  ['B', 'C', 'D', 'E']),
        ('3_BCDEF_translit_OFF','B+C+D+E+F (Transliteration OFF)',False, ['B', 'C', 'D', 'E', 'F']),
        ('4_BCDEF_translit_ON', 'B+C+D+E+F (Transliteration ON / Base G)', True, ['B', 'C', 'D', 'E', 'F']),
    ]

    exp_results = []
    recalled_pairs_by_cfg = {}
    candidate_stats_by_cfg = {}

    # --- Run Stage 1: BCDE Comparison ---
    print("\n--- Running BCDE Configurations ---")
    
    # Config 1: BCDE OFF
    t_cfg = time.time()
    cands_bcde_off = generate_candidates(s1_norm_off, idx_off, ['B', 'C', 'D', 'E'])
    dt1 = time.time() - t_cfg
    m1, _ = evaluate_blocking_candidates(
        '1_BCDE_translit_OFF', 'B+C+D+E (Transliteration OFF)',
        cands_bcde_off, gt_matches, total_true_pairs, len(target_norm_off),
        dt1, get_ram_mb(), s1_norm_off, target_norm_off
    )
    exp_results.append(m1)
    rec1 = set((s, m) for s, ms in gt_matches.items() for m in ms if m in cands_bcde_off.get(s, set()))
    recalled_pairs_by_cfg['1_BCDE_translit_OFF'] = rec1
    tot_cands_bcde_off = sum(len(v) for v in cands_bcde_off.values())

    # Config 2: BCDE ON
    t_cfg = time.time()
    cands_bcde_on = generate_candidates(s1_norm_on, idx_on, ['B', 'C', 'D', 'E'])
    dt2 = time.time() - t_cfg
    m2, _ = evaluate_blocking_candidates(
        '2_BCDE_translit_ON', 'B+C+D+E (Transliteration ON)',
        cands_bcde_on, gt_matches, total_true_pairs, len(target_norm_on),
        dt2, get_ram_mb(), s1_norm_on, target_norm_on
    )
    exp_results.append(m2)
    rec2 = set((s, m) for s, ms in gt_matches.items() for m in ms if m in cands_bcde_on.get(s, set()))
    recalled_pairs_by_cfg['2_BCDE_translit_ON'] = rec2
    tot_cands_bcde_on = sum(len(v) for v in cands_bcde_on.values())

    # Candidate set comparison for BCDE
    newly_added_cands_bcde = 0
    dropped_cands_bcde = 0
    for s in s1_raw:
        c_off = cands_bcde_off.get(s, set())
        c_on = cands_bcde_on.get(s, set())
        newly_added_cands_bcde += len(c_on - c_off)
        dropped_cands_bcde += len(c_off - c_on)

    candidate_stats_by_cfg['BCDE'] = {
        'total_off': tot_cands_bcde_off,
        'total_on': tot_cands_bcde_on,
        'newly_added': newly_added_cands_bcde,
        'dropped': dropped_cands_bcde,
        'net_change': tot_cands_bcde_on - tot_cands_bcde_off
    }

    # Free memory before running BCDEF
    del cands_bcde_off
    del cands_bcde_on
    gc.collect()

    # --- Run Stage 2: BCDEF Comparison ---
    print("\n--- Running BCDEF Configurations ---")
    
    # Config 3: BCDEF OFF
    t_cfg = time.time()
    cands_bcdef_off = generate_candidates(s1_norm_off, idx_off, ['B', 'C', 'D', 'E', 'F'])
    dt3 = time.time() - t_cfg
    m3, _ = evaluate_blocking_candidates(
        '3_BCDEF_translit_OFF', 'B+C+D+E+F (Transliteration OFF)',
        cands_bcdef_off, gt_matches, total_true_pairs, len(target_norm_off),
        dt3, get_ram_mb(), s1_norm_off, target_norm_off
    )
    exp_results.append(m3)
    rec3 = set((s, m) for s, ms in gt_matches.items() for m in ms if m in cands_bcdef_off.get(s, set()))
    recalled_pairs_by_cfg['3_BCDEF_translit_OFF'] = rec3
    tot_cands_bcdef_off = sum(len(v) for v in cands_bcdef_off.values())

    # Config 4: BCDEF ON (Baseline G)
    t_cfg = time.time()
    cands_bcdef_on = generate_candidates(s1_norm_on, idx_on, ['B', 'C', 'D', 'E', 'F'])
    dt4 = time.time() - t_cfg
    m4, _ = evaluate_blocking_candidates(
        '4_BCDEF_translit_ON', 'B+C+D+E+F (Transliteration ON / Base G)',
        cands_bcdef_on, gt_matches, total_true_pairs, len(target_norm_on),
        dt4, get_ram_mb(), s1_norm_on, target_norm_on
    )
    exp_results.append(m4)
    rec4 = set((s, m) for s, ms in gt_matches.items() for m in ms if m in cands_bcdef_on.get(s, set()))
    recalled_pairs_by_cfg['4_BCDEF_translit_ON'] = rec4
    tot_cands_bcdef_on = sum(len(v) for v in cands_bcdef_on.values())

    # Candidate set comparison for BCDEF
    newly_added_cands_bcdef = 0
    dropped_cands_bcdef = 0
    for s in s1_raw:
        c_off = cands_bcdef_off.get(s, set())
        c_on = cands_bcdef_on.get(s, set())
        newly_added_cands_bcdef += len(c_on - c_off)
        dropped_cands_bcdef += len(c_off - c_on)

    candidate_stats_by_cfg['BCDEF'] = {
        'total_off': tot_cands_bcdef_off,
        'total_on': tot_cands_bcdef_on,
        'newly_added': newly_added_cands_bcdef,
        'dropped': dropped_cands_bcdef,
        'net_change': tot_cands_bcdef_on - tot_cands_bcdef_off
    }

    # Free candidate sets
    del cands_bcdef_off
    del cands_bcdef_on
    gc.collect()

    # Verify Baseline G exact reproduction
    assert m4['recalled_pairs'] == baseline_metrics['recalled_pairs'], f"Expected {baseline_metrics['recalled_pairs']}, got {m4['recalled_pairs']}"
    assert m4['missed_pairs'] == baseline_metrics['missed_pairs'], f"Expected {baseline_metrics['missed_pairs']}, got {m4['missed_pairs']}"

    # Print summary metrics table
    print("\n" + "="*85)
    print("CONFIG SUMMARY TABLE")
    print("="*85)
    print(f"{'Config ID':<25} | {'Recall':<10} | {'Recalled':<9} | {'Missed':<6} | {'Avg Cand':<10} | {'P95':<6} | {'0-Cand':<6} | {'RAM'}")
    print("-" * 85)
    for m in exp_results:
        print(f"{m['experiment_id']:<25} | {m['recall']:<10} | {m['recalled_pairs']:<9} | {m['missed_pairs']:<6} | {m['avg_candidates']:<10.1f} | {m['p95_candidates']:<6} | {m['zero_candidate_s1']:<6} | {m['peak_memory_mb']:.1f}MB")
    print("="*85)

    # 5. Required Attribution Analysis
    print("\n=================================================================")
    print("DETAILED ATTRIBUTION ANALYSIS: TRANSLITERATION IMPACT")
    print("=================================================================")

    # A: BCDE Comparison (Transliteration ON vs OFF)
    rec_bcde_off = recalled_pairs_by_cfg['1_BCDE_translit_OFF']
    rec_bcde_on  = recalled_pairs_by_cfg['2_BCDE_translit_ON']
    newly_rec_bcde = rec_bcde_on - rec_bcde_off
    lost_by_translit_bcde = rec_bcde_off - rec_bcde_on

    stats_bcde = candidate_stats_by_cfg['BCDE']
    marginal_cands_bcde = stats_bcde['net_change']

    print(f"\n1. In the Core Backbone (BCDE):")
    print(f"   - Recall without Transliteration: {len(rec_bcde_off)/total_true_pairs*100:.4f}% ({len(rec_bcde_off)} pairs)")
    print(f"   - Recall with Transliteration:    {len(rec_bcde_on)/total_true_pairs*100:.4f}% ({len(rec_bcde_on)} pairs)")
    print(f"   - True Pairs Newly Recovered:    +{len(newly_rec_bcde)} pairs")
    print(f"   - True Pairs Lost by Translit:   -{len(lost_by_translit_bcde)} pairs")
    print(f"   - Net True Pair Gain:            +{len(newly_rec_bcde) - len(lost_by_translit_bcde)} pairs")
    print(f"   - Total Candidates OFF:          {stats_bcde['total_off']:,} (avg {stats_bcde['total_off']/10000:.1f}/S1)")
    print(f"   - Total Candidates ON:           {stats_bcde['total_on']:,} (avg {stats_bcde['total_on']/10000:.1f}/S1)")
    print(f"   - Candidates Newly Added:        +{stats_bcde['newly_added']:,}")
    print(f"   - Candidates Dropped:            -{stats_bcde['dropped']:,}")
    print(f"   - Net Candidate Change:          +{marginal_cands_bcde:,} (+{marginal_cands_bcde/10000:.1f} per S1)")
    non_true_bcde = stats_bcde['newly_added'] - len(newly_rec_bcde)
    print(f"   - Additional Non-True Candidates: +{non_true_bcde:,}")
    if len(newly_rec_bcde) > 0:
        ratio_bcde = non_true_bcde / len(newly_rec_bcde)
        print(f"   - Non-true added per True Pair:  {ratio_bcde:.1f} non-true candidates per 1 true pair gained")
        print(f"   - Marginal Gain / Cand Increase: {len(newly_rec_bcde) / max(1, stats_bcde['newly_added']):.6f}")

    # B: BCDEF Comparison (Transliteration ON vs OFF)
    rec_bcdef_off = recalled_pairs_by_cfg['3_BCDEF_translit_OFF']
    rec_bcdef_on  = recalled_pairs_by_cfg['4_BCDEF_translit_ON']
    newly_rec_bcdef = rec_bcdef_on - rec_bcdef_off
    lost_by_translit_bcdef = rec_bcdef_off - rec_bcdef_on

    stats_bcdef = candidate_stats_by_cfg['BCDEF']
    marginal_cands_bcdef = stats_bcdef['net_change']

    print(f"\n2. In the Full Multi-Channel System (BCDEF / Baseline G):")
    print(f"   - Recall without Transliteration: {len(rec_bcdef_off)/total_true_pairs*100:.4f}% ({len(rec_bcdef_off)} pairs)")
    print(f"   - Recall with Transliteration:    {len(rec_bcdef_on)/total_true_pairs*100:.4f}% ({len(rec_bcdef_on)} pairs)")
    print(f"   - True Pairs Newly Recovered:    +{len(newly_rec_bcdef)} pairs")
    print(f"   - True Pairs Lost by Translit:   -{len(lost_by_translit_bcdef)} pairs")
    print(f"   - Net True Pair Gain:            +{len(newly_rec_bcdef) - len(lost_by_translit_bcdef)} pairs")
    print(f"   - Total Candidates OFF:          {stats_bcdef['total_off']:,} (avg {stats_bcdef['total_off']/10000:.1f}/S1)")
    print(f"   - Total Candidates ON:           {stats_bcdef['total_on']:,} (avg {stats_bcdef['total_on']/10000:.1f}/S1)")
    print(f"   - Candidates Newly Added:        +{stats_bcdef['newly_added']:,}")
    print(f"   - Candidates Dropped:            -{stats_bcdef['dropped']:,}")
    print(f"   - Net Candidate Change:          +{marginal_cands_bcdef:,} (+{marginal_cands_bcdef/10000:.1f} per S1)")
    non_true_bcdef = stats_bcdef['newly_added'] - len(newly_rec_bcdef)
    print(f"   - Additional Non-True Candidates: +{non_true_bcdef:,}")
    if len(newly_rec_bcdef) > 0:
        ratio_bcdef = non_true_bcdef / len(newly_rec_bcdef)
        print(f"   - Non-true added per True Pair:  {ratio_bcdef:.1f} non-true candidates per 1 true pair gained")
        print(f"   - Marginal Gain / Cand Increase: {len(newly_rec_bcdef) / max(1, stats_bcdef['newly_added']):.6f}")

    # C: Classify Recovery Source (Name vs Address vs Both)
    # Check all newly recovered pairs across BCDE and BCDEF
    all_newly_rec = newly_rec_bcde | newly_rec_bcdef
    recovered_name_only = 0
    recovered_addr_only = 0
    recovered_both = 0
    recovered_other = 0

    translit_details_list = []

    for s1_id, mid in all_newly_rec:
        s1_raw_row = s1_raw[s1_id]
        t_raw_row = target_raw[mid]

        f1_on = s1_norm_on[s1_id]
        f2_on = target_norm_on[mid]

        f1_off = s1_norm_off[s1_id]
        f2_off = target_norm_off[mid]

        # Check if name matched because of transliteration
        name_matched_on = (f1_on['core'] and f1_on['core'] == f2_on['core']) or bool(set(f1_on['tokens']) & set(f2_on['tokens'])) or (f1_on['prefix4'] and f1_on['prefix4'] == f2_on['prefix4'])
        name_matched_off = (f1_off['core'] and f1_off['core'] == f2_off['core']) or bool(set(f1_off['tokens']) & set(f2_off['tokens'])) or (f1_off['prefix4'] and f1_off['prefix4'] == f2_off['prefix4'])
        name_caused = name_matched_on and not name_matched_off

        # Check if address matched because of transliteration
        addr_matched_on = bool(set(f1_on['digits']) & set(f2_on['digits'])) or bool(set(f1_on['loc_tokens']) & set(f2_on['loc_tokens']))
        addr_matched_off = bool(set(f1_off['digits']) & set(f2_off['digits'])) or bool(set(f1_off['loc_tokens']) & set(f2_off['loc_tokens']))
        addr_caused = addr_matched_on and not addr_matched_off

        if name_caused and addr_caused:
            source_type = "BOTH"
            recovered_both += 1
        elif name_caused:
            source_type = "NAME_TRANSLITERATION"
            recovered_name_only += 1
        elif addr_caused:
            source_type = "ADDRESS_TRANSLITERATION"
            recovered_addr_only += 1
        else:
            source_type = "OTHER_NORM_EFFECT"
            recovered_other += 1

        in_bcde = (s1_id, mid) in newly_rec_bcde
        in_bcdef = (s1_id, mid) in newly_rec_bcdef

        translit_details_list.append({
            's1_id': s1_id,
            'target_id': mid,
            'source_type': source_type,
            'recovered_in_bcde': in_bcde,
            'recovered_in_bcdef': in_bcdef,
            's1_name': s1_raw_row[1],
            'target_name': t_raw_row[1],
            's1_addr': s1_raw_row[2],
            'target_addr': t_raw_row[2]
        })

    print(f"\n3. Source Classification for Newly Recovered Pairs ({len(all_newly_rec)} total pairs):")
    print(f"   - Name Transliteration Only:    {recovered_name_only} pairs ({recovered_name_only/max(1, len(all_newly_rec))*100:.1f}%)")
    print(f"   - Address Transliteration Only: {recovered_addr_only} pairs ({recovered_addr_only/max(1, len(all_newly_rec))*100:.1f}%)")
    print(f"   - Both Name and Address:        {recovered_both} pairs ({recovered_both/max(1, len(all_newly_rec))*100:.1f}%)")
    if recovered_other > 0:
        print(f"   - Other Normalization Effects:  {recovered_other} pairs")

    # D: Did Transliteration recover any of the 19 Baseline-G Misses?
    with open(f"{RESULTS_DIR}/baseline_g_missed_pairs.tsv", 'r', encoding='utf-8') as f:
        next(f)
        baseline_misses_pairs = set()
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            baseline_misses_pairs.add((parts[1], parts[2]))

    recovered_from_19_misses = newly_rec_bcdef & baseline_misses_pairs
    print(f"\n4. Recovery of the 19 Baseline-G Misses:")
    print(f"   - Baseline G Misses count: {len(baseline_misses_pairs)}")
    print(f"   - Did transliteration recover any of the 19 Baseline-G misses? {'YES: ' + str(len(recovered_from_19_misses)) if recovered_from_19_misses else 'NO: 0 pairs (Baseline G is with transliteration ON)'}")

    # Check whether turning transliteration OFF in Baseline G loses pairs
    pairs_lost_if_translit_off_in_g = rec_bcdef_on - rec_bcdef_off
    print(f"   - Pairs lost from Baseline G if transliteration is turned OFF: {len(pairs_lost_if_translit_off_in_g)} pairs")

    # Save detailed complement log
    with open(f"{RESULTS_DIR}/exp4_transliteration_recovered_pairs.tsv", 'w', encoding='utf-8') as f:
        f.write("s1_id\ttarget_id\tsource_type\trecovered_in_bcde\trecovered_in_bcdef\ts1_name\ttarget_name\ts1_address\ttarget_address\n")
        for r in translit_details_list:
            f.write(f"{r['s1_id']}\t{r['target_id']}\t{r['source_type']}\t{r['recovered_in_bcde']}\t{r['recovered_in_bcdef']}\t{r['s1_name']}\t{r['target_name']}\t{r['s1_addr']}\t{r['target_addr']}\n")

    with open(f"{RESULTS_DIR}/exp4_transliteration_metrics.json", 'w', encoding='utf-8') as f:
        json.dump(exp_results, f, indent=2)

    print(f"\nSaved metrics to {RESULTS_DIR}/exp4_transliteration_metrics.json")
    print(f"Saved recovered pairs details to {RESULTS_DIR}/exp4_transliteration_recovered_pairs.tsv")
    print(f"Experiment 4 completed in {time.time()-t_start:.2f}s | Final RAM: {get_ram_mb():.2f} MB")

    return exp_results, translit_details_list

if __name__ == '__main__':
    run_experiment_4()
