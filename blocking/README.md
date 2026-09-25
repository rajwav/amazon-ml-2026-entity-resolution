# Production Blocking Module: Champion v2 Surgical

This module implements the official frozen candidate-generation architecture (**Champion v2 Surgical**) for the Amazon ML Challenge 2026 Business Entity Resolution challenge.

---

## 1. Frozen Architecture Status & Benchmark Performance

Champion v2 Surgical is the official frozen blocker. It achieves **99.9855% true-pair recall** (only 5 missed pairs out of 34,481 on the standardized benchmark) while slashing candidate volume by **-65.25%** and median candidates by **-76.76%** relative to Baseline G.

| Metric | Baseline G (Control) | Champion v2 Surgical (FROZEN) | Improvement |
|:---|:---|:---|:---|
| **True-Pair Recall** | 99.9449% | **99.9855%** | +0.0406% (+14 Matches) |
| **Missed True Pairs** | 19 | **5** | **-73.68% Defect Drop** |
| **Average Candidates / S1** | 3,294.6 | **1,145.0** | **-65.25% Candidate Load** |
| **Median Candidates / S1** | 2,621 | **609** | **-76.76% Median Load** |
| **P95 Candidates / S1** | 9,555 | **4,250** | -55.52% Tail Burden |
| **Zero-Candidate Queries** | 0 | **0** | **0.00% Defect Rate** |
| **Multi-Match Recall** | 99.78% | **99.94%** | Near-Perfect Completeness |

---

## 2. Directory Structure

```text
blocking/
├── __init__.py                # Package initialization and exports
├── README.md                  # This runbook and developer documentation
├── requirements.txt           # Pinned dependencies
├── config.json                # Immutable architecture parameters and frequency limits
├── transliteration.py         # Offline Indic script transliteration
├── normalization.py           # Core text normalization and token extraction
├── blocking_core.py           # Inverted hash indexer and candidate retrieval engine
├── run_blocking.py            # Production execution CLI
├── split_queries.py           # Deterministic 4-way S1 query partitioner
├── merge_candidates.py        # Candidate partition merger
├── validate_candidates.py     # Rigorous quality audit and Amazon compliance checker
├── tests/                     # Unit and regression test suite
│   ├── __init__.py
│   ├── test_normalization.py
│   ├── test_partitioning.py
│   └── test_champion_v2_pilot.py
└── documentation/             # 41 publication-grade architectural and historical documents
```

---

## 3. Team Division of Work: 4-Way Distributed Execution

The full test query set ($S1$) contains **1,732,544 business records**.
To execute candidate generation efficiently without single-machine bottlenecks, $S1$ is split into 4 deterministic, mutually exclusive partitions:

| Worker | Assigned S1 Partition | S1 Row Count | Target Datasets (Full) | Output Candidate File |
|:---|:---|:---|:---|:---|
| **Raj** | `partitions/test_s1_part0.tsv` | 432,472 (24.96%) | Complete `test_source2.tsv` + `test_source3.tsv` | `partitions/candidate_pairs_part0.tsv` |
| **Banamudra** | `partitions/test_s1_part1.tsv` | 433,785 (25.04%) | Complete `test_source2.tsv` + `test_source3.tsv` | `partitions/candidate_pairs_part1.tsv` |
| **Shristi** | `partitions/test_s1_part2.tsv` | 433,233 (25.01%) | Complete `test_source2.tsv` + `test_source3.tsv` | `partitions/candidate_pairs_part2.tsv` |
| **Abhijeet** | `partitions/test_s1_part3.tsv` | 433,054 (25.00%) | Complete `test_source2.tsv` + `test_source3.tsv` | `partitions/candidate_pairs_part3.tsv` |

*Note: S2 and S3 are NEVER split. Every worker indexes the complete target corpus ($9,969,589$ records).*

---

## 4. Execution Commands for Each Team Member

### 4.1 Step 1: Pre-build Target Index (Optional Speedup)
To avoid having all 4 members rebuild the 10M target index independently, one member can build and serialize the index once:
```bash
python -m blocking.run_blocking \
    --s2 student_resource/dataset/test/test_source2.tsv \
    --s3 student_resource/dataset/test/test_source3.tsv \
    --save-index target_index.pkl
```

### 4.2 Step 2: Individual Worker Execution Commands

#### Raj:
```bash
python -m blocking.run_blocking \
    --s1 partitions/test_s1_part0.tsv \
    --s2 student_resource/dataset/test/test_source2.tsv \
    --s3 student_resource/dataset/test/test_source3.tsv \
    --output partitions/candidate_pairs_part0.tsv
```
*(Or with pre-built index: `--s1 partitions/test_s1_part0.tsv --index target_index.pkl --output partitions/candidate_pairs_part0.tsv`)*

#### Banamudra:
```bash
python -m blocking.run_blocking \
    --s1 partitions/test_s1_part1.tsv \
    --s2 student_resource/dataset/test/test_source2.tsv \
    --s3 student_resource/dataset/test/test_source3.tsv \
    --output partitions/candidate_pairs_part1.tsv
```

#### Shristi:
```bash
python -m blocking.run_blocking \
    --s1 partitions/test_s1_part2.tsv \
    --s2 student_resource/dataset/test/test_source2.tsv \
    --s3 student_resource/dataset/test/test_source3.tsv \
    --output partitions/candidate_pairs_part2.tsv
```

#### Abhijeet:
```bash
python -m blocking.run_blocking \
    --s1 partitions/test_s1_part3.tsv \
    --s2 student_resource/dataset/test/test_source2.tsv \
    --s3 student_resource/dataset/test/test_source3.tsv \
    --output partitions/candidate_pairs_part3.tsv
```

---

## 5. Merging & Final Candidate Validation

Once all 4 partition files are generated, Raj merges them:
```bash
python -m blocking.merge_candidates \
    --parts partitions/candidate_pairs_part0.tsv \
            partitions/candidate_pairs_part1.tsv \
            partitions/candidate_pairs_part2.tsv \
            partitions/candidate_pairs_part3.tsv \
    --order-reference student_resource/dataset/test/test_source1.tsv \
    --output candidate_pairs.tsv
```

Then, Abhijeet validates the merged file against all Amazon competition requirements:
```bash
python -m blocking.validate_candidates \
    --candidates candidate_pairs.tsv \
    --test-dir student_resource/dataset/test \
    --report-output validation_report.md
```

Also verify directly using Amazon's official submission validator:
```bash
python3 student_resource/utils/validate_submission.py \
    --matching candidate_pairs.tsv \
    --test-dir student_resource/dataset/test
```
*(Passing candidate_pairs.tsv as `--matching` tests that all 1,732,544 rows exist and IDs are valid)*

---

## 6. Running Test Suite

Verify local environment integrity before running:
```bash
PYTHONPATH=. pytest blocking/tests/
```
All 12 tests (normalization, Indic transliteration, partitioning, and pilot 99.9855% regression) must pass.
