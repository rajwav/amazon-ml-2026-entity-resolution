#!/usr/bin/env python3
"""
End-to-End Test Inference Script.
Amazon ML Challenge 2026: Business Entity Resolution.

Usage:
    python3 run_inference.py [--test-dir PATH] [--output-dir PATH]
"""

import os
import sys
import time
import pickle
import argparse
import numpy as np
from collections import defaultdict

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import (
    clean_name, get_tokens, get_addr_tokens, get_digits, get_char_bigrams,
    extract_features_v2_fast
)

def run_inference(test_dir: str, output_dir: str):
    t_start = time.time()
    s1_path = os.path.join(test_dir, 'test_source1.tsv')
    s2_path = os.path.join(test_dir, 'test_source2.tsv')
    s3_path = os.path.join(test_dir, 'test_source3.tsv')

    os.makedirs(output_dir, exist_ok=True)
    out_matching = os.path.join(output_dir, 'matching_results.tsv')
    out_candidates = os.path.join(output_dir, 'candidate_pairs.tsv')

    model_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(model_dir, 'model_v2.pkl')
    thresh_path = os.path.join(model_dir, 'threshold_v2.txt')

    print(f"Loading Model V2 from {model_path}...")
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    with open(thresh_path, 'r') as f:
        threshold = float(f.read().strip())
    print(f"Loaded model. Decision threshold: {threshold:.2f}")

    # 1. Ingest S1 Entities & Build Index
    print("\n--- Step 1: Ingesting & Indexing S1 Queries ---")
    t_s1 = time.time()
    s1_order = []
    s1_data = {}

    idx_exact = defaultdict(list)
    idx_token_dig = defaultdict(list)
    idx_pref_dig = defaultdict(list)

    with open(s1_path, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            eid = parts[0].strip()
            s1_order.append(eid)
            cty = parts[3].strip() if len(parts) > 3 else ''
            cname = clean_name(parts[1]) if len(parts) > 1 else ''
            tokens = get_tokens(parts[1]) if len(parts) > 1 else []
            digs = get_digits(parts[2]) if len(parts) > 2 else ()
            atoks = get_addr_tokens(parts[2]) if len(parts) > 2 else []
            bg = get_char_bigrams(cname)
            s1_data[eid] = (cname, tokens, digs, atoks, bg)

            if len(cname) >= 3 and len(idx_exact[(cty, cname)]) < 20:
                idx_exact[(cty, cname)].append(eid)
            if digs:
                first_dig = digs[0]
                if len(cname) >= 5 and len(idx_pref_dig[(cty, cname[:5], first_dig)]) < 20:
                    idx_pref_dig[(cty, cname[:5], first_dig)].append(eid)
                for tok in tokens:
                    if len(idx_token_dig[(cty, tok, first_dig)]) < 20:
                        idx_token_dig[(cty, tok, first_dig)].append(eid)

    print(f"  Ingested and indexed {len(s1_order):,} S1 queries in {time.time()-t_s1:.2f}s")

    candidate_counts = defaultdict(int)
    predicted_matches = defaultdict(list)
    all_candidates = defaultdict(list)

    BATCH_SIZE = 500000
    batch_feats = []
    batch_pairs = []

    def flush_batch():
        nonlocal batch_feats, batch_pairs
        if not batch_feats:
            return
        X_batch = np.array(batch_feats, dtype=np.float32)
        probs = model.predict_proba(X_batch)[:, 1]

        for idx in range(len(probs)):
            prob = probs[idx]
            sid, tid = batch_pairs[idx]

            if len(all_candidates[sid]) < 50:
                all_candidates[sid].append(tid)

            if prob >= threshold:
                if len(predicted_matches[sid]) < 10:
                    predicted_matches[sid].append(tid)

        batch_feats = []
        batch_pairs = []

    # 2. Streaming Target Entities
    print("\n--- Step 2: Streaming Targets with Vectorized LightGBM Inference ---")
    t_targets = time.time()
    for target_file in [s2_path, s3_path]:
        t_file = time.time()
        print(f"Streaming from {target_file}...")
        count = 0
        with open(target_file, 'r', encoding='utf-8') as f:
            next(f)
            for line in f:
                count += 1
                parts = line.rstrip('\r\n').split('\t')
                tid = parts[0].strip()
                cty = parts[3].strip() if len(parts) > 3 else ''
                cname = clean_name(parts[1]) if len(parts) > 1 else ''
                tokens = get_tokens(parts[1]) if len(parts) > 1 else []
                digs = get_digits(parts[2]) if len(parts) > 2 else ()
                atoks = get_addr_tokens(parts[2]) if len(parts) > 2 else []
                bg = get_char_bigrams(cname)

                matching_s1s = set()
                if len(cname) >= 3 and (cty, cname) in idx_exact:
                    matching_s1s.update(idx_exact[(cty, cname)])
                if digs:
                    first_dig = digs[0]
                    if len(cname) >= 5 and (cty, cname[:5], first_dig) in idx_pref_dig:
                        matching_s1s.update(idx_pref_dig[(cty, cname[:5], first_dig)])
                    for tok in tokens:
                        if (cty, tok, first_dig) in idx_token_dig:
                            matching_s1s.update(idx_token_dig[(cty, tok, first_dig)])

                for sid in matching_s1s:
                    if candidate_counts[sid] < 50:
                        candidate_counts[sid] += 1
                        s1_t = s1_data[sid]
                        feat = extract_features_v2_fast(
                            s1_t[0], s1_t[1], s1_t[2], s1_t[3], s1_t[4],
                            cname, tokens, digs, atoks, bg
                        )
                        batch_feats.append(feat)
                        batch_pairs.append((sid, tid))

                        if len(batch_feats) >= BATCH_SIZE:
                            flush_batch()

        print(f"  Finished {os.path.basename(target_file)} in {time.time()-t_file:.2f}s")

    flush_batch()
    print(f"  Target streaming + inference completed in {time.time()-t_targets:.2f}s")

    del s1_data
    del idx_exact
    del idx_pref_dig
    del idx_token_dig
    del candidate_counts
    del model
    del batch_feats
    del batch_pairs
    import gc
    gc.collect()

    # 3. Export Output Files
    print("\n--- Step 3: Exporting Submission Files ---")
    t_write = time.time()
    with open(out_matching, 'w', encoding='utf-8', buffering=1024*1024) as f_m, \
         open(out_candidates, 'w', encoding='utf-8', buffering=1024*1024) as f_c:

        f_m.write("source1_entity_id\tmatched_entity_ids\n")
        f_c.write("source1_entity_id\tcandidate_entity_ids\n")

        for sid in s1_order:
            m_list = predicted_matches.get(sid, [])
            c_list = all_candidates.get(sid, [])

            c_set = set(c_list)
            for mid in m_list:
                if mid not in c_set:
                    c_list.append(mid)
                    c_set.add(mid)

            m_str = ",".join(m_list) if m_list else ""
            c_str = ",".join(c_list) if c_list else ""

            f_m.write(f"{sid}\t{m_str}\n")
            f_c.write(f"{sid}\t{c_str}\n")

    print(f"Export completed in {time.time()-t_write:.2f}s")
    print(f"Total pipeline runtime: {time.time()-t_start:.2f}s")
    print(f"Generated: {out_matching} ({os.path.getsize(out_matching)/(1024*1024):.2f} MB)")
    print(f"Generated: {out_candidates} ({os.path.getsize(out_candidates)/(1024*1024):.2f} MB)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run full-scale business entity resolution inference.")
    parser.add_argument('--test-dir', default='student_resource/dataset/test', help='Path to test directory')
    parser.add_argument('--output-dir', default='output', help='Path to output directory')
    args = parser.parse_args()
    run_inference(args.test_dir, args.output_dir)
