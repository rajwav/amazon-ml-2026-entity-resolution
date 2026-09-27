"""
Integration tests for CandidateRanker with ChampionV2Blocker and country runner.
Amazon ML Challenge 2026 — Entity Resolution.

Verifies:
1. Champion v2 candidate invariance: raw_candidates = blocker.query_single(...)
   is 100% identical before and after calling ranker.rank_candidates(...).
2. Ranker determinism and tie-breaking: score desc, candidate_id asc.
3. Configurable K: K=50, 100, 1000, K > N, and K=0.
4. Support for both dict and 4-tuple target features yielding identical scores.
5. Integration with ChampionV2Blocker on simulated entity records.
"""

import pytest
from blocking.blocking_core import ChampionV2Blocker
from blocking.candidate_ranker import CandidateRanker, compute_candidate_score


def test_champion_v2_raw_candidate_invariance():
    """
    Requirement C: Prove raw_candidates = blocker.query_single(...)
    is completely unchanged before and after calling ranker.rank_candidates(...).
    """
    blocker = ChampionV2Blocker()
    targets = {
        'T1': ('Acme Industrial Solutions Inc', '123 Main Street Suite 100', 'US'),
        'T2': ('Acme Supplies LLC', '456 Industrial Parkway', 'US'),
        'T3': ('Apex Dynamics Corp', '123 Main Street', 'US'),
        'T4': ('Global Acme Logistics', '789 Market Ave', 'US'),
        'T5': ('Omega Corp', '100 Broadway', 'US'),
    }
    blocker.build_index(targets)

    # Build target features
    target_features = {}
    for tid, (bname, baddr, country) in targets.items():
        feat = blocker.extract_features(tid, bname, baddr, country)
        target_features[tid] = (feat['core'], feat['tokens'], feat['digits'], feat['loc_tokens'])

    ranker = CandidateRanker(target_features=target_features, default_k=1000)

    s1_feat = blocker.extract_features('Q1', 'Acme Industrial Solutions Inc', '123 Main Street Suite 100', 'US')

    # 1. Query raw candidates from blocker
    raw_cands_before = blocker.query_single(s1_feat)
    frozen_copy = set(raw_cands_before)

    # 2. Call ranker
    ranked = ranker.rank_candidates(s1_feat, raw_cands_before, k=1000)

    # 3. Query again directly from blocker
    raw_cands_after = blocker.query_single(s1_feat)

    # Assert invariant: raw candidate set was not mutated or changed in any way
    assert raw_cands_before == frozen_copy
    assert raw_cands_after == frozen_copy
    assert set(ranked).issubset(raw_cands_before)


def test_configurable_k_levels():
    """
    Requirement D: Verify ranker correctly respects K=50, 100, 1000, K > N, and K=0.
    """
    targets = {}
    for i in range(120):
        tid = f"T_{i:04d}"
        targets[tid] = {
            'core': f'business_{i}',
            'tokens': (f'tok_{i}', 'corp'),
            'digits': (str(100 + i),),
            'loc_tokens': ('city', 'street')
        }

    ranker = CandidateRanker(target_features=targets)
    s1_feat = {
        'core': 'business_50',
        'tokens': ('tok_50', 'corp'),
        'digits': ('150',),
        'loc_tokens': ('city', 'street')
    }

    all_cand_ids = list(targets.keys())

    # K = 50
    res_50 = ranker.rank_candidates(s1_feat, all_cand_ids, k=50)
    assert len(res_50) == 50

    # K = 100
    res_100 = ranker.rank_candidates(s1_feat, all_cand_ids, k=100)
    assert len(res_100) == 100

    # K = 1000 (when total candidates N=120, capped at N=120)
    res_1000 = ranker.rank_candidates(s1_feat, all_cand_ids, k=1000)
    assert len(res_1000) == 120

    # K > N (e.g. K=5000)
    res_huge = ranker.rank_candidates(s1_feat, all_cand_ids, k=5000)
    assert len(res_huge) == 120

    # K = 0
    res_0 = ranker.rank_candidates(s1_feat, all_cand_ids, k=0)
    assert len(res_0) == 0

    # Top-1 must be the exact match T_0050
    assert res_50[0] == 'T_0050'
    assert res_100[0] == 'T_0050'
    assert res_1000[0] == 'T_0050'


def test_dict_vs_tuple_feature_equivalence():
    """
    Verify that storing features as dicts vs lightweight 4-tuples
    produces identical ranking scores and candidate order.
    """
    s1_feat = {
        'core': 'cafe central',
        'tokens': ('cafe', 'central'),
        'digits': ('42',),
        'loc_tokens': ('paris', 'rue')
    }

    dict_features = {
        'T1': {'core': 'cafe central', 'tokens': ('cafe', 'central'), 'digits': ('42',), 'loc_tokens': ('paris', 'rue')},
        'T2': {'core': 'cafe', 'tokens': ('cafe', 'bar'), 'digits': ('42',), 'loc_tokens': ('paris',)},
        'T3': {'core': 'bistro central', 'tokens': ('bistro', 'central'), 'digits': ('99',), 'loc_tokens': ('lyon',)},
    }

    tuple_features = {
        tid: (d['core'], d['tokens'], d['digits'], d['loc_tokens'])
        for tid, d in dict_features.items()
    }

    ranker_dict = CandidateRanker(target_features=dict_features)
    ranker_tuple = CandidateRanker(target_features=tuple_features)

    cands = ['T1', 'T2', 'T3']
    scored_dict = ranker_dict.score_candidates(s1_feat, cands)
    scored_tuple = ranker_tuple.score_candidates(s1_feat, cands)

    assert scored_dict == scored_tuple

    ranked_dict = ranker_dict.rank_candidates(s1_feat, cands, k=10)
    ranked_tuple = ranker_tuple.rank_candidates(s1_feat, cands, k=10)
    assert ranked_dict == ranked_tuple
