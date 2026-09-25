"""
End-to-End Regression Test for Champion v2 Surgical Blocker on Pilot Benchmark.
Verifies that ChampionV2Blocker achieves exactly 99.9855% recall and 5 misses on the 10k pilot.
"""

import os
import pytest
from blocking.blocking_core import ChampionV2Blocker

PILOT_S1 = "experiments/data/pilot_s1.tsv"
PILOT_TARGETS = "experiments/data/pilot_targets.tsv"
PILOT_GT = "experiments/data/pilot_ground_truth.tsv"

@pytest.mark.skipif(not os.path.isfile(PILOT_S1), reason="Pilot data not available")
def test_champion_v2_pilot_recall():
    # 1. Load Targets
    targets = {}
    with open(PILOT_TARGETS, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            p = line.rstrip('\r\n').split('\t')
            while len(p) < 4: p.append('')
            targets[p[0]] = (p[1], p[2], p[3])

    # 2. Build Index
    blocker = ChampionV2Blocker()
    blocker.build_index(targets)
    assert blocker.is_indexed

    # 3. Load Ground Truth
    gt_matches = {}
    total_true_pairs = 0
    with open(PILOT_GT, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            s1_id, tab, rest = line.rstrip('\r\n').partition('\t')
            mids = [x.strip() for x in rest.split(',') if x.strip()] if rest.strip() else []
            gt_matches[s1_id] = mids
            total_true_pairs += len(mids)

    # 4. Query S1
    recalled = 0
    total_cands = 0
    zero_cands = 0
    with open(PILOT_S1, 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            p = line.rstrip('\r\n').split('\t')
            while len(p) < 4: p.append('')
            feat = blocker.extract_features(p[0], p[1], p[2], p[3])
            cands = blocker.query_single(feat)
            total_cands += len(cands)
            if len(cands) == 0:
                zero_cands += 1
            for mid in gt_matches.get(p[0], []):
                if mid in cands:
                    recalled += 1

    recall_pct = (recalled / total_true_pairs) * 100
    missed_count = total_true_pairs - recalled

    # Assert exact benchmark numbers:
    assert recalled == 34476, f"Expected 34,476 recalled pairs, got {recalled}"
    assert missed_count == 5, f"Expected exactly 5 missed pairs, got {missed_count}"
    assert recall_pct > 99.98, f"Expected recall > 99.98%, got {recall_pct:.4f}%"
    assert zero_cands == 0, f"Expected 0 zero-candidate queries, got {zero_cands}"
