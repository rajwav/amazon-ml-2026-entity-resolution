# Champion Architecture Version 2 Technical Specification (`CHAMPION_V2_SPEC`)

| Attribute | Specification |
|:---|:---|
| **Document Version** | 1.0 (Frozen Production Specification) |
| **Target Implementation** | Production Candidate Generator |
| **Reference Implementation** | [`experiments/blocking/final_tail_investigation.py`](../../../experiments/blocking/final_tail_investigation.py) |
| **Status** | **OFFICIAL PRODUCTION BLUEPRINT** |

---

## 1. System Architecture Overview

Champion v2 Surgical is an in-memory, partitioned multi-index candidate generator operating in three sequential tiers and seven surgical tail channels.

```
                      Query Record (S1)
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [Country Partition]               [Selective Transliteration]
      (US vs India)                     (Names ON, Loc OFF)
            │                                 │
            ├─────────────────────────────────┤
            ▼                                 ▼
    [Tier 1: Fast Sieve]              [Tier 2: Core Backbone]
    • Exact Name                      • Exact Core Name
    • 5 Composite Keys                • Significant Tokens (≥3 char)
      - (tok, loc)                    • Prefix-4
      - (tok, dig)                    • Address Digits
      - (pref, loc)                           │
      - (pref, dig)                           ▼
      - (dig, loc)                    [Tier 3: Dynamic Location]
            │                         • Top-2 Rarest Loc Tokens
            └────────────────┬────────────────┘
                             │
                             ▼
               [Tier 4: Surgical Tail Channels]
               • T1: 2-Char Tokens (freq ≤ 200)
               • T2: Domain / Handle Nospace Stem
               • T3: Consonant Collapse
               • T4: Composite Enriched Digits + Loc
               • S2: Consonant Trigram (freq ≤ 50)
               • S4: US State + Digit (freq ≤ 50)
               • S5: Alphanumeric Unit (freq ≤ 100)
                             │
                             ▼
                [Candidate Union & Deduplication]
            Candidates(S1) = ⋃ (All Active Channel Matches)
```

---

## 2. Preprocessing & Normalization Specifications

### 2.1 Country Partitioning
- Invariant: Candidate generation is strictly executed within country partitions:
  $$\forall (q, t), \quad \text{country}(q) == \text{country}(t)$$

### 2.2 Text Normalization (`normalize_name`, `clean_address`)
1. **Case Normalization**: Convert all characters to lowercase.
2. **Punctuation Stripping**: Replace all non-alphanumeric characters with spaces, except when extracting composite tokens.
3. **Legal Entity Designation Stripping**: Strip common legal entity stopwords:
   `{'llc', 'inc', 'corp', 'corporation', 'co', 'ltd', 'limited', 'pvt', 'private', 'llp', 'enterprises', 'company', 'associates', 'group', 'holdings'}`
4. **Whitespace Normalization**: Strip leading/trailing spaces and collapse internal consecutive whitespace to a single space.

### 2.3 Selective Transliteration Protocol
- **Library**: `indic-transliteration` (`sansscript.transliterate`).
- **Target Alphabets**: Devanagari, Bengali, Gujarati, Kannada, Tamil, Telugu, Malayalam, Gurmukhi, Oriya.
- **Output Scheme**: `sansscript.ITRANS` / `sansscript.ISO`.
- **Policy Invariant**:
  - `name`: Transliteration **ENABLED**.
  - `address_digits`: Transliteration **ENABLED** (converts Indic numerals `०-९` $\to$ `0-9`).
  - `location_tokens`: Transliteration **DISABLED** (prevents phonetic hash bloat).

---

## 3. Inverted Index Schema & Channel Definitions

Let $C \in \{\text{'US'}, \text{'IN'}\}$ denote country. The following hash indexes are constructed across the target corpus:

### Level 1: Composite Keys (`C2_Union_All`)
1. `idx_exact_name[C, norm_name] -> List[TargetID]`
2. `idx_tok_loc[C, (tok, loc)] -> List[TargetID]` (for each name token $\ge 3$ chars, for each location token)
3. `idx_tok_dig[C, (tok, dig)] -> List[TargetID]` (for each name token $\ge 3$ chars, for each street digit string)
4. `idx_pref_loc[C, (pref_4, loc)] -> List[TargetID]`
5. `idx_pref_dig[C, (pref_4, dig)] -> List[TargetID]`
6. `idx_dig_loc[C, (dig, loc)] -> List[TargetID]`

### Level 2: Core Backbone ($B+C+D+E$)
7. `idx_core_name[C, core_name] -> List[TargetID]`
8. `idx_sig_tokens[C, token] -> List[TargetID]` (filtered if corpus frequency $>5\%$)
9. `idx_prefix_4[C, prefix_4] -> List[TargetID]`
10. `idx_address_digits[C, digit_string] -> List[TargetID]`

### Level 3: Dynamic Channel F (Top-2 Location)
11. `idx_top2_loc[C, loc_token] -> List[TargetID]`
    - **Target-Side Rule**: For each target record, extract all location tokens. Sort ascending by target corpus document frequency. Index **strictly the 2 rarest tokens**.
    - **Query-Side Rule**: For each query $S1$, look up **all** location tokens in `idx_top2_loc`.

### Surgical Tail Channels (T1 - T4, S2, S4, S5)
12. **Channel T1 (2-Char Tokens)**:
    - Key: `(C, token_2char)`
    - Constraint: Index only if corpus frequency $\le 200$.
13. **Channel T2 (Domain & Social Handles)**:
    - Key: `(C, nospace_stem)`
    - Rule: Strip protocols and extensions (`http`, `www`, `.com`, `.org`, `@`), concatenate remaining tokens without spaces.
14. **Channel T3 (Consonant Collapse)**:
    - Key: `(C, core_collapsed)`
    - Rule: Replace consecutive duplicate consonants with single character (`re.sub(r'([b-df-hj-np-tv-z])\1+', r'\1', name)`).
15. **Channel T4 (Composite Enriched Digits + Loc)**:
    - Key: `(C, (enriched_digit, rarest_loc))`
16. **Signal S2 (Consonant Trigram Prefix)**:
    - Key: `(C, cons_tri)`
    - Rule: Extract first 3 consonants of normalized name. Constraint: Frequency $\le 50$.
17. **Signal S4 (US State + Street Digit)**:
    - Key: `(C, (state_code, street_digit))`
    - Constraint: Country == 'US'. Constraint: Frequency $\le 50$.
18. **Signal S5 (Alphanumeric Address Unit)**:
    - Key: `(C, unit_string)`
    - Rule: Extract unit patterns (e.g., `re.findall(r'\b(?:unit|ste|apt|suite|no|#)?\s*([0-9]+[a-z]|[a-z][0-9]+)\b', address)`). Constraint: Frequency $\le 100$.

---

## 4. Query Retrieval Algorithm (Pseudocode)

```python
def generate_candidates_for_query(s1_record, indexes, doc_freqs):
    country = s1_record.country
    candidates = set()
    
    # 1. Level 1: Exact & Composites
    candidates.update(indexes.exact_name[country].get(s1_record.norm_name, []))
    for tok in s1_record.sig_tokens:
        for loc in s1_record.loc_tokens:
            candidates.update(indexes.tok_loc[country].get((tok, loc), []))
        for dig in s1_record.address_digits:
            candidates.update(indexes.tok_dig[country].get((tok, dig), []))
            
    for loc in s1_record.loc_tokens:
        candidates.update(indexes.pref_loc[country].get((s1_record.pref_4, loc), []))
    for dig in s1_record.address_digits:
        candidates.update(indexes.pref_dig[country].get((s1_record.pref_4, dig), []))
        for loc in s1_record.loc_tokens:
            candidates.update(indexes.dig_loc[country].get((dig, loc), []))
            
    # 2. Level 2: Core Backbone
    candidates.update(indexes.core_name[country].get(s1_record.core_name, []))
    for tok in s1_record.sig_tokens:
        if doc_freqs.token[country].get(tok, 0) <= doc_freqs.token_5pct_cap[country]:
            candidates.update(indexes.sig_tokens[country].get(tok, []))
    candidates.update(indexes.prefix_4[country].get(s1_record.pref_4, []))
    for dig in s1_record.address_digits:
        candidates.update(indexes.address_digits[country].get(dig, []))
        
    # 3. Level 3: Dynamic Channel F (Query looks up all its location tokens)
    for loc in s1_record.loc_tokens:
        candidates.update(indexes.top2_loc[country].get(loc, []))
        
    # 4. Surgical Tail Channels
    for t2 in s1_record.tokens_2char:
        if doc_freqs.t2[country].get(t2, 0) <= 200:
            candidates.update(indexes.t1_2char[country].get(t2, []))
            
    if s1_record.domain_stem:
        candidates.update(indexes.t2_domain[country].get(s1_record.domain_stem, []))
        
    candidates.update(indexes.t3_collapsed[country].get(s1_record.core_collapsed, []))
    
    if s1_record.rarest_loc:
        for edig in s1_record.enriched_digits:
            candidates.update(indexes.t4_dig_loc[country].get((edig, s1_record.rarest_loc), []))
            
    # 5. Final Micro-Signals
    if s1_record.cons_tri and doc_freqs.cons_tri[country].get(s1_record.cons_tri, 0) <= 50:
        candidates.update(indexes.s2_cons_tri[country].get(s1_record.cons_tri, []))
        
    if country == 'US' and s1_record.us_state:
        for dig in s1_record.address_digits:
            if doc_freqs.state_dig.get((s1_record.us_state, dig), 0) <= 50:
                candidates.update(indexes.s4_state_dig.get((s1_record.us_state, dig), []))
                
    for unit in s1_record.address_units:
        if doc_freqs.unit[country].get(unit, 0) <= 100:
            candidates.update(indexes.s5_unit[country].get(unit, []))
            
    return candidates
```
