"""
Error and Complement Analysis for Experiment 2 (C2_Union_All).
Investigates the 1,528 true pairs missed by C2_Union_All and the 116 zero-candidate S1s.
Determines which Baseline G channels recover them and categorizes failure modes.
Saves details to experiments/results/exp2_complement_analysis.tsv.
"""

import sys
import os
import json
import collections

sys.path.append('.')
from experiments.blocking.common import (
    load_pilot_raw,
    get_normalized_records,
    DATA_DIR,
    RESULTS_DIR
)

def run_complement_analysis():
    print("=================================================================")
    print("EXP 2 COMPLEMENT ANALYSIS: WHY DID C2_UNION_ALL MISS 1,528 PAIRS?")
    print("=================================================================")

    # 1. Load data
    s1_raw, target_raw, gt_matches, total_true_pairs = load_pilot_raw()
    s1_norm, target_norm = get_normalized_records(s1_raw, target_raw)

    with open(f"{DATA_DIR}/baseline_g_candidates.json", 'r', encoding='utf-8') as f:
        baseline_candidates = {k: set(v) for k, v in json.load(f).items()}

    # 2. Reconstruct C2_Union_All candidate generation
    idx_exact_name = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_tok_loc    = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_tok_dig    = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_pref_loc   = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_pref_dig   = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_dig_loc    = collections.defaultdict(lambda: collections.defaultdict(list))

    # Single channel indexes to check which G channel recovers the missed pairs
    idx_exact_name_g = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_sig_token_g  = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_prefix4_g    = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_digits_g     = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_loc_token_g  = collections.defaultdict(lambda: collections.defaultdict(list))

    for eid, feat in target_norm.items():
        c = feat['country']
        # Single G indexes
        if feat['core']: idx_exact_name_g[c][feat['core']].append(eid)
        for tok in feat['tokens']: idx_sig_token_g[c][tok].append(eid)
        if feat['prefix4']: idx_prefix4_g[c][feat['prefix4']].append(eid)
        for dig in feat['digits']: idx_digits_g[c][dig].append(eid)
        for loc in feat['loc_tokens']: idx_loc_token_g[c][loc].append(eid)

        # Composite indexes
        if feat['core']: idx_exact_name[c][feat['core']].append(eid)
        for tok in feat['tokens']:
            for loc in feat['loc_tokens']: idx_tok_loc[c][(tok, loc)].append(eid)
            for dig in feat['digits']: idx_tok_dig[c][(tok, dig)].append(eid)
        if feat['prefix4']:
            p = feat['prefix4']
            for loc in feat['loc_tokens']: idx_pref_loc[c][(p, loc)].append(eid)
            for dig in feat['digits']: idx_pref_dig[c][(p, dig)].append(eid)
        for dig in feat['digits']:
            for loc in feat['loc_tokens']: idx_dig_loc[c][(dig, loc)].append(eid)

    c2_candidates = {}
    zero_cand_s1s = []

    for s1_id, feat in s1_norm.items():
        c = feat['country']
        cands = set()
        if feat['core'] and feat['core'] in idx_exact_name[c]:
            cands.update(idx_exact_name[c][feat['core']])
        for tok in feat['tokens']:
            for loc in feat['loc_tokens']:
                pair = (tok, loc)
                if pair in idx_tok_loc[c]: cands.update(idx_tok_loc[c][pair])
            for dig in feat['digits']:
                pair = (tok, dig)
                if pair in idx_tok_dig[c]: cands.update(idx_tok_dig[c][pair])
        if feat['prefix4']:
            p = feat['prefix4']
            for loc in feat['loc_tokens']:
                pair = (p, loc)
                if pair in idx_pref_loc[c]: cands.update(idx_pref_loc[c][pair])
            for dig in feat['digits']:
                pair = (p, dig)
                if pair in idx_pref_dig[c]: cands.update(idx_pref_dig[c][pair])
        for dig in feat['digits']:
            for loc in feat['loc_tokens']:
                pair = (dig, loc)
                if pair in idx_dig_loc[c]: cands.update(idx_dig_loc[c][pair])

        c2_candidates[s1_id] = cands
        if len(cands) == 0:
            zero_cand_s1s.append(s1_id)

    assert len(zero_cand_s1s) == 116
    print(f"Verified: exactly 116 S1 entities received zero candidates from C2_Union_All.")

    # 3. Analyze the 1,528 missed pairs
    missed_records = []
    failure_category_counts = collections.Counter()
    recovered_by_channel_counts = collections.Counter()
    recovered_by_baseline_count = 0

    tsv_out_path = f"{RESULTS_DIR}/exp2_complement_analysis.tsv"

    with open(tsv_out_path, 'w', encoding='utf-8') as f:
        f.write("s1_entity_id\ttarget_entity_id\trecovered_by_baseline\trecovery_channel\ttarget_missing_address\ts1_name\ttarget_name\ts1_address\ttarget_address\tfailure_category\n")

        for s1_id, true_mids in gt_matches.items():
            c2_cands = c2_candidates.get(s1_id, set())
            base_cands = baseline_candidates.get(s1_id, set())
            f1 = s1_norm[s1_id]
            s1_raw_row = s1_raw[s1_id]

            for mid in true_mids:
                if mid not in c2_cands:
                    # This is one of the 1,528 missed pairs
                    f2 = target_norm[mid]
                    target_raw_row = target_raw[mid]
                    c = f1['country']

                    rec_by_base = (mid in base_cands)
                    if rec_by_base:
                        recovered_by_baseline_count += 1

                    # Determine which single Baseline G channel recovers it
                    rec_channels = []
                    if f1['core'] and f1['core'] in idx_exact_name_g[c] and mid in idx_exact_name_g[c][f1['core']]:
                        rec_channels.append('B_ExactName')
                    for tok in f1['tokens']:
                        if tok in idx_sig_token_g[c] and mid in idx_sig_token_g[c][tok]:
                            rec_channels.append('C_SigToken')
                            break
                    if f1['prefix4'] and f1['prefix4'] in idx_prefix4_g[c] and mid in idx_prefix4_g[c][f1['prefix4']]:
                        rec_channels.append('D_Prefix4')
                    for dig in f1['digits']:
                        if dig in idx_digits_g[c] and mid in idx_digits_g[c][dig]:
                            rec_channels.append('E_Digits')
                            break
                    for loc in f1['loc_tokens']:
                        if loc in idx_loc_token_g[c] and mid in idx_loc_token_g[c][loc]:
                            rec_channels.append('F_Location')
                            break

                    rec_channel_str = "+".join(rec_channels) if rec_channels else "None (Missed by G too)"
                    for rc in rec_channels:
                        recovered_by_channel_counts[rc] += 1
                    if not rec_channels:
                        recovered_by_channel_counts['None'] += 1

                    # Check attributes
                    target_missing_addr = (len(target_raw_row[2].strip()) == 0)
                    has_s1_digits = bool(f1['digits'])
                    has_t_digits = bool(f2['digits'])
                    has_s1_loc = bool(f1['loc_tokens'])
                    has_t_loc = bool(f2['loc_tokens'])
                    has_s1_tokens = bool(f1['tokens'])
                    has_t_tokens = bool(f2['tokens'])

                    # Categorize failure mode
                    if target_missing_addr:
                        cat = "TARGET_MISSING_ADDRESS"
                    elif not has_t_digits and not has_s1_digits:
                        cat = "NO_DIGITS_EITHER_RECORD"
                    elif not has_t_digits:
                        cat = "TARGET_LACKS_DIGITS"
                    elif not (set(f1['tokens']) & set(f2['tokens'])) and (f1['prefix4'] != f2['prefix4']):
                        cat = "NAME_DISJOINT_AND_NO_DIGIT_LOC_COOCCURRENCE"
                    elif not (set(f1['loc_tokens']) & set(f2['loc_tokens'])):
                        cat = "LOCATION_TOKENS_DISJOINT"
                    elif not (set(f1['digits']) & set(f2['digits'])):
                        cat = "DIGITS_DISJOINT"
                    else:
                        cat = "CROSS_ATTRIBUTE_MISMATCH"

                    failure_category_counts[cat] += 1

                    f.write(f"{s1_id}\t{mid}\t{rec_by_base}\t{rec_channel_str}\t{target_missing_addr}\t{s1_raw_row[1]}\t{target_raw_row[1]}\t{s1_raw_row[2]}\t{target_raw_row[2]}\t{cat}\n")

    print(f"Total pairs missed by C2_Union_All: {sum(failure_category_counts.values())}")
    print(f"Recovered by Baseline G:           {recovered_by_baseline_count} / {sum(failure_category_counts.values())} ({recovered_by_baseline_count/sum(failure_category_counts.values())*100:.2f}%)")
    print(f"Missed by both C2 and Baseline G:  {sum(failure_category_counts.values()) - recovered_by_baseline_count} (The exact 19 baseline misses)")

    print("\n--- RECOVERY CHANNELS IN BASELINE G ---")
    for ch, count in recovered_by_channel_counts.most_common():
        print(f"  {ch:20s}: {count:5d} pairs ({count/1528*100:5.2f}%)")

    print("\n--- FAILURE CATEGORY BREAKDOWN ---")
    for cat, count in failure_category_counts.most_common():
        print(f"  {cat:45s}: {count:5d} pairs ({count/1528*100:5.2f}%)")

    # 4. Analyze the 116 Zero-Candidate S1 Entities
    zero_cand_categories = collections.Counter()
    print("\n--- ZERO-CANDIDATE S1 ENTITIES (116 total) ---")
    for s1_id in zero_cand_s1s[:10]:
        f1 = s1_norm[s1_id]
        raw_s1 = s1_raw[s1_id]
        print(f"  S1: {s1_id} ({raw_s1[3]}) | '{raw_s1[1]}' | '{raw_s1[2]}'")
        print(f"      Tokens: {f1['tokens']} | Prefix: '{f1['prefix4']}' | Digits: {f1['digits']} | Locs: {f1['loc_tokens']}")

    for s1_id in zero_cand_s1s:
        f1 = s1_norm[s1_id]
        if not f1['tokens'] and not f1['prefix4']:
            zero_cand_categories["NO_NAME_TOKENS"] += 1
        elif not f1['digits'] and not f1['loc_tokens']:
            zero_cand_categories["NO_ADDRESS_INFORMATION"] += 1
        elif not f1['digits']:
            zero_cand_categories["NAME_ONLY_NO_DIGITS"] += 1
        else:
            zero_cand_categories["RARE_TOKENS_NO_CONJUNCTIVE_MATCH"] += 1

    print("\nZero-candidate S1 Profile:")
    for cat, cnt in zero_cand_categories.most_common():
        print(f"  {cat}: {cnt}")

    return failure_category_counts, recovered_by_channel_counts

if __name__ == '__main__':
    run_complement_analysis()
