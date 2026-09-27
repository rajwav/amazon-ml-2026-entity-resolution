import os
import json
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from matching.dataset_builder import build_staged_dataset
from matching.evaluator import compute_macro_f05

def train_and_evaluate():
    data_dir = 'experiments/data'
    s1_path = os.path.join(data_dir, 'pilot_s1.tsv')
    target_path = os.path.join(data_dir, 'pilot_targets.tsv')
    candidates_path = os.path.join(data_dir, 'baseline_g_candidates.json')
    gt_path = os.path.join(data_dir, 'pilot_ground_truth.tsv')
    
    # We will use all 10k S1s with 10x negative multiplier
    df = build_staged_dataset(s1_path, target_path, candidates_path, gt_path, negative_multiplier=10)
    
    # Split using GroupShuffleSplit based on s1_id
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, val_idx = next(gss.split(df, groups=df['s1_id']))
    
    train_df = df.iloc[train_idx]
    val_df = df.iloc[val_idx]
    
    print(f"\n--- Split Info ---")
    print(f"Train size: {len(train_df)} pairs")
    print(f"  Positives: {train_df['label'].sum()}, Negatives: {len(train_df) - train_df['label'].sum()}")
    print(f"Val size: {len(val_df)} pairs")
    print(f"  Positives: {val_df['label'].sum()}, Negatives: {len(val_df) - val_df['label'].sum()}")
    
    # Features
    drop_cols = ['s1_id', 'target_id', 'label']
    features = [c for c in df.columns if c not in drop_cols]
    
    X_train = train_df[features]
    y_train = train_df['label']
    X_val = val_df[features]
    y_val = val_df['label']
    
    print(f"Training HistGradientBoostingClassifier on {len(features)} features...")
    # Calculate sample weight to balance classes manually for HistGradientBoostingClassifier
    weights = np.ones(len(y_train))
    neg_weight = 1.0
    pos_weight = (len(y_train) - y_train.sum()) / y_train.sum() if y_train.sum() > 0 else 1.0
    weights[y_train == 1] = pos_weight

    model = HistGradientBoostingClassifier(
        max_iter=150,
        learning_rate=0.05,
        max_depth=6,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=20
    )
    
    model.fit(X_train, y_train, sample_weight=weights)
    
    # Predict probabilities on val
    y_pred_prob = model.predict_proba(X_val)[:, 1]
    val_df = val_df.copy()
    val_df['pred_prob'] = y_pred_prob
    
    print("\nCalibrating threshold for Macro F0.5...")
    # Reconstruct ground truth format for evaluation
    # {s1_id: set(target_ids)}
    val_gt = {}
    for _, row in val_df[val_df['label'] == 1].iterrows():
        val_gt.setdefault(row['s1_id'], set()).add(row['target_id'])
    
    # We must also include S1s that have NO positive matches in val
    for s1 in val_df['s1_id'].unique():
        if s1 not in val_gt:
            val_gt[s1] = set()
            
    thresholds = np.linspace(0.1, 0.95, 86)
    best_th = 0.5
    best_f05 = -1.0
    best_metrics = {}
    
    for th in thresholds:
        # Construct predictions
        val_preds = {}
        # initialize empty sets for all val S1s
        for s1 in val_gt.keys():
            val_preds[s1] = set()
            
        matches = val_df[val_df['pred_prob'] >= th]
        for _, row in matches.iterrows():
            val_preds[row['s1_id']].add(row['target_id'])
            
        metrics = compute_macro_f05(val_preds, val_gt)
        if metrics['macro_f05'] > best_f05:
            best_f05 = metrics['macro_f05']
            best_th = th
            best_metrics = metrics
            
    print(f"\n--- Best Validation Threshold: {best_th:.2f} ---")
    print(f"Macro F0.5: {best_metrics['macro_f05']:.4f}")
    print(f"Macro Precision: {best_metrics['macro_precision']:.4f}")
    print(f"Macro Recall: {best_metrics['macro_recall']:.4f}")
    
    import pickle
    
    # Feature Importance (Permutation)
    print("\nCalculating Feature Importances...")
    r = permutation_importance(model, X_val, y_val, n_repeats=5, random_state=42, n_jobs=-1)
    importance = pd.DataFrame({
        'feature': features,
        'importance': r.importances_mean
    }).sort_values('importance', ascending=False)
    print("\nTop 10 Features:")
    print(importance.head(10))
    
    # Save model and threshold
    with open('matching/hgbm_baseline.pkl', 'wb') as f:
        pickle.dump(model, f)
    with open('matching/best_threshold.txt', 'w') as f:
        f.write(str(best_th))
    print("Model and threshold saved.")

if __name__ == '__main__':
    train_and_evaluate()
