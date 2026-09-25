# Complete Architectural Decision Log (ADR-01 through ADR-13)

This document records the formal sequence of 13 Architectural Decision Records (ADRs) that governed the evolution, optimization, and final freezing of the candidate generation architecture for the Amazon ML Challenge 2026.

---

## ADR-01: Stratified 10,000 $S1$ Pilot as Benchmark Reference
- **Date**: 2026-09-25
- **Status**: **ACTIVE & LOCKED**
- **Context**: The full dataset consists of 2,233,142 $S1$ query entities and 10,309,088 target records. Running iterative candidate generation experiments on the full corpus requires substantial wall-clock time and disk I/O, preventing rapid hypothesis testing.
- **Alternatives Considered**:
  1. Full corpus execution for every experiment (too slow, hours per iteration).
  2. 1,000-query pilot (insufficient statistical power; standard error on tail misses $>1.5\%$).
  3. Stratified 10,000-query pilot with fixed random seed (standard error $\le 0.005$, runs in seconds).
- **Decision**: Adopt a standardized pilot of 10,000 $S1$ records (6,000 US, 4,000 India; 34,481 ground truth pairs; 84,481 target records) with `seed=42`.
- **Consequences**: Fast feedback loops (<30 seconds per run, <400 MB RAM) while guaranteeing mathematical fidelity and statistical significance.

---

## ADR-02: Strict Country-Partitioned Indexing
- **Date**: 2026-09-25
- **Status**: **ACTIVE & INVIOLATE**
- **Context**: Evaluating potential matches across the full cross-product of countries creates an intractable $O(N \times M)$ search space and causes immediate memory exhaustion.
- **Alternatives Considered**:
  1. Global inverted indexing across all countries.
  2. Soft country penalty in downstream scoring.
  3. Strict country partition (block only within `country_s1 == country_target`).
- **Decision**: Partition all inverted indexes, hash tables, and candidate queries strictly by country (`US`, `IN`).
- **Evidence**: Analysis of 7,638,365 ground-truth pairs verified exactly **0 cross-country matches** (100.00% intra-country). Memory consumption plummeted from >6 GB to <400 MB.

---

## ADR-03: Conservative 5% Global Document-Frequency Threshold (E1-B)
- **Date**: 2026-09-25
- **Status**: **SUPERSEDED BY DYNAMIC RARITY (ADR-11)**
- **Context**: Baseline G generated 3,294.6 candidates per query, overwhelming downstream classification models.
- **Alternatives Considered**:
  1. No filtering (Baseline G control).
  2. Conservative cutoff (>5% frequency).
  3. Moderate cutoff (>2% frequency).
  4. Aggressive cutoff (>1% frequency).
- **Decision**: Adopt the 5% threshold as an initial candidate reduction mechanism.
- **Evidence**: Slashed candidate volume by 57.21% (from 3,294.6 to 1,409.7) while losing only 14 pairs (99.904% recall). 2% and 1% cutoffs violated the $\ge 99.90\%$ safety floor.

---

## ADR-04: Permanent Rejection of Standalone Exact-Name Blocking
- **Date**: 2026-09-25
- **Status**: **FINAL & REJECTED**
- **Context**: Evaluated whether exact normalized business name matching (Channel B) could serve as a standalone candidate generator.
- **Alternatives Considered**: Standalone exact name blocker vs multi-channel union.
- **Decision**: Permanently reject exact name matching as a standalone blocker.
- **Evidence**: Achieved only **39.12% recall** (missing 20,991 out of 34,481 true matches, a 60.88% failure rate). Exact matching is strictly confined to being an input channel in composite and multi-channel unions.

---

## ADR-05: Rejection of Standalone Composite Keys; Reservation for Tier-1 Sieve
- **Date**: 2026-09-25
- **Status**: **ACTIVE & INTEGRATED AS LEVEL 1**
- **Context**: Tested whether multi-attribute conjunction keys (e.g., `Tok & Loc`, `Pref & Dig`) could replace single-attribute channels to minimize candidate noise.
- **Decision**: Reject standalone composite keys due to severe recall degradation (59.9% to 80.4% recall). Reserve the composite union (`C2_Union_All`) as the Level-1 high-precision fast sieve in a multi-tier pipeline.
- **Evidence**: Standalone composites missed 6,700 to 13,800 true pairs due to missing address attributes. However, `C2_Union_All` captured 95.57% of pairs at only 113.8 candidates/S1.

---

## ADR-06: Establishment of the Core High-Efficiency Backbone ($B+C+D+E$)
- **Date**: 2026-09-25
- **Status**: **ACTIVE & INTEGRATED AS LEVEL 2**
- **Context**: Evaluated cumulative channel attribution to isolate the exact source of candidate volume bloat.
- **Decision**: Standardize $B+C+D+E$ (Exact Name + Tokens + Prefix-4 + Address Digits) as the Core Candidate Generation Backbone. Channel F is isolated as a secondary/fallback tier.
- **Evidence**: $B+C+D+E$ delivers **98.09% recall at 836.1 candidates/S1**. In contrast, Channel F added only +641 true pairs (+1.86%) while generating 24.58 million candidates (38,355 candidates per recovered pair).

---

## ADR-07: Selective Transliteration (Names ON, Broad Location OFF)
- **Date**: 2026-09-25
- **Status**: **ACTIVE & INVIOLATE**
- **Context**: Evaluated Indic script transliteration (`indic-transliteration`) across entity names, digits, and location tokens.
- **Decision**: Transliteration is **permanently enabled** on business names (Channels B, C, D) and address digits (Channel E), and **permanently disabled** on broad location fields (Channel F).
- **Evidence**: Transliterating names recovered 146 Indian business pairs at a negligible cost of +4.9 candidates/S1 (338 cands/TP). Transliterating location tokens caused a massive explosion of +4.33 million candidates (+433 cands/S1) while losing 4 true pairs to index collisions.

---

## ADR-08: Rejection of Query-Side Candidate Suppression ($k < T$); Recognition of Multi-Match Blindspot
- **Date**: 2026-09-25
- **Status**: **NEGATIVE ARCHITECTURAL INVARIANT**
- **Context**: Tested whether adaptive query-level gating (triggering Channel F only if query yield $k < T$ or evidence is low) could control Channel F bloat.
- **Decision**: **Permanently ban all query-side candidate volume gating ($k < T$)**. Filter inverted indexes on the target side instead.
- **Evidence**: In 1-to-many matching, **92.4% of Channel F-recoverable pairs belonged to queries that already had at least one matching target**. Suppressing Channel F because $k \ge 10$ capped recall at 98.49%, permanently discarding secondary true matches.

---

## ADR-09: Adoption of 3-Tier Cumulative Union ($L1 \cup L2 \cup L3$) as Champion v1
- **Date**: 2026-09-25
- **Status**: **SUPERSEDED BY CHAMPION V2 (ADR-13)**
- **Context**: Integrated validated components into an end-to-end hierarchical pipeline.
- **Decision**: Adopt the 3-tier cumulative union as Champion v1:
  - Level 1: `C2_Union_All` (fast sieve, 95.63% recall, 104 cands).
  - Level 2: Core Backbone ($B+C+D+E$ with selective transliteration, 98.09% recall, 836 cands).
  - Level 3: Target-side 5% IDF-filtered Channel F (evaluated universally, 99.9275% recall).
- **Evidence**: Slashed candidate volume by 48.46% (from 3,294.6 to 1,698.0 cands/S1) and cut P95 from 9,555 to 5,321 while achieving 99.9275% recall.

---

## ADR-10: Streaming Micro-Batch Execution for Scalability
- **Date**: 2026-09-25
- **Status**: **PRODUCTION OPERATIONAL STANDARD**
- **Context**: Scaling benchmarks to 50,000 queries generated 422.9 million candidate pairs, exceeding single-machine RAM if materialized all at once.
- **Decision**: Mandate streaming micro-batch processing (micro-batches of 1,000 queries streamed directly to disk or downstream scoring).
- **Evidence**: Maintained peak RAM under 750 MB across 50,000 queries while completing candidate generation in 205 seconds.

---

## ADR-11: Adoption of Dynamic Target-Side Top-2 Rarest Token Channel F
- **Date**: 2026-09-25
- **Status**: **ACTIVE IN CHAMPION V2**
- **Context**: Re-engineered Level 3 to eliminate the 5% static cutoff's candidate bloat and recover city-center losses.
- **Decision**: Replace static 5% global cutoff with **Dynamic Target-Side Top-2 Rarest Location Token Indexing**: sort location tokens per target record by frequency and index strictly the 2 rarest.
- **Evidence**: Slashed candidate volume from 1,698.0 to **1,064.5 candidates/S1** (-67.7% vs Baseline G), median from 1,135 to 588, and recovered 100% (9/9) of cutoff losses with 3,568 cands/TP efficiency.

---

## ADR-12: Adoption of Surgical Tail Recovery Channels
- **Date**: 2026-09-25
- **Status**: **ACTIVE IN CHAMPION V2**
- **Context**: Evaluated specialized channels for the 19 Baseline G misses.
- **Decision**: Deploy four surgical tail channels:
  1. Channel T1: Country-partitioned 2-character tokens (frequency $\le 200$).
  2. Channel T2: Domain stem & social handle nospace matching.
  3. Channel T3: Double-consonant collapsing (`core_collapsed`).
  4. Channel T4: Composite enriched digits + location (`digits + loc`).
- **Evidence**: Boosted recall from 99.9420% to **99.9710%** (slashing misses from 20 to 10) while adding only +76 candidates/S1 (1,140.7 avg cands). Recovered 12 of the 19 historic baseline misses.

---

## ADR-13: Champion v2 Surgical Crowned & Candidate Generation Frozen
- **Date**: 2026-09-25
- **Status**: **FINAL, APPROVED & FROZEN**
- **Context**: Final hard-tail investigation on the 10 remaining missed pairs.
- **Decision**: Integrate micro-signals S2 (`cons_tri`), S4 (`state, dig`), and S5 (`unit`) into **Champion v2 Surgical**. Permanently freeze the candidate generation architecture.
- **Evidence**:
  - Recall: **99.9855%** (34,476 / 34,481) — only 5 true pairs missed across the entire benchmark.
  - Misses slashed by **73.7%** relative to Baseline G (from 19 to 5).
  - Average candidates: **1,145.0** (-65.25% vs Baseline G's 3,294.6).
  - Median candidates: **609** (-76.76% vs Baseline G's 2,621).
  - Zero-candidate $S1$s: **0** (0.00% defect rate).
  - Multi-match complete recall: **99.90%**.
  - Total candidates for 5 tail recoveries: +43,025 (+4.3 cands/S1, efficiency: 8,605 cands/TP).
- **Subsequent Action**: Transition immediately to Phase 3 (Feature Engineering & Fast Pre-Ranking).
