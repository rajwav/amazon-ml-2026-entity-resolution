# Root Cause Analysis: Candidate Generation Failure Taxonomy

This document formalizes the eight fundamental failure modes identified during the candidate generation phase, documenting their underlying technical mechanisms, empirical impact, resolution status, and architectural mitigations.

---

## 1. Summary Taxonomy of Failure Modes

| # | Failure Mode | Underlying Mechanism | Empirical Impact | Resolution / Mitigation | Status in Champion v2 |
|:---|:---|:---|:---|:---|:---|
| **FM-1** | **Indic Script Discrepancy** | Devanagari/Bengali/Gujarati vs Latin ISO | 146 missed true pairs in India corpus | Preprocessing transliteration on name fields | **RESOLVED (100% recovered)** |
| **FM-2** | **Multi-Match Query Gating Blindspot** | 1-to-many cardinality masked by query-level candidate counts | Capped recall at 98.49% (520+ missed pairs) | Ban $S1$-level gating; enforce target-side filtering | **RESOLVED (Architecture Redesigned)** |
| **FM-3** | **Missing / Null Target Addresses** | Target record has empty string or whitespace address | Neutralizes digits, prefixes, and location keys | Channels B, C, T1 (2-char), and T2 (domain) | **MITIGATED (Residual is irreducible)** |
| **FM-4** | **Extreme Short Business Acronyms** | 2-character names ("OM", "TB", "JB") stripped by stopword tokenizers | Missed 12 pairs in baseline control | Channel T1 (`tokens_2char` with freq $\le 200$) | **RESOLVED (12 pairs recovered)** |
| **FM-5** | **Domain & Social Handle Concatenation** | Entity formatted as URL/handle (`empirecastillo.com`, `@HANDLE`) | Exact and token match fail due to TLD and no spaces | Channel T2 (TLD strip + nospace normalized index) | **RESOLVED (Recovered)** |
| **FM-6** | **Double-Consonant & Phonetic Drift** | Typing variance, doubled consonants ("wllrow" $\leftrightarrow$ "willow") | Missed across standard exact/token channels | Channel T3 (`core_collapsed`) + S2 (`cons_tri`) | **RESOLVED (Recovered)** |
| **FM-7** | **Metropolitan Location Hub Bloat** | Dense cities ("Mumbai", "New York") cause explosive posting list sizes | Saturated candidate volume (3,295 cands/S1) | Policy 8B: Top-2 rarest location tokens per record | **RESOLVED (-67.7% candidate load)** |
| **FM-8** | **Total Alias Substitution & Label Noise** | Entity operates under completely distinct trading name / brand | Only reachable via broad cartesian joins | Micro-signals S4/S5; Top-4 location rejected | **BOUNDED RESIDUE (5 pairs frozen)** |

---

## 2. Deep Dive: The 8 Failure Modes

### FM-1: Indic Script Discrepancy
- **Mechanism**: Target databases in India frequently record business names in indigenous scripts (Devanagari, Gujarati, Bengali, Kannada, Tamil) whereas official query records ($S1$) are standard Romanized English (e.g., `"Al Estate Private Limited"` vs `"अल एस्टेट प्राइवेट लिमिटेड"`).
- **Ablation Finding**: In Experiment 04, transliterating name fields unlocked **146 true pairs** at a candidate cost of only **+4.9 candidates/S1**.
- **Crucial Invariant**: Applying transliteration to general location fields caused a **+4.33 million candidate explosion** due to phonetic collisions. Transliteration must remain **strictly selective** (Names: ON, Location: OFF).

### FM-2: Multi-Match Query Gating Blindspot
- **Mechanism**: Many entity resolution pipelines use adaptive querying: if a query generates enough candidates ($k \ge 10$), expensive fallback passes are skipped.
- **Empirical Trap**: Entity resolution is a 1-to-many problem (up to 17 targets per query). In Experiment 05, **92.4% of tail pairs belonged to queries that had already found at least one target**.
- **Outcome**: The gating condition mistakenly assumed the query was complete, permanently discarding secondary, highly-corrupted target records.
- **Mitigation**: Permanently ban query-level gating. Target-side frequency filtering is evaluated universally across all queries.

### FM-3: Missing / Null Target Addresses
- **Mechanism**: In secondary corporate registries, target addresses are often truncated, missing, or stored as empty strings `""`.
- **Impact**: Any conjunction requiring address digits or location tokens (Channels D, E, F, and Composites) fails immediately.
- **Mitigation**: For target records with null addresses, the pipeline relies on pure name tokens (Channel C), 2-character tokens (Channel T1), and domain stems (Channel T2).

### FM-4: Extreme Short Business Acronyms
- **Mechanism**: Standard NLP tokenizers often discard 1- and 2-character tokens as noise or punctuation.
- **Impact**: True Indian and US businesses named "OM", "BK", "TB", or "JB" were completely dropped from inverted indexes.
- **Mitigation**: Channel T1 extracts all 2-character alphanumeric tokens but restricts indexing to those with corpus frequency $\le 200$ to prevent indexing two-letter noise words (e.g., "in", "at", "to").

### FM-5: Domain & Social Handle Concatenation
- **Mechanism**: Modern digital entities frequently list their web URL (e.g., `empirecastillo.com`) or social handle (`@SIBYLSBAKERY`) directly as the registered business name.
- **Impact**: Tokenization yields `"empirecastillo"` and `"com"`, failing to match `"Castillo Empire Bny"`.
- **Mitigation**: Channel T2 strips common protocols and extensions (`http`, `www`, `.com`, `.org`, `@`), sorts constituent tokens, and indexes the concatenated alphanumeric stem.

### FM-6: Double-Consonant & Phonetic Drift
- **Mechanism**: Data entry errors and OCR transcription issues frequently double consonants (e.g., `"K+ Willow LLC"` vs `"K+ Wllrow LLC"`).
- **Mitigation**:
  1. Channel T3 (`core_collapsed`): Replaces all consecutive identical consonants with a single character (`"wllrow"` $\to$ `"wlrow"`).
  2. Micro-Signal S2 (`cons_tri`): Extracts the first three consonants of the normalized string as an invariant anchor.

### FM-7: Metropolitan Location Hub Bloat
- **Mechanism**: When using raw location tokens (Channel F), mega-cities like "New York", "Los Angeles", "Mumbai", or "Delhi" create posting lists spanning tens of thousands of records, bloating candidate pools to $>3,200$ candidates/query.
- **Mitigation**: Rather than dropping these tokens globally (which destroys matches), **Policy 8B_Top2** indexes only the **top-2 rarest location tokens per target record**. Entities in Mumbai index by locality or pincode, eliminating the city hub bloat.

### FM-8: Total Alias Substitution & Label Noise
- **Mechanism**: The true entity pair consists of completely different strings (e.g., `"Straight Edge Barbershop"` $\leftrightarrow$ `"Deltazeta"`, or `"Metro Logistics Group"` $\leftrightarrow$ `"Pinnacle Transport"`).
- **Analysis**: These records represent legal corporate rebrands, parent-subsidiary mappings, or label noise. They share zero name tokens.
- **Decision**: Recovering these records requires either full cartesian product or 4th-order location retrieval, which costs 1.88 million candidate comparisons per match. This trade-off is economically non-viable. The remaining 5 pairs are accepted as irreducible candidate generation residue.
