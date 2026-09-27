#!/usr/bin/env python3
"""
Full-Scale Production Matching Inference Engine.
Amazon ML Challenge 2026.

Consumes candidate_pairs.tsv and produces official submission-ready matching_results.tsv.
Supports both trained GBDT model and high-speed composite similarity matcher.
"""

import os
import sys
import time
import pickle
import argparse
from typing import Dict, List, Set, Tuple

sys.path.append('.')
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
from matching.baseline_matcher import compute_composite_similarity

def parse_entity_light(eid: str, bname: str, baddr: str, country: str) -> dict:
    """Fast entity feature extraction for pairwise matching."""
    core, legal, tokens, _ = normalize_business_name(bname, enable_transliteration=True)
    pref4 = core[:4] if len(core) >= 4 else core
    _, digits, locs = normalize_business_address(baddr, enable_transliteration=True)
    domain = clean_domain_or_handle(bname)
    nospace_core = core.replace(" ", "")
    core_collapsed = collapse_double_consonants(core)
    cons_tri = extract_consonant_trigram(core)
    units = extract_alphanumeric_units(baddr)
    state = extract_state_code(baddr, country)
    tokens_2char = tuple(t for t in tokens if len(t) == 2)

    return {
        'id': eid,
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

def load_target_raw_map(s2_path: str, s3_path: str) -> Dict[str, Tuple[str, str, str]]:
    """Load S2/S3 target text into compact raw tuple dictionary (~720 MB RAM for 10M records)."""
    targets = {}
    for p in [s2_path, s3_path]:
        if not p or not os.path.isfile(p):
            continue
        print(f"Loading target raw texts from {p}...")
        t0 = time.time()
        with open(p, 'r', encoding='utf-8') as f:
            next(f, None)
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                eid = parts[0].strip()
                bname = parts[1] if len(parts) > 1 else ''
                baddr = parts[2] if len(parts) > 2 else ''
                cty = parts[3] if len(parts) > 3 else ''
                targets[eid] = (bname, baddr, cty)
        print(f"  Loaded {len(targets):,} targets so far in {time.time()-t0:.1f}s")
    return targets

def load_s1_dict(s1_path: str) -> Dict[str, dict]:
    """Parse all S1 queries into feature dictionaries (~350 MB RAM for 1.73M queries)."""
    print(f"Loading and pre-parsing S1 queries from {s1_path}...")
    t0 = time.time()
    s1_dict = {}
    with open(s1_path, 'r', encoding='utf-8') as f:
        next(f, None)
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            eid = parts[0].strip()
            bname = parts[1] if len(parts) > 1 else ''
            baddr = parts[2] if len(parts) > 2 else ''
            cty = parts[3] if len(parts) > 3 else ''
            s1_dict[eid] = parse_entity_light(eid, bname, baddr, cty)
    print(f"Parsed {len(s1_dict):,} S1 queries in {time.time()-t0:.1f}s")
    return s1_dict

def run_matching_inference(
    candidates_path: str,
    s1_path: str,
    s2_path: str,
    s3_path: str,
    output_path: str,
    model_path: str = None,
    threshold: float = 0.65,
    batch_size: int = 50000
):
    print("="*60)
    print("STARTING MATCHING INFERENCE PIPELINE")
    print("="*60)
    print(f"Candidates Input:   {candidates_path}")
    print(f"Output Submission:  {output_path}")
    print(f"Decision Threshold: {threshold}")
    
    # Check if ML model exists
    model = None
    if model_path and os.path.exists(model_path):
        print(f"Loading trained matching model from {model_path}...")
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        print("ML Model loaded successfully.")
    else:
        print("Using production Composite Similarity scoring engine.")
        
    # 1. Load target and query data
    s1_dict = load_s1_dict(s1_path)
    target_raw = load_target_raw_map(s2_path, s3_path)
    
    # Target feature cache (LRU / on-demand)
    target_cache: Dict[str, dict] = {}
    
    def get_target_feat(tid: str) -> dict:
        feat = target_cache.get(tid)
        if feat is None:
            raw = target_raw.get(tid)
            if raw is None:
                return None
            feat = parse_entity_light(tid, raw[0], raw[1], raw[2])
            target_cache[tid] = feat
        return feat

    # 2. Stream through candidates file
    print(f"\nEvaluating candidate pairs and predicting matches...")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)
    
    t_start = time.time()
    total_queries = 0
    total_candidates_scored = 0
    total_matches_predicted = 0
    singletons = 0
    
    with open(candidates_path, 'r', encoding='utf-8') as in_f, \
         open(output_path, 'w', encoding='utf-8') as out_f:
        
        header = in_f.readline()
        out_f.write("source1_entity_id\tmatched_entity_ids\n")
        
        for line in in_f:
            if not line.strip():
                continue
            total_queries += 1
            s1_id, tab, rest = line.partition('\t')
            s1_id = s1_id.strip()
            cands_str = rest.rstrip('\r\n')
            
            s1_feat = s1_dict.get(s1_id)
            if not s1_feat or not cands_str:
                singletons += 1
                out_f.write(f"{s1_id}\t\n")
                continue
                
            candidate_ids = cands_str.split(',')
            matched_targets = []
            
            for tid in candidate_ids:
                tid = tid.strip()
                if not tid:
                    continue
                t_feat = get_target_feat(tid)
                if not t_feat:
                    continue
                    
                total_candidates_scored += 1
                
                # Feature extraction
                feats = extract_pairwise_features(s1_feat, t_feat)
                
                if model is not None:
                    # Model prediction
                    import pandas as pd
                    row_df = pd.DataFrame([feats])
                    prob = model.predict_proba(row_df)[0, 1]
                    score = prob
                else:
                    # Composite similarity
                    score = compute_composite_similarity(feats)
                    
                if score >= threshold:
                    matched_targets.append(tid)
                    
            if matched_targets:
                matched_targets.sort()
                total_matches_predicted += len(matched_targets)
                out_f.write(f"{s1_id}\t{','.join(matched_targets)}\n")
            else:
                singletons += 1
                out_f.write(f"{s1_id}\t\n")
                
            if total_queries % batch_size == 0:
                elapsed = time.time() - t_start
                rate = total_queries / elapsed
                print(f"Processed {total_queries:,} queries | Candidates scored: {total_candidates_scored:,} | Matches: {total_matches_predicted:,} | Rate: {rate:,.0f} q/s")
                
    elapsed = time.time() - t_start
    print("\n" + "="*60)
    print("MATCHING INFERENCE COMPLETED SUCCESSFULLY")
    print("="*60)
    print(f"Total S1 Queries Processed:   {total_queries:,}")
    print(f"Total Candidates Scored:      {total_candidates_scored:,}")
    print(f"Total Matches Predicted:      {total_matches_predicted:,}")
    print(f"Queries with Matches:         {total_queries - singletons:,}")
    print(f"Singletons (Zero Matches):    {singletons:,}")
    print(f"Inference Runtime:            {elapsed:.1f}s ({total_queries/elapsed:,.0f} queries/s)")
    print(f"Output File:                  {output_path} ({os.path.getsize(output_path)/(1024*1024):.2f} MB)")
    print("="*60)
    return output_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run full matching inference on candidate_pairs.tsv")
    parser.add_argument("--candidates", default="candidate_pairs.tsv")
    parser.add_argument("--s1", default="student_resource/dataset/test/test_source1.tsv")
    parser.add_argument("--s2", default="student_resource/dataset/test/test_source2.tsv")
    parser.add_argument("--s3", default="student_resource/dataset/test/test_source3.tsv")
    parser.add_argument("--model", default="matching/hgbm_baseline.pkl")
    parser.add_argument("--threshold", type=float, default=0.65)
    parser.add_argument("--output", default="matching_results.tsv")
    args = parser.parse_args()
    
    run_matching_inference(
        candidates_path=args.candidates,
        s1_path=args.s1,
        s2_path=args.s2,
        s3_path=args.s3,
        output_path=args.output,
        model_path=args.model if os.path.exists(args.model) else None,
        threshold=args.threshold
    )
