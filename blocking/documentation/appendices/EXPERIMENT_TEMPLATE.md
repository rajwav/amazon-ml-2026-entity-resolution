# Standard Engineering Experiment Template (14-Section Protocol)

Any future engineering experiment or ablation study conducted within this codebase must be documented using this standard 14-section format to maintain archival integrity.

---

```markdown
# Experiment [ID]: [Descriptive Title]

| Attribute | Specification |
|:---|:---|
| **Experiment ID** | `EXP_XX` |
| **Date Executed** | YYYY-MM-DD |
| **Author / Operator** | [Engineer Name / Team] |
| **Status** | [Completed / Validated / Rejected] |
| **Source Script** | [`experiments/blocking/your_script.py`](file:///path/to/script.py) |
| **Metrics Artifact** | [`experiments/results/metrics.json`](file:///path/to/metrics.json) |
| **Error / Trace Artifact** | [`experiments/results/errors.tsv`](file:///path/to/errors.tsv) |

---

## 1. Objective
[State the exact technical goal and question this experiment seeks to answer.]

---

## 2. Hypothesis
[Formal hypothesis: If we do X, then metric Y will change by Z because of mechanism W.]

---

## 3. Starting Point / Baseline Reference
[Specify the prior experiment ID and exact performance numbers serving as reference.]

---

## 4. Dataset & Benchmark Setup
- Query Sample Size ($S1$):
- Target Record Pool:
- Ground Truth Pairs:
- Seed / Partitioning:

---

## 5. Method & Implementation Details
[Detailed explanation of algorithm, data structures, preprocessing, and indexing logic.]

---

## 6. Code & Artifact References
- **Script**:
- **Metrics JSON**:
- **Output Tables**:

---

## 7. Results & Metrics Table

| Configuration | Recall % | Recalled | Missed | Avg Cands / $S1$ | Median | P95 | Max | Zero $S1$ | Runtime | RAM |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| Baseline | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
| Treatment | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

---

## 8. Candidate Volume & Distribution Analysis
[Analyze candidate count reductions, percentile distribution shifts, and outliers.]

---

## 9. Recall & Recovery Analysis
[Analyze newly recalled true pairs, multi-match cardinality behavior, and recall gains.]

---

## 10. Failure / Error Analysis
[Analyze records that remained missed or were newly lost. Inspect raw records.]

---

## 11. Key Lessons Learned
1.
2.
3.

---

## 12. Architectural Decision
- **Role**: [e.g., Level-1 Sieve / Production Baseline / Rejected]
- **Decision**: [Accept / Reject / Shelve with rationale]

---

## 13. Impact on Subsequent Architecture
[Explain what changes in the project roadmap as a direct result of this experiment.]
```
