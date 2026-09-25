"""
Deterministic extraction and persistence of the 10,000-S1 representative pilot dataset.
Saves extracted raw records and ground truth to experiments/data/ for zero-redundancy loading.
"""

import os
import json
import random
import time

random.seed(42)

s1_path = 'student_resource/dataset/train/train_source1.tsv'
s2_path = 'student_resource/dataset/train/train_source2.tsv'
s3_path = 'student_resource/dataset/train/train_source3.tsv'
gt_path = 'student_resource/dataset/train/train_ground_truth.tsv'

data_dir = 'experiments/data'
os.makedirs(data_dir, exist_ok=True)

print("--- STEP 0 & 1: EXTRACTING & PERSISTING 10,000-S1 PILOT DATA ---")
t0 = time.time()

# 1. Map S1 countries
print("Reading S1 countries...")
s1_country_map = {}
with open(s1_path, 'r', encoding='utf-8') as f:
    next(f)
    for line in f:
        parts = line.rstrip('\r\n').split('\t')
        s1_country_map[parts[0]] = parts[3]

# 2. Categorize S1 entities from ground truth
print("Categorizing S1 entities from ground truth...")
us_zero, us_one, us_multi = [], [], []
in_zero, in_one, in_multi = [], [], []
s1_to_gt = {}

with open(gt_path, 'r', encoding='utf-8') as f:
    next(f)
    for line in f:
        s1_id, tab, rest = line.rstrip('\r\n').partition('\t')
        c = s1_country_map.get(s1_id, '')
        mids = [x.strip() for x in rest.split(',') if x.strip()] if rest.strip() else []
        n_m = len(mids)
        s1_to_gt[s1_id] = mids
        
        if c == 'US':
            if n_m == 0: us_zero.append(s1_id)
            elif n_m == 1: us_one.append(s1_id)
            else: us_multi.append(s1_id)
        elif c == 'India':
            if n_m == 0: in_zero.append(s1_id)
            elif n_m == 1: in_one.append(s1_id)
            else: in_multi.append(s1_id)

# Sample 10k S1 exactly as in run_pilot_benchmark.py
pilot_us = (
    random.sample(us_zero, 335) +
    random.sample(us_one, 324) +
    random.sample(us_multi, 5341)
)
pilot_in = (
    random.sample(in_zero, 223) +
    random.sample(in_one, 216) +
    random.sample(in_multi, 3561)
)
pilot_s1_ids = set(pilot_us + pilot_in)
assert len(pilot_s1_ids) == 10000

# True matches
pilot_true_pairs = 0
needed_target_ids = set()
for s1_id in pilot_s1_ids:
    mids = s1_to_gt[s1_id]
    pilot_true_pairs += len(mids)
    for m in mids:
        needed_target_ids.add(m)

assert pilot_true_pairs == 34481
assert len(needed_target_ids) == 34481

# Extract target records (all true matches + 50,000 distractors)
print("Extracting target records...")
needed_s2 = {m for m in needed_target_ids if m.startswith('S2-')}
needed_s3 = {m for m in needed_target_ids if m.startswith('S3-')}

target_records_raw = {}
distractor_s2 = set()
distractor_s3 = set()

with open(s2_path, 'r', encoding='utf-8') as f:
    next(f)
    for i, line in enumerate(f):
        parts = line.rstrip('\r\n').split('\t')
        eid = parts[0]
        if eid in needed_s2:
            target_records_raw[eid] = parts
        elif len(distractor_s2) < 25000 and i % 100 == 0:
            distractor_s2.add(eid)
            target_records_raw[eid] = parts

with open(s3_path, 'r', encoding='utf-8') as f:
    next(f)
    for i, line in enumerate(f):
        parts = line.rstrip('\r\n').split('\t')
        eid = parts[0]
        if eid in needed_s3:
            target_records_raw[eid] = parts
        elif len(distractor_s3) < 25000 and i % 100 == 0:
            distractor_s3.add(eid)
            target_records_raw[eid] = parts

assert len(target_records_raw) == 84481

# Save pilot_s1.tsv
print("Writing pilot_s1.tsv...")
with open(f"{data_dir}/pilot_s1.tsv", 'w', encoding='utf-8') as f_out, open(s1_path, 'r', encoding='utf-8') as f_in:
    header = f_in.readline()
    f_out.write(header)
    for line in f_in:
        parts = line.rstrip('\r\n').split('\t')
        if parts[0] in pilot_s1_ids:
            f_out.write(line)

# Save pilot_targets.tsv
print("Writing pilot_targets.tsv...")
with open(f"{data_dir}/pilot_targets.tsv", 'w', encoding='utf-8') as f_out:
    f_out.write("entity_id\tbusiness_name\tbusiness_address\tcountry\n")
    for eid, parts in target_records_raw.items():
        while len(parts) < 4: parts.append('')
        f_out.write('\t'.join(parts[:4]) + '\n')

# Save pilot_ground_truth.tsv
print("Writing pilot_ground_truth.tsv...")
with open(f"{data_dir}/pilot_ground_truth.tsv", 'w', encoding='utf-8') as f_out:
    f_out.write("source1_entity_id\tmatched_entity_ids\n")
    for s1_id in pilot_us + pilot_in:
        mids = s1_to_gt[s1_id]
        f_out.write(f"{s1_id}\t{','.join(mids)}\n")

metadata = {
    "total_s1": len(pilot_s1_ids),
    "us_s1": len(pilot_us),
    "in_s1": len(pilot_in),
    "total_true_pairs": pilot_true_pairs,
    "unique_true_targets": len(needed_target_ids),
    "total_target_pool": len(target_records_raw),
    "distractors_count": len(distractor_s2) + len(distractor_s3),
    "timestamp": time.ctime()
}

with open(f"{data_dir}/pilot_metadata.json", 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=2)

print(f"Setup complete in {time.time()-t0:.2f}s!")
print(f"Metadata: {json.dumps(metadata, indent=2)}")
