#!/usr/bin/env python3
"""
Production Candidate Assembly and Multi-Country Merger.
Amazon ML Challenge 2026.

Assembles candidate_pairs.tsv from country candidate files (India, France, US),
ensuring 100% of S1 test queries are present in their original sequence.
"""

import os
import sys
import argparse
from typing import Dict, List, Set

def assemble_candidate_file(
    s1_path: str,
    country_candidate_files: List[str],
    output_path: str
):
    print("="*60)
    print("ASSEMBLING FINAL CANDIDATE PAIRS")
    print("="*60)
    print(f"S1 Reference:          {s1_path}")
    print(f"Country Shards:        {country_candidate_files}")
    print(f"Final Output Path:     {output_path}")
    
    # 1. Ingest candidate files from available countries
    cands_by_s1: Dict[str, str] = {}
    total_pairs = 0
    
    for fpath in country_candidate_files:
        if not fpath or not os.path.exists(fpath):
            print(f"Notice: Country shard {fpath} not found or not provided, skipping.")
            continue
            
        print(f"Ingesting country shard: {fpath} ({os.path.getsize(fpath)/(1024*1024):.1f} MB)...")
        file_queries = 0
        file_pairs = 0
        with open(fpath, 'r', encoding='utf-8') as f:
            header = f.readline()
            for line in f:
                if not line.strip():
                    continue
                s1_id, tab, rest = line.partition('\t')
                s1_id = s1_id.strip()
                cands_str = rest.rstrip('\r\n')
                
                if cands_str:
                    cands = cands_str.split(',')
                    # Deduplicate while preserving order
                    deduped = []
                    seen = set()
                    for c in cands:
                        c = c.strip()
                        if c and c not in seen:
                            seen.add(c)
                            deduped.append(c)
                    cleaned_cands = ','.join(deduped)
                    file_pairs += len(deduped)
                else:
                    cleaned_cands = ""
                    
                cands_by_s1[s1_id] = cleaned_cands
                file_queries += 1
                
        print(f"  Loaded {file_queries:,} queries with {file_pairs:,} candidates from {fpath}")
        total_pairs += file_pairs
        
    print(f"\nTotal queries with candidate entries: {len(cands_by_s1):,}")
    print(f"Total candidate pairs:               {total_pairs:,}")
    
    # 2. Stream through test S1 in exact reference sequence
    print(f"\nWriting final candidate file matching exact sequence of {s1_path}...")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)
    
    written_s1 = 0
    zero_cand_s1 = 0
    with open(output_path, 'w', encoding='utf-8') as out_f:
        out_f.write("source1_entity_id\tcandidate_entity_ids\n")
        with open(s1_path, 'r', encoding='utf-8') as s1_f:
            next(s1_f) # Skip header
            for line in s1_f:
                if not line.strip():
                    continue
                s1_id = line.split('\t', 1)[0].strip()
                cands = cands_by_s1.get(s1_id, "")
                if not cands:
                    zero_cand_s1 += 1
                out_f.write(f"{s1_id}\t{cands}\n")
                written_s1 += 1
                
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    avg_cands = total_pairs / written_s1 if written_s1 else 0
    print("\n" + "="*60)
    print("CANDIDATE PAIRS ASSEMBLY COMPLETE")
    print("="*60)
    print(f"Total S1 Queries Written: {written_s1:,}")
    print(f"Total Candidate Pairs:    {total_pairs:,}")
    print(f"Average Candidates / S1:  {avg_cands:.2f}")
    print(f"Zero-Candidate Queries:   {zero_cand_s1:,}")
    print(f"Output File:              {output_path} ({file_size_mb:.2f} MB)")
    print("="*60)
    return output_path

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Assemble candidate_pairs.tsv from country shards")
    parser.add_argument("--s1", default="student_resource/dataset/test/test_source1.tsv")
    parser.add_argument("--shards", nargs='+', required=True, help="List of country candidate TSV files")
    parser.add_argument("--output", default="candidate_pairs.tsv")
    args = parser.parse_args()
    
    assemble_candidate_file(args.s1, args.shards, args.output)
