# 05 LESSONS LEARNED & MISTAKE PREVENTIONS

*Format: What Happened? $\rightarrow$ Why? $\rightarrow$ Evidence $\rightarrow$ Lesson Learned $\rightarrow$ How to Prevent.*

---

## 1. The 1h40m Heap Allocation & Virtual Memory Paging Bottleneck
- **What Happened:** The initial full benchmark script `benchmark_true_pair_recall.py` ran for 1 hour 40 minutes without completing even the US split.
- **Why:**
  1. Materializing 6M records into nested Python `set`s created **>25 million Python set objects and >180 million string objects**, exceeding physical RAM (~6–7 GB) and causing intense disk swapping/paging.
  2. Inside the pair evaluation loop, `len(set_a & set_b) >= 2` dynamically allocated and deallocated millions of temporary Python set objects on the heap.
- **Evidence:** CPU utilization dropped to single digits, disk I/O thrashing occurred, and set intersection overhead exceeded 75 minutes.
- **Lesson Learned:** Python dynamic heap set allocations inside millions of iterations under memory pressure will stall execution.
- **Prevention:**
  - Always use lightweight inverted indexes (`Country -> Key -> list[ID]`) or flat integer arrays.
  - Query indexes directly instead of computing pairwise dynamic set intersections.
  - Isolate country runs to keep RAM usage strictly below 400 MB.

---

## 2. Exact Name Matching Fails as a Standalone Blocking Strategy
- **What Happened:** Strategy B (Exact Normalized Core Name) achieved only **39.12% recall**, missing over 60% of true pairs.
- **Why:** Real-world data features frequent spelling variations (`Enterprises` vs `Enterpires`), concatenated domains (`empirecastillo.com`), legal suffix reorderings (`Schubert LLC Adr`), and cross-script text.
- **Lesson Learned:** Exact string matching cannot be relied upon as a primary candidate generator.

---

## 3. Location Tokens Cause Catastrophic Candidate Explosion Without Filtering
- **What Happened:** Strategy F (Address Location Tokens alone) generated an average of **2,568 candidates per S1** (Max: 14,641).
- **Why:** Common cities like `delhi` (7,502 occurrences), `mumbai` (3,778), `city` (3,372), and `texas` (2,343) inflate posting lists.
- **Lesson Learned:** Location tokens must undergo frequency filtering (IDF cutoff) or be compounded with street numbers/name tokens.

---

## 4. Short 2-Letter Names Are Vulnerable When Target Address is Empty
- **What Happened:** 8 of the 19 Baseline G misses were 2-letter business acronyms (`TY`, `DK`, `AL`, `JD`, `TB`, `XF`, `IT`, `F`) where the target address was empty.
- **Why:** Token filtering with minimum length $\ge 3$ discarded 2-letter words, leaving 0 tokens when address was missing.
- **Lesson Learned:** Names with short acronyms require special 2-letter token preservation or exact fallback matching.

---

## 5. Standalone Composite Keys Suffer Catastrophic Recall Loss
- **What Happened:** In Experiment 2, individual composite keys (e.g. `Prefix & Digit`, `Token & Digit`) crashed recall to **59.97%–80.37%** and left up to **1,689 S1 records with 0 candidates**.
- **Why:** Requiring two attributes simultaneously creates an $A \land B$ dependency. If either the house number is missing or the name token has a typo, the entire block fails.
- **Lesson Learned:** Never use a single composite key as a primary blocker. However, a multi-composite union (`C2_Union_All_Composites`) achieves **95.57% recall with only 113.8 candidates/S1**, making it an outstanding first-tier sieve in a hierarchical fallback pipeline.

---

## 6. Marginal Value and Cost Asymmetry Across Blocking Channels
- **What Happened:** In Experiment 3, channels exhibited extreme cost-benefit asymmetry:
  - Channel C (+ Significant Name Token) is the primary workhorse, adding **+16,171 true pairs** (+46.9% recall) for 348 candidates.
  - Channel D (+ 4-Char Prefix) is the most efficient channel in the entire system, adding **+1,780 true pairs** (+5.2% recall) for only **+21.3 candidates/S1**.
  - Channel E (+ Address Digits) breaks the 98% recall barrier, adding **+2,380 true pairs** for +467 candidates.
  - Channel F (+ Location Tokens) adds **+641 true pairs** (+1.85% recall) but causes **+2,458.5 candidates/S1 (74.6% of all candidates)**.
- **Lesson Learned:** The core triangle ($B + C + D + E$) achieves **98.09% recall with only 836 candidates/S1**. Channel F is a high-cost recall closer that must either be constrained with IDF filtering (E1-B) or reserved for fallback levels.

---

## 7. Transliteration Asymmetry: High Precision in Names, Toxic Bloat in Location Tokens
- **What Happened:** In Experiment 4, evaluating Indic transliteration revealed opposite behaviors across channels:
  1. In Name channels ($B, C, D$), transliteration recovered **155 genuine cross-script true pairs** (Devanagari, Kannada, Tamil, Gujarati, Bengali, Malayalam) with almost zero candidate expansion (**+4.9 candidates/S1**, a 0.59% candidate increase).
  2. In Address Location tokens (Channel $F$), transliterating Indic addresses generated **+4,330,186 useless non-true candidates (+433 candidates/S1)** while actually losing 4 true pairs (from 34,466 to 34,462) due to noisy short-syllable token collisions.
- **Why:** Business names are distinctive proper nouns where transliteration produces discriminating tokens. Address fields contain frequent recurring geographic words and postal fragments that, when transliterated into short phonetic Latin roots (e.g. `pur`, `ngr`, `rd`), collide with thousands of unrelated entities in the same country.
- **Lesson Learned:** Transliteration must be **selective**: enable transliteration on business names and address digits, but disable transliteration for generic address location tokens in Channel F.

---

## 8. The Multi-Match Gating Blindspot in 1-to-Many Entity Resolution
- **What Happened:** In Experiment 5, candidate-count threshold policies ($k < 5, 10, 20$) and "no-match" gating failed to recover ~540 out of the 644 Channel F true pairs.
- **Why:**
  1. In multi-match entity resolution, an S1 query entity has multiple matching targets in S2/S3 (e.g. 2 to 9 matches).
  2. The high-evidence matches (e.g. Target 1 with exact name, Target 2 with house number) match easily in $B+C+D+E$, generating $k \ge 50$ or $k \ge 100$ candidates.
  3. However, Target 3 or 4 is heavily corrupted (e.g. synthetic noise name like `Veozephgild`, or missing house number), meaning it can **only** be found via street/location tokens (Channel F).
  4. If Channel F is gated by S1 candidate counts ($k < T$) or "S1 has no exact name match", the policy falsely assumes that because S1 found Target 1, it needs no further recall channels. Consequently, Channel F is suppressed, and Target 3 is lost!
- **Evidence:** Out of the 644 pairs missed by BCDE and recoverable by Channel F, **92.4% (595 / 644)** belong to S1 entities that ALREADY had at least one other true match recalled by BCDE!
- **Lesson Learned:** Query-level candidate count ($k < T$) cannot act as a universal gatekeeper in 1-to-many ER. To capture the full 99.9% recall, Channel F must be present, BUT its candidate explosion must be tamed via **Target-Side Filtering** (e.g. E1-B rare token/IDF filtering or composite key pairing) rather than blanket S1 suppression.

---

## 9. Cumulative Hierarchical Union ($L1 \cup L2 \cup L3$) Tames Candidate Volume While Preserving 99.93% Recall
- **What Happened:** In Experiment 6, combining Level 1 (Composite Sieve), Level 2 (Core Backbone $B+C+D+E$ with selective transliteration), and Level 3 (Target-side E1-B filtered Channel F) achieved **99.9275% recall (34,456 / 34,481)** while eliminating **15.97 million candidate pairs (-48.46% candidate reduction)** vs Baseline G.
- **Why It Works:**
  1. **Level 1 (Composite Sieve)** sweeps **95.63%** of true pairs into ultra-compact buckets (median 10 candidates/S1).
  2. **Level 2 (Core Backbone)** adds **+848 marginal true pairs**, pushing cumulative recall to **98.09%** with 377 median candidates.
  3. **Level 3 (Filtered Channel F)** recovers **+635 of the 660 backbone misses (96.2%)** without the 32.9M candidate blowout because target-side 5% IDF filtering prunes hyper-frequent stopwords like `delhi`, `mumbai`, `nagar`, `city`.
  4. Crucially, because Channel F is evaluated across all queries (unsuppressed at query level), multi-match S1s that found Target 1 via exact name still successfully find their corrupted Target 2 via location tokens.
- **Evidence:** 99.76% of all multi-match S1 queries had 100% of their true targets recalled. Average candidates fell from 3,294.6 to **1,698.0**, and P95 dropped from 9,555 to **5,321**.
- **Lesson Learned:** The 3-tier hierarchical union ($L1 \cup L2 \cup L3$) is the optimal candidate generation architecture for production scaling.

---

## 10. The Candidate Materialization Limit vs Streaming Evaluation
- **What Happened:** During Experiment 7 at 50k S1, attempting to store the full candidate sets `cands_final[s1_id]` for all 50,000 S1 records in a single Python dictionary exhausted system RAM and crashed the process.
- **Why:**
  1. Average candidate count per S1 scales linearly with target pool size: $\approx 0.0201 \times N_{\text{targets}}$.
  2. At 50k S1 ($N_{\text{targets}} = 421.5\text{k}$), total candidate pairs exceed **422.9 million**.
  3. Storing 422 million Python string pointers across 50,000 nested sets requires $>12\text{ GB}$ of RAM.
  4. However, the **inverted index itself for 421k targets occupies only 898 MB**!
- **Evidence:** Switching from batch candidate set materialization to **streaming evaluation** (evaluating S1 by S1, updating running recall/percentiles, and discarding the per-query candidate set) reduced peak RAM from $>8\text{ GB}$ to **637.88 MB** and completed in 205 seconds.
- **Lesson Learned:** Candidate sets must NEVER be materialized in bulk in RAM across hundreds of thousands of queries. The pipeline must generate and stream candidates directly to disk (TSV) or feed them in micro-batches directly to the ranking/matcher model.

---

## 13. Dynamic Target-Side Location Pruning (Top-2 Rarest Tokens) Eliminates 67% of Bloat
- **Context:** Channel F is essential for corrupted names, but global 5% frequency cutoffs starved targets that only had common city tokens (Mumbai, Delhi), losing 9 pairs.
- **Evidence:** In Experiment 8, sorting each target's location tokens by frequency and indexing strictly the **Top-2 rarest tokens per target** recovered **100% (9/9)** of all cutoff losses while slashing Channel F candidate volume from 2,458 cands/S1 down to **228 cands/S1** (efficiency: 3,568 cands / recovered TP vs 31,517 in baseline).
- **Lesson Learned:** Rather than globally banning tokens, bound target representation dynamically. Targets with specific locality tokens will index those, while targets with only city tokens will still index them without being flooded by targets with specific addresses.

---

## 14. The 2-Letter Business Name Blindspot
- **Context:** 7 out of the 19 Baseline-G misses (`TY`, `DK`, `TB`, `XF`, `JD`, `AL`, `IT`) had empty target addresses and failed to match in any channel.
- **Evidence:** Analysis revealed that `len(token) >= 3` in `normalize_business_name` silently discarded all 2-letter tokens. Standalone 2-letter words like `ty` in the US have an index size of only 5 targets in the whole country!
- **Lesson Learned:** 2-letter business abbreviations are highly discriminating identifiers. Partitioning by country and indexing 2-letter non-stopword tokens recovered ALL 7 misses while adding only **+1.4 candidates per S1** (efficiency: 1,998 cands / recovered TP).

---

## 15. Address Ordinal & Leading-Zero Normalization
- **Context:** Addresses like `10848 54th Lane` vs `54TH LN` or `1711 37th Ave` vs `001711 37ST AVE` failed digit matching.
- **Evidence:** `\b\d+\b` failed to extract numbers from `54th`, `37th`, `121st`, discarding critical street numbers. Furthermore, `001711` and `1711` failed exact digit matching.
- **Lesson Learned:** Stripping ordinal suffixes (`st`, `nd`, `rd`, `th`) and normalizing leading zeros matches address digits on hard alias/DBA cases. Combining enriched digits with location (`dig, loc`) recovers targets without standalone digit explosion.





