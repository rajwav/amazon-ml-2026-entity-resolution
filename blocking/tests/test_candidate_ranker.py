"""
Unit Tests for Candidate Ranking and Pruning Layer.
Amazon ML Challenge 2026.

Verifies:
1. exact-name scoring
2. name Jaccard scoring
3. shared-digit scoring
4. location Jaccard scoring
5. combined score
6. deterministic candidate-ID tie breaking
7. K limit
8. K larger than candidate count
9. zero candidates
10. multiple true matches surviving ranking
11. raw Champion V2 candidate set remains unchanged by ranking layer
"""

import pytest
from blocking.candidate_ranker import (
    CandidateRanker,
    compute_exact_name,
    compute_name_jaccard,
    compute_shared_digits,
    compute_location_jaccard,
    compute_candidate_score,
    WEIGHT_EXACT_NAME,
    WEIGHT_NAME_JACCARD,
    WEIGHT_SHARED_DIGITS,
    WEIGHT_LOCATION_JACCARD,
)
from blocking.blocking_core import ChampionV2Blocker


# 1. Exact-Name Scoring Tests
def test_exact_name_scoring():
    # Identical non-empty core names
    s1 = {'core': 'apex summit'}
    t1 = {'core': 'apex summit'}
    assert compute_exact_name(s1, t1) == 1.0

    # Differing core names
    t2 = {'core': 'apex group'}
    assert compute_exact_name(s1, t2) == 0.0

    # Empty core names
    assert compute_exact_name({'core': ''}, {'core': ''}) == 0.0
    assert compute_exact_name({'core': 'apex'}, {'core': ''}) == 0.0
    assert compute_exact_name({'core': ''}, {'core': 'apex'}) == 0.0


# 2. Name Jaccard Scoring Tests
def test_name_jaccard_scoring():
    # Identical token sets
    s1 = {'tokens': ('apex', 'summit')}
    t1 = {'tokens': ('apex', 'summit')}
    assert compute_name_jaccard(s1, t1) == 1.0

    # Partial overlap: 1 shared, union size 3 -> 1/3
    t2 = {'tokens': ('apex', 'holdings')}
    assert pytest.approx(compute_name_jaccard(s1, t2), rel=1e-5) == 1.0 / 3.0

    # Disjoint token sets
    t3 = {'tokens': ('global', 'ventures')}
    assert compute_name_jaccard(s1, t3) == 0.0

    # Empty token sets
    assert compute_name_jaccard({'tokens': ()}, {'tokens': ()}) == 0.0
    assert compute_name_jaccard({'tokens': ('apex',)}, {'tokens': ()}) == 0.0


# 3. Shared-Digit Scoring Tests
def test_shared_digit_scoring():
    # Common street digit
    s1 = {'digits': ('100', '200')}
    t1 = {'digits': ('100', '300')}
    assert compute_shared_digits(s1, t1) == 1.0

    # No common digits
    t2 = {'digits': ('500', '600')}
    assert compute_shared_digits(s1, t2) == 0.0

    # Empty digits
    assert compute_shared_digits({'digits': ()}, {'digits': ()}) == 0.0
    assert compute_shared_digits({'digits': ('100',)}, {'digits': ()}) == 0.0


# 4. Location Jaccard Scoring Tests
def test_location_jaccard_scoring():
    # Identical location tokens
    s1 = {'loc_tokens': ('new', 'york')}
    t1 = {'loc_tokens': ('new', 'york')}
    assert compute_location_jaccard(s1, t1) == 1.0

    # Partial overlap: 1 shared ("york"), union size 3 ("new", "york", "city") -> 1/3
    t2 = {'loc_tokens': ('york', 'city')}
    assert pytest.approx(compute_location_jaccard(s1, t2), rel=1e-5) == 1.0 / 3.0

    # Disjoint location tokens
    t3 = {'loc_tokens': ('california', 'los', 'angeles')}
    assert compute_location_jaccard(s1, t3) == 0.0

    # Empty location tokens
    assert compute_location_jaccard({'loc_tokens': ()}, {'loc_tokens': ()}) == 0.0


# 5. Combined Score Tests
def test_combined_score():
    s1 = {
        'core': 'willow cafe',
        'tokens': ('willow', 'cafe'),
        'digits': ('12',),
        'loc_tokens': ('main', 'street'),
    }
    # Perfect match on all 4 components
    t_perfect = {
        'core': 'willow cafe',
        'tokens': ('willow', 'cafe'),
        'digits': ('12',),
        'loc_tokens': ('main', 'street'),
    }
    expected_perfect = (
        5.0 * 1.0  # exact_name
        + 4.0 * 1.0  # name_jaccard
        + 2.5 * 1.0  # shared_digits
        + 1.5 * 1.0  # loc_jaccard
    )
    assert expected_perfect == 13.0
    assert pytest.approx(compute_candidate_score(s1, t_perfect), rel=1e-5) == 13.0

    # Partial match
    t_partial = {
        'core': 'willow bistro',  # exact=0.0
        'tokens': ('willow', 'bistro'),  # 1/3
        'digits': ('12', '4b'),  # shared=1.0
        'loc_tokens': ('main', 'avenue'),  # 1/3
    }
    expected_partial = (
        5.0 * 0.0
        + 4.0 * (1.0 / 3.0)
        + 2.5 * 1.0
        + 1.5 * (1.0 / 3.0)
    )
    assert pytest.approx(compute_candidate_score(s1, t_partial), rel=1e-5) == expected_partial

    # Zero match
    t_zero = {
        'core': 'omega steel',
        'tokens': ('omega', 'steel'),
        'digits': ('99',),
        'loc_tokens': ('broadway',),
    }
    assert compute_candidate_score(s1, t_zero) == 0.0


# 6. Deterministic Candidate-ID Tie Breaking Tests
def test_deterministic_tie_breaking():
    s1 = {'core': 'target', 'tokens': ('target',), 'digits': (), 'loc_tokens': ()}
    # Four candidates with identical score (all 0.0)
    target_store = {
        'S2-004': {'core': 'unrelated_d', 'tokens': (), 'digits': (), 'loc_tokens': ()},
        'S2-002': {'core': 'unrelated_b', 'tokens': (), 'digits': (), 'loc_tokens': ()},
        'S2-001': {'core': 'unrelated_a', 'tokens': (), 'digits': (), 'loc_tokens': ()},
        'S2-003': {'core': 'unrelated_c', 'tokens': (), 'digits': (), 'loc_tokens': ()},
    }
    ranker = CandidateRanker(target_features=target_store, default_k=10)
    raw_cands = ['S2-004', 'S2-002', 'S2-001', 'S2-003']

    ranked = ranker.rank_candidates(s1, raw_cands)
    # Must sort strictly ascending by candidate_entity_id on score ties
    assert ranked == ['S2-001', 'S2-002', 'S2-003', 'S2-004']


# 7. K Limit Tests
def test_k_limit():
    s1 = {'core': 'anchor', 'tokens': ('anchor',), 'digits': ('10',), 'loc_tokens': ()}
    # Create 10 candidates with varying scores
    target_store = {}
    for i in range(10):
        cid = f'T-{i:02d}'
        if i < 3:
            target_store[cid] = {'core': 'anchor', 'tokens': ('anchor',), 'digits': ('10',), 'loc_tokens': ()}  # high score
        elif i < 6:
            target_store[cid] = {'core': 'anchor', 'tokens': ('anchor',), 'digits': (), 'loc_tokens': ()}  # med score
        else:
            target_store[cid] = {'core': 'other', 'tokens': (), 'digits': (), 'loc_tokens': ()}  # low score

    ranker = CandidateRanker(target_features=target_store, default_k=50)

    # Test K=3 limit
    top_3 = ranker.rank_candidates(s1, list(target_store.keys()), k=3)
    assert len(top_3) == 3
    assert top_3 == ['T-00', 'T-01', 'T-02']

    # Test K=5 limit
    top_5 = ranker.rank_candidates(s1, list(target_store.keys()), k=5)
    assert len(top_5) == 5
    assert top_5 == ['T-00', 'T-01', 'T-02', 'T-03', 'T-04']


# 8. K Larger Than Candidate Count Tests
def test_k_larger_than_candidate_count():
    s1 = {'core': 'beacon', 'tokens': ('beacon',), 'digits': (), 'loc_tokens': ()}
    target_store = {
        'T-1': {'core': 'beacon', 'tokens': ('beacon',), 'digits': (), 'loc_tokens': ()},
        'T-2': {'core': 'beacon light', 'tokens': ('beacon', 'light'), 'digits': (), 'loc_tokens': ()},
    }
    ranker = CandidateRanker(target_features=target_store, default_k=50)

    # 2 candidates available, K=50 requested
    ranked = ranker.rank_candidates(s1, ['T-2', 'T-1'], k=50)
    assert len(ranked) == 2
    assert ranked == ['T-1', 'T-2']  # T-1 has higher exact match score


# 9. Zero Candidates Tests
def test_zero_candidates():
    s1 = {'core': 'singleton', 'tokens': ('singleton',), 'digits': (), 'loc_tokens': ()}
    ranker = CandidateRanker(target_features={}, default_k=50)

    # Empty candidate input
    ranked = ranker.rank_candidates(s1, [], k=50)
    assert ranked == []

    # k=0 returns empty list
    ranked_zero_k = ranker.rank_candidates(s1, ['T-1', 'T-2'], k=0)
    assert ranked_zero_k == []


# 10. Multiple True Matches Surviving Ranking Tests
def test_multiple_true_matches_surviving():
    s1 = {
        'core': 'metro pharmacy',
        'tokens': ('metro', 'pharmacy'),
        'digits': ('101',),
        'loc_tokens': ('springfield',),
    }

    # 3 true matches (all highly similar) + 10 distractors with lower scores
    target_store = {
        # True match 1: exact name, shared digit, shared loc
        'TRUE-1': {'core': 'metro pharmacy', 'tokens': ('metro', 'pharmacy'), 'digits': ('101',), 'loc_tokens': ('springfield',)},
        # True match 2: exact name, shared digit
        'TRUE-2': {'core': 'metro pharmacy', 'tokens': ('metro', 'pharmacy'), 'digits': ('101',), 'loc_tokens': ('downtown',)},
        # True match 3: high token jaccard + shared digit
        'TRUE-3': {'core': 'metro pharmacy inc', 'tokens': ('metro', 'pharmacy', 'inc'), 'digits': ('101',), 'loc_tokens': ('springfield',)},
    }

    # 10 distractor candidates with low or zero similarity
    all_cands = ['TRUE-1', 'TRUE-2', 'TRUE-3']
    for i in range(10):
        dist_id = f'DIST-{i:02d}'
        target_store[dist_id] = {'core': f'distractor {i}', 'tokens': (f'dist{i}',), 'digits': ('999',), 'loc_tokens': ('boston',)}
        all_cands.append(dist_id)

    ranker = CandidateRanker(target_features=target_store, default_k=5)
    top_5 = ranker.rank_candidates(s1, all_cands, k=5)

    # All 3 true matches must be in the top-5
    assert 'TRUE-1' in top_5
    assert 'TRUE-2' in top_5
    assert 'TRUE-3' in top_5
    # The top 3 slots must be the 3 true matches
    assert set(top_5[:3]) == {'TRUE-1', 'TRUE-2', 'TRUE-3'}


# 11. Champion V2 Blocker Invariance Test
def test_champion_v2_unmodified_by_ranker():
    """Verify that Champion v2 candidate generation is completely unchanged by the ranker."""
    blocker = ChampionV2Blocker()
    targets = {
        'T-1': ('Acme Corp', '123 Main St', 'US'),
        'T-2': ('Acme LLC', '123 Main St', 'US'),
        'T-3': ('Beta Inc', '456 Oak Rd', 'US'),
    }
    blocker.build_index(targets)

    s1_feat = blocker.extract_features('S1-1', 'Acme', '123 Main St', 'US')
    
    # Raw blocker output before ranker
    raw_before = blocker.query_single(s1_feat)
    raw_copy = set(raw_before)

    # Build target store and rank
    target_store = {
        tid: blocker.extract_features(tid, bname, baddr, country)
        for tid, (bname, baddr, country) in targets.items()
    }
    ranker = CandidateRanker(target_features=target_store, default_k=2)
    ranked = ranker.rank_candidates(s1_feat, raw_before, k=2)

    # Raw blocker output after ranker
    raw_after = blocker.query_single(s1_feat)

    # Invariants:
    assert raw_before == raw_copy, "Raw candidate set modified during ranking!"
    assert raw_after == raw_copy, "Raw candidate set altered by ranker invocation!"
    assert len(ranked) == 2
    assert set(ranked).issubset(raw_copy), "Ranked candidates contain elements not generated by blocker!"
