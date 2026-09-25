"""
Reusable infrastructure for blocking experiments.
Handles data loading, normalized caching, indexing, metric evaluation, and missed-pair logging.
"""

import os
import sys
import time
import json
import psutil
from typing import Dict, List, Set, Tuple, Any

sys.path.append('.')
from src.preprocessing.normalization import normalize_business_name, normalize_business_address

DATA_DIR = 'experiments/data'
RESULTS_DIR = 'experiments/results'
os.makedirs(RESULTS_DIR, exist_ok=True)

process = psutil.Process(os.getpid())

def get_ram_mb() -> float:
    return process.memory_info().rss / (1024 * 1024)

def load_pilot_raw():
    """Load the raw pilot datasets (10k S1, 84.4k targets, ground truth)."""
    s1_records = {}
    with open(f"{DATA_DIR}/pilot_s1.tsv", 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            while len(parts) < 4: parts.append('')
            s1_records[parts[0]] = parts

    target_records = {}
    with open(f"{DATA_DIR}/pilot_targets.tsv", 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            parts = line.rstrip('\r\n').split('\t')
            while len(parts) < 4: parts.append('')
            target_records[parts[0]] = parts

    gt_matches = {}
    total_true_pairs = 0
    with open(f"{DATA_DIR}/pilot_ground_truth.tsv", 'r', encoding='utf-8') as f:
        next(f)
        for line in f:
            s1_id, tab, rest = line.rstrip('\r\n').partition('\t')
            mids = [x.strip() for x in rest.split(',') if x.strip()] if rest.strip() else []
            gt_matches[s1_id] = mids
            total_true_pairs += len(mids)

    return s1_records, target_records, gt_matches, total_true_pairs

def get_normalized_records(s1_records: Dict[str, list], target_records: Dict[str, list]):
    """Normalize records and return compact feature dictionaries."""
    s1_norm = {}
    for eid, parts in s1_records.items():
        bname, baddr, country = parts[1], parts[2], parts[3]
        core, legal, sig_tokens, ngrams = normalize_business_name(bname)
        norm_addr, digits, loc_tokens = normalize_business_address(baddr)
        prefix4 = core[:4] if len(core) >= 4 else core
        s1_norm[eid] = {
            'id': eid,
            'country': country,
            'core': core,
            'legal': legal,
            'tokens': tuple(sig_tokens),
            'prefix4': prefix4,
            'ngrams': tuple(ngrams),
            'digits': tuple(digits),
            'loc_tokens': tuple(loc_tokens)
        }

    target_norm = {}
    for eid, parts in target_records.items():
        bname, baddr, country = parts[1], parts[2], parts[3]
        core, legal, sig_tokens, ngrams = normalize_business_name(bname)
        norm_addr, digits, loc_tokens = normalize_business_address(baddr)
        prefix4 = core[:4] if len(core) >= 4 else core
        target_norm[eid] = {
            'id': eid,
            'country': country,
            'core': core,
            'legal': legal,
            'tokens': tuple(sig_tokens),
            'prefix4': prefix4,
            'ngrams': tuple(ngrams),
            'digits': tuple(digits),
            'loc_tokens': tuple(loc_tokens)
        }

    return s1_norm, target_norm

def evaluate_blocking_candidates(
    experiment_id: str,
    description: str,
    s1_candidates: Dict[str, Set[str]],
    gt_matches: Dict[str, List[str]],
    total_true_pairs: int,
    total_target_pool: int,
    runtime_sec: float,
    peak_ram_mb: float,
    s1_norm: Dict[str, dict] = None,
    target_norm: Dict[str, dict] = None
) -> Tuple[Dict[str, Any], List[dict]]:
    """
    Compute official blocking evaluation metrics and extract missed true pairs.
    """
    recalled_pairs = 0
    missed_pairs_list = []
    candidate_counts = []
    zero_cand_count = 0

    for s1_id, true_mids in gt_matches.items():
        cands = s1_candidates.get(s1_id, set())
        cnt = len(cands)
        candidate_counts.append(cnt)
        if cnt == 0:
            zero_cand_count += 1

        for mid in true_mids:
            if mid in cands:
                recalled_pairs += 1
            else:
                reason = "UNKNOWN"
                if s1_norm and target_norm and mid in target_norm:
                    f1 = s1_norm[s1_id]
                    f2 = target_norm[mid]
                    if not f2['digits'] and f1['digits']:
                        reason = "target_address_missing_digits"
                    elif not f2['core']:
                        reason = "target_name_empty"
                    elif not (set(f1['tokens']) & set(f2['tokens'])):
                        reason = "no_shared_name_tokens"
                    elif not (set(f1['digits']) & set(f2['digits'])):
                        reason = "no_shared_address_digits"
                    elif not (set(f1['loc_tokens']) & set(f2['loc_tokens'])):
                        reason = "no_shared_location_tokens"
                    else:
                        reason = "lexical_variation_or_typo"

                missed_pairs_list.append({
                    'experiment': experiment_id,
                    's1_entity_id': s1_id,
                    'target_entity_id': mid,
                    'source': 'S2' if mid.startswith('S2-') else 'S3',
                    'reason': reason
                })

    missed_count = total_true_pairs - recalled_pairs
    recall_pct = (recalled_pairs / total_true_pairs * 100) if total_true_pairs > 0 else 0

    candidate_counts.sort()
    n_s1 = len(candidate_counts)
    avg_cands = sum(candidate_counts) / n_s1 if n_s1 else 0
    median_cands = candidate_counts[n_s1 // 2] if n_s1 else 0
    p95_cands = candidate_counts[int(n_s1 * 0.95)] if n_s1 else 0
    max_cands = max(candidate_counts) if n_s1 else 0

    total_possible = n_s1 * total_target_pool
    total_generated = sum(candidate_counts)
    reduction_ratio = (1.0 - (total_generated / total_possible)) * 100 if total_possible else 0

    metrics = {
        'experiment_id': experiment_id,
        'description': description,
        'recall': f"{recall_pct:.4f}%",
        'recall_pct': recall_pct,
        'true_pairs': total_true_pairs,
        'recalled_pairs': recalled_pairs,
        'missed_pairs': missed_count,
        'avg_candidates': avg_cands,
        'median_candidates': median_cands,
        'p95_candidates': p95_cands,
        'max_candidates': max_cands,
        'zero_candidate_s1': zero_cand_count,
        'candidate_reduction_ratio': f"{reduction_ratio:.4f}%",
        'runtime_seconds': runtime_sec,
        'peak_memory_mb': peak_ram_mb
    }

    return metrics, missed_pairs_list
