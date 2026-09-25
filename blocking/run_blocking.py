#!/usr/bin/env python3
"""
Production CLI Runner for Frozen Champion v2 Surgical Candidate Generation.

Usage:
  # Option A: Run directly on raw S1, S2, S3:
  python -m blocking.run_blocking \\
      --s1 student_resource/dataset/test/test_source1.tsv \\
      --s2 student_resource/dataset/test/test_source2.tsv \\
      --s3 student_resource/dataset/test/test_source3.tsv \\
      --output candidate_pairs.tsv

  # Option B: Build and save target index once:
  python -m blocking.run_blocking \\
      --s2 student_resource/dataset/test/test_source2.tsv \\
      --s3 student_resource/dataset/test/test_source3.tsv \\
      --save-index target_index.pkl

  # Option C: Run partition worker using pre-built target index:
  python -m blocking.run_blocking \\
      --s1 partitions/test_s1_part0.tsv \\
      --index target_index.pkl \\
      --output partitions/candidate_pairs_part0.tsv
"""

import os
import sys
import time
import argparse
from typing import Dict, Tuple

sys.path.append('.')
from blocking.blocking_core import ChampionV2Blocker

def load_targets(s2_path: str, s3_path: str) -> Dict[str, Tuple[str, str, str]]:
    """Load S2 and S3 target records into memory dictionary."""
    targets = {}
    for p in [s2_path, s3_path]:
        if not p or not os.path.isfile(p):
            continue
        print(f"Loading targets from {p}...")
        with open(p, 'r', encoding='utf-8') as f:
            header = next(f, None)
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                if len(parts) >= 4:
                    targets[parts[0]] = (parts[1], parts[2], parts[3])
                elif len(parts) == 3:
                    targets[parts[0]] = (parts[1], parts[2], '')
    print(f"Total unique target records loaded: {len(targets):,}")
    return targets

def stream_s1_records(s1_path: str):
    """Generator yielding (entity_id, business_name, business_address, country)."""
    with open(s1_path, 'r', encoding='utf-8') as f:
        header = next(f, None)
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            while len(parts) < 4:
                parts.append('')
            yield parts[0], parts[1], parts[2], parts[3]

def main():
    parser = argparse.ArgumentParser(description="Run Frozen Champion v2 Surgical Candidate Generation")
    parser.add_argument("--s1", default=None, help="Path to S1 queries TSV")
    parser.add_argument("--s2", default=None, help="Path to S2 targets TSV")
    parser.add_argument("--s3", default=None, help="Path to S3 targets TSV")
    parser.add_argument("--index", default=None, help="Path to pre-built target index file (.pkl)")
    parser.add_argument("--save-index", default=None, help="Path to save built index (.pkl)")
    parser.add_argument("--output", default="candidate_pairs.tsv", help="Path to output candidate pairs TSV")
    parser.add_argument("--batch-size", type=int, default=10000, help="Query progress report interval")
    parser.add_argument("--pairwise-output", default=None, help="Optional path to output pairwise candidates TSV")
    args = parser.parse_args()

    blocker = ChampionV2Blocker()

    # 1. Load or build target index
    if args.index and os.path.isfile(args.index):
        print(f"Loading pre-built target index from {args.index}...")
        t0 = time.time()
        blocker.load_index(args.index)
        print(f"Loaded index ({blocker.target_count:,} targets) in {time.time()-t0:.2f}s")
    elif args.s2 and args.s3:
        target_records = load_targets(args.s2, args.s3)
        print("Building Champion v2 inverted indexes...")
        t0 = time.time()
        blocker.build_index(target_records)
        print(f"Built target indexes in {time.time()-t0:.2f}s")
        if args.save_index:
            print(f"Saving serialized index to {args.save_index}...")
            blocker.save_index(args.save_index)
            print(f"Saved index successfully.")
    else:
        if not args.s1 and args.save_index:
            print("Target index saved successfully.")
            return 0
        parser.error("Either --index OR both --s2 and --s3 must be provided.")

    if not args.s1:
        if args.save_index:
            print("Index construction completed. No S1 query file specified.")
            return 0
        parser.error("--s1 query file is required to generate candidate pairs.")

    # 2. Execute Candidate Generation
    print(f"Processing S1 queries from {args.s1}...")
    t_start = time.time()
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or '.', exist_ok=True)
    
    pairwise_f = None
    if args.pairwise_output:
        os.makedirs(os.path.dirname(os.path.abspath(args.pairwise_output)) or '.', exist_ok=True)
        pairwise_f = open(args.pairwise_output, 'w', encoding='utf-8')
        pairwise_f.write("source1_entity_id\ttarget_entity_id\n")

    total_s1 = 0
    total_candidates = 0
    zero_cands = 0

    with open(args.output, 'w', encoding='utf-8') as out_f:
        out_f.write("source1_entity_id\tcandidate_entity_ids\n")
        
        for s1_id, bname, baddr, country in stream_s1_records(args.s1):
            total_s1 += 1
            feat = blocker.extract_features(s1_id, bname, baddr, country)
            cands = blocker.query_single(feat)
            
            cand_count = len(cands)
            total_candidates += cand_count
            if cand_count == 0:
                zero_cands += 1
                out_f.write(f"{s1_id}\t\n")
            else:
                cands_sorted = sorted(list(cands))
                out_f.write(f"{s1_id}\t{','.join(cands_sorted)}\n")
                if pairwise_f:
                    for cid in cands_sorted:
                        pairwise_f.write(f"{s1_id}\t{cid}\n")
                        
            if total_s1 % args.batch_size == 0:
                rate = total_s1 / (time.time() - t_start)
                print(f"Processed {total_s1:,} queries | Total cands: {total_candidates:,} | Rate: {rate:,.0f} q/s")

    if pairwise_f:
        pairwise_f.close()

    elapsed = time.time() - t_start
    avg_c = total_candidates / total_s1 if total_s1 else 0
    print("\n=======================================================")
    print("BLOCKING EXECUTION SUMMARY")
    print("=======================================================")
    print(f"Total S1 Queries Processed: {total_s1:,}")
    print(f"Total Candidate Pairs:      {total_candidates:,}")
    print(f"Average Candidates / S1:    {avg_c:.1f}")
    print(f"Zero-Candidate Queries:     {zero_cands:,}")
    print(f"Execution Time:             {elapsed:.2f}s ({total_s1/elapsed:,.0f} queries/s)")
    print(f"Output File:                {args.output}")
    print("=======================================================\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
