"""
Matching & Classification Module for Business Entity Resolution.
Amazon ML Challenge 2026.
"""

from matching.evaluator import compute_macro_f05
from matching.features import extract_pairwise_features

__all__ = ["compute_macro_f05", "extract_pairwise_features"]
