# Catalog of Accepted Candidate Generation Channels (Champion v2)

This catalog specifies all 10 active candidate generation channels comprising the frozen **Champion v2 Surgical** blocking architecture.

---

## 1. Summary Channel Architecture

| Channel ID | Tier / Level | Signal Type | Index Key Definition | Normalization / Preprocessing | Frequency Cap / Constraint | Marginal Efficiency |
|:---|:---|:---|:---|:---|:---|:---|
| **L1_Exact** | Level 1 | Exact Name | `(country, norm_name)` | Transliterated, lowercase, stripped punctuation | None (unique name) | Ultra-high |
| **L1_Composites**| Level 1 | 5 Composite Keys | `(country, k1, k2)` | Conjunctions: `tok&loc`, `tok&dig`, `pref&loc`, `pref&dig`, `dig&loc` | Natural conjunction constraint | 113.8 cands/S1 |
| **L2_Tokens** | Level 2 | Name Tokens | `(country, token)` | Alphanumeric tokens $\ge 3$ chars, legal stopwords removed | Drop if corpus freq $>5\%$ | 214 cands/TP |
| **L2_Prefix** | Level 2 | Name Prefix-4 | `(country, prefix_4)` | First 4 alphanumeric characters of normalized name | Natural prefix cap | 120 cands/TP |
| **L2_Digits** | Level 2 | Street Digits | `(country, digit_string)` | Raw numeric sequences extracted from address | Natural street number cap | 1,962 cands/TP |
| **L3_Dynamic_F**| Level 3 | Location Rarity | `(country, loc_token)` | Top-2 rarest location tokens per target record | Dynamic target-side IDF sort | 3,569 cands/TP |
| **T1_ShortTokens**| Tail 1 | 2-Char Acronyms | `(country, token_2char)` | 2-letter tokens extracted from core name | **Strict corpus freq $\le 200$** | 1,166 cands/TP |
| **T2_DomainStem** | Tail 2 | URL & Social Handle | `(country, nospace_stem)` | TLDs stripped (`.com`, `.org`, `@`), concatenated stem | None (sparse web handles) | High |
| **T3_Collapse** | Tail 3 | Consonant Collapse | `(country, core_collapsed)`| Consecutive duplicate consonants reduced to single char | None | High |
| **T4_SurgicalDig**| Tail 4 | Digits + Location | `(country, digit, top_loc)` | Enriched street digits compounded with rarest loc token | Conjunction constraint | 76 cands/S1 |
| **Micro_S2** | Tail 5 | Consonant Trigram | `(country, cons_tri)` | First 3 consonants of normalized name | **Strict corpus freq $\le 50$** | 18,150 cands/TP |
| **Micro_S4** | Tail 6 | State + Street Digit | `(country, state_code, digit)` | US 2-letter state code + street digit | **Strict corpus freq $\le 50$** | 1,878 cands/TP |
| **Micro_S5** | Tail 7 | Alphanumeric Unit | `(country, unit_code)` | Alphanumeric suite/unit (e.g., `3a`, `4b`, `f1118`) | **Strict corpus freq $\le 100$** | 2,976 cands/TP |

---

## 2. In-Depth Channel Specifications

### 1. Level 1: `C2_Union_All` Composite Sieve
- **Function**: Ultra-fast, high-confidence tier that executes in sub-second time.
- **Components**:
  - `(country, norm_name)`: Exact name match.
  - `(country, token, loc_token)`: Conjunction of any name token $\ge 3$ chars and location token.
  - `(country, token, digit)`: Conjunction of name token and street digit.
  - `(country, prefix_4, loc_token)`: Conjunction of first 4 letters of name and location.
  - `(country, prefix_4, digit)`: Conjunction of prefix-4 and street digit.
  - `(country, digit, loc_token)`: Conjunction of street digit and location token.
- **Yield**: Generates a median of **10 candidates per query** while capturing **95.63% of true pairs**.

### 2. Level 2: Core Backbone ($B+C+D+E$)
- **Function**: Standardizes core lexical and numerical matching.
- **Components**:
  - Channel B: Exact core name (legal designations removed).
  - Channel C: Individual significant name tokens ($\ge 3$ characters).
  - Channel D: 4-character name prefixes.
  - Channel E: Address digit sequences.
- **Transliteration Policy**: Indic transliteration is **ENABLED** across all name and digit tokens.
- **Yield**: Escalates cumulative recall to **98.09%** at 836 candidates/query.

### 3. Level 3: Dynamic Top-2 Location Channel F
- **Function**: Captures matches where business names underwent severe semantic or lexical drift, leaving location as the primary bridge.
- **Algorithm**:
  1. For each target record, extract all location tokens (city, district, locality).
  2. Query the corpus-wide document frequency table for each token.
  3. Sort tokens ascending by document frequency.
  4. Index strictly the **2 rarest tokens**.
- **Yield**: Recovers 100% of location tail pairs, adding only +228 candidates/S1 over the backbone.

### 4. Surgical Tail Channels (T1 through T4)
- **T1 (`tokens_2char`)**: Recovers entities with 2-letter business acronyms ("TB", "OM", "BK", "JB"). Hard cap at frequency $\le 200$ prevents stopword contamination.
- **T2 (`domain_nospace`)**: Strips web protocols and domain extensions (`.com`, `.net`, `.in`, `@`), sorting constituent terms to link `"Castillo Empire Bny"` to `empirecastillo.com`.
- **T3 (`core_collapsed`)**: Collapses adjacent identical consonants (`"wllrow"` $\to$ `"wlrow"`), bridging OCR and phonetic duplication.
- **T4 (`enriched_digits + loc`)**: Extracts embedded alphanumeric street numbers and compounds them with the rarest location token to prevent standalone digit fan-out.

### 5. Final Micro-Signals (S2, S4, S5)
- **Signal S2 (`cons_tri`)**: Consonant trigram prefix (e.g., `"klw"` for `"k willow"`). Enforced frequency cap $\le 50$. Recovers 2 true pairs for 18,150 cands/TP.
- **Signal S4 (`state, dig`)**: Conjunction of US state code and address digit string. Enforced frequency cap $\le 50$. Recovers 2 true pairs for only 1,878 cands/TP.
- **Signal S5 (`unit`)**: Alphanumeric unit and apartment markers (`3a`, `4b`, `f1118`). Enforced frequency cap $\le 100$. Recovers 1 true pair for 2,976 cands/TP.
