# Mathematical Formulations & Metrics Reference Guide

This reference document formalizes the mathematical definitions, notation, and optimization criteria used to evaluate candidate generation and downstream entity matching.

---

## 1. Candidate Generation (Blocking) Evaluation Metrics

Let:
- $Q = \{q_1, q_2, \dots, q_N\}$ denote the set of query records ($S1$), with $|Q| = N$.
- $T = \{t_1, t_2, \dots, t_M\}$ denote the target record pool, with $|T| = M$.
- $G \subset Q \times T$ denote the set of ground-truth true matching entity pairs, with $|G| = |\{ (q, t) \mid q \equiv t \}|$.
- $C(q) \subset T$ denote the set of candidate target records generated for query $q$ by candidate generator $B$.
- $C_{\text{total}} = \bigcup_{q \in Q} \{ (q, t) \mid t \in C(q) \}$ denote the total set of candidate pairs generated.

---

### 1.1 True-Pair Recall (Pair Completeness)
$$\text{Recall} = \frac{|C_{\text{total}} \cap G|}{|G|} = \frac{\sum_{(q, t) \in G} \mathbb{I}(t \in C(q))}{|G|}$$
- **Role**: **Hard Upper Bound**. Downstream classifiers cannot score pairs that are not retrieved. Any drop in blocking recall directly penalizes final model recall.
- **Safety Gate**: $\text{Recall} \ge 99.90\%$.

---

### 1.2 Candidate Reduction Ratio (RR)
$$\text{RR} = 1 - \frac{|C_{\text{total}}|}{|Q| \times |T|} = 1 - \frac{\sum_{q \in Q} |C(q)|}{N \times M}$$
- **Role**: Measures the fraction of the Cartesian search space eliminated by blocking.
- **Benchmark Value**: Champion v2 achieves $\text{RR} = 99.9864\%$ on the pilot benchmark.

---

### 1.3 Average Candidates per Query ($\mu_{\text{cands}}$)
$$\mu_{\text{cands}} = \frac{|C_{\text{total}}|}{|Q|} = \frac{1}{N} \sum_{q \in Q} |C(q)|$$
- **Role**: Primary proxy for downstream feature extraction and scoring compute cost.

---

### 1.4 Distribution Percentiles (Median, P90, P95, P99, Max)
For the ordered sequence of candidate counts $k_1 \le k_2 \le \dots \le k_N$ where $k_i = |C(q_i)|$:
- **Median ($\text{P50}$)**: The central value $k_{\lceil 0.50 N \rceil}$, representing typical query load.
- **P95**: The 95th percentile $k_{\lceil 0.95 N \rceil}$, measuring heavy query burden.
- **Maximum**: $\max_{q \in Q} |C(q)|$, identifying worst-case query fan-out.

---

### 1.5 Zero-Candidate Query Rate ($R_{\text{zero}}$)
$$R_{\text{zero}} = \frac{1}{N} \sum_{q \in Q} \mathbb{I}(|C(q)| == 0)$$
- **Role**: Evaluates catastrophic recall failure. Any query generating 0 candidates guarantees a precision and recall of 0.
- **Requirement**: Must be strictly $0.00\%$.

---

### 1.6 Marginal Candidate Efficiency ($\eta$)
When adding candidate channel or signal $\Delta S$:
$$\eta = \frac{\Delta |C_{\text{total}}|}{\Delta |C_{\text{total}} \cap G|} = \frac{|C_{\text{new}}| - |C_{\text{old}}|}{\text{TP}_{\text{new}} - \text{TP}_{\text{old}}}$$
- **Role**: Evaluates the marginal cost-benefit trade-off of introducing new blocking signals.
- **Adoption Ceiling**: $\eta \le 20,000 \text{ candidates per recovered true pair}$.

---

## 2. Downstream Optimization Metric: Macro $F_{0.5}$

The official competition evaluation metric for the Amazon ML Challenge 2026 is **Macro-Averaged $F_{0.5}$ Score across query entities ($S1$)**.

For each query entity $q_i \in Q$:
Let:
- $\text{TP}_i = |P(q_i) \cap G(q_i)|$ (predicted targets that are true matches)
- $\text{FP}_i = |P(q_i) \setminus G(q_i)|$ (predicted targets that are false matches)
- $\text{FN}_i = |G(q_i) \setminus P(q_i)|$ (true targets not predicted)

### Query-Level Precision and Recall:
$$\text{Precision}_i = \frac{\text{TP}_i}{\text{TP}_i + \text{FP}_i}, \quad \text{Recall}_i = \frac{\text{TP}_i}{\text{TP}_i + \text{FN}_i}$$

### Query-Level $F_{0.5}$ Score:
$$F_{0.5, i} = \frac{(1 + 0.5^2) \cdot \text{Precision}_i \cdot \text{Recall}_i}{0.5^2 \cdot \text{Precision}_i + \text{Recall}_i} = \frac{1.25 \cdot \text{Precision}_i \cdot \text{Recall}_i}{0.25 \cdot \text{Precision}_i + \text{Recall}_i}$$

### Macro-Averaged $F_{0.5}$:
$$\text{Macro } F_{0.5} = \frac{1}{N} \sum_{i=1}^N F_{0.5, i}$$

### Strategic Mathematical Implication of $\beta = 0.5$:
- In $F_{\beta}$, precision is weighted $\beta^{-2} = 4\times$ more heavily than recall.
- **Blocking Phase Implication**: Even though precision is heavily weighted in the final metric, **blocking recall must remain near 100%** because blocking defines the ceiling $\text{Recall}_{\max} = \text{Recall}_{\text{blocker}}$. If a true match is blocked, $\text{FN}$ is permanently fixed, suppressing $F_{0.5, i}$.
- Conversely, candidate generation must achieve compact candidate pools ($\approx 1,145$ cands/S1) so that the downstream classifier is not inundated with noisy negative pairs that risk false positive errors.
