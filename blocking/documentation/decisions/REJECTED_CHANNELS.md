# Catalog of Rejected Channels & Negative Experimental Findings

This document formalizes all candidate generation channels, gating strategies, and parameter configurations that were tested, evaluated, and formally rejected during the project.

---

## 1. Summary of Rejected Proposals

| Proposal / Channel | Tested In | Measured Effect | Primary Failure Mechanism | Rejection Ruling |
|:---|:---|:---|:---|:---|
| **Standalone Exact Name** | EXP_00, EXP_03 | Recall: 39.12% | Misses 60.88% of ground truth | **REJECTED (Fatal recall drop)** |
| **Standalone Composite Keys** | EXP_02 | Recall: 59.9% to 80.4% | Conjunction fragility ($A \land B$) on missing address data | **REJECTED (Fatal recall drop)** |
| **Aggressive Global Cutoffs (<2%)** | EXP_01 | Recall: 99.62% to 99.77% | Prunes genuine entity tokens in medium-sized cities | **REJECTED (Violates $\ge 99.9\%$ floor)** |
| **Broad Location Transliteration** | EXP_04 | +4.33M candidates (+433/query) | Spurious phonetic matches across common location words | **REJECTED (Extreme noise explosion)** |
| **$S1$-Level Gating ($k < T$)** | EXP_05 | Recall capped at 98.49% | **Multi-Match Blindspot**: suppresses F on true secondary targets | **REJECTED (Banned invariant)** |
| **Unconstrained Enriched Digits** | EXP_09 | +5.15M candidates (+514/query) | Massive posting lists on common street numbers ("100", "200") | **REJECTED (Must compound with loc)** |
| **Top-4 Location Tokens (S1)** | EXP_10 | +5.65M candidates (+565/query) | 1,884,418 candidates per true pair recovered (+3 TP) | **REJECTED (Degenerative efficiency)** |
| **Domain Stem Subwords (S3)** | EXP_10 | +40 candidates, +0 TP | Produced zero marginal true pairs | **REJECTED (Zero marginal utility)** |
| **Short Street + State (S6)** | EXP_10 | +907 candidates, +0 TP | Produced zero marginal true pairs | **REJECTED (Zero marginal utility)** |

---

## 2. Detailed Post-Mortem on Key Rejections

### Rejection 1: Query-Side Candidate Volume Gating ($k < T$)
- **Proposal**: If query $S1$ already has $\ge 10$ candidates from Channels B, C, D, or E, do not evaluate Channel F.
- **Hypothesis**: Queries with $\ge 10$ candidates are already "satisfied", so skipping Channel F saves 20 million comparisons.
- **Empirical Reality**: The hypothesis was completely disproven in Experiment 05. Because this is a 1-to-many matching challenge (cardinality up to 17), **92.4% of tail pairs belonged to queries that already had candidates**. The policy assumed finding Target A meant the query was finished, permanently discarding Target B.
- **Permanent Ban**: Query candidate volume gating is permanently banned across the entire project.

### Rejection 2: Broad Location Transliteration
- **Proposal**: Apply Indic script transliteration to all address fields, converting Hindi/Bengali/Gujarati location strings to Latin.
- **Hypothesis**: More transliteration will increase recall across India records.
- **Empirical Reality**: In Experiment 04, transliterating name fields added only +4.9 candidates/S1 and recovered 146 true pairs. But transliterating Channel F added **4,330,186 non-matching candidates (+433/S1)** and *reduced* recall by 4 pairs due to hash collision noise.
- **Ruling**: Transliteration is restricted strictly to name fields and numeric digits.

### Rejection 3: Signal S1 (Top-4 Location Tokens)
- **Proposal**: In Level 3, expand the dynamic rarity index from Top-2 to Top-4 rarest location tokens per target record.
- **Empirical Reality**: In Experiment 10, Top-4 location recovered 3 of the final 10 misses, pushing recall from 99.9710% to 99.9797%. However, it generated **5,653,253 additional candidates** (+565.3 candidates per query).
- **Efficiency Metric**:
  $$\text{Efficiency} = \frac{5,653,253 \text{ cands}}{3 \text{ recovered TP}} = 1,884,418 \text{ cands / TP}$$
- **Ruling**: Forcing downstream scoring models to evaluate nearly 2 million candidate comparisons to recover a single entity match is mathematically and economically degenerative. Rejected.

### Rejection 4: Unconstrained Standalone Enriched Digits
- **Proposal**: Index all extracted numeric sequences from addresses directly.
- **Empirical Reality**: In Experiment 09, unconstrained numeric indexing generated 5,145,764 extra candidates (+514.6 cands/query) for only 5 true pairs. Common building numbers (e.g., "1", "101", "202") created enormous posting lists across every city.
- **Ruling**: Standalone enriched digits were rejected. The channel was rescued by compounding enriched digits with the rarest location token (`digits + location`), which dropped candidate volume from +514 cands/S1 to only +76 cands/S1.
