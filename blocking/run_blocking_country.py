#!/usr/bin/env python3
"""
Country-Partitioned Runner for Frozen Champion v2 Surgical Candidate Generation.

Guarantees 100% mathematical and algorithmic equivalence to Champion v2 Surgical Blocking
while bounding physical RAM to <3.5 GB by processing one country partition at a time.

Key Invariants & Optimizations:
1. Strict intra-country candidate generation (no cross-country false positives).
2. Global document frequency counts computed over the complete target corpus (S2 + S3)
   for the active country before index construction.
3. Memory safety: raw targets loaded per country (~600MB for France, ~1.6GB for US, ~2GB for India).
   Intermediate 10M feature dicts eliminated.
4. Persistent country index caching: serialized country index (.pkl) can be saved/loaded,
   allowing instant benchmarking across query scales without rebuilding.
5. Strict output sequence: writes candidate pairs in exact input S1 sequence.

Usage:
  python -m blocking.run_blocking_country \\
      --s1 partitions/test_s1_part3.tsv \\
      --s2 student_resource/dataset/test/test_source2.tsv \\
      --s3 student_resource/dataset/test/test_source3.tsv \\
      --output partitions/benchmark_100.tsv \\
      --limit-s1 100
"""

import os
import sys
import gc
import time
import argparse
import collections
from typing import Dict, List, Set, Tuple, Optional

import psutil

sys.path.append('.')
from blocking.blocking_core import ChampionV2Blocker

process = psutil.Process(os.getpid())

def get_ram_mb() -> float:
    """Return current process Resident Set Size (RSS) in MB."""
    return process.memory_info().rss / (1024 * 1024)

def get_vmem_gb() -> float:
    """Return current process Virtual Memory size in GB."""
    return process.memory_info().vms / (1024 * 1024 * 1024)

def load_s1_queries(s1_path: str, limit: Optional[int] = None):
    """
    Load S1 query records up to optional limit.
    Returns:
      ordered_ids: List of S1 IDs in original sequence
      queries_by_country: Dict[country, List[(s1_id, bname, baddr, country)]]
    """
    ordered_ids = []
    queries_by_country = collections.defaultdict(list)
    
    with open(s1_path, 'r', encoding='utf-8') as f:
        header = next(f, None)
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            while len(parts) < 4:
                parts.append('')
            eid = parts[0].strip()
            c = parts[3].strip()
            ordered_ids.append(eid)
            queries_by_country[c].append((eid, parts[1], parts[2], c))
            if limit is not None and len(ordered_ids) >= limit:
                break
                
    return ordered_ids, queries_by_country

def load_country_raw_targets(s2_path: str, s3_path: str, country: str) -> List[Tuple[str, str, str]]:
    """
    Load raw (entity_id, business_name, business_address) tuples for a single country.
    Keeps memory minimal by storing only 3-tuples of strings.
    """
    t0 = time.time()
    targets = []
    for path in [s2_path, s3_path]:
        if not path or not os.path.isfile(path):
            continue
        with open(path, 'r', encoding='utf-8') as f:
            header = next(f, None)
            for line in f:
                parts = line.rstrip('\r\n').split('\t')
                while len(parts) < 4:
                    parts.append('')
                if parts[3].strip() == country:
                    targets.append((parts[0].strip(), parts[1], parts[2]))
    elapsed = time.time() - t0
    print(f"  [Load Targets] Loaded {len(targets):,} [{country}] raw targets in {elapsed:.2f}s | RAM: {get_ram_mb():.1f} MB", flush=True)
    return targets

def build_country_index_from_targets(
    blocker: ChampionV2Blocker, 
    country: str, 
    targets: List[Tuple[str, str, str]]
):
    """
    Build complete Champion v2 index for a single country in two memory-efficient passes:
    Pass 1: Computes global document frequency tables.
    Pass 2: Populates inverted indexes with frequency guardrails.
    """
    t0 = time.time()
    c = country
    blocker.target_count = len(targets)

    # Pass 1: Global Frequencies
    print(f"  [Pass 1] Computing global document frequencies for {len(targets):,} [{country}] targets...", flush=True)
    t_p1 = time.time()
    for eid, bname, baddr in targets:
        feat = blocker.extract_features(eid, bname, baddr, c)
        for loc in feat['loc_tokens']:
            blocker.freq_loc_token[c][loc] += 1
        for t in feat['tokens_2char']:
            blocker.freq_2char_token[c][t] += 1
        if feat['consonant_tri']:
            blocker.freq_cons_tri[c][feat['consonant_tri']] += 1
        if feat['state'] and feat['digits_enriched']:
            for d in feat['digits_enriched']:
                blocker.freq_state_dig[c][(feat['state'], d)] += 1
        for u in feat['units']:
            blocker.freq_unit[c][u] += 1
    print(f"  [Pass 1 Complete] Frequencies computed in {time.time()-t_p1:.2f}s | RAM: {get_ram_mb():.1f} MB", flush=True)

    # Pass 2: Inverted Indexes
    print(f"  [Pass 2] Populating inverted indexes with exact Champion v2 frequency guardrails...", flush=True)
    t_p2 = time.time()
    for eid, bname, baddr in targets:
        feat = blocker.extract_features(eid, bname, baddr, c)
        
        if feat['core']:
            blocker.idx_exact[c][feat['core']].append(eid)
            blocker.idx_B[c][feat['core']].append(eid)
            
        for tok in feat['tokens']:
            blocker.idx_C[c][tok].append(eid)
            for loc in feat['loc_tokens']:
                blocker.idx_tok_loc[c][(tok, loc)].append(eid)
            for dig in feat['digits']:
                blocker.idx_tok_dig[c][(tok, dig)].append(eid)
                
        if feat['prefix4']:
            blocker.idx_D[c][feat['prefix4']].append(eid)
            for loc in feat['loc_tokens']:
                blocker.idx_pref_loc[c][(feat['prefix4'], loc)].append(eid)
            for dig in feat['digits']:
                blocker.idx_pref_dig[c][(feat['prefix4'], dig)].append(eid)
                
        for dig in feat['digits']:
            blocker.idx_E[c][dig].append(eid)
            for loc in feat['loc_tokens']:
                blocker.idx_dig_loc[c][(dig, loc)].append(eid)

        # Dynamic Top-2 Location Tokens
        locs = feat['loc_tokens']
        if locs:
            lsorted = sorted(locs, key=lambda l: (blocker.freq_loc_token[c][l], len(l)))
            for loc in lsorted[:2]:
                blocker.idx_F_top2[c][loc].append(eid)

        # Surgical Tail Channels
        for t2 in feat['tokens_2char']:
            if blocker.freq_2char_token[c][t2] <= 200:
                blocker.idx_2char[c][t2].append(eid)
        if len(feat['nospace_core']) >= 4:
            blocker.idx_nospace[c][feat['nospace_core']].append(eid)
        if len(feat['domain_stem']) >= 4:
            blocker.idx_nospace[c][feat['domain_stem']].append(eid)
        if len(feat['core_collapsed']) >= 4:
            blocker.idx_collapsed[c][feat['core_collapsed']].append(eid)
        for ed in feat['digits_enriched']:
            for loc in feat['loc_tokens']:
                blocker.idx_dig_loc_en[c][(ed, loc)].append(eid)

        # Micro-signals
        if feat['consonant_tri'] and blocker.freq_cons_tri[c][feat['consonant_tri']] <= 50:
            blocker.idx_cons_tri[c][feat['consonant_tri']].append(eid)
        if feat['state']:
            for d in feat['digits_enriched']:
                if blocker.freq_state_dig[c][(feat['state'], d)] <= 50:
                    blocker.idx_state_dig[c][(feat['state'], d)].append(eid)
        for u in feat['units']:
            if blocker.freq_unit[c][u] <= 100:
                blocker.idx_unit[c][u].append(eid)

    blocker.is_indexed = True
    print(f"  [Pass 2 Complete] Inverted indexes built in {time.time()-t_p2:.2f}s | Total Indexing: {time.time()-t0:.2f}s | RAM: {get_ram_mb():.1f} MB", flush=True)

def run_country_blocking(
    s1_path: str,
    s2_path: str,
    s3_path: str,
    output_path: str,
    limit_s1: Optional[int] = None,
    target_countries: Optional[List[str]] = None,
    index_cache_dir: Optional[str] = "partitions/indexes",
    batch_size: int = 10000
) -> dict:
    t_global_start = time.time()
    print("\n=======================================================", flush=True)
    print("COUNTRY-PARTITIONED CHAMPION V2 SURGICAL BLOCKING", flush=True)
    print("=======================================================", flush=True)
    print(f"Query Source (S1):     {s1_path}", flush=True)
    print(f"Target Source (S2):    {s2_path}", flush=True)
    print(f"Target Source (S3):    {s3_path}", flush=True)
    print(f"Output Destination:    {output_path}", flush=True)
    print(f"Query Limit:           {limit_s1 if limit_s1 is not None else 'FULL'}", flush=True)
    print(f"Initial Process RAM:   {get_ram_mb():.1f} MB (Virtual: {get_vmem_gb():.2f} GB)", flush=True)
    print("-------------------------------------------------------", flush=True)

    # 1. Load S1 queries and partition by country
    print("Scanning S1 query workload...", flush=True)
    t_s1_start = time.time()
    ordered_ids, queries_by_country = load_s1_queries(s1_path, limit=limit_s1)
    print(f"Loaded {len(ordered_ids):,} S1 queries in {time.time()-t_s1_start:.2f}s across {len(queries_by_country)} countries:", flush=True)
    for c, qlist in sorted(queries_by_country.items()):
        print(f"  - {c}: {len(qlist):,} queries", flush=True)
    print("-------------------------------------------------------", flush=True)

    if index_cache_dir:
        os.makedirs(index_cache_dir, exist_ok=True)

    countries_to_run = target_countries or sorted(queries_by_country.keys())
    candidate_results: Dict[str, str] = {}
    total_candidates_all = 0
    zero_candidates_all = 0
    country_metrics = {}
    peak_ram_overall = get_ram_mb()
    peak_vmem_overall = get_vmem_gb()

    # 2. Process Country-by-Country sequentially
    for country in countries_to_run:
        country_queries = queries_by_country.get(country, [])
        if not country_queries:
            print(f"Skipping [{country}]: 0 queries in active batch.", flush=True)
            continue

        print(f"\n>>> PROCESSING PARTITION: [{country}] ({len(country_queries):,} queries)", flush=True)
        t_country_start = time.time()
        blocker = ChampionV2Blocker()

        index_file = os.path.join(index_cache_dir, f"index_{country}.pkl") if index_cache_dir else None
        
        # Check for pre-built serialized index
        if index_file and os.path.isfile(index_file):
            print(f"  [Index Cache] Found cached index: {index_file}. Loading into memory...", flush=True)
            t_load = time.time()
            blocker.load_index(index_file)
            print(f"  [Index Cache] Loaded {blocker.target_count:,} targets in {time.time()-t_load:.2f}s | RAM: {get_ram_mb():.1f} MB", flush=True)
        else:
            # Build index from scratch
            raw_targets = load_country_raw_targets(s2_path, s3_path, country)
            build_country_index_from_targets(blocker, country, raw_targets)
            
            # Free raw targets list from RAM immediately
            del raw_targets
            gc.collect()
            print(f"  [Memory Optimization] Raw targets list freed. Index RAM: {get_ram_mb():.1f} MB", flush=True)
            
            # Optionally cache serialized index
            if index_file:
                print(f"  [Index Cache] Saving serialized index to: {index_file}...", flush=True)
                t_save = time.time()
                blocker.save_index(index_file)
                idx_size_mb = os.path.getsize(index_file) / (1024 * 1024)
                print(f"  [Index Cache] Saved ({idx_size_mb:.1f} MB) in {time.time()-t_save:.2f}s", flush=True)

        ram_after_index = get_ram_mb()
        vmem_after_index = get_vmem_gb()
        peak_ram_overall = max(peak_ram_overall, ram_after_index)
        peak_vmem_overall = max(peak_vmem_overall, vmem_after_index)

        # Query Candidate Generation
        print(f"  [Query Evaluation] Generating candidates for {len(country_queries):,} [{country}] queries...", flush=True)
        t_query_start = time.time()
        c_count = 0
        c_zero = 0
        q_done = 0

        for s1_id, bname, baddr, c_str in country_queries:
            q_done += 1
            feat = blocker.extract_features(s1_id, bname, baddr, c_str)
            cands = blocker.query_single(feat)
            
            cand_len = len(cands)
            c_count += cand_len
            if cand_len == 0:
                c_zero += 1
                candidate_results[s1_id] = ""
            else:
                cands_sorted = sorted(cands)
                candidate_results[s1_id] = ','.join(cands_sorted)

            if q_done % batch_size == 0 or q_done == len(country_queries):
                q_rate = q_done / (time.time() - t_query_start)
                print(f"    Progress: {q_done:,}/{len(country_queries):,} queries | Cands: {c_count:,} | Rate: {q_rate:,.0f} q/s", flush=True)

        query_elapsed = time.time() - t_query_start
        country_elapsed = time.time() - t_country_start
        total_candidates_all += c_count
        zero_candidates_all += c_zero
        
        country_metrics[country] = {
            'targets': blocker.target_count,
            'queries': len(country_queries),
            'candidates': c_count,
            'avg_candidates': c_count / len(country_queries) if country_queries else 0,
            'zero_candidates': c_zero,
            'index_ram_mb': ram_after_index,
            'query_elapsed_s': query_elapsed,
            'total_elapsed_s': country_elapsed,
            'query_rate_qps': len(country_queries) / query_elapsed if query_elapsed > 0 else 0
        }
        
        print(f"  [Partition Summary] [{country}] Finished in {country_elapsed:.2f}s | Query rate: {len(country_queries)/query_elapsed:,.0f} q/s | Avg cands: {c_count/len(country_queries):.1f}", flush=True)

        # Release country index from memory
        del blocker
        gc.collect()
        ram_after_gc = get_ram_mb()
        print(f"  [GC] Released [{country}] index. Process RAM: {ram_after_gc:.1f} MB", flush=True)

    # 3. Write final candidate output in original S1 sequence
    print("\n-------------------------------------------------------", flush=True)
    print(f"Writing candidate pairs to: {output_path}...", flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or '.', exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("source1_entity_id\tcandidate_entity_ids\n")
        for s1_id in ordered_ids:
            cands_str = candidate_results.get(s1_id, "")
            f.write(f"{s1_id}\t{cands_str}\n")

    total_elapsed = time.time() - t_global_start
    total_queries = len(ordered_ids)
    overall_qps = total_queries / total_elapsed if total_elapsed > 0 else 0
    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    avg_cands_overall = total_candidates_all / total_queries if total_queries else 0

    print("\n=======================================================", flush=True)
    print("EXECUTION TELEMETRY & RESULTS SUMMARY", flush=True)
    print("=======================================================", flush=True)
    print(f"Total S1 Queries Processed: {total_queries:,}", flush=True)
    print(f"Total Candidates Generated: {total_candidates_all:,}", flush=True)
    print(f"Average Candidates / S1:    {avg_cands_overall:.1f}", flush=True)
    print(f"Zero-Candidate Queries:     {zero_candidates_all:,}", flush=True)
    print(f"Total Wall-Clock Time:      {total_elapsed:.2f}s ({overall_qps:,.0f} queries/s)", flush=True)
    print(f"Peak Process RAM (RSS):     {peak_ram_overall:.1f} MB", flush=True)
    print(f"Peak Virtual Memory (VMS):  {peak_vmem_overall:.2f} GB", flush=True)
    print(f"Output File Size:           {file_size_mb:.2f} MB ({output_path})", flush=True)
    print("-------------------------------------------------------", flush=True)
    for c, m in country_metrics.items():
        print(f"Country {c:<8} | Targets: {m['targets']:,} | Queries: {m['queries']:,} | Cands/S1: {m['avg_candidates']:.1f} | QueryRate: {m['query_rate_qps']:,.0f} q/s | RAM: {m['index_ram_mb']:.0f}MB", flush=True)
    print("=======================================================\n", flush=True)

    return {
        'total_queries': total_queries,
        'total_candidates': total_candidates_all,
        'avg_candidates': avg_cands_overall,
        'zero_candidates': zero_candidates_all,
        'total_elapsed_s': total_elapsed,
        'overall_qps': overall_qps,
        'peak_ram_mb': peak_ram_overall,
        'peak_vmem_gb': peak_vmem_overall,
        'output_size_mb': file_size_mb,
        'country_metrics': country_metrics
    }

def main():
    parser = argparse.ArgumentParser(description="Country-Partitioned Champion v2 Candidate Generator")
    parser.add_argument("--s1", default="partitions/test_s1_part3.tsv", help="Path to S1 query TSV")
    parser.add_argument("--s2", default="student_resource/dataset/test/test_source2.tsv", help="Path to S2 target TSV")
    parser.add_argument("--s3", default="student_resource/dataset/test/test_source3.tsv", help="Path to S3 target TSV")
    parser.add_argument("--output", default="partitions/candidate_pairs_part3.tsv", help="Path to output candidate TSV")
    parser.add_argument("--limit-s1", type=int, default=None, help="Optional limit on number of S1 queries to process")
    parser.add_argument("--countries", nargs="+", default=None, help="Optional list of countries to run (e.g. France US India)")
    parser.add_argument("--index-cache-dir", default="partitions/indexes", help="Directory for cached country indexes")
    parser.add_argument("--batch-size", type=int, default=10000, help="Progress report interval")
    args = parser.parse_args()

    run_country_blocking(
        s1_path=args.s1,
        s2_path=args.s2,
        s3_path=args.s3,
        output_path=args.output,
        limit_s1=args.limit_s1,
        target_countries=args.countries,
        index_cache_dir=args.index_cache_dir,
        batch_size=args.batch_size
    )

if __name__ == "__main__":
    main()

