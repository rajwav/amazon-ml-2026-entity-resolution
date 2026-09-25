"""
Frozen Champion v2 Surgical Blocking Module for Business Entity Resolution.
Amazon ML Challenge 2026.
"""

from blocking.blocking_core import ChampionV2Blocker
from blocking.normalization import normalize_business_name, normalize_business_address

__version__ = "2.0.0"
__all__ = ["ChampionV2Blocker", "normalize_business_name", "normalize_business_address"]
