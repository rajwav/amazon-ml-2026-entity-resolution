"""
Correctness & Equivalence Test: Monolithic Champion v2 vs Country-Partitioned Champion v2.
Verifies that country-partitioned execution produces 100% IDENTICAL candidate sets
for every single query compared to the monolithic runner on the pilot benchmark.
"""

import sys
import collections
from typing import Dict, Set, Tuple

sys.path.append('.')
from blocking.blocking_core import ChampionV2Blocker

PILOT_S1 = "experiments/data/pilot_s1.tsv"
PILOT_TARGETS = "experiments/data/pilot_targets.tsv"
PILOT_GT = "experiments/data/pilot_ground_truth.tsv"

def load_data():
    s1_records = []
    with open(PILOT_S1, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            p = line.rstrip('\r\n').split('\t')
            while len(p) < 4: p.append('')
            s1_records.append((p[0], p[1], p[2], p[3]))

    targets_all = {}
    targets_by_country = collections.defaultdict(dict)
    with open(PILOT_TARGETS, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            p = line.rstrip('\r\n').split('\t')
            while len(p) < 4: p.append('')
            eid, bname, baddr, country = p[0], p[1], p[2], p[3]
            targets_all[eid] = (bname, baddr, country)
            targets_by_country[country][eid] = (bname, baddr, country)

    gt_matches = {}
    total_true_pairs = 0
    with open(PILOT_GT, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            s1_id, tab, rest = line.rstrip('\r\n').partition('\t')
            mids = [x.strip() for x in rest.split(',') if x.strip()] if rest.strip() else []
            gt_matches[s1_id] = mids
            total_true_pairs += len(mids)

    return s1_records, targets_all, targets_by_country, gt_matches, total_true_pairs

def test_equivalence():
    print("Loading pilot data...")
    s1_records, targets_all, targets_by_country, gt_matches, total_true_pairs = load_data()
    print(f"Loaded {len(s1_records):,} S1 queries, {len(targets_all):,} targets across {list(targets_by_country.keys())}")

    # 1. Monolithic Run
    print("\n--- Running Monolithic Champion v2 ---")
    mono_blocker = ChampionV2Blocker()
    mono_blocker.build_index(targets_all)
    
    mono_candidates: Dict[str, Set[str]] = {}
    mono_recalled = 0
    for s1_id, bname, baddr, country in s1_records:
        feat = mono_blocker.extract_features(s1_id, bname, baddr, country)
        cands = mono_blocker.query_single(feat)
        mono_candidates[s1_id] = cands
        for mid in gt_matches.get(s1_id, []):
            if mid in cands:
                mono_recalled += 1

    print(f"Monolithic: {len(mono_candidates):,} queries, {sum(len(c) for c in mono_candidates.values()):,} total candidates")
    print(f"Monolithic Recall: {mono_recalled}/{total_true_pairs} ({mono_recalled/total_true_pairs*100:.4f}%)")

    # 2. Country-Partitioned Run
    print("\n--- Running Country-Partitioned Champion v2 ---")
    part_candidates: Dict[str, Set[str]] = {}
    part_recalled = 0

    s1_by_country = collections.defaultdict(list)
    for row in s1_records:
        s1_by_country[row[3]].append(row)

    for country, country_s1 in s1_by_country.items():
        country_targets = targets_by_country[country]
        print(f"Partition [{country}]: {len(country_targets):,} targets, {len(country_s1):,} S1 queries")
        
        country_blocker = ChampionV2Blocker()
        country_blocker.build_index(country_targets)
        
        for s1_id, bname, baddr, c_str in country_s1:
            feat = country_blocker.extract_features(s1_id, bname, baddr, c_str)
            cands = country_blocker.query_single(feat)
            part_candidates[s1_id] = cands
            for mid in gt_matches.get(s1_id, []):
                if mid in cands:
                    part_recalled += 1

    print(f"Partitioned: {len(part_candidates):,} queries, {sum(len(c) for c in part_candidates.values()):,} total candidates")
    print(f"Partitioned Recall: {part_recalled}/{total_true_pairs} ({part_recalled/total_true_pairs*100:.4f}%)")

    # 3. Exact Equivalence Verification
    print("\n--- Verifying Exact Query-by-Query Equivalence ---")
    assert len(mono_candidates) == len(part_candidates), "Query counts differ!"
    
    mismatches = 0
    total_mono_cands = 0
    total_part_cands = 0

    for s1_id in mono_candidates:
        c_mono = mono_candidates[s1_id]
        c_part = part_candidates[s1_id]
        total_mono_cands += len(c_mono)
        total_part_cands += len(c_part)
        
        diff = c_mono ^ c_part
        if diff:
            mismatches += 1
            if mismatches <= 5:
                print(f"Mismatch for {s1_id}: missing={c_mono - c_part}, extra={c_part - c_mono}")

    print(f"Total queries compared:    {len(mono_candidates):,}")
    print(f"Mismatched queries:        {mismatches}")
    print(f"Monolithic total cands:    {total_mono_cands:,}")
    print(f"Partitioned total cands:   {total_part_cands:,}")
    print(f"Monolithic recall:         {mono_recalled} / {total_true_pairs}")
    print(f"Partitioned recall:        {part_recalled} / {total_true_pairs}")

    assert mismatches == 0, f"Equivalence test FAILED with {mismatches} mismatched queries!"
    assert total_mono_cands == total_part_cands, "Candidate count mismatch!"
    assert mono_recalled == part_recalled == 34476, f"Recall mismatch! Expected 34,476, got {part_recalled}"
    print("\n=======================================================")
    print("EQUIVALENCE TEST PASSED: 100.00% IDENTICAL CANDIDATES")
    print("Zero candidates lost. Zero candidates added. Exact match.")
    print("=======================================================\n")
    return True

if __name__ == "__main__":
    test_equivalence()

