"""
Official Competition Metric Evaluator: Macro-Averaged F_0.5 Score.
Amazon ML Challenge 2026.
"""

from typing import Dict, List, Set, Tuple

def compute_query_f05(predicted: Set[str], ground_truth: Set[str]) -> Tuple[float, float, float]:
    """
    Compute Precision, Recall, and F_0.5 for a single S1 query.
    Correctly accounts for singletons:
      - If ground truth is empty:
          - predicting empty gives F_0.5 = 1.0 (true negative singleton)
          - predicting any match gives F_0.5 = 0.0 (false positive)
      - If ground truth is non-empty:
          - predicting empty gives F_0.5 = 0.0
    """
    if not ground_truth:
        if not predicted:
            return 1.0, 1.0, 1.0 # True negative singleton
        else:
            return 0.0, 0.0, 0.0 # False positive match on singleton

    if not predicted:
        return 0.0, 0.0, 0.0

    tp = len(predicted & ground_truth)
    fp = len(predicted - ground_truth)
    fn = len(ground_truth - predicted)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    if precision == 0.0 and recall == 0.0:
        return 0.0, 0.0, 0.0

    # F_0.5 = (1.25 * P * R) / (0.25 * P + R)
    beta_sq = 0.25
    denom = beta_sq * precision + recall
    f05 = (1.25 * precision * recall) / denom if denom > 0 else 0.0

    return precision, recall, f05

def compute_macro_f05(predictions: Dict[str, Set[str]], ground_truth: Dict[str, Set[str]]) -> Dict[str, float]:
    """
    Compute Macro-Averaged F_0.5, Precision, and Recall across all queries in ground_truth.
    """
    total_queries = len(ground_truth)
    if total_queries == 0:
        return {'macro_f05': 0.0, 'macro_precision': 0.0, 'macro_recall': 0.0}

    sum_p = 0.0
    sum_r = 0.0
    sum_f05 = 0.0

    for s1_id, gt_set in ground_truth.items():
        pred_set = predictions.get(s1_id, set())
        p, r, f = compute_query_f05(pred_set, gt_set)
        sum_p += p
        sum_r += r
        sum_f05 += f

    return {
        'macro_f05': sum_f05 / total_queries,
        'macro_precision': sum_p / total_queries,
        'macro_recall': sum_r / total_queries,
        'total_evaluated_queries': total_queries
    }
