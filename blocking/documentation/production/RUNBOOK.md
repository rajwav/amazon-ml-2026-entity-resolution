# Production Candidate Generation Runbook

This runbook provides step-by-step instructions for operators executing Champion v2 candidate generation on developer machines or cloud compute instances.

---

## 1. Environment & Pre-requisites

### 1.1 Python Environment Setup
```bash
# Verify Python version (>= 3.10)
python3 --version

# Activate project virtual environment
source .venv/bin/activate

# Install required dependencies
pip install indic-transliteration pyarrow pandas polars psutil
```

### 1.2 Data Availability Check
Verify the presence of source dataset files:
- Target files: `data/raw/` containing corpus records.
- Query files: `data/raw/` containing $S1$ records.
- Ground truth: `data/raw/` or `experiments/data/` for validation.

---

## 2. Step-by-Step Execution Sequence

### Step 1: Pre-Flight Integrity Check
Run the pre-flight verification script to ensure all index schemas and Indic transliteration libraries are functional:
```bash
python3 -c "
import indic_transliteration
from indic_transliteration import sansscript
res = sansscript.transliterate('अल एस्टेट', sansscript.DEVANAGARI, sansscript.ITRANS)
assert 'al' in res.lower()
print('Pre-flight check passed successfully.')
"
```

### Step 2: Execute Candidate Generation Benchmark Verification
Before executing full-scale runs, execute the verified 10k benchmark to confirm zero regression:
```bash
python3 experiments/blocking/final_tail_investigation.py
```
**Verification Gate**:
- Confirm True-Pair Recall is exactly **99.9855%** (34,476 recalled).
- Confirm Missed Pairs count is exactly **5**.
- Confirm Average Candidates is **1,145.0**.

### Step 3: Launch Partitioned Production Run
Execute candidate generation across the production corpus:
```bash
# Run India Partition
python3 -m blocking.src.generate_candidates \
    --country IN \
    --input_queries data/processed/s1_queries_IN.parquet \
    --input_targets data/processed/targets_IN.parquet \
    --output_dir data/candidates/IN/ \
    --batch_size 10000 \
    --format parquet

# Run United States Partition
python3 -m blocking.src.generate_candidates \
    --country US \
    --input_queries data/processed/s1_queries_US.parquet \
    --input_targets data/processed/targets_US.parquet \
    --output_dir data/candidates/US/ \
    --batch_size 10000 \
    --format parquet
```

---

## 3. Monitoring & Telemetry

During execution, monitor system resources in a separate terminal:
```bash
# Monitor Memory and CPU
top -pid $(pgrep -f generate_candidates)

# Check Output File Generation
ls -lh data/candidates/IN/
```

### Health Indicators:
- **Memory Consumption**: Should plateau around 1.2 GB for India and 2.8 GB for US. If memory exceeds 4.5 GB, reduce `--batch_size` from 10,000 to 5,000.
- **Query Throughput**: Target rate is $1,500\text{ to }2,000\text{ queries/sec}$. If throughput drops below 500 queries/sec, verify disk write speeds.

---

## 4. Troubleshooting & Recovery Procedures

### Issue 1: `MemoryError` or Out-of-Memory (OOM) Termination
- **Root Cause**: Batch size too large or candidate sets being stored in memory.
- **Recovery**:
  1. Ensure streaming output is active (no global list append).
  2. Reduce `--batch_size 2500`.
  3. Ensure country partitions run sequentially, not in parallel on memory-constrained hardware.

### Issue 2: Script Hanging or Slow I/O
- **Root Cause**: Writing uncompressed TSV files to slow mechanical disks.
- **Recovery**:
  1. Switch output format to compressed Parquet with Snappy compression (`--format parquet`).
  2. Ensure write path is on an NVMe SSD drive.

### Issue 3: Missing Indic Characters Warning
- **Root Cause**: Corrupted unicode codepoints in raw India text.
- **Recovery**: The normalization preprocessor automatically catches and strips non-printable control characters via `re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)`.
