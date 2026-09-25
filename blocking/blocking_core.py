"""
Champion v2 Surgical: Production Core Blocking & Candidate Generation Engine.
Implements the frozen 3-tier hierarchical multi-channel blocking architecture.
Features sub-second querying, deterministic candidate generation, and index serialization.
"""

import os
import re
import sys
import time
import pickle
import collections
from typing import Dict, Set, Tuple, List, Optional, Iterator

from blocking.normalization import (
    normalize_business_name,
    normalize_business_address,
    clean_domain_or_handle,
    collapse_double_consonants,
    extract_clean_digits,
    extract_2char_tokens,
    extract_consonant_trigram,
    extract_alphanumeric_units,
    extract_state_code,
    extract_short_street_tokens
)

class ChampionV2Blocker:
    """
    Frozen Champion v2 Surgical Candidate Generator.
    Maintains 100% fidelity to the verified 10k benchmark.
    """
    def __init__(self):
        # Target Inverted Indexes partitioned by country string
        self.idx_exact = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_tok_loc = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_tok_dig = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_pref_loc = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_pref_dig = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_dig_loc = collections.defaultdict(lambda: collections.defaultdict(list))
        
        self.idx_B = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_C = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_D = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_E = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_F_top2 = collections.defaultdict(lambda: collections.defaultdict(list))
        
        self.idx_2char = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_nospace = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_collapsed = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_dig_loc_en = collections.defaultdict(lambda: collections.defaultdict(list))
        
        self.idx_cons_tri = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_state_dig = collections.defaultdict(lambda: collections.defaultdict(list))
        self.idx_unit = collections.defaultdict(lambda: collections.defaultdict(list))

        # Target Frequency Tables
        self.freq_loc_token = collections.defaultdict(collections.Counter)
        self.freq_2char_token = collections.defaultdict(collections.Counter)
        self.freq_cons_tri = collections.defaultdict(collections.Counter)
        self.freq_state_dig = collections.defaultdict(collections.Counter)
        self.freq_unit = collections.defaultdict(collections.Counter)
        
        self.is_indexed = False
        self.target_count = 0

    @staticmethod
    def extract_features(entity_id: str, name: str, addr: str, country: str) -> dict:
        """Extract and normalize all entity features for indexing and querying."""
        core, legal, sig_tokens, _ = normalize_business_name(name, enable_transliteration=True)
        _, digits, _ = normalize_business_address(addr, enable_transliteration=True)
        _, _, loc_tokens = normalize_business_address(addr, enable_transliteration=False)
        prefix4 = core[:4] if len(core) >= 4 else core
        dig_en = extract_clean_digits(addr)
        t2 = extract_2char_tokens(name)
        c_tri = extract_consonant_trigram(name)
        st = extract_state_code(addr, country)
        units = extract_alphanumeric_units(addr)

        return {
            'id': entity_id,
            'country': country,
            'core': core,
            'tokens': tuple(sig_tokens),
            'prefix4': prefix4,
            'digits': tuple(digits),
            'loc_tokens': tuple(loc_tokens),
            'digits_enriched': tuple(dig_en),
            'tokens_2char': tuple(t2),
            'domain_stem': clean_domain_or_handle(name),
            'nospace_core': re.sub(r'[^a-z0-9]', '', core),
            'core_collapsed': collapse_double_consonants(core),
            'consonant_tri': c_tri,
            'state': st,
            'units': tuple(units)
        }

    def build_index(self, target_records: Dict[str, Tuple[str, str, str]]):
        """
        Build all Champion v2 inverted indexes across target records.
        target_records: {entity_id: (business_name, business_address, country)}
        """
        t0 = time.time()
        self.target_count = len(target_records)
        target_norm = {}

        # Pass 1: Extract features and compute corpus frequencies
        for eid, (bname, baddr, country) in target_records.items():
            feat = self.extract_features(eid, bname, baddr, country)
            target_norm[eid] = feat
            c = country
            for loc in feat['loc_tokens']:
                self.freq_loc_token[c][loc] += 1
            for t in feat['tokens_2char']:
                self.freq_2char_token[c][t] += 1
            if feat['consonant_tri']:
                self.freq_cons_tri[c][feat['consonant_tri']] += 1
            if feat['state'] and feat['digits_enriched']:
                for d in feat['digits_enriched']:
                    self.freq_state_dig[c][(feat['state'], d)] += 1
            for u in feat['units']:
                self.freq_unit[c][u] += 1

        # Pass 2: Populate inverted indexes with exact frequency guardrails
        for eid, feat in target_norm.items():
            c = feat['country']
            if feat['core']:
                self.idx_exact[c][feat['core']].append(eid)
                self.idx_B[c][feat['core']].append(eid)
                
            for tok in feat['tokens']:
                self.idx_C[c][tok].append(eid)
                for loc in feat['loc_tokens']:
                    self.idx_tok_loc[c][(tok, loc)].append(eid)
                for dig in feat['digits']:
                    self.idx_tok_dig[c][(tok, dig)].append(eid)
                    
            if feat['prefix4']:
                self.idx_D[c][feat['prefix4']].append(eid)
                for loc in feat['loc_tokens']:
                    self.idx_pref_loc[c][(feat['prefix4'], loc)].append(eid)
                for dig in feat['digits']:
                    self.idx_pref_dig[c][(feat['prefix4'], dig)].append(eid)
                    
            for dig in feat['digits']:
                self.idx_E[c][dig].append(eid)
                for loc in feat['loc_tokens']:
                    self.idx_dig_loc[c][(dig, loc)].append(eid)

            # Level 3: Dynamic Top-2 Location Tokens
            locs = feat['loc_tokens']
            if locs:
                lsorted = sorted(locs, key=lambda l: (self.freq_loc_token[c][l], len(l)))
                for loc in lsorted[:2]:
                    self.idx_F_top2[c][loc].append(eid)

            # Surgical Tail Channels
            for t2 in feat['tokens_2char']:
                if self.freq_2char_token[c][t2] <= 200:
                    self.idx_2char[c][t2].append(eid)
            if len(feat['nospace_core']) >= 4:
                self.idx_nospace[c][feat['nospace_core']].append(eid)
            if len(feat['domain_stem']) >= 4:
                self.idx_nospace[c][feat['domain_stem']].append(eid)
            if len(feat['core_collapsed']) >= 4:
                self.idx_collapsed[c][feat['core_collapsed']].append(eid)
            for ed in feat['digits_enriched']:
                for loc in feat['loc_tokens']:
                    self.idx_dig_loc_en[c][(ed, loc)].append(eid)

            # Micro-signals
            if feat['consonant_tri'] and self.freq_cons_tri[c][feat['consonant_tri']] <= 50:
                self.idx_cons_tri[c][feat['consonant_tri']].append(eid)
            if feat['state']:
                for d in feat['digits_enriched']:
                    if self.freq_state_dig[c][(feat['state'], d)] <= 50:
                        self.idx_state_dig[c][(feat['state'], d)].append(eid)
            for u in feat['units']:
                if self.freq_unit[c][u] <= 100:
                    self.idx_unit[c][u].append(eid)

        self.is_indexed = True
        return time.time() - t0

    def query_single(self, s1_feat: dict) -> Set[str]:
        """
        Generate candidates for a single pre-extracted S1 feature dictionary.
        Returns a deduplicated set of target entity IDs.
        """
        c = s1_feat['country']
        cands = set()

        # 1. Base L1 Composites
        if s1_feat['core'] and s1_feat['core'] in self.idx_exact[c]:
            cands.update(self.idx_exact[c][s1_feat['core']])
        for tok in s1_feat['tokens']:
            for loc in s1_feat['loc_tokens']:
                if (tok, loc) in self.idx_tok_loc[c]:
                    cands.update(self.idx_tok_loc[c][(tok, loc)])
            for dig in s1_feat['digits']:
                if (tok, dig) in self.idx_tok_dig[c]:
                    cands.update(self.idx_tok_dig[c][(tok, dig)])
        if s1_feat['prefix4']:
            for loc in s1_feat['loc_tokens']:
                if (s1_feat['prefix4'], loc) in self.idx_pref_loc[c]:
                    cands.update(self.idx_pref_loc[c][(s1_feat['prefix4'], loc)])
            for dig in s1_feat['digits']:
                if (s1_feat['prefix4'], dig) in self.idx_pref_dig[c]:
                    cands.update(self.idx_pref_dig[c][(s1_feat['prefix4'], dig)])
        for dig in s1_feat['digits']:
            if dig in self.idx_E[c]:
                cands.update(self.idx_E[c][dig])
            for loc in s1_feat['loc_tokens']:
                if (dig, loc) in self.idx_dig_loc[c]:
                    cands.update(self.idx_dig_loc[c][(dig, loc)])

        # 2. Base L2 Core Backbone (B, C, D)
        if s1_feat['core'] and s1_feat['core'] in self.idx_B[c]:
            cands.update(self.idx_B[c][s1_feat['core']])
        for tok in s1_feat['tokens']:
            if tok in self.idx_C[c]:
                cands.update(self.idx_C[c][tok])
        if s1_feat['prefix4'] and s1_feat['prefix4'] in self.idx_D[c]:
            cands.update(self.idx_D[c][s1_feat['prefix4']])

        # 3. Base L3 Dynamic Channel F (Top-2)
        for loc in s1_feat['loc_tokens']:
            if loc in self.idx_F_top2[c]:
                cands.update(self.idx_F_top2[c][loc])

        # 4. Tail Channels
        for t2 in s1_feat['tokens_2char']:
            if t2 in self.idx_2char[c]:
                cands.update(self.idx_2char[c][t2])
        if s1_feat['nospace_core'] and s1_feat['nospace_core'] in self.idx_nospace[c]:
            cands.update(self.idx_nospace[c][s1_feat['nospace_core']])
        if s1_feat['domain_stem'] and s1_feat['domain_stem'] in self.idx_nospace[c]:
            cands.update(self.idx_nospace[c][s1_feat['domain_stem']])
        if s1_feat['core_collapsed'] and s1_feat['core_collapsed'] in self.idx_collapsed[c]:
            cands.update(self.idx_collapsed[c][s1_feat['core_collapsed']])
        for ed in s1_feat['digits_enriched']:
            for loc in s1_feat['loc_tokens']:
                if (ed, loc) in self.idx_dig_loc_en[c]:
                    cands.update(self.idx_dig_loc_en[c][(ed, loc)])

        # 5. Micro-Signals (Champion v2 Surgical)
        if s1_feat['consonant_tri'] and s1_feat['consonant_tri'] in self.idx_cons_tri[c]:
            cands.update(self.idx_cons_tri[c][s1_feat['consonant_tri']])

        if s1_feat['state']:
            for d in s1_feat['digits_enriched']:
                if (s1_feat['state'], d) in self.idx_state_dig[c]:
                    cands.update(self.idx_state_dig[c][(s1_feat['state'], d)])

        for u in s1_feat['units']:
            if u in self.idx_unit[c]:
                cands.update(self.idx_unit[c][u])

        return cands

    def save_index(self, path: str):
        """Serialize the complete index to disk using pickle."""
        data = {
            'target_count': self.target_count,
            'idx_exact': dict(self.idx_exact),
            'idx_tok_loc': dict(self.idx_tok_loc),
            'idx_tok_dig': dict(self.idx_tok_dig),
            'idx_pref_loc': dict(self.idx_pref_loc),
            'idx_pref_dig': dict(self.idx_pref_dig),
            'idx_dig_loc': dict(self.idx_dig_loc),
            'idx_B': dict(self.idx_B),
            'idx_C': dict(self.idx_C),
            'idx_D': dict(self.idx_D),
            'idx_E': dict(self.idx_E),
            'idx_F_top2': dict(self.idx_F_top2),
            'idx_2char': dict(self.idx_2char),
            'idx_nospace': dict(self.idx_nospace),
            'idx_collapsed': dict(self.idx_collapsed),
            'idx_dig_loc_en': dict(self.idx_dig_loc_en),
            'idx_cons_tri': dict(self.idx_cons_tri),
            'idx_state_dig': dict(self.idx_state_dig),
            'idx_unit': dict(self.idx_unit),
            'freq_loc_token': dict(self.freq_loc_token),
            'freq_2char_token': dict(self.freq_2char_token),
            'freq_cons_tri': dict(self.freq_cons_tri),
            'freq_state_dig': dict(self.freq_state_dig),
            'freq_unit': dict(self.freq_unit),
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    def load_index(self, path: str):
        """Load pre-serialized index from disk."""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        self.target_count = data['target_count']
        for k in ['idx_exact', 'idx_tok_loc', 'idx_tok_dig', 'idx_pref_loc', 'idx_pref_dig',
                  'idx_dig_loc', 'idx_B', 'idx_C', 'idx_D', 'idx_E', 'idx_F_top2',
                  'idx_2char', 'idx_nospace', 'idx_collapsed', 'idx_dig_loc_en',
                  'idx_cons_tri', 'idx_state_dig', 'idx_unit']:
            setattr(self, k, data[k])
        for k in ['freq_loc_token', 'freq_2char_token', 'freq_cons_tri', 'freq_state_dig', 'freq_unit']:
            setattr(self, k, data[k])
        self.is_indexed = True
