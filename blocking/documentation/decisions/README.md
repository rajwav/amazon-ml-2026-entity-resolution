# Architectural Decision Records (ADRs) Directory

This directory houses the formal Architectural Decision Records (ADRs) governing the candidate generation and blocking phase of the Amazon ML Challenge 2026.

---

## 1. Directory Structure

| Document | Purpose |
|:---|:---|
| [`README.md`](README.md) | Overview of decision framework and ADR methodology. |
| [`DECISION_LOG.md`](DECISION_LOG.md) | Complete sequential record of all 13 formal architectural decisions (ADR-01 through ADR-13). |
| [`ACCEPTED_CHANNELS.md`](ACCEPTED_CHANNELS.md) | Exhaustive catalog of all 10 accepted candidate generation channels, keys, and frequency limits. |
| [`REJECTED_CHANNELS.md`](REJECTED_CHANNELS.md) | Formal record of rejected channels, negative experiments, candidate explosion metrics, and post-mortems. |

---

## 2. ADR Governance Framework
Every architectural choice in the candidate generation phase is evaluated against three immutable governing principles:
1. **Recall as a Hard Constraint**: Blocking recall must never fall below the **99.90% safety floor**. An algorithm yielding 500 candidates per query at 98% recall is strictly inferior to one yielding 1,200 candidates at 99.98% recall.
2. **Marginal Candidate Efficiency**: Any new channel or micro-signal must deliver an acceptable candidate efficiency:
   $$\text{Efficiency} = \frac{\Delta \text{Candidates}}{\Delta \text{True Pairs Recovered}} \le 20,000 \text{ cands/TP}$$
3. **Multi-Match Non-Suppression**: In 1-to-many entity resolution, query-side candidate volume gating is prohibited. Inverted indexes must be constrained at indexing time, not query time.
