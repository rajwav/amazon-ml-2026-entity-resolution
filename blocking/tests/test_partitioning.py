"""
Unit tests for deterministic S1 partitioning and candidate merging.
"""

import os
import tempfile
import pytest
from blocking.split_queries import split_s1, get_hash_partition
from blocking.merge_candidates import merge_candidate_partitions

def test_hash_partition_determinism():
    # Must yield identical partition across separate runs
    eid = "S1-714132312"
    p1 = get_hash_partition(eid, 4)
    p2 = get_hash_partition(eid, 4)
    assert p1 == p2
    assert 0 <= p1 < 4

def test_split_and_merge():
    sample_s1 = (
        "entity_id\tbusiness_name\tbusiness_address\tcountry\n"
        "S1-1\tAlpha Corp\t123 Main St\tUS\n"
        "S1-2\tBeta LLC\t456 Market Rd\tIndia\n"
        "S1-3\tGamma SAS\t789 Rue Paris\tFrance\n"
        "S1-4\tDelta Inc\t101 First Ave\tUS\n"
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        input_s1 = os.path.join(tmpdir, "test_s1.tsv")
        with open(input_s1, 'w', encoding='utf-8') as f:
            f.write(sample_s1)

        # Split into 2 parts
        out_files = split_s1(input_s1, tmpdir, num_partitions=2, method='hash')
        assert len(out_files) == 2

        # Verify each partition has header
        for pf in out_files:
            with open(pf, 'r', encoding='utf-8') as f:
                header = f.readline()
                assert "entity_id" in header

        # Simulate candidate output files
        cand_files = []
        for i, pf in enumerate(out_files):
            cand_path = os.path.join(tmpdir, f"cand_part{i}.tsv")
            with open(pf, 'r') as s1_f, open(cand_path, 'w') as c_f:
                next(s1_f)
                c_f.write("source1_entity_id\tcandidate_entity_ids\n")
                for line in s1_f:
                    eid = line.split('\t')[0]
                    c_f.write(f"{eid}\tS2-100,S3-200\n")
            cand_files.append(cand_path)

        # Merge
        merged_path = os.path.join(tmpdir, "merged_candidates.tsv")
        merge_candidate_partitions(cand_files, input_s1, merged_path)

        # Validate merged content
        with open(merged_path, 'r') as f:
            lines = [l.strip() for l in f if l.strip()]
            assert len(lines) == 5 # 1 header + 4 rows
            assert lines[0] == "source1_entity_id\tcandidate_entity_ids"
