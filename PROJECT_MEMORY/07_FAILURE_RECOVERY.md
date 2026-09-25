# 07 FAILURE RECOVERY PLAYBOOK: SELF-HEALING PROTOCOLS

When an unexpected event, error, or metric collapse occurs, follow these exact procedures:

---

## Protocol 1: Baseline Numbers Suddenly Change
- **Action:** **STOP IMMEDIATELY.** Do not proceed with experimental comparisons.
- **Diagnostics:**
  1. Check data files in `experiments/data/`: verify `pilot_s1.tsv` has 10,000 rows, `pilot_ground_truth.tsv` has 34,481 true pairs, `pilot_targets.tsv` has 84,481 rows.
  2. Verify random seed is 42.
  3. Check git diff on `src/preprocessing/normalization.py`: did any regex or token filter change?
  4. Run `experiments/blocking/baseline_g.py` and verify metrics against `experiments/results/baseline_g_metrics.json`.
  5. Only continue once Baseline G is perfectly restored (34,462 recalled / 19 missed).

---

## Protocol 2: Recall Suddenly Drops ($<99.0\%$)
- **Action:** **HALT.** Do not promote the strategy.
- **Diagnostics:**
  1. Compare candidate sets against `experiments/data/baseline_g_candidates.json`.
  2. Identify the exact newly lost pairs:
     $$\text{Newly Lost} = \text{Baseline Recalled} - \text{Current Recalled}$$
  3. Classify failure mechanism: Was it an aggressive token cutoff? Was a key token filtered out?
  4. Adjust frequency threshold or re-introduce the missing channel.

---

## Protocol 3: Runtime Explodes ($>3\text{ minutes on 10k Pilot}$)
- **Action:** **CANCEL / KILL TASK.**
- **Diagnostics:**
  1. Check for unindexed pairwise comparisons ($\mathcal{O}(N \times M)$ loops).
  2. Check for dynamic set allocations (`len(s1 & s2)`) inside loops.
  3. Profile memory with `psutil`: is the system swapping memory to disk?
  4. Ensure inverted index lookups are used instead of linear scans.

---

## Protocol 4: Memory Approaches System Limit ($>2\text{ GB RAM}$)
- **Action:** **ABORT AND RE-PARTITION.**
- **Diagnostics:**
  1. Verify country isolation: are US and India processed separately?
  2. Avoid building massive in-memory candidate dictionaries holding all pairs simultaneously.
  3. Stream evaluations or flush candidate counts to summary metrics.
