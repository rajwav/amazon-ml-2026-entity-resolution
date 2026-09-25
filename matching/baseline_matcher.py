"""
Baseline Matcher: Rule-Based Similarity Scoring & Threshold Calibration.
Amazon ML Challenge 2026.

Provides:
1. Baseline 1: Interpretable composite similarity scoring.
2. Fast threshold sweep directly optimizing Macro F_0.5.
3. Formatter generating valid matching_results.tsv.
"""

from typing import Dict, List, Set, Tuple
from matching.evaluator import compute_macro_f05

def compute_composite_similarity(feat: Dict[str, float]) -> float:
    """
    Compute a weighted baseline similarity score in [0.0, 1.0].
    Prioritizes exact name matches, high Levenshtein similarity, and street digit agreement.
    """
    # Name signal: exact (0.50), Levenshtein (0.25), tokens (0.15)
    name_score = (
        0.50 * feat['exact_core_match'] +
        0.25 * feat['levenshtein_name'] +
        0.15 * feat['token_jaccard'] +
        0.10 * feat['cons_tri_match']
    )
    
    # Address signal: digits (0.50), location (0.35), unit (0.15)
    addr_score = (
        0.50 * feat['has_shared_digit'] +
        0.35 * feat['loc_jaccard'] +
        0.15 * feat['unit_match']
    )

    # If both have addresses, require agreement; otherwise rely on name
    if feat['s1_has_address'] and feat['t_has_address']:
        composite = 0.60 * name_score + 0.40 * addr_score
    else:
        composite = 0.90 * name_score + 0.10 * addr_score

    # Bonus for domain / social handle equivalence
    if feat['domain_match']:
        composite = max(composite, 0.85)

    return composite

def calibrate_threshold(
    candidate_scores: Dict[str, List[Tuple[str, float]]],
    ground_truth: Dict[str, Set[str]],
    thresholds: List[float] = None
) -> Tuple[float, Dict[str, float]]:
    """
    Grid-search optimal threshold on validation set maximizing Macro F_0.5.
    candidate_scores: {s1_id: [(target_id, score), ...]}
    """
    if thresholds is None:
        thresholds = [0.40, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]

    best_thresh = 0.60
    best_metrics = None
    best_f05 = -1.0

    print("Sweeping classification thresholds for Macro F_0.5 optimization...")
    for th in thresholds:
        preds = {}
        for s1_id, scored_cands in candidate_scores.items():
            matches = {tid for tid, score in scored_cands if score >= th}
            preds[s1_id] = matches

        metrics = compute_macro_f05(preds, ground_truth)
        f05 = metrics['macro_f05']
        p = metrics['macro_precision']
        r = metrics['macro_recall']
        print(f"  Threshold {th:.2f} -> Macro F_0.5: {f05:.4f} (Precision: {p:.4f}, Recall: {r:.4f})")

        if f05 > best_f05:
            best_f05 = f05
            best_thresh = th
            best_metrics = metrics

    print(f"\nOptimal Threshold: {best_thresh:.2f} (Macro F_0.5 = {best_f05:.4f})")
    return best_thresh, best_metrics

def export_matching_results(
    candidate_scores: Dict[str, List[Tuple[str, float]]],
    threshold: float,
    all_s1_ids: List[str],
    output_path: str
):
    """
    Export final matching predictions to matching_results.tsv in official competition format:
    source1_entity_id\tmatched_entity_ids
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("source1_entity_id\tmatched_entity_ids\n")
        for s1_id in all_s1_ids:
            scored = candidate_scores.get(s1_id, [])
            matches = [tid for tid, score in scored if score >= threshold]
            matches_str = ",".join(sorted(matches)) if matches else ""
            f.write(f"{s1_id}\t{matches_str}\n")
    print(f"Exported final matching results to {output_path}")
