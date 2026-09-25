"""
Unit tests for matching features, evaluator, and baseline matcher.
"""

from matching.evaluator import compute_query_f05, compute_macro_f05
from matching.features import jaccard_similarity, levenshtein_similarity, extract_pairwise_features
from matching.baseline_matcher import compute_composite_similarity

def test_jaccard_and_levenshtein():
    assert jaccard_similarity({"apple", "banana"}, {"apple", "orange"}) == 1 / 3
    assert levenshtein_similarity("apple", "apple") == 1.0
    assert levenshtein_similarity("kitten", "sitting") > 0.5

def test_singleton_f05():
    # True singleton predicted correctly
    p, r, f = compute_query_f05(set(), set())
    assert p == 1.0 and r == 1.0 and f == 1.0

    # True singleton falsely predicted with a match
    p, r, f = compute_query_f05({"S2-1"}, set())
    assert f == 0.0

    # Non-singleton correctly predicted
    p, r, f = compute_query_f05({"S2-1"}, {"S2-1"})
    assert f == 1.0

def test_pairwise_feature_extraction():
    s1 = {
        'id': 'S1-1',
        'country': 'US',
        'core': 'apex summit',
        'tokens': ('apex', 'summit'),
        'prefix4': 'apex',
        'digits_enriched': ('67',),
        'loc_tokens': ('kentucky',),
        'tokens_2char': (),
        'domain_stem': 'apexsummit',
        'nospace_core': 'apexsummit',
        'core_collapsed': 'apex summit',
        'consonant_tri': 'pxs',
        'state': 'ky',
        'units': ()
    }
    target = {
        'id': 'S2-89663826',
        'country': 'US',
        'core': 'apex summit',
        'tokens': ('apex', 'summit'),
        'prefix4': 'apex',
        'digits_enriched': ('67',),
        'loc_tokens': ('kentucky',),
        'tokens_2char': (),
        'domain_stem': 'apexsummit',
        'nospace_core': 'apexsummit',
        'core_collapsed': 'apex summit',
        'consonant_tri': 'pxs',
        'state': 'ky',
        'units': ()
    }
    feats = extract_pairwise_features(s1, target)
    assert feats['exact_core_match'] == 1.0
    assert feats['exact_digits_match'] == 1.0
    score = compute_composite_similarity(feats)
    assert score > 0.80
