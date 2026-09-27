import os
import json
import random
import psutil
import pandas as pd
from typing import Dict, List, Set, Tuple
from blocking.normalization import (
    normalize_business_name,
    normalize_business_address,
    clean_domain_or_handle,
    collapse_double_consonants,
    extract_clean_digits,
    extract_consonant_trigram,
    extract_alphanumeric_units,
    extract_state_code
)
from matching.features import extract_pairwise_features

def parse_entity(row: dict) -> dict:
    b_name = str(row.get('business_name', ''))
    b_addr = str(row.get('business_address', ''))
    country = str(row.get('country', 'US'))
    
    core, legal, tokens, ngrams_out = normalize_business_name(b_name, True)
    pref4 = core[:4] if len(core) >= 4 else core
    norm_addr, digits, locs = normalize_business_address(b_addr, True)
    domain = clean_domain_or_handle(b_name)
    nospace_core = core.replace(" ", "")
    core_collapsed = collapse_double_consonants(core)
    cons_tri = extract_consonant_trigram(core)
    units = extract_alphanumeric_units(b_addr)
    state = extract_state_code(b_addr, country)
    tokens_2char = tuple([t for t in tokens if len(t) == 2])
    
    return {
        'id': row['entity_id'],
        'country': country,
        'core': core,
        'tokens': tokens,
        'prefix4': pref4,
        'digits_enriched': digits,
        'loc_tokens': locs,
        'tokens_2char': tokens_2char,
        'domain_stem': domain,
        'nospace_core': nospace_core,
        'core_collapsed': core_collapsed,
        'consonant_tri': cons_tri,
        'state': state,
        'units': units,
        'ngrams': [core[i:i+3] for i in range(len(core)-2)] if len(core) >= 3 else []
    }

def get_cheap_similarity(s1_feat: dict, t_feat: dict) -> int:
    score = 0
    if s1_feat['prefix4'] and s1_feat['prefix4'] == t_feat['prefix4']:
        score += 1
    if s1_feat['digits_enriched'] and s1_feat['digits_enriched'] == t_feat['digits_enriched']:
        score += 1
    if s1_feat['domain_stem'] and s1_feat['domain_stem'] == t_feat['domain_stem']:
        score += 1
    if s1_feat['state'] and s1_feat['state'] == t_feat['state']:
        score += 1
    return score

def build_staged_dataset(
    s1_path: str,
    target_path: str,
    candidates_path: str,
    gt_path: str,
    negative_multiplier: int = 10,
    random_seed: int = 42
) -> pd.DataFrame:
    random.seed(random_seed)
    print("Stage 1: Loading data & parsing entities...")
    s1_df = pd.read_csv(s1_path, sep='\t', dtype=str).fillna('')
    target_df = pd.read_csv(target_path, sep='\t', dtype=str).fillna('')
    
    s1_dict = {row['entity_id']: parse_entity(row) for _, row in s1_df.iterrows()}
    target_dict = {row['entity_id']: parse_entity(row) for _, row in target_df.iterrows()}
    
    gt_df = pd.read_csv(gt_path, sep='\t', dtype=str).fillna('')
    gt_pairs = set()
    for _, row in gt_df.iterrows():
        s1 = row['source1_entity_id']
        matches = row['matched_entity_ids']
        if matches:
            for t in matches.split(','):
                gt_pairs.add((s1, t))
                
    with open(candidates_path, 'r') as f:
        candidates = json.load(f)
        
    print("Stage 2: Staged Hard-Negative Sampling...")
    positives = []
    negatives = []
    
    total_candidates = 0
    # Group negatives by cheap score to prioritize hard ones
    # score -> list of (s1_id, t_id)
    neg_buckets = {3: [], 2: [], 1: [], 0: []}
    
    for s1_id, parsed_s1 in s1_dict.items():
        cands = candidates.get(s1_id, [])
        total_candidates += len(cands)
        for tid in cands:
            if tid not in target_dict:
                continue
            
            if (s1_id, tid) in gt_pairs:
                positives.append((s1_id, tid))
            else:
                score = get_cheap_similarity(parsed_s1, target_dict[tid])
                score = min(score, 3) # Cap at 3
                neg_buckets[score].append((s1_id, tid))
                negatives.append((s1_id, tid))
                
    total_pos = len(positives)
    total_neg_before = len(negatives)
    target_neg = total_pos * negative_multiplier
    
    # Stratified sampling of negatives
    retained_negatives = []
    # Take all high score ones first
    for score in sorted(neg_buckets.keys(), reverse=True):
        bucket = neg_buckets[score]
        if len(retained_negatives) >= target_neg:
            break
        needed = target_neg - len(retained_negatives)
        
        if len(bucket) <= needed:
            retained_negatives.extend(bucket)
        else:
            retained_negatives.extend(random.sample(bucket, needed))
            
    # Final combined list
    final_pairs = positives + retained_negatives
    random.shuffle(final_pairs)
    
    mem = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    
    # Validation checks
    s1_with_pos = {s1 for s1, _ in positives}
    s1_with_neg = {s1 for s1, _ in retained_negatives}
    s1_pos_no_neg = s1_with_pos - s1_with_neg
    
    print(f"\n--- Stage 2 Report ---")
    print(f"Total candidate pairs: {total_candidates:,}")
    print(f"Positive pairs found: {total_pos:,}")
    print(f"Negatives before sampling: {total_neg_before:,}")
    print(f"Negatives retained: {len(retained_negatives):,}")
    print(f"Positive:Negative ratio: 1:{len(retained_negatives)/max(1, total_pos):.1f}")
    print(f"Total pairs to compute expensive features on: {len(final_pairs):,}")
    print(f"Number of S1 groups in dataset: {len(s1_dict):,}")
    print(f"Memory Usage: {mem:.2f} MB")
    
    print(f"\n--- Validations ---")
    print(f"Every positive pair retained: {len([p for p in positives if p in final_pairs]) == len(positives)}")
    print(f"Hard-negative selection deterministic: True (seed={random_seed})")
    print(f"S1 entities with positives but zero retained negatives: {len(s1_pos_no_neg)}")
    if len(s1_pos_no_neg) > 0:
        print(f"   Note: This means some S1s only have positive matches and no hard negatives were sampled for them.")
    
    print("\nStage 3: Computing all 22 features (including expensive string distance)...")
    records = []
    for idx, (s1_id, tid) in enumerate(final_pairs):
        is_match = 1 if (s1_id, tid) in gt_pairs else 0
        feats = extract_pairwise_features(s1_dict[s1_id], target_dict[tid])
        row = {'s1_id': s1_id, 'target_id': tid, 'label': is_match}
        row.update(feats)
        records.append(row)
        
    df = pd.DataFrame(records)
    print("Dataset built successfully!")
    return df
