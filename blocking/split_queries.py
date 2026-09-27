#!/usr/bin/env python3
"""
Deterministic S1 Query Partitioner for Distributed Team Execution.

Partitions the complete test S1 dataset (1,732,544 records) into N deterministic partitions
(default 4) for parallel execution across distributed workers/processes.

Usage:
  python -m blocking.split_queries \\
      --input student_resource/dataset/test/test_source1.tsv \\
      --output-dir partitions/ \\
      --num-partitions 4 \\
      --method hash
"""

import os
import sys
import hashlib
import argparse
from typing import List

def get_hash_partition(entity_id: str, num_partitions: int) -> int:
    """Deterministic cryptographic hash partition."""
    h = int(hashlib.md5(entity_id.strip().encode('utf-8')).hexdigest(), 16)
    return h % num_partitions

def split_s1(input_path: str, output_dir: str, num_partitions: int = 4, method: str = 'hash') -> List[str]:
    """
    Split S1 dataset into deterministic partition TSVs with headers.
    Returns list of generated file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    out_files = [os.path.join(output_dir, f"test_s1_part{i}.tsv") for i in range(num_partitions)]
    writers = [open(p, 'w', encoding='utf-8') for p in out_files]

    total_rows = 0
    partition_counts = [0] * num_partitions
    seen_ids = [set() for _ in range(num_partitions)]

    with open(input_path, 'r', encoding='utf-8') as f:
        header = f.readline()
        for w in writers:
            w.write(header)

        if method == 'contiguous':
            # Count lines first for contiguous split
            lines = f.readlines()
            total_lines = len(lines)
            chunk_size = (total_lines + num_partitions - 1) // num_partitions
            for i, line in enumerate(lines):
                part = min(i // chunk_size, num_partitions - 1)
                writers[part].write(line)
                eid = line.split('\t', 1)[0].strip()
                seen_ids[part].add(eid)
                partition_counts[part] += 1
                total_rows += 1
        else:
            # Hash-based partitioning (default)
            for line in f:
                if not line.strip():
                    continue
                eid = line.split('\t', 1)[0].strip()
                part = get_hash_partition(eid, num_partitions)
                writers[part].write(line)
                seen_ids[part].add(eid)
                partition_counts[part] += 1
                total_rows += 1

    for w in writers:
        w.close()

    # Validation Checks
    print("\n=======================================================")
    print("DETERMINISTIC S1 PARTITIONING SUMMARY")
    print("=======================================================")
    print(f"Source S1 Dataset:    {input_path}")
    print(f"Total S1 Rows Split:  {total_rows:,}")
    print(f"Partition Method:     {method}")
    print(f"Partitions Created:   {num_partitions}")
    print("-------------------------------------------------------")
    for i in range(num_partitions):
        pct = (partition_counts[i] / total_rows * 100) if total_rows else 0
        print(f"Part {i}: {partition_counts[i]:,} rows ({pct:.2f}%) -> {out_files[i]}")

    # Check non-overlap
    all_seen = set()
    for i in range(num_partitions):
        overlap = all_seen & seen_ids[i]
        assert not overlap, f"Fatal error: Overlap detected in partition {i}: {len(overlap)} IDs!"
        all_seen.update(seen_ids[i])

    assert len(all_seen) == total_rows, f"Fatal error: Union count ({len(all_seen)}) != total ({total_rows})"
    print("-------------------------------------------------------")
    print("Integrity Check: PASSED (100% disjoint, zero duplicate IDs, complete coverage)")
    print("=======================================================\n")
    return out_files

def main():
    parser = argparse.ArgumentParser(description="Deterministically split S1 queries into N partitions")
    parser.add_argument("--input", default="student_resource/dataset/test/test_source1.tsv", help="Path to test_source1.tsv")
    parser.add_argument("--output-dir", default="partitions", help="Output directory for partitioned TSVs")
    parser.add_argument("--num-partitions", type=int, default=4, help="Number of partitions (default: 4)")
    parser.add_argument("--method", choices=['hash', 'contiguous'], default='hash', help="Partition method (default: hash)")
    args = parser.parse_args()

    split_s1(args.input, args.output_dir, args.num_partitions, args.method)

if __name__ == "__main__":
    main()
