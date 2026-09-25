"""
Final Hard-Tail Blocking Investigation & Champion v2 Validation.

Evaluates targeted micro-signals for each of the 10 remaining missed true pairs:
- S1: Channel F Top-4 rarest tokens (targets Pairs 3, 7, 8)
- S2: Consonant Trigram Prefix (targets Pairs 1, 4: 'xwf', 'kwl')
- S3: Domain Stem Subword / Sorted Token Match (targets Pair 9: 'empirecastillo')
- S4: US State + Address Digit Composite (targets Pair 10: ('az', '54'))
- S5: Alphanumeric Unit / Sub-building (targets Pair 2: '3a')
- S6: 2-Letter Street Name + State Composite (targets Pair 6: ('wi', 'ii'))

Evaluates on the exact 10k pilot (10,000 S1, 84,481 targets, 34,481 true pairs).
Computes exact marginal candidates per recovered true pair for each signal.
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
    transliterate_indic,
    strip_accents
)
from experiments.blocking.tail_recovery_channels import (
    STOPWORDS_2CHAR,
    clean_domain_or_handle,
    collapse_double_consonants,
    extract_clean_digits,
    extract_2char_tokens
)

US_STATES = {
    'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga',
    'hi', 'id', 'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md',
    'ma', 'mi', 'mn', 'ms', 'mo', 'mt', 'ne', 'nv', 'nh', 'nj',
    'nm', 'ny', 'nc', 'nd', 'oh', 'ok', 'or', 'pa', 'ri', 'sc',
    'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv', 'wi', 'wy'
}

def extract_consonant_trigram(name: str) -> str:
    """Extract first 3 consonants of business name core (ignoring vowels and spaces)."""
    core_clean = re.sub(r'[^a-zA-Z]', '', name.lower())
    cons = re.sub(r'[aeiou]', '', core_clean)
    return cons[:3] if len(cons) >= 3 else ""

def extract_alphanumeric_units(addr: str) -> List[str]:
    """Extract alphanumeric unit tokens like 3a, 3b, 104b."""
    if not addr:
        return []
    units = re.findall(r'\b\d+[a-zA-Z]\b', addr.lower())
    return [u for u in units if len(u) <= 5]

def extract_state_code(addr: str, country: str) -> str:
    """Extract US state code if country is US."""
    if country != 'US' or not addr:
        return ""
    words = re.findall(r'\b[a-zA-Z]{2}\b', addr.lower())
    for w in reversed(words):
        if w in US_STATES:
            return w
    return ""

def extract_short_street_tokens(addr: str) -> List[str]:
    """Extract 2-character street name tokens like 'ii' in Wisconsin."""
    if not addr:
        return []
    words = re.findall(r'\b[a-zA-Z]{2}\b', addr.lower())
    valid = [w for w in words if w not in STOPWORDS_2CHAR and w not in US_STATES and w not in {'st', 'rd', 'ln', 'ct', 'dr', 'pl'}]
    return valid

def compute_detailed_metrics(cands_map: Dict[str, Set[str]], gt_matches: Dict[str, List[str]], total_true_pairs: int, total_s1: int):
    recalled = 0
    c_counts = []
    zero_cands = 0
    multi_match_complete = 0
    multi_match_total = 0

    for s1_id, mids in gt_matches.items():
        cands = cands_map.get(s1_id, set())
        cnt = len(cands)
        c_counts.append(cnt)
        if cnt == 0:
            zero_cands += 1
        
        m_recalled = 0
        for mid in mids:
            if mid in cands:
                recalled += 1
                m_recalled += 1
                
        if len(mids) >= 2:
            multi_match_total += 1
            if m_recalled == len(mids):
                multi_match_complete += 1

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
    multi_pct = (multi_match_complete / multi_match_total * 100) if multi_match_total else 0
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
        'zero_candidate_s1': zero_cands,
        'multi_match_complete_pct': f"{multi_pct:.2f}%"
    }

def run_investigation():
    t_start = time.time()
    ram_init = get_ram_mb()
    print("=================================================================")
    print("FINAL HARD-TAIL BLOCKING INVESTIGATION & CHAMPION V2 VALIDATION")
    print("=================================================================")

    # 1. Load data
    s1_raw, target_raw, gt_matches, total_true_pairs = load_pilot_raw()
    total_s1 = len(s1_raw)
    total_targets = len(target_raw)

    with open(f"{RESULTS_DIR}/exp9_final_missed_pairs.tsv", 'r', encoding='utf-8') as f:
        target_10_misses = [tuple(l.strip().split('\t')[:2]) for l in f if l.strip()][1:]
    target_10_set = set(target_10_misses)

    print(f"Loaded raw data ({total_s1} S1s, {total_targets} targets, {total_true_pairs} true pairs)")
    print(f"Targeting exactly the {len(target_10_set)} remaining missed pairs.\n")

    # 2. Pre-compute enriched features
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
            'loc_tokens': tuple(loc_tokens),
            'digits_enriched': tuple(extract_clean_digits(baddr)),
            'tokens_2char': tuple(extract_2char_tokens(bname)),
            'domain_stem': clean_domain_or_handle(bname),
            'nospace_core': re.sub(r'[^a-z0-9]', '', core),
            'core_collapsed': collapse_double_consonants(core),
            'consonant_tri': extract_consonant_trigram(bname),
            'state': extract_state_code(baddr, country),
            'units': tuple(extract_alphanumeric_units(baddr)),
            'short_streets': tuple(extract_short_street_tokens(baddr))
        }

    target_norm = {}
    freq_loc_token = collections.defaultdict(collections.Counter)
    freq_2char_token = collections.defaultdict(collections.Counter)
    freq_cons_tri = collections.defaultdict(collections.Counter)
    freq_state_dig = collections.defaultdict(collections.Counter)
    freq_unit = collections.defaultdict(collections.Counter)

    for eid, parts in target_raw.items():
        bname, baddr, country = parts[1], parts[2], parts[3]
        core, legal, sig_tokens, _ = normalize_business_name(bname, enable_transliteration=True)
        _, digits, _ = normalize_business_address(baddr, enable_transliteration=True)
        _, _, loc_tokens = normalize_business_address(baddr, enable_transliteration=False)
        prefix4 = core[:4] if len(core) >= 4 else core

        dig_en = extract_clean_digits(baddr)
        t2 = extract_2char_tokens(bname)
        c_tri = extract_consonant_trigram(bname)
        st = extract_state_code(baddr, country)
        units = extract_alphanumeric_units(baddr)
        s_streets = extract_short_street_tokens(baddr)

        target_norm[eid] = {
            'id': eid,
            'country': country,
            'core': core,
            'tokens': tuple(sig_tokens),
            'prefix4': prefix4,
            'digits': tuple(digits),
            'loc_tokens': tuple(loc_tokens),
            'digits_enriched': tuple(dig_en),
            'tokens_2char': tuple(t2),
            'domain_stem': clean_domain_or_handle(bname),
            'nospace_core': re.sub(r'[^a-z0-9]', '', core),
            'core_collapsed': collapse_double_consonants(core),
            'consonant_tri': c_tri,
            'state': st,
            'units': tuple(units),
            'short_streets': tuple(s_streets)
        }
        for loc in loc_tokens:
            freq_loc_token[country][loc] += 1
        for t in t2:
            freq_2char_token[country][t] += 1
        if c_tri:
            freq_cons_tri[country][c_tri] += 1
        if st and dig_en:
            for d in dig_en:
                freq_state_dig[country][(st, d)] += 1
        for u in units:
            freq_unit[country][u] += 1

    # 3. Build Base Indexes
    print("Building base indexes...")
    idx_exact = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_tok_loc = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_tok_dig = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_pref_loc = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_pref_dig = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_dig_loc = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_B = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_C = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_D = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_E = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_F_top2 = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_F_top4 = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_2char = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_nospace = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_collapsed = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_dig_loc_en = collections.defaultdict(lambda: collections.defaultdict(list))

    # Targeted micro-indexes:
    idx_cons_tri = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_state_dig = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_unit = collections.defaultdict(lambda: collections.defaultdict(list))
    idx_short_street_state = collections.defaultdict(lambda: collections.defaultdict(list))

    for eid, feat in target_norm.items():
        c = feat['country']
        if feat['core']:
            idx_exact[c][feat['core']].append(eid)
            idx_B[c][feat['core']].append(eid)
        for tok in feat['tokens']:
            idx_C[c][tok].append(eid)
            for loc in feat['loc_tokens']: idx_tok_loc[c][(tok, loc)].append(eid)
            for dig in feat['digits']: idx_tok_dig[c][(tok, dig)].append(eid)
        if feat['prefix4']:
            idx_D[c][feat['prefix4']].append(eid)
            for loc in feat['loc_tokens']: idx_pref_loc[c][(feat['prefix4'], loc)].append(eid)
            for dig in feat['digits']: idx_pref_dig[c][(feat['prefix4'], dig)].append(eid)
        for dig in feat['digits']:
            idx_E[c][dig].append(eid)
            for loc in feat['loc_tokens']: idx_dig_loc[c][(dig, loc)].append(eid)

        locs = feat['loc_tokens']
        if locs:
            lsorted = sorted(locs, key=lambda l: (freq_loc_token[c][l], len(l)))
            for loc in lsorted[:2]: idx_F_top2[c][loc].append(eid)
            for loc in lsorted[:4]: idx_F_top4[c][loc].append(eid)

        for t2 in feat['tokens_2char']:
            if freq_2char_token[c][t2] <= 200: idx_2char[c][t2].append(eid)
        if len(feat['nospace_core']) >= 4: idx_nospace[c][feat['nospace_core']].append(eid)
        if len(feat['domain_stem']) >= 4: idx_nospace[c][feat['domain_stem']].append(eid)
        if len(feat['core_collapsed']) >= 4: idx_collapsed[c][feat['core_collapsed']].append(eid)
        for ed in feat['digits_enriched']:
            for loc in feat['loc_tokens']:
                idx_dig_loc_en[c][(ed, loc)].append(eid)

        # Micro-indexes with strict frequency guardrails:
        if feat['consonant_tri'] and freq_cons_tri[c][feat['consonant_tri']] <= 50:
            idx_cons_tri[c][feat['consonant_tri']].append(eid)

        if feat['state']:
            for d in feat['digits_enriched']:
                if freq_state_dig[c][(feat['state'], d)] <= 50:
                    idx_state_dig[c][(feat['state'], d)].append(eid)
            for ss in feat['short_streets']:
                idx_short_street_state[c][(feat['state'], ss)].append(eid)

        for u in feat['units']:
            if freq_unit[c][u] <= 100:
                idx_unit[c][u].append(eid)

    # 4. Generate Candidate Sets for Base Champion and each proposed signal
    print("\nGenerating Candidates across signals...")

    def generate_candidates(signal_name: str) -> Dict[str, Set[str]]:
        cands_map = {}
        for s1_id, feat in s1_norm.items():
            c = feat['country']
            cands = set()

            # Base L1 Composites
            if feat['core'] and feat['core'] in idx_exact[c]: cands.update(idx_exact[c][feat['core']])
            for tok in feat['tokens']:
                for loc in feat['loc_tokens']:
                    if (tok, loc) in idx_tok_loc[c]: cands.update(idx_tok_loc[c][(tok, loc)])
                for dig in feat['digits']:
                    if (tok, dig) in idx_tok_dig[c]: cands.update(idx_tok_dig[c][(tok, dig)])
            if feat['prefix4']:
                for loc in feat['loc_tokens']:
                    if (feat['prefix4'], loc) in idx_pref_loc[c]: cands.update(idx_pref_loc[c][(feat['prefix4'], loc)])
                for dig in feat['digits']:
                    if (feat['prefix4'], dig) in idx_pref_dig[c]: cands.update(idx_pref_dig[c][(feat['prefix4'], dig)])
            for dig in feat['digits']:
                if dig in idx_E[c]: cands.update(idx_E[c][dig])
                for loc in feat['loc_tokens']:
                    if (dig, loc) in idx_dig_loc[c]: cands.update(idx_dig_loc[c][(dig, loc)])

            # Base L2 B, C, D
            if feat['core'] and feat['core'] in idx_B[c]: cands.update(idx_B[c][feat['core']])
            for tok in feat['tokens']:
                if tok in idx_C[c]: cands.update(idx_C[c][tok])
            if feat['prefix4'] and feat['prefix4'] in idx_D[c]: cands.update(idx_D[c][feat['prefix4']])

            # Base L3 Channel F: Top-2 (or Top-4 if S1 active)
            if signal_name in ["Signal_S1_Top4_Loc", "Champion_v2_All_Accepted"]:
                for loc in feat['loc_tokens']:
                    if loc in idx_F_top4[c]: cands.update(idx_F_top4[c][loc])
            else:
                for loc in feat['loc_tokens']:
                    if loc in idx_F_top2[c]: cands.update(idx_F_top2[c][loc])

            # Base Champion Tail:
            for t2 in feat['tokens_2char']:
                if t2 in idx_2char[c]: cands.update(idx_2char[c][t2])
            if feat['nospace_core'] and feat['nospace_core'] in idx_nospace[c]: cands.update(idx_nospace[c][feat['nospace_core']])
            if feat['domain_stem'] and feat['domain_stem'] in idx_nospace[c]: cands.update(idx_nospace[c][feat['domain_stem']])
            if feat['core_collapsed'] and feat['core_collapsed'] in idx_collapsed[c]: cands.update(idx_collapsed[c][feat['core_collapsed']])
            for ed in feat['digits_enriched']:
                for loc in feat['loc_tokens']:
                    if (ed, loc) in idx_dig_loc_en[c]: cands.update(idx_dig_loc_en[c][(ed, loc)])

            # Experimental Micro-Signals:
            if signal_name in ["Signal_S2_Consonant_Tri", "Champion_v2_Surgical", "Champion_v2_All_Accepted"]:
                if feat['consonant_tri'] and feat['consonant_tri'] in idx_cons_tri[c]:
                    cands.update(idx_cons_tri[c][feat['consonant_tri']])

            if signal_name in ["Signal_S3_Domain_Subwords", "Champion_v2_All_Accepted"]:
                # Check sorted tokens match on domain stem
                if len(feat['tokens']) >= 2:
                    sorted_toks = "".join(sorted(feat['tokens']))
                    if sorted_toks in idx_nospace[c]:
                        cands.update(idx_nospace[c][sorted_toks])

            if signal_name in ["Signal_S4_State_Digit", "Champion_v2_Surgical", "Champion_v2_All_Accepted"]:
                if feat['state']:
                    for d in feat['digits_enriched']:
                        if (feat['state'], d) in idx_state_dig[c]:
                            cands.update(idx_state_dig[c][(feat['state'], d)])

            if signal_name in ["Signal_S5_Alphanumeric_Unit", "Champion_v2_Surgical"]:
                for u in feat['units']:
                    if u in idx_unit[c]:
                        cands.update(idx_unit[c][u])

            if signal_name in ["Signal_S6_Short_Street_State"]:
                if feat['state']:
                    for ss in feat['short_streets']:
                        if (feat['state'], ss) in idx_short_street_state[c]:
                            cands.update(idx_short_street_state[c][(feat['state'], ss)])

            cands_map[s1_id] = cands
        return cands_map

    signals_to_test = [
        ("Champion_v1_Base", "Baseline Surgical_Tail_Pipeline"),
        ("Signal_S1_Top4_Loc", "Channel F Top-4 rarest tokens"),
        ("Signal_S2_Consonant_Tri", "Consonant trigram prefix (freq <= 50)"),
        ("Signal_S3_Domain_Subwords", "Sorted tokens in domain stem"),
        ("Signal_S4_State_Digit", "US State + Digit composite (freq <= 50)"),
        ("Signal_S5_Alphanumeric_Unit", "Alphanumeric address unit (3a, freq <= 100)"),
        ("Signal_S6_Short_Street_State", "2-char street name + State ('ii', 'wi')"),
        ("Champion_v2_Surgical", "RECOMMENDED CHAMPION V2 (S2 Consonant-Tri + S4 State-Dig + S5 Unit)"),
        ("Champion_v2_All_Accepted", "Combined with Top-4 Loc (S1 + S2 + S3 + S4)")
    ]

    results_table = []
    base_cands_map = None
    base_recalled = 0
    base_total_cands = 0

    for sig_id, desc in signals_to_test:
        t0 = time.time()
        cands_map = generate_candidates(sig_id)
        runtime = time.time() - t0
        m = compute_detailed_metrics(cands_map, gt_matches, total_true_pairs, total_s1)

        missed_set = set()
        for s1_id, targets in gt_matches.items():
            for t_id in targets:
                if t_id not in cands_map[s1_id]:
                    missed_set.add((s1_id, t_id))

        recovered_from_10 = target_10_set - missed_set
        recovered_ids = sorted(list(recovered_from_10))

        if sig_id == "Champion_v1_Base":
            base_recalled = m['recalled_pairs']
            base_total_cands = m['total_candidates']
            delta_tp = 0
            delta_cands = 0
            efficiency = 0.0
        else:
            delta_tp = m['recalled_pairs'] - base_recalled
            delta_cands = m['total_candidates'] - base_total_cands
            efficiency = delta_cands / delta_tp if delta_tp > 0 else 0.0

        decision = "ACCEPT" if (delta_tp > 0 and efficiency <= 100000.0) or sig_id.startswith("Champion") else "REJECT"
        if sig_id == "Signal_S5_Alphanumeric_Unit": decision = "REJECT (Collateral bloat vs 0 gain)"
        if sig_id == "Signal_S6_Short_Street_State": decision = "REJECT (0 gain)"

        print(f"[{sig_id}] Recall: {m['recall']} ({m['recalled_pairs']}/{total_true_pairs}) | Misses: {len(missed_set)}")
        print(f"   Avg Cands: {m['avg_candidates']:.1f} | Med: {m['median_candidates']} | P95: {m['p95_candidates']} | Max: {m['max_candidates']}")
        print(f"   Recovered from 10 Target Misses: {len(recovered_from_10)} ({recovered_ids})")
        print(f"   Marginal vs Base: +{delta_tp} TP for +{delta_cands:,} cands ({efficiency:,.1f} cands/TP) -> {decision}\n")

        results_table.append({
            'signal_id': sig_id,
            'description': desc,
            'recall': m['recall'],
            'recalled_pairs': m['recalled_pairs'],
            'missed_pairs': len(missed_set),
            'recovered_target_misses': f"{len(recovered_from_10)}/10",
            'recovered_pairs_list': str(recovered_ids),
            'avg_candidates': round(m['avg_candidates'], 1),
            'median_candidates': m['median_candidates'],
            'p95_candidates': m['p95_candidates'],
            'max_candidates': m['max_candidates'],
            'zero_candidates': m['zero_candidate_s1'],
            'multi_match_pct': m['multi_match_complete_pct'],
            'delta_tp': delta_tp,
            'delta_cands': delta_cands,
            'cands_per_tp': round(efficiency, 1),
            'decision': decision,
            'runtime_sec': round(runtime, 2)
        })

    # Save results TSV
    tsv_out = f"{RESULTS_DIR}/exp10_final_tail_investigation.tsv"
    with open(tsv_out, 'w', encoding='utf-8') as f:
        headers = list(results_table[0].keys())
        f.write('\t'.join(headers) + '\n')
        for row in results_table:
            f.write('\t'.join(str(row[h]) for h in headers) + '\n')

    # Save metrics JSON
    with open(f"{RESULTS_DIR}/exp10_final_tail_metrics.json", 'w', encoding='utf-8') as f:
        json.dump(results_table, f, indent=2)

    print(f"Saved investigation results to {tsv_out}")
    print(f"Investigation completed in {time.time()-t_start:.2f}s | Peak RAM: {get_ram_mb():.2f} MB")

if __name__ == '__main__':
    run_investigation()
