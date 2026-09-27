"""
Feature extraction module for LightGBM Entity Resolution model.
Amazon ML Challenge 2026.
"""

import re

CLEAN_RE = re.compile(r'[^a-z0-9]')
TOKEN_RE = re.compile(r'[a-z0-9]+')
DIGIT_RE = re.compile(r'\d+')

LEGAL_STOPWORDS = {
    'inc', 'incorporated', 'corp', 'corporation', 'llc', 'ltd', 'limited', 'pvt',
    'private', 'co', 'company', 'services', 'enterprises', 'solutions', 'and', 'the',
    'of', 'in', 'group', 'holdings', 'technologies', 'industries', 'associates',
    'sarl', 'sas', 'sci', 'eurl', 'sa', 'llp', 'center', 'centre'
}

def clean_name(s: str) -> str:
    return CLEAN_RE.sub('', s.lower())

def get_tokens(s: str) -> list:
    return [w for w in TOKEN_RE.findall(s.lower()) if len(w) >= 5 and not w.isdigit() and w not in LEGAL_STOPWORDS]

def get_addr_tokens(s: str) -> list:
    return [w for w in TOKEN_RE.findall(s.lower()) if len(w) >= 4 and not w.isdigit()]

def get_digits(s: str) -> tuple:
    return tuple(DIGIT_RE.findall(s))

def get_char_bigrams(s: str) -> set:
    if len(s) < 2:
        return set()
    return {s[i:i+2] for i in range(len(s)-1)}

def extract_features_v2_fast(s1_name, s1_toks, s1_digs, s1_atoks, s1_bg,
                             t_name, t_toks, t_digs, t_atoks, t_bg) -> list:
    """Extract 11 lightweight pairwise signals."""
    exact_match = 1.0 if s1_name and s1_name == t_name else 0.0

    s1_tok_set = set(s1_toks)
    t_tok_set = set(t_toks)
    tok_inter = len(s1_tok_set & t_tok_set)
    tok_union = len(s1_tok_set | t_tok_set)
    tok_jaccard = tok_inter / tok_union if tok_union > 0 else 0.0

    s1_dig_set = set(s1_digs)
    t_dig_set = set(t_digs)
    has_shared_dig = 1.0 if (s1_dig_set & t_dig_set) else 0.0
    exact_dig = 1.0 if (s1_dig_set and s1_dig_set == t_dig_set) else 0.0
    dig_union = len(s1_dig_set | t_dig_set)
    dig_jaccard = len(s1_dig_set & t_dig_set) / dig_union if dig_union > 0 else 0.0

    pref4_match = 1.0 if (len(s1_name) >= 4 and len(t_name) >= 4 and s1_name[:4] == t_name[:4]) else 0.0
    len_diff = float(abs(len(s1_name) - len(t_name)))
    max_len = max(len(s1_name), len(t_name))
    len_ratio = min(len(s1_name), len(t_name)) / max_len if max_len > 0 else 0.0

    s1_atok_set = set(s1_atoks)
    t_atok_set = set(t_atoks)
    atok_inter = len(s1_atok_set & t_atok_set)
    atok_union = len(s1_atok_set | t_atok_set)
    addr_tok_jaccard = atok_inter / atok_union if atok_union > 0 else 0.0

    first_dig_match = 1.0 if (s1_digs and t_digs and s1_digs[0] == t_digs[0]) else 0.0

    bg_inter = len(s1_bg & t_bg)
    bg_total = len(s1_bg) + len(t_bg)
    char_dice = (2.0 * bg_inter) / bg_total if bg_total > 0 else 0.0

    return [
        exact_match,
        tok_jaccard,
        has_shared_dig,
        exact_dig,
        dig_jaccard,
        pref4_match,
        len_diff,
        len_ratio,
        addr_tok_jaccard,
        first_dig_match,
        char_dice
    ]
