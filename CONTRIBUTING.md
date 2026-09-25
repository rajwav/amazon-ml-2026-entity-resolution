# Team Collaboration & Contribution Guidelines

**Amazon ML Challenge 2026 — Business Entity Resolution**

---

## 1. Team Structure & Functional Ownership

This project follows an evidence-based, collaborative engineering model where every team member owns primary technical deliverables and peer-reviews teammates' work:

| Team Member | Branch Name | Primary Ownership | Secondary Responsibility |
|:---|:---|:---|:---|
| **Raj** | `raj/blocking` | Blocking Architecture & Production Integration | Model Training Assistance |
| **Banamudra** | `banamudra/features-matching` | Feature Engineering Pipeline & Matching Model | Pairwise Scoring Optimization |
| **Shristi** | `shristi/data-error-analysis` | Exploratory Data Analysis & Error Analysis | Feature Exploration & Extraction |
| **Abhijeet** | `abhijeet/evaluation-model` | Evaluation Metrics ($F_{0.5}$), Validation & Calibration | Baseline Matching Models & Threshold Tuning |

---

## 2. Inviolable Governance Principles

### Rule 1: The Candidate Generation Blocker is FROZEN
- **Champion v2 Surgical** is the frozen candidate generation baseline.
- **NO SILENT EDITS**: No individual team member may alter blocking channels, regex normalizations, frequency caps, or candidate retrieval logic.
- Any proposed change requires:
  1. A reproducible failure case on the benchmark.
  2. A formal written Architectural Change Request.
  3. Team consensus based on statistical proof.

### Rule 2: No Direct Commits to `main`
- Direct commits to `main` are strictly prohibited.
- All code, features, models, and experiments must originate on personal feature branches and be merged exclusively via reviewed Pull Requests (PRs).

### Rule 3: Peer Review is Mandatory
- Every PR requires an explicit review and approval from at least one teammate before merging.
- Reviews must check:
  - Correctness and adherence to competition constraints.
  - No external data or network lookups (strict Amazon challenge prohibition).
  - Reproducibility with fixed random seeds (`seed=42`).
  - No hardcoded local machine paths.

### Rule 4: Raj Handles Final Integration & Merge
- After review approvals and passing automated tests, Raj performs the final merge into `main` to maintain architectural cohesion.

---

## 3. Git Workflow & Branch Naming Conventions

### Branch Naming:
- `raj/<feature-description>`
- `banamudra/<feature-description>`
- `shristi/<feature-description>`
- `abhijeet/<feature-description>`

Examples:
- `banamudra/string-similarity-features`
- `shristi/error-analysis-singletons`
- `abhijeet/macro-f05-evaluator`

### PR Lifecycle:
```text
Local Feature Branch
        │
        ▼
Run Unit Tests (`pytest blocking/tests/`)
        │
        ▼
Push Branch & Open PR against `main`
        │
        ▼
Teammate Review & Approval
        │
        ▼
Integration by Raj into `main`
```

---

## 4. Coding & Architecture Standards

1. **Python Compatibility**: Python $\ge 3.10$.
2. **Deterministic Seeds**: All stochastic processes (sampling, LightGBM/XGBoost, neural networks) must use `seed=42`.
3. **No Hardcoded Machine Paths**: Use relative paths from repository root (e.g. `student_resource/dataset/test/` or `data/`). Never use absolute paths like `/Users/username/...`.
4. **Performance & Memory Discipline**: The full dataset contains millions of records. Memory must remain bounded ($\le 4\text{ GB}$). Always use streaming generators or chunked iteration for large files.
5. **No External Data**: External geocoders, commercial ER APIs, government registries, or internet lookups are **strictly banned** by Amazon competition rules. All features must derive purely from provided tables.

---

## 5. Experiment Tracking Protocol

Every feature engineering or model training experiment must be logged in `experiments/models/` with:
- **Experiment ID**: e.g., `EXP_FEAT_01`, `EXP_MODEL_01`.
- **Objective & Hypothesis**: What feature/model was tested and why.
- **Features Used**: Exact list of feature columns.
- **Model & Hyperparameters**: Model family, learning rate, tree depth, etc.
- **Threshold Calibration**: Selected classification threshold.
- **Validation Metrics**: Precision, Recall, Macro $F_{0.5}$, False Positives (FP), False Negatives (FN).
- **Outcome**: ACCEPT or REJECT with evidence.
