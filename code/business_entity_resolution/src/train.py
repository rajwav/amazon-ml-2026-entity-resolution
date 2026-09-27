#!/usr/bin/env python3
"""
Model Training Script for LightGBM V2 Entity Resolution.
Amazon ML Challenge 2026.
"""

import os
import sys
import time
import pickle
import numpy as np
from collections import defaultdict
import lightgbm as lgb
from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import (
    clean_name, get_tokens, get_addr_tokens, get_digits, get_char_bigrams,
    extract_features_v2_fast
)
from evaluator import compute_macro_f05

def train_model(s1_path: str, target_path: str, gt_path: str, model_save_path: str, thresh_save_path: str):
    print("Loading Ground Truth...")
    gt = defaultdict(set)
    with open(gt_path, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            s1, tab, rest = line.partition('\t')
            s1 = s1.strip()
            if rest.strip():
                gt[s1].update(rest.strip().split(','))

    print("Indexing S1...")
    s1_data = {}
    idx_exact = defaultdict(list)
    idx_token_dig = defaultdict(list)
    idx_pref_dig = defaultdict(list)

    with open(s1_path, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            p = line.rstrip('\r\n').split('\t')
            sid = p[0].strip()
            cty = p[3].strip()
            cname = clean_name(p[1])
            tokens = get_tokens(p[1])
            digs = get_digits(p[2])
            atoks = get_addr_tokens(p[2])
            bg = get_char_bigrams(cname)
            s1_data[sid] = (cname, tokens, digs, atoks, bg)

            if len(cname) >= 3 and len(idx_exact[(cty, cname)]) < 20:
                idx_exact[(cty, cname)].append(sid)
            if digs:
                first_dig = digs[0]
                if len(cname) >= 5 and len(idx_pref_dig[(cty, cname[:5], first_dig)]) < 20:
                    idx_pref_dig[(cty, cname[:5], first_dig)].append(sid)
                for tok in tokens:
                    if len(idx_token_dig[(cty, tok, first_dig)]) < 20:
                        idx_token_dig[(cty, tok, first_dig)].append(sid)

    print("Generating Candidates from Targets...")
    target_data = {}
    candidate_pairs = defaultdict(set)
    with open(target_path, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            p = line.rstrip('\r\n').split('\t')
            tid = p[0].strip()
            cty = p[3].strip()
            cname = clean_name(p[1])
            tokens = get_tokens(p[1])
            digs = get_digits(p[2])
            atoks = get_addr_tokens(p[2])
            bg = get_char_bigrams(cname)
            target_data[tid] = (cname, tokens, digs, atoks, bg)

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
                if len(candidate_pairs[sid]) < 50:
                    candidate_pairs[sid].add(tid)

    # Feature extraction
    print("Extracting 11 Features...")
    X_rows = []
    y_labels = []
    s1_ids = []
    tid_ids = []

    for sid, tids in candidate_pairs.items():
        s1_t = s1_data[sid]
        actual = gt.get(sid, set())
        for tid in tids:
            t_t = target_data[tid]
            feat = extract_features_v2_fast(
                s1_t[0], s1_t[1], s1_t[2], s1_t[3], s1_t[4],
                t_t[0], t_t[1], t_t[2], t_t[3], t_t[4]
            )
            label = 1 if tid in actual else 0
            X_rows.append(feat)
            y_labels.append(label)
            s1_ids.append(sid)
            tid_ids.append(tid)

    X = np.array(X_rows, dtype=np.float32)
    y = np.array(y_labels, dtype=np.int32)

    unique_s1 = list(s1_data.keys())
    train_s1, val_s1 = train_test_split(unique_s1, test_size=0.25, random_state=42)
    train_s1_set = set(train_s1)
    val_s1_set = set(val_s1)

    train_mask = np.array([sid in train_s1_set for sid in s1_ids])
    val_mask = ~train_mask

    val_pair_s1 = [s1_ids[i] for i in range(len(s1_ids)) if val_mask[i]]
    val_pair_tid = [tid_ids[i] for i in range(len(tid_ids)) if val_mask[i]]
    val_gt = {sid: gt.get(sid, set()) for sid in val_s1}

    print(f"Training LightGBM on {int(train_mask.sum()):,} pairs...")
    scale_pos = (len(y[train_mask]) - y[train_mask].sum()) / max(1, y[train_mask].sum())
    model = lgb.LGBMClassifier(
        n_estimators=100, learning_rate=0.08, num_leaves=31,
        scale_pos_weight=min(scale_pos, 5.0), random_state=42, n_jobs=-1
    )
    model.fit(X[train_mask], y[train_mask])

    probs = model.predict_proba(X[val_mask])[:, 1]

    # Threshold calibration
    best_th = 0.40
    best_f05 = -1.0
    for th in [0.30, 0.40, 0.50, 0.60, 0.70]:
        preds = {sid: set() for sid in val_s1}
        for i in range(len(probs)):
            if probs[i] >= th:
                preds[val_pair_s1[i]].add(val_pair_tid[i])
        res = compute_macro_f05(preds, val_gt)
        if res['macro_f05'] > best_f05:
            best_f05 = res['macro_f05']
            best_th = th

    print(f"Optimal Threshold: {best_th} (Validation Macro F0.5 = {best_f05:.4f})")

    with open(model_save_path, 'wb') as f:
        pickle.dump(model, f)
    with open(thresh_save_path, 'w') as f:
        f.write(str(best_th))
    print(f"Saved model to {model_save_path} and threshold to {thresh_save_path}")

if __name__ == '__main__':
    train_model(
        'experiments/data/pilot_s1.tsv',
        'experiments/data/pilot_targets.tsv',
        'experiments/data/pilot_ground_truth.tsv',
        'code/business_entity_resolution/src/model_v2.pkl',
        'code/business_entity_resolution/src/threshold_v2.txt'
    )
