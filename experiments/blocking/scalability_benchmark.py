"""
Experiment 7: Scalability & Robustness Testing Benchmark.
Progressively benchmarks the Experiment 6 hierarchical blocker across increasing dataset scales:
1. 10k S1 (Reference Baseline from Exp 6)
2. 25k S1 (~211k target pool, ~86k true pairs)
3. 50k S1 (~423k target pool, ~173k true pairs)
4. France Test Split Robustness & Candidate Distribution Check

Maintains the exact validated Experiment 6 architecture:
- Level 1: Composite Sieve (C2_Union_All)
- Level 2: Core Backbone (B+C+D+E with selective transliteration)
- Level 3: Target-side 5% IDF-filtered Channel F (unsuppressed query evaluation)
Uses streaming evaluation to guarantee bounded memory (< 900 MB RAM).
"""

import os
import sys
import gc
import time
import json
import random
import collections
from typing import Dict, Set, Tuple, List, Any

sys.path.append('.')
from src.preprocessing.normalization import normalize_business_name, normalize_business_address
from experiments.blocking.common import get_ram_mb, RESULTS_DIR

TRAIN_S1 = 'student_resource/dataset/train/train_source1.tsv'
TRAIN_S2 = 'student_resource/dataset/train/train_source2.tsv'
TRAIN_S3 = 'student_resource/dataset/train/train_source3.tsv'
TRAIN_GT = 'student_resource/dataset/train/train_ground_truth.tsv'

TEST_S1 = 'student_resource/dataset/test/test_source1.tsv'
TEST_S2 = 'student_resource/dataset/test/test_source2.tsv'
TEST_S3 = 'student_resource/dataset/test/test_source3.tsv'

def extract_scale_sample(N: int, seed: int = 42):
    """
    Extract a representative sample of N S1 entities, stratified by country and match count,
    along with all their true target records and a proportional set of distractors (ratio 5:1).
    """
    random.seed(seed)
    t0 = time.time()
    print(f"\nExtracting stratified sample for N = {N:,} (seed={seed})...")

    # 1. Read S1 country map
    s1_country_map = {}
    with open(TRAIN_S1, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            s1_country_map[parts[0]] = parts[3]

    # 2. Categorize S1 entities from ground truth
    us_zero, us_one, us_multi = [], [], []
    in_zero, in_one, in_multi = [], [], []
    s1_to_gt = {}

    with open(TRAIN_GT, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            s1_id, tab, rest = line.rstrip('\r\n').partition('\t')
            c = s1_country_map.get(s1_id, '')
            mids = [x.strip() for x in rest.split(',') if x.strip()] if rest.strip() else []
            n_m = len(mids)
            s1_to_gt[s1_id] = mids
            if c == 'US':
                if n_m == 0: us_zero.append(s1_id)
                elif n_m == 1: us_one.append(s1_id)
                else: us_multi.append(s1_id)
            elif c == 'India':
                if n_m == 0: in_zero.append(s1_id)
                elif n_m == 1: in_one.append(s1_id)
                else: in_multi.append(s1_id)

    n_us = int(N * 0.60)
    n_in = int(N * 0.40)

    # Stratified sampling matching ground-truth distribution (5.58% 0-match, 5.40% 1-match, 89.02% multi-match)
    us_sample = (
        random.sample(us_zero, int(n_us * 0.0558)) +
        random.sample(us_one, int(n_us * 0.0540)) +
        random.sample(us_multi, n_us - int(n_us * 0.0558) - int(n_us * 0.0540))
    )
    in_sample = (
        random.sample(in_zero, int(n_in * 0.0558)) +
        random.sample(in_one, int(n_in * 0.0540)) +
        random.sample(in_multi, n_in - int(n_in * 0.0558) - int(n_in * 0.0540))
    )

    sampled_s1_ids = set(us_sample + in_sample)
    assert len(sampled_s1_ids) == N

    # Identify needed targets
    needed_targets = set()
    total_true_pairs = 0
    gt_matches = {}
    for s in sampled_s1_ids:
        mids = s1_to_gt[s]
        gt_matches[s] = mids
        total_true_pairs += len(mids)
        for m in mids:
            needed_targets.add(m)

    needed_s2 = {m for m in needed_targets if m.startswith('S2-')}
    needed_s3 = {m for m in needed_targets if m.startswith('S3-')}

    # Read S1 raw records
    s1_raw = {}
    with open(TRAIN_S1, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            while len(parts) < 4: parts.append('')
            if parts[0] in sampled_s1_ids:
                s1_raw[parts[0]] = parts
                if len(s1_raw) == N: break

    # Read Target records (all true matches + proportional distractors: 2.5 per S1 from S2, 2.5 from S3)
    target_distractor_budget = int(N * 2.5)
    target_raw = {}
    step_s2 = max(1, 5000000 // target_distractor_budget)
    step_s3 = max(1, 5200000 // target_distractor_budget)

    with open(TRAIN_S2, 'r', encoding='utf-8') as f:
        next(f)
        s2_dist_count = 0
        for i, line in enumerate(f):
            parts = line.rstrip('\r\n').split('\t')
            while len(parts) < 4: parts.append('')
            eid = parts[0]
            if eid in needed_s2:
                target_raw[eid] = parts
            elif s2_dist_count < target_distractor_budget and (i % step_s2 == 0):
                target_raw[eid] = parts
                s2_dist_count += 1

    with open(TRAIN_S3, 'r', encoding='utf-8') as f:
        next(f)
        s3_dist_count = 0
        for i, line in enumerate(f):
            parts = line.rstrip('\r\n').split('\t')
            while len(parts) < 4: parts.append('')
            eid = parts[0]
            if eid in needed_s3:
                target_raw[eid] = parts
            elif s3_dist_count < target_distractor_budget and (i % step_s3 == 0):
                target_raw[eid] = parts
                s3_dist_count += 1

    print(f"Sample ready: {len(s1_raw):,} S1s, {len(target_raw):,} Targets, {total_true_pairs:,} True Pairs in {time.time()-t0:.2f}s | RAM: {get_ram_mb():.2f} MB")
    return s1_raw, target_raw, gt_matches, total_true_pairs

def run_pipeline_streaming(scale_name: str, s1_raw: dict, target_raw: dict, gt_matches: dict, total_true_pairs: int):
    """
    Execute Experiment 6 Hierarchical Pipeline using streaming evaluation.
    Keeps RAM strictly bounded to index size.
    """
    t_start = time.time()
    n_s1 = len(s1_raw)
    n_targets = len(target_raw)
    print(f"\n=================================================================")
    print(f"STREAMING BENCHMARK ON {scale_name} ({n_s1:,} S1s, {n_targets:,} Targets)")
    print(f"=================================================================")

    # 1. Normalize Records with Selective Transliteration
    t0 = time.time()
    s1_norm = {}
    for eid, parts in s1_raw.items():
        bname, baddr, country = parts[1], parts[2], parts[3]
        core, legal, sig_tokens, _ = normalize_business_name(bname, enable_transliteration=True)
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
        core, legal, sig_tokens, _ = normalize_business_name(bname, enable_transliteration=True)
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

    dt_norm = time.time() - t0
    print(f"Normalized in {dt_norm:.2f}s | RAM: {get_ram_mb():.2f} MB")

    # 2. Determine E1-B Filtered Location Tokens (Cutoff > 5% of target country pool)
    filtered_loc_tokens = collections.defaultdict(set)
    for c, cnt in target_country_counts.items():
        cutoff = int(cnt * 0.05)
        for loc, f in freq_loc_token[c].items():
            if f <= cutoff:
                filtered_loc_tokens[c].add(loc)

    # 3. Build Inverted Indexes for L1, L2, L3
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
    idx_F_filtered = collections.defaultdict(lambda: collections.defaultdict(list))

    for eid, feat in target_norm.items():
        c = feat['country']
        # Single (L2)
        if feat['core']:
            idx_exact_name[c][feat['core']].append(eid)
            idx_B[c][feat['core']].append(eid)
        for tok in feat['tokens']:
            idx_C[c][tok].append(eid)
        if feat['prefix4']:
            idx_D[c][feat['prefix4']].append(eid)
        for dig in feat['digits']:
            idx_E[c][dig].append(eid)

        # L3 Filtered F
        for loc in feat['loc_tokens']:
            if loc in filtered_loc_tokens[c]:
                idx_F_filtered[c][loc].append(eid)

        # L1 Composites
        for tok in feat['tokens']:
            for loc in feat['loc_tokens']:
                idx_tok_loc[c][(tok, loc)].append(eid)
            for dig in feat['digits']:
                idx_tok_dig[c][(tok, dig)].append(eid)
        if feat['prefix4']:
            for loc in feat['loc_tokens']:
                idx_pref_loc[c][(feat['prefix4'], loc)].append(eid)
            for dig in feat['digits']:
                idx_pref_dig[c][(feat['prefix4'], dig)].append(eid)
        for dig in feat['digits']:
            for loc in feat['loc_tokens']:
                idx_dig_loc[c][(dig, loc)].append(eid)

    dt_index = time.time() - t0
    print(f"Indexed in {dt_index:.2f}s | RAM: {get_ram_mb():.2f} MB")

    # 4. Streaming Candidate Generation & Recall Tracking
    t0 = time.time()
    recalled_L1 = set()
    recalled_L2 = set()
    recalled_final = set()

    final_cand_counts = []
    zero_cand_s1 = 0
    total_candidates = 0

    mm_s1_total = 0
    mm_pairs_total = 0
    mm_pairs_recalled = 0
    mm_partial_s1 = 0

    for s1_id, feat in s1_norm.items():
        c = feat['country']
        true_m = gt_matches.get(s1_id, [])

        # --- Level 1: Composite Sieve ---
        cands_L1 = set()
        if feat['core'] and feat['core'] in idx_exact_name[c]:
            cands_L1.update(idx_exact_name[c][feat['core']])
        for tok in feat['tokens']:
            for loc in feat['loc_tokens']:
                p = (tok, loc)
                if p in idx_tok_loc[c]: cands_L1.update(idx_tok_loc[c][p])
            for dig in feat['digits']:
                p = (tok, dig)
                if p in idx_tok_dig[c]: cands_L1.update(idx_tok_dig[c][p])
        if feat['prefix4']:
            for loc in feat['loc_tokens']:
                p = (feat['prefix4'], loc)
                if p in idx_pref_loc[c]: cands_L1.update(idx_pref_loc[c][p])
            for dig in feat['digits']:
                p = (feat['prefix4'], dig)
                if p in idx_pref_dig[c]: cands_L1.update(idx_pref_dig[c][p])
        for dig in feat['digits']:
            for loc in feat['loc_tokens']:
                p = (dig, loc)
                if p in idx_dig_loc[c]: cands_L1.update(idx_dig_loc[c][p])

        for m in true_m:
            if m in cands_L1:
                recalled_L1.add((s1_id, m))

        # --- Level 2: Core Backbone B+C+D+E ---
        cands_L2 = set(cands_L1)
        if feat['core'] and feat['core'] in idx_B[c]:
            cands_L2.update(idx_B[c][feat['core']])
        for tok in feat['tokens']:
            if tok in idx_C[c]: cands_L2.update(idx_C[c][tok])
        if feat['prefix4'] and feat['prefix4'] in idx_D[c]:
            cands_L2.update(idx_D[c][feat['prefix4']])
        for dig in feat['digits']:
            if dig in idx_E[c]: cands_L2.update(idx_E[c][dig])

        for m in true_m:
            if m in cands_L2:
                recalled_L2.add((s1_id, m))

        # --- Level 3: Filtered Channel F ---
        cands_final = set(cands_L2)
        for loc in feat['loc_tokens']:
            if loc in idx_F_filtered[c]:
                cands_final.update(idx_F_filtered[c][loc])

        k = len(cands_final)
        final_cand_counts.append(k)
        total_candidates += k
        if k == 0: zero_cand_s1 += 1

        rec_for_s1 = 0
        for m in true_m:
            if m in cands_final:
                recalled_final.add((s1_id, m))
                rec_for_s1 += 1

        if len(true_m) >= 2:
            mm_s1_total += 1
            mm_pairs_total += len(true_m)
            mm_pairs_recalled += rec_for_s1
            if 0 < rec_for_s1 < len(true_m):
                mm_partial_s1 += 1

    dt_eval = time.time() - t0

    # Summary Stats
    final_cand_counts.sort()
    med_c = final_cand_counts[n_s1 // 2]
    p90_c = final_cand_counts[int(n_s1 * 0.90)]
    p95_c = final_cand_counts[int(n_s1 * 0.95)]
    p99_c = final_cand_counts[int(n_s1 * 0.99)]
    max_c = final_cand_counts[-1]
    avg_c = total_candidates / n_s1

    rec_L1_pct = len(recalled_L1) / total_true_pairs * 100.0
    rec_L2_pct = len(recalled_L2) / total_true_pairs * 100.0
    rec_final_pct = len(recalled_final) / total_true_pairs * 100.0

    total_possible = n_s1 * n_targets
    reduct_ratio = (1.0 - (total_candidates / total_possible)) * 100.0
    dt_total = time.time() - t_start
    peak_ram = get_ram_mb()

    metrics = {
        'scale': scale_name,
        's1_rows': n_s1,
        'target_rows': n_targets,
        'ground_truth_pairs': total_true_pairs,
        'L1_recall': f"{rec_L1_pct:.4f}%",
        'L1_recalled_pairs': len(recalled_L1),
        'L2_recall': f"{rec_L2_pct:.4f}%",
        'L2_recalled_pairs': len(recalled_L2),
        'L3_final_recall': f"{rec_final_pct:.4f}%",
        'L3_recalled_pairs': len(recalled_final),
        'missed_pairs': total_true_pairs - len(recalled_final),
        'total_candidates': total_candidates,
        'avg_candidates': avg_c,
        'median_candidates': med_c,
        'p90_candidates': p90_c,
        'p95_candidates': p95_c,
        'p99_candidates': p99_c,
        'max_candidates': max_c,
        'zero_candidate_s1': zero_cand_s1,
        'candidate_reduction_ratio': f"{reduct_ratio:.4f}%",
        'runtime_norm_sec': dt_norm,
        'runtime_index_sec': dt_index,
        'runtime_eval_sec': dt_eval,
        'total_runtime_sec': dt_total,
        'peak_ram_mb': peak_ram,
        'multi_match_s1_total': mm_s1_total,
        'multi_match_pairs_recalled_pct': f"{(mm_pairs_recalled / mm_pairs_total)*100:.4f}%" if mm_pairs_total else "0.0%",
        'multi_match_partial_s1_pct': f"{(mm_partial_s1 / mm_s1_total)*100:.2f}%" if mm_s1_total else "0.0%"
    }

    print(f"\n{scale_name} Results Summary:")
    print(f"  Recall (L1 -> L2 -> Final L3): {metrics['L1_recall']} -> {metrics['L2_recall']} -> {metrics['L3_final_recall']} ({len(recalled_final):,}/{total_true_pairs:,} true pairs)")
    print(f"  Missed Pairs:                  {metrics['missed_pairs']:,}")
    print(f"  Total Candidates:              {total_candidates:,} (Avg {avg_c:.1f}/S1)")
    print(f"  P50 / P90 / P95 / P99 / Max:   {med_c} / {p90_c} / {p95_c} / {p99_c} / {max_c}")
    print(f"  Zero-Candidate S1s:            {zero_cand_s1}")
    print(f"  Candidate Reduction:           {metrics['candidate_reduction_ratio']}")
    print(f"  Multi-Match Recall:            {metrics['multi_match_pairs_recalled_pct']} (Partials: {mm_partial_s1}/{mm_s1_total} = {metrics['multi_match_partial_s1_pct']})")
    print(f"  Runtime: Norm={dt_norm:.1f}s, Index={dt_index:.1f}s, Eval={dt_eval:.1f}s | Total = {dt_total:.1f}s")
    print(f"  Peak RAM:                      {peak_ram:.2f} MB")

    return metrics

def run_france_robustness_test():
    """
    Test French normalization and candidate generation behavior on a real test split sample.
    """
    print("\n=================================================================")
    print("RUNNING FRANCE TEST SET ROBUSTNESS VALIDATION")
    print("=================================================================")
    t0 = time.time()

    # Read sample of French S1 records (up to 5,000)
    fr_s1_raw = {}
    with open(TEST_S1, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            while len(parts) < 4: parts.append('')
            if parts[3] == 'France':
                fr_s1_raw[parts[0]] = parts
                if len(fr_s1_raw) >= 5000: break

    # Read sample of French Target records (up to 25,000 from S2 and 25,000 from S3)
    fr_target_raw = {}
    with open(TEST_S2, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            while len(parts) < 4: parts.append('')
            if parts[3] == 'France':
                fr_target_raw[parts[0]] = parts
                if len(fr_target_raw) >= 25000: break

    with open(TEST_S3, 'r', encoding='utf-8') as f:
        next(f)
        s3_cnt = 0
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            while len(parts) < 4: parts.append('')
            if parts[3] == 'France':
                fr_target_raw[parts[0]] = parts
                s3_cnt += 1
                if s3_cnt >= 25000: break

    print(f"Loaded France test sample: {len(fr_s1_raw):,} S1s, {len(fr_target_raw):,} Targets in {time.time()-t0:.2f}s")

    # Run French Normalization
    fr_s1_norm = {}
    legal_suffix_detected = collections.Counter()
    for eid, parts in fr_s1_raw.items():
        core, legal, sig_tokens, _ = normalize_business_name(parts[1], enable_transliteration=True)
        _, digits, _ = normalize_business_address(parts[2], enable_transliteration=True)
        _, _, loc_tokens = normalize_business_address(parts[2], enable_transliteration=False)
        prefix4 = core[:4] if len(core) >= 4 else core
        fr_s1_norm[eid] = {
            'id': eid,
            'country': 'France',
            'core': core,
            'legal': legal,
            'tokens': tuple(sig_tokens),
            'prefix4': prefix4,
            'digits': tuple(digits),
            'loc_tokens': tuple(loc_tokens)
        }
        if legal: legal_suffix_detected[legal] += 1

    fr_target_norm = {}
    freq_fr_loc = collections.Counter()
    for eid, parts in fr_target_raw.items():
        core, legal, sig_tokens, _ = normalize_business_name(parts[1], enable_transliteration=True)
        _, digits, _ = normalize_business_address(parts[2], enable_transliteration=True)
        _, _, loc_tokens = normalize_business_address(parts[2], enable_transliteration=False)
        prefix4 = core[:4] if len(core) >= 4 else core
        fr_target_norm[eid] = {
            'id': eid,
            'country': 'France',
            'core': core,
            'tokens': tuple(sig_tokens),
            'prefix4': prefix4,
            'digits': tuple(digits),
            'loc_tokens': tuple(loc_tokens)
        }
        for loc in loc_tokens:
            freq_fr_loc[loc] += 1

    # Filter French location tokens (5% cutoff)
    cutoff_fr = int(len(fr_target_raw) * 0.05)
    filtered_fr_loc = {loc for loc, cnt in freq_fr_loc.items() if cnt <= cutoff_fr}

    # Build French Indexes for L1, L2, L3
    idx_exact_name = collections.defaultdict(list)
    idx_tok_loc = collections.defaultdict(list)
    idx_tok_dig = collections.defaultdict(list)
    idx_pref_loc = collections.defaultdict(list)
    idx_pref_dig = collections.defaultdict(list)
    idx_dig_loc = collections.defaultdict(list)

    idx_B = collections.defaultdict(list)
    idx_C = collections.defaultdict(list)
    idx_D = collections.defaultdict(list)
    idx_E = collections.defaultdict(list)
    idx_F = collections.defaultdict(list)

    for eid, feat in fr_target_norm.items():
        if feat['core']:
            idx_exact_name[feat['core']].append(eid)
            idx_B[feat['core']].append(eid)
        for tok in feat['tokens']: idx_C[tok].append(eid)
        if feat['prefix4']: idx_D[feat['prefix4']].append(eid)
        for dig in feat['digits']: idx_E[dig].append(eid)
        for loc in feat['loc_tokens']:
            if loc in filtered_fr_loc:
                idx_F[loc].append(eid)

        for tok in feat['tokens']:
            for loc in feat['loc_tokens']: idx_tok_loc[(tok, loc)].append(eid)
            for dig in feat['digits']: idx_tok_dig[(tok, dig)].append(eid)
        if feat['prefix4']:
            for loc in feat['loc_tokens']: idx_pref_loc[(feat['prefix4'], loc)].append(eid)
            for dig in feat['digits']: idx_pref_dig[(feat['prefix4'], dig)].append(eid)
        for dig in feat['digits']:
            for loc in feat['loc_tokens']: idx_dig_loc[(dig, loc)].append(eid)

    # Candidate generation across L1 U L2 U L3
    cand_counts = []
    zero_cands = 0
    total_c = 0
    for s1_id, feat in fr_s1_norm.items():
        cands = set()
        # L1
        if feat['core'] and feat['core'] in idx_exact_name: cands.update(idx_exact_name[feat['core']])
        for tok in feat['tokens']:
            for loc in feat['loc_tokens']:
                p = (tok, loc)
                if p in idx_tok_loc: cands.update(idx_tok_loc[p])
            for dig in feat['digits']:
                p = (tok, dig)
                if p in idx_tok_dig: cands.update(idx_tok_dig[p])
        if feat['prefix4']:
            for loc in feat['loc_tokens']:
                p = (feat['prefix4'], loc)
                if p in idx_pref_loc: cands.update(idx_pref_loc[p])
            for dig in feat['digits']:
                p = (feat['prefix4'], dig)
                if p in idx_pref_dig: cands.update(idx_pref_dig[p])
        for dig in feat['digits']:
            for loc in feat['loc_tokens']:
                p = (dig, loc)
                if p in idx_dig_loc: cands.update(idx_dig_loc[p])

        # L2
        if feat['core'] and feat['core'] in idx_B: cands.update(idx_B[feat['core']])
        for tok in feat['tokens']:
            if tok in idx_C: cands.update(idx_C[tok])
        if feat['prefix4'] and feat['prefix4'] in idx_D: cands.update(idx_D[feat['prefix4']])
        for dig in feat['digits']:
            if dig in idx_E: cands.update(idx_E[dig])

        # L3
        for loc in feat['loc_tokens']:
            if loc in idx_F: cands.update(idx_F[loc])

        k = len(cands)
        cand_counts.append(k)
        total_c += k
        if k == 0: zero_cands += 1

    cand_counts.sort()
    n = len(cand_counts)
    fr_metrics = {
        'scale': 'France_Test_Sample',
        's1_rows': len(fr_s1_raw),
        'target_rows': len(fr_target_raw),
        'legal_suffixes_detected': dict(legal_suffix_detected),
        'avg_candidates': total_c / n,
        'median_candidates': cand_counts[n // 2],
        'p90_candidates': cand_counts[int(n * 0.90)],
        'p95_candidates': cand_counts[int(n * 0.95)],
        'max_candidates': cand_counts[-1],
        'zero_candidate_s1': zero_cands,
        'candidate_reduction_ratio': f"{(1.0 - (total_c / (n * len(fr_target_raw)))) * 100:.4f}%"
    }

    print(f"France Validation Results:")
    print(f"  Legal Suffixes Identified:     {legal_suffix_detected.most_common(5)}")
    print(f"  Avg Candidates/S1:             {fr_metrics['avg_candidates']:.1f}")
    print(f"  Median / P95 / Max Candidates: {fr_metrics['median_candidates']} / {fr_metrics['p95_candidates']} / {fr_metrics['max_candidates']}")
    print(f"  Zero-Candidate S1s:            {zero_cands}")
    print(f"  Candidate Reduction:           {fr_metrics['candidate_reduction_ratio']}")
    return fr_metrics

def main():
    print("=================================================================")
    print("EXPERIMENT 7: SCALABILITY & ROBUSTNESS TESTING (PROGRESSIVE)")
    print("=================================================================")
    all_scale_metrics = []

    # 1. 10k Reference from Exp 6
    with open(f"{RESULTS_DIR}/exp6_hierarchical_pipeline_metrics.json", 'r', encoding='utf-8') as f:
        exp6_data = json.load(f)
    m10k_orig = exp6_data['benchmark_metrics'][-1]
    m10k = {
        'scale': '10k_S1',
        's1_rows': 10000,
        'target_rows': 84481,
        'ground_truth_pairs': 34481,
        'L1_recall': '95.6266%',
        'L2_recall': '98.0859%',
        'L3_final_recall': m10k_orig['recall'],
        'L3_recalled_pairs': m10k_orig['recalled_pairs'],
        'missed_pairs': m10k_orig['missed_pairs'],
        'total_candidates': m10k_orig['total_candidates'],
        'avg_candidates': m10k_orig['avg_candidates'],
        'median_candidates': m10k_orig['median_candidates'],
        'p90_candidates': m10k_orig['p90_candidates'],
        'p95_candidates': m10k_orig['p95_candidates'],
        'p99_candidates': m10k_orig['p99_candidates'],
        'max_candidates': m10k_orig['max_candidates'],
        'zero_candidate_s1': m10k_orig['zero_candidate_s1'],
        'candidate_reduction_ratio': m10k_orig['candidate_reduction_ratio'],
        'total_runtime_sec': m10k_orig['runtime_seconds'],
        'peak_ram_mb': m10k_orig['peak_memory_mb']
    }
    all_scale_metrics.append(m10k)

    # 2. Scale 25k S1
    s1_25, t_25, gt_25, tp_25 = extract_scale_sample(25000, seed=42)
    m25k = run_pipeline_streaming('25k_S1', s1_25, t_25, gt_25, tp_25)
    all_scale_metrics.append(m25k)
    del s1_25, t_25, gt_25
    gc.collect()

    # 3. Scale 50k S1
    s1_50, t_50, gt_50, tp_50 = extract_scale_sample(50000, seed=42)
    m50k = run_pipeline_streaming('50k_S1', s1_50, t_50, gt_50, tp_50)
    all_scale_metrics.append(m50k)
    del s1_50, t_50, gt_50
    gc.collect()

    # 4. France Robustness Check
    fr_metrics = run_france_robustness_test()

    # 5. Save Artifacts
    with open(f"{RESULTS_DIR}/exp7_scalability_metrics.json", 'w', encoding='utf-8') as f:
        json.dump({
            'scale_metrics': all_scale_metrics,
            'france_validation': fr_metrics
        }, f, indent=2)

    with open(f"{RESULTS_DIR}/exp7_scalability_comparison.tsv", 'w', encoding='utf-8') as f:
        f.write("scale\ts1_rows\ttarget_rows\tground_truth_pairs\tL1_recall\tL2_recall\tL3_final_recall\tmissed_pairs\ttotal_candidates\tavg_candidates\tmedian_candidates\tp90_candidates\tp95_candidates\tp99_candidates\tmax_candidates\tzero_candidate_s1\tcandidate_reduction_ratio\ttotal_runtime_sec\tpeak_ram_mb\n")
        for m in all_scale_metrics:
            f.write(f"{m['scale']}\t{m['s1_rows']}\t{m['target_rows']}\t{m['ground_truth_pairs']}\t{m['L1_recall']}\t{m['L2_recall']}\t{m['L3_final_recall']}\t{m['missed_pairs']}\t{m['total_candidates']}\t{m['avg_candidates']:.2f}\t{m['median_candidates']}\t{m['p90_candidates']}\t{m['p95_candidates']}\t{m['p99_candidates']}\t{m['max_candidates']}\t{m['zero_candidate_s1']}\t{m['candidate_reduction_ratio']}\t{m['total_runtime_sec']:.2f}\t{m['peak_ram_mb']:.2f}\n")

    print("\nSaved metrics to exp7_scalability_metrics.json and exp7_scalability_comparison.tsv")

if __name__ == '__main__':
    main()
