# AGENT PROTOCOL: ANTIGRAVITY OPERATIONAL MANDATES

You are working inside an ongoing ML research project.

Your job is NOT to blindly execute instructions.

Your job is to:
1. Understand the current project state.
2. Preserve verified facts.
3. Test hypotheses experimentally.
4. Detect contradictions.
5. Stop when results are suspicious.
6. Recover from failures.
7. Never fabricate evidence.

---

## 1. Source of Truth Priority
Use this priority when resolving any ambiguity:
1. **Actual dataset / executable output**
2. **Verified experiment artifacts** (`experiments/results/`, `PROJECT_MEMORY/02_DATASET_FACTS.md`)
3. **Current project documentation** (`PROJECT_MEMORY/`)
4. **Previous experiment logs** (`PROJECT_MEMORY/04_EXPERIMENT_LOG.md`)
5. **User instructions**
6. **Your own assumptions**

*Never treat an assumption as a verified fact.*

---

## 2. Anti-Hallucination Protocol
If information or a metric is unknown:
- **SAY:** *"Unknown — needs verification."*
- **DO NOT:**
  - Guess or extrapolate without stating so explicitly.
  - Invent candidate numbers, recalls, or failure reasons.
  - Present an assumption as an empirical fact.

---

## 3. Experiment Discipline
Every experiment must execute this full cycle:
$$\text{HYPOTHESIS} \longrightarrow \text{CONFIGURATION} \longrightarrow \text{EXECUTION} \longrightarrow \text{MEASUREMENT} \longrightarrow \text{COMPARISON} \longrightarrow \text{CONCLUSION}$$
*Never skip measurement or declare victory without data.*

---

## 4. Baseline Protection & Reproducibility
- **Never modify the baseline experiment.** Create a new experiment ID instead.
- Every result must record:
  - Dataset sample & seed (`random.seed(42)`)
  - Ground-truth universe
  - Code version / diff
  - Concrete metrics (Recall, Recalled, Missed, Avg, P50, P95, Max, Zero-cand)
  - Runtime and peak RAM

---

## 5. Failure & Contradiction Protocol
- **If something unexpected happens:** STOP. Do not continue automatically.
- First determine:
  - What changed?
  - Why did it change?
  - Is the result reproducible?
  - Follow the playbook in `07_FAILURE_RECOVERY.md`.
- **If two documents or outputs disagree:**
  - Report: `CONFLICT DETECTED`.
  - Re-run or trace to determine which source is newer and verified.

---

## 6. Communication Structure
Before long operations:
- Report what script will run, input data, expected runtime, RAM, and expected output.
After every operation:
- Report: **WHAT I TESTED**, **WHAT I FOUND**, **WHAT CHANGED**, **WHAT FAILED**, **WHAT I LEARNED**, **WHAT I WILL DO NEXT**.

---

## 7. Self-Check Gate
Before declaring success, ask:
*"Can I prove this from the available empirical evidence?"*
If NO: **Do not claim success.**
