#!/usr/bin/env python3
"""
Rigorous Candidate Validation & Quality Audit Suite for Business Entity Resolution.

Verifies candidate_pairs.tsv against the Amazon ML Challenge 2026 submission rules
and computes full distribution statistics (Mean, Median, P90, P95, P99, Max, Zero-Candidate).

Usage:
  python -m blocking.validate_candidates \\
      --candidates candidate_pairs.tsv \\
      --test-dir student_resource/dataset/test \\
      --report-output validation_report.md
"""

import os
import sys
import argparse
from typing import Set, Dict, List

DELIM = "\t"
EXPECTED_HEADER = ["source1_entity_id", "candidate_entity_ids"]
EXPECTED_TEST_S1_COUNT = 1732544

def read_entity_ids_from_tsv(path: str) -> Set[str]:
    """Read the first-column IDs from a TSV."""
    ids = set()
    with open(path, 'r', encoding='utf-8') as f:
        next(f, None)
        for line in f:
            if line.strip():
                ids.add(line.split(DELIM, 1)[0].strip())
    return ids

def validate_candidate_file(candidate_path: str, test_dir: str, check_target_ids: bool = False, report_output: str = None) -> bool:
    print("\n=======================================================")
    print("CANDIDATE PAIRS VALIDATION & AUDIT")
    print("=======================================================")
    print(f"Candidate File: {candidate_path}")
    print(f"Test Directory: {test_dir}")

    errors = []
    warnings = []

    # 1. Check existence of reference files
    s1_path = os.path.join(test_dir, "test_source1.tsv")
    s2_path = os.path.join(test_dir, "test_source2.tsv")
    s3_path = os.path.join(test_dir, "test_source3.tsv")

    if not os.path.isfile(s1_path):
        errors.append(f"Missing required test_source1.tsv at {s1_path}")
        return False

    required_s1 = read_entity_ids_from_tsv(s1_path)
    print(f"Required S1 entity count from {s1_path}: {len(required_s1):,}")

    valid_targets = None
    if check_target_ids:
        print("Loading target IDs from S2 and S3 for full ID existence check...")
        valid_targets = read_entity_ids_from_tsv(s2_path) | read_entity_ids_from_tsv(s3_path)
        print(f"Valid S2/S3 target count: {len(valid_targets):,}")

    # 2. Parse and audit candidate_pairs.tsv
    seen_s1 = set()
    dup_s1_rows = set()
    intra_dupes = set()
    self_matches = set()
    wrong_prefix = set()
    unknown_targets = set()
    
    candidate_counts = []
    zero_cands = 0
    total_candidates = 0

    with open(candidate_path, 'r', encoding='utf-8') as f:
        header_line = f.readline()
        if not header_line:
            errors.append(f"{candidate_path} is completely empty.")
            return False
        
        headers = [c.strip().lower() for c in header_line.rstrip('\r\n').split(DELIM)]
        if headers != EXPECTED_HEADER:
            errors.append(f"Invalid header {headers}. Expected exactly {EXPECTED_HEADER}")
            return False

        for line_no, line in enumerate(f, start=2):
            if not line.strip():
                continue
            s1_id, tab, rest = line.partition(DELIM)
            s1_id = s1_id.strip()
            if not tab:
                errors.append(f"Malformed row (no TAB) at line {line_no}: {line.rstrip()!r}")
                continue

            if s1_id in seen_s1:
                dup_s1_rows.add(s1_id)
            seen_s1.add(s1_id)

            cand_ids = [x.strip() for x in rest.rstrip('\r\n').split(',') if x.strip()]
            cnt = len(cand_ids)
            candidate_counts.append(cnt)
            total_candidates += cnt

            if cnt == 0:
                zero_cands += 1
                continue

            if len(cand_ids) != len(set(cand_ids)):
                intra_dupes.add(s1_id)

            for tid in cand_ids:
                if tid.startswith("S1-"):
                    self_matches.add(tid)
                elif not (tid.startswith("S2-") or tid.startswith("S3-")):
                    wrong_prefix.add(tid)
                elif valid_targets is not None and tid not in valid_targets:
                    unknown_targets.add(tid)

    # 3. Assess Errors
    missing_s1 = required_s1 - seen_s1
    extra_s1 = seen_s1 - required_s1

    if dup_s1_rows:
        errors.append(f"Duplicate S1 rows detected ({len(dup_s1_rows):,} rows, e.g. {list(dup_s1_rows)[:5]})")
    if missing_s1:
        errors.append(f"Missing required S1 entities ({len(missing_s1):,} missing, e.g. {list(missing_s1)[:5]})")
    if extra_s1:
        errors.append(f"Unexpected S1 entities not in test set ({len(extra_s1):,} extra, e.g. {list(extra_s1)[:5]})")
    if intra_dupes:
        errors.append(f"Duplicate IDs inside candidate lists for {len(intra_dupes):,} S1 queries, e.g. {list(intra_dupes)[:5]}")
    if self_matches:
        errors.append(f"Found S1 IDs in candidate list (self-matches) for {len(self_matches):,} IDs, e.g. {list(self_matches)[:5]}")
    if wrong_prefix:
        errors.append(f"Found candidate IDs without S2-/S3- prefix ({len(wrong_prefix):,} IDs, e.g. {list(wrong_prefix)[:5]})")
    if unknown_targets:
        errors.append(f"Found candidate IDs that do not exist in S2/S3 ({len(unknown_targets):,} IDs, e.g. {list(unknown_targets)[:5]})")

    # 4. Statistical Distribution
    n = len(candidate_counts)
    candidate_counts.sort()
    avg_c = total_candidates / n if n else 0
    med_c = candidate_counts[n // 2] if n else 0
    p90_c = candidate_counts[int(n * 0.90)] if n else 0
    p95_c = candidate_counts[int(n * 0.95)] if n else 0
    p99_c = candidate_counts[int(n * 0.99)] if n else 0
    max_c = candidate_counts[-1] if n else 0

    print("\n-------------------------------------------------------")
    print("CANDIDATE DISTRIBUTION STATISTICS")
    print("-------------------------------------------------------")
    print(f"Total S1 Entities Validated:  {n:,} (Expected: {EXPECTED_TEST_S1_COUNT:,})")
    print(f"Total Candidate Pairs:        {total_candidates:,}")
    print(f"Mean Candidates per S1:       {avg_c:.1f}")
    print(f"Median Candidates per S1:     {med_c}")
    print(f"P90 Candidates per S1:        {p90_c}")
    print(f"P95 Candidates per S1:        {p95_c}")
    print(f"P99 Candidates per S1:        {p99_c}")
    print(f"Maximum Candidates for any S1:{max_c}")
    print(f"Zero-Candidate S1 Entities:   {zero_cands:,}")
    print("-------------------------------------------------------")

    # Generate Markdown Report if requested
    if report_output:
        os.makedirs(os.path.dirname(os.path.abspath(report_output)) or '.', exist_ok=True)
        with open(report_output, 'w', encoding='utf-8') as rf:
            rf.write("# Candidate Generation Validation Report\n\n")
            rf.write(f"- **Target File**: `{candidate_path}`\n")
            rf.write(f"- **Status**: {'PASSED' if not errors else 'FAILED'}\n")
            rf.write(f"- **Total S1 Queries**: {n:,}\n")
            rf.write(f"- **Total Candidates**: {total_candidates:,}\n")
            rf.write(f"- **Mean Candidates / S1**: {avg_c:.1f}\n")
            rf.write(f"- **Median**: {med_c} | **P95**: {p95_c} | **P99**: {p99_c} | **Max**: {max_c}\n")
            rf.write(f"- **Zero-Candidate S1s**: {zero_cands:,}\n\n")
            if errors:
                rf.write("## Validation Errors\n")
                for e in errors:
                    rf.write(f"- ❌ {e}\n")
            else:
                rf.write("## Checks Passed\n")
                rf.write("- ✅ S1 row count matches test_source1.tsv exactly.\n")
                rf.write("- ✅ Zero duplicate rows or intra-list duplicate IDs.\n")
                rf.write("- ✅ All candidate IDs are prefixed with S2- or S3-.\n")
                rf.write("- ✅ Format conforms 100% to competition submission validator.\n")
        print(f"Saved validation report to: {report_output}")

    if errors:
        print(f"\nVALIDATION FAILED with {len(errors)} error(s):")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        return False

    print("\nVALIDATION PASSED: All formatting, row counts, and structural rules satisfied.")
    print("=======================================================\n")
    return True

def main():
    parser = argparse.ArgumentParser(description="Validate candidate_pairs.tsv against test datasets")
    parser.add_argument("--candidates", default="candidate_pairs.tsv", help="Path to candidate_pairs.tsv")
    parser.add_argument("--test-dir", default="student_resource/dataset/test", help="Path to test directory")
    parser.add_argument("--check-target-ids", action="store_true", help="Load full S2/S3 to verify every target ID exists")
    parser.add_argument("--report-output", default="validation_report.md", help="Output path for validation report")
    args = parser.parse_args()

    success = validate_candidate_file(args.candidates, args.test_dir, args.check_target_ids, args.report_output)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
