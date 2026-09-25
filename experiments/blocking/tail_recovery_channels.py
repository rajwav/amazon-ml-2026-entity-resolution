"""
Experiment 9: Hard-Tail Recovery Channels Benchmark.

Tests targeted blocking channels to recover the 19 Baseline-G misses and remaining tail pairs:
1. Address Ordinals & Leading-Zero Normalization (54th -> 54, 001711 -> 1711)
2. Domain / Social Handle / Nospace Matching (empirecastillo.com, @SIBYLSBAKERY, tristatefoundation)
3. 2-Letter Word Abbreviation Channel (TY, DK, TB, XF, JD, AL, IT partitioned by Country)
4. Double Consonant Normalization (Mallone -> Malone)
5. Comprehensive Combined Tail Pipeline

Evaluates on the exact 10k pilot (10,000 S1, 84,481 targets, 34,481 true pairs).
Tracks:
- True-pair recall
- Newly recovered pairs (specifically from the 19 Baseline G misses!)
- Candidates per S1 (mean, median, P95, max)
- Marginal candidates / recovered true pair efficiency ratio
- Zero-candidate S1s
- Runtime and memory
"""

import os
import sys
import gc
import re
import time
import json
import unicodedata
import collections
from typing import Dict, Set, Tuple, List, Any

sys.path.append('.')
from experiments.blocking.common import (
    load_pilot_raw,
    get_ram_mb,
    RESULTS_DIR,
    DATA_DIR
)
from src.preprocessing.normalization import (
    normalize_business_name,
    normalize_business_address,
    LEGAL_SUFFIX_PATTERNS,
    LEGAL_STOPWORDS
)

STOPWORDS_2CHAR = {'to', 'in', 'on', 'at', 'of', 'by', 'is', 'as', 'or', 'an', 'co', 'st', 'rd', 'no'}

def clean_domain_or_handle(name: str) -> str:
    """Extract domain stem or handle stem, strip diacritics, accents, and punctuation."""
    if not name:
        return ""
    n = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('utf-8')
    n = n.lower()
    n = re.sub(r'https?://|www\.|\.(com|org|net|in|co|io|biz|info|us).*|[@#]', '', n)
    n = re.sub(r'[^a-z0-9]', '', n)
    return n

def collapse_double_consonants(name: str) -> str:
    """Collapse repeated consonants (e.g. 'll' -> 'l', 'tt' -> 't')."""
    return re.sub(r'([b-df-hj-np-tv-z])\1+', r'\1', name.lower())

def extract_clean_digits(addr: str) -> List[str]:
    """Extract all digit sequences with ordinal suffix stripping and leading-zero normalization."""
    if not addr:
        return []
    # Replace ordinal numbers like 54th, 1st, 2nd, 3rd, 121rd with just the number
    addr_clean = re.sub(r'(\d+)(st|nd|rd|th)\b', r'\1', addr.lower())
    digits_raw = re.findall(r'\d+', addr_clean)
    digits = []
    for d in digits_raw:
        # strip leading zeros (001711 -> 1711)
        d_norm = str(int(d))
        if d_norm not in digits:
            digits.append(d_norm)
    return digits

def extract_2char_tokens(name: str) -> List[str]:
    """Extract standalone 2-letter uppercase or abbreviation tokens excluding prepositions."""
    if not name:
        return []
    words = re.findall(r'\b[a-zA-Z]{2}\b', name)
    valid = []
    for w in words:
        wl = w.lower()
        if wl not in STOPWORDS_2CHAR and wl not in valid:
            valid.append(wl)
    return valid

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

def run_experiment_9():
    t_start = time.time()
    ram_init = get_ram_mb()
    print("=================================================================")
    print("EXPERIMENT 9: HARD-TAIL RECOVERY CHANNELS BENCHMARK")
    print("=================================================================")
    print(f"Initial RAM: {ram_init:.2f} MB")

    # 1. Load raw pilot data
    t0 = time.time()
    s1_raw, target_raw, gt_matches, total_true_pairs = load_pilot_raw()
    total_s1 = len(s1_raw)
    total_targets = len(target_raw)

    with open(f"{RESULTS_DIR}/baseline_g_missed_pairs.tsv", 'r', encoding='utf-8') as f:
        next(f)
        baseline_misses_pairs = set(tuple(line.rstrip('\r\n').split('\t')[1:3]) for line in f)

    print(f"Loaded raw data ({total_s1} S1s, {total_targets} targets, {total_true_pairs} true pairs) in {time.time()-t0:.2f}s")
    print(f"Tracking 19 Baseline G misses.")

    # 2. Pre-compute enriched representations
    print("\nPre-computing enriched representations...")
    t0 = time.time()

    s1_norm = {}
    for eid, parts in s1_raw.items():
        bname, baddr, country = parts[1], parts[2], parts[3]
        core, legal, sig_tokens, ngrams = normalize_business_name(bname, enable_transliteration=True)
        _, digits, _ = normalize_business_address(baddr, enable_transliteration=True)
        _, _, loc_tokens = normalize_business_address(baddr, enable_transliteration=False)
        prefix4 = core[:4] if len(core) >= 4 else core
        
        # New enriched features
        digits_enriched = extract_clean_digits(baddr)
        tokens_2char = extract_2char_tokens(bname)
        domain_stem = clean_domain_or_handle(bname)
        nospace_core = re.sub(r'[^a-z0-9]', '', core)
        core_collapsed = collapse_double_consonants(core)

        s1_norm[eid] = {
            'id': eid,
            'country': country,
            'core': core,
            'tokens': tuple(sig_tokens),
            'prefix4': prefix4,
            'digits': tuple(digits),
            'digits_enriched': tuple(digits_enriched),
            'loc_tokens': tuple(loc_tokens),
            'tokens_2char': tuple(tokens_2char),
            'domain_stem': domain_stem,
            'nospace_core': nospace_core,
            'core_collapsed': core_collapsed
        }

    target_norm = {}
    freq_loc_token = collections.defaultdict(collections.Counter)
    freq_2char_token = collections.defaultdict(collections.Counter)
    target_country_counts = collections.Counter()

    for eid, parts in target_raw.items():
        bname, baddr, country = parts[1], parts[2], parts[3]
        core, legal, sig_tokens, ngrams = normalize_business_name(bname, enable_transliteration=True)
        _, digits, _ = normalize_business_address(baddr, enable_transliteration=True)
        _, _, loc_tokens = normalize_business_address(baddr, enable_transliteration=False)
        prefix4 = core[:4] if len(core) >= 4 else core
        
        # New enriched features
        digits_enriched = extract_clean_digits(baddr)
        tokens_2char = extract_2char_tokens(bname)
        domain_stem = clean_domain_or_handle(bname)
        nospace_core = re.sub(r'[^a-z0-9]', '', core)
        core_collapsed = collapse_double_consonants(core)

        target_norm[eid] = {
            'id': eid,
            'country': country,
            'core': core,
            'tokens': tuple(sig_tokens),
            'prefix4': prefix4,
            'digits': tuple(digits),
            'digits_enriched': tuple(digits_enriched),
            'loc_tokens': tuple(loc_tokens),
            'tokens_2char': tuple(tokens_2char),
            'domain_stem': domain_stem,
            'nospace_core': nospace_core,
            'core_collapsed': core_collapsed
        }
        target_country_counts[country] += 1
        for loc in loc_tokens:
            freq_loc_token[country][loc] += 1
        for t2 in tokens_2char:
            freq_2char_token[country][t2] += 1

    print(f"Enriched normalization in {time.time()-t0:.2f}s | RAM: {get_ram_mb():.2f} MB")

    # 3. Build Base Indexes (L1, L2, and L3 Channel F Top-2)
    print("\nBuilding Inverted Indexes...")
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

    # Channel F: Top-2 rarest tokens
    idx_F_top2 = collections.defaultdict(lambda: collections.defaultdict(list))

    # New Specialized Tail Indexes:
    idx_digits_enriched = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_dig_loc_enriched = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_2char = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_nospace = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_collapsed = collections.defaultdict(lambda: collections.defaultdict(list))

    for eid, feat in target_norm.items():
        c = feat['country']
        
        # Base L1 & L2
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

        # Level 3: Channel F Top-2 rarest
        locs = feat['loc_tokens']
        if locs:
            locs_sorted = sorted(locs, key=lambda l: (freq_loc_token[c][l], len(l)))
            for loc in locs_sorted[:2]:
                idx_F_top2[c][loc].append(eid)

        # Tail Channels
        for dig in feat['digits_enriched']:
            idx_digits_enriched[c][dig].append(eid)
            for loc in feat['loc_tokens']:
                idx_dig_loc_enriched[c][(dig, loc)].append(eid)
            
        for t2 in feat['tokens_2char']:
            # Frequency cap: only index 2-letter tokens if frequency <= 200 in country target pool
            if freq_2char_token[c][t2] <= 200:
                idx_2char[c][t2].append(eid)

        if len(feat['nospace_core']) >= 4:
            idx_nospace[c][feat['nospace_core']].append(eid)
        if len(feat['domain_stem']) >= 4:
            idx_nospace[c][feat['domain_stem']].append(eid)

        if len(feat['core_collapsed']) >= 4:
            idx_collapsed[c][feat['core_collapsed']].append(eid)

    print(f"Built all base and tail indexes in {time.time()-t0:.2f}s | RAM: {get_ram_mb():.2f} MB")

    # 4. Generate Candidates for Progressive Configurations
    # Config 1: Baseline Experiment 8 (L1 + L2 + F_Top2)
    # Config 2: Config 1 + Enriched Digits (Ordinals + Leading Zeros)
    # Config 3: Config 2 + 2-Letter Word Channel
    # Config 4: Config 3 + Domain / Nospace Matching
    # Config 5: Config 4 + Consonant Collapse
    # Config 6: All Tail Combined + Fallback Channel F (Policy 8A)

    configs = [
        "E8_Top2_Base",
        "+Enriched_Digits",
        "+ShortNames_2Char",
        "+Domain_Nospace",
        "+Consonant_Collapse",
        "Full_Tail_Recovery_Pipeline",
        "Surgical_Tail_Pipeline"
    ]

    results_table = []
    config_metrics_dict = {}

    for cfg in configs:
        print(f"\n=======================================================")
        print(f"Evaluating Configuration: {cfg}")
        print(f"=======================================================")
        t_cfg_start = time.time()

        cands_cum: Dict[str, Set[str]] = {}
        zero_cands = 0

        for s1_id, feat in s1_norm.items():
            c = feat['country']
            cands = set()

            # Base L1: Composites
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

            # Base L2: B, C, D, E
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

            # Base L3: Channel F Top-2
            for loc in feat['loc_tokens']:
                if loc in idx_F_top2[c]:
                    cands.update(idx_F_top2[c][loc])

            # Progressive Enhancements:
            if cfg in ["+Enriched_Digits", "+ShortNames_2Char", "+Domain_Nospace", "+Consonant_Collapse", "Full_Tail_Recovery_Pipeline"]:
                for dig in feat['digits_enriched']:
                    if dig in idx_digits_enriched[c]:
                        cands.update(idx_digits_enriched[c][dig])

            if cfg in ["+ShortNames_2Char", "+Domain_Nospace", "+Consonant_Collapse", "Full_Tail_Recovery_Pipeline", "Surgical_Tail_Pipeline"]:
                for t2 in feat['tokens_2char']:
                    if t2 in idx_2char[c]:
                        cands.update(idx_2char[c][t2])

            if cfg in ["+Domain_Nospace", "+Consonant_Collapse", "Full_Tail_Recovery_Pipeline", "Surgical_Tail_Pipeline"]:
                if feat['nospace_core'] and feat['nospace_core'] in idx_nospace[c]:
                    cands.update(idx_nospace[c][feat['nospace_core']])
                if feat['domain_stem'] and feat['domain_stem'] in idx_nospace[c]:
                    cands.update(idx_nospace[c][feat['domain_stem']])

            if cfg in ["+Consonant_Collapse", "Full_Tail_Recovery_Pipeline", "Surgical_Tail_Pipeline"]:
                if feat['core_collapsed'] and feat['core_collapsed'] in idx_collapsed[c]:
                    cands.update(idx_collapsed[c][feat['core_collapsed']])

            if cfg == "Surgical_Tail_Pipeline":
                # Composite enriched digit + location (avoids standalone digit explosion)
                for ed in feat['digits_enriched']:
                    for loc in feat['loc_tokens']:
                        if (ed, loc) in idx_dig_loc_enriched[c]:
                            cands.update(idx_dig_loc_enriched[c][(ed, loc)])

            if len(cands) == 0:
                zero_cands += 1
            cands_cum[s1_id] = cands

        cfg_total_time = time.time() - t_cfg_start

        # Detailed metrics
        m = compute_detailed_metrics(cands_cum, gt_matches, total_true_pairs, total_s1)
        m['config'] = cfg
        m['runtime_sec'] = cfg_total_time
        m['zero_candidate_s1'] = zero_cands

        # Missed pairs analysis
        missed_set = set()
        for s1_id, targets in gt_matches.items():
            for t_id in targets:
                if t_id not in cands_cum[s1_id]:
                    missed_set.add((s1_id, t_id))

        m['missed_pairs_count'] = len(missed_set)
        recovered_from_baseline_19 = baseline_misses_pairs - missed_set
        m['recovered_baseline_19'] = len(recovered_from_baseline_19)

        # Compare vs Base
        base_total_cands = results_table[0]['total_cands'] if results_table else m['total_candidates']
        base_recalled = results_table[0]['recalled_pairs'] if results_table else m['recalled_pairs']
        delta_cands = m['total_candidates'] - base_total_cands
        delta_tp = m['recalled_pairs'] - base_recalled
        cands_per_tp = delta_cands / delta_tp if delta_tp > 0 else 0
        m['cands_per_recovered_tp'] = round(cands_per_tp, 1)

        config_metrics_dict[cfg] = m

        print(f"  Recall: {m['recall']} ({m['recalled_pairs']}/{total_true_pairs}) | Missed: {len(missed_set)}")
        print(f"  Avg Cands/S1: {m['avg_candidates']:.1f} | Med: {m['median_candidates']} | P95: {m['p95_candidates']} | Max: {m['max_candidates']}")
        print(f"  Recovered from Baseline G 19 Misses: {len(recovered_from_baseline_19)}/19 ({sorted(list(recovered_from_baseline_19))[:4]}...)")
        if delta_tp > 0:
            print(f"  Marginal vs Base: +{delta_tp} TP for +{delta_cands:,} candidates ({m['cands_per_recovered_tp']} cands/TP)")
        print(f"  Time: {cfg_total_time:.2f}s")

        results_table.append({
            'config': cfg,
            'recall': m['recall'],
            'recalled_pairs': m['recalled_pairs'],
            'missed_pairs': len(missed_set),
            'recovered_b19': f"{len(recovered_from_baseline_19)}/19",
            'avg_candidates': round(m['avg_candidates'], 1),
            'median_candidates': m['median_candidates'],
            'p90_candidates': m['p90_candidates'],
            'p95_candidates': m['p95_candidates'],
            'p99_candidates': m['p99_candidates'],
            'max_candidates': m['max_candidates'],
            'zero_candidates': zero_cands,
            'delta_tp': delta_tp,
            'delta_cands': delta_cands,
            'cands_per_tp': m['cands_per_recovered_tp'],
            'total_cands': m['total_candidates'],
            'runtime_sec': round(cfg_total_time, 2)
        })

    # Save metrics JSON
    with open(f"{RESULTS_DIR}/exp9_tail_recovery_metrics.json", 'w', encoding='utf-8') as f:
        json.dump(config_metrics_dict, f, indent=2)

    # Save comparison TSV
    tsv_path = f"{RESULTS_DIR}/exp9_tail_recovery_comparison.tsv"
    with open(tsv_path, 'w', encoding='utf-8') as f:
        headers = list(results_table[0].keys())
        f.write('\t'.join(headers) + '\n')
        for row in results_table:
            f.write('\t'.join(str(row[h]) for h in headers) + '\n')

    # Output detailed missed pairs for the final configuration
    final_misses_path = f"{RESULTS_DIR}/exp9_final_missed_pairs.tsv"
    with open(final_misses_path, 'w', encoding='utf-8') as f:
        f.write("s1_id\ttarget_id\ts1_name\ttarget_name\ts1_address\ttarget_address\n")
        for s1_id, t_id in missed_set:
            s1_p = s1_raw.get(s1_id, ['', '', '', ''])
            t_p = target_raw.get(t_id, ['', '', '', ''])
            f.write(f"{s1_id}\t{t_id}\t{s1_p[1]}\t{t_p[1]}\t{s1_p[2]}\t{t_p[2]}\n")

    print(f"\nSaved Experiment 9 comparison to {tsv_path}")
    print(f"Saved remaining {len(missed_set)} misses to {final_misses_path}")
    print(f"Total Experiment 9 Runtime: {time.time()-t_start:.2f}s | Peak RAM: {get_ram_mb():.2f} MB")

if __name__ == '__main__':
    run_experiment_9()
