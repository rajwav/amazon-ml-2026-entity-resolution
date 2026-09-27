"""
Candidate Ranking and Pruning Layer.
Amazon ML Challenge 2026 — Entity Resolution.

Separation of Concerns:
- Operates downstream of the frozen Champion v2 Surgical candidate generator.
- Consumes raw candidate entity IDs from Champion v2 and ranks them using a
  high-precision weighted multi-signal scoring function.
- Prunes candidate lists to Top-K candidates per S1 query.
- Preserves Champion v2 blocking code and normalization 100% untouched.

Scoring Formula:
    score =
        5.0 * exact_name
      + 4.0 * name_jaccard
      + 2.5 * shared_digits
      + 1.5 * location_jaccard

Ranking Policy:
    Deterministic sort order:
    1. score descending (-score)
    2. candidate_entity_id ascending (lexicographical string tie-breaker)
"""

from typing import Dict, Iterable, List, Optional, Set, Tuple


# Component weights
WEIGHT_EXACT_NAME = 5.0
WEIGHT_NAME_JACCARD = 4.0
WEIGHT_SHARED_DIGITS = 2.5
WEIGHT_LOCATION_JACCARD = 1.5


def compute_exact_name(s1_feat, target_feat) -> float:
    """
    Compute binary exact core name match in [0.0, 1.0].
    Returns 1.0 if both core names are non-empty and match identically.
    Supports target_feat as dict or 4-tuple (core, tokens, digits, loc_tokens).
    """
    if target_feat is None or not s1_feat:
        return 0.0
    s1_core = s1_feat.get('core', '') if isinstance(s1_feat, dict) else s1_feat[0]
    if isinstance(target_feat, tuple):
        t_core = target_feat[0]
    elif isinstance(target_feat, dict):
        t_core = target_feat.get('core', '')
    else:
        return 0.0
    if s1_core and s1_core == t_core:
        return 1.0
    return 0.0


def compute_name_jaccard(s1_feat, target_feat) -> float:
    """
    Compute Jaccard similarity of normalized significant name tokens in [0.0, 1.0].
    Supports target_feat as dict or 4-tuple (core, tokens, digits, loc_tokens).
    """
    if target_feat is None or not s1_feat:
        return 0.0
    s1_tokens = set(s1_feat.get('tokens', ())) if isinstance(s1_feat, dict) else (set(s1_feat[1]) if s1_feat[1] else set())
    if isinstance(target_feat, tuple):
        t_tokens = set(target_feat[1]) if target_feat[1] else set()
    elif isinstance(target_feat, dict):
        t_tokens = set(target_feat.get('tokens', ()))
    else:
        return 0.0
    if not s1_tokens and not t_tokens:
        return 0.0
    inter = len(s1_tokens & t_tokens)
    union = len(s1_tokens) + len(t_tokens) - inter
    return inter / union if union else 0.0


def compute_shared_digits(s1_feat, target_feat) -> float:
    """
    Compute binary shared street digits indicator in [0.0, 1.0].
    Returns 1.0 if S1 and target address share at least one street number digit.
    Supports target_feat as dict or 4-tuple (core, tokens, digits, loc_tokens).
    """
    if target_feat is None or not s1_feat:
        return 0.0
    s1_digits = set(s1_feat.get('digits', ())) if isinstance(s1_feat, dict) else (set(s1_feat[2]) if s1_feat[2] else set())
    if isinstance(target_feat, tuple):
        t_digits = set(target_feat[2]) if target_feat[2] else set()
    elif isinstance(target_feat, dict):
        t_digits = set(target_feat.get('digits', ()))
    else:
        return 0.0
    if s1_digits and t_digits and not s1_digits.isdisjoint(t_digits):
        return 1.0
    return 0.0


def compute_location_jaccard(s1_feat, target_feat) -> float:
    """
    Compute Jaccard similarity of location tokens in [0.0, 1.0].
    Supports target_feat as dict or 4-tuple (core, tokens, digits, loc_tokens).
    """
    if target_feat is None or not s1_feat:
        return 0.0
    s1_loc = set(s1_feat.get('loc_tokens', ())) if isinstance(s1_feat, dict) else (set(s1_feat[3]) if s1_feat[3] else set())
    if isinstance(target_feat, tuple):
        t_loc = set(target_feat[3]) if target_feat[3] else set()
    elif isinstance(target_feat, dict):
        t_loc = set(target_feat.get('loc_tokens', ()))
    else:
        return 0.0
    if not s1_loc and not t_loc:
        return 0.0
    inter = len(s1_loc & t_loc)
    union = len(s1_loc) + len(t_loc) - inter
    return inter / union if union else 0.0


def compute_candidate_score(s1_feat, target_feat) -> float:
    """
    Compute combined similarity score for an S1-target candidate pair:
        score = 5.0 * exact_name + 4.0 * name_jaccard + 2.5 * shared_digits + 1.5 * location_jaccard
    """
    exact = compute_exact_name(s1_feat, target_feat)
    name_jacc = compute_name_jaccard(s1_feat, target_feat)
    shared_dig = compute_shared_digits(s1_feat, target_feat)
    loc_jacc = compute_location_jaccard(s1_feat, target_feat)

    return (
        WEIGHT_EXACT_NAME * exact
        + WEIGHT_NAME_JACCARD * name_jacc
        + WEIGHT_SHARED_DIGITS * shared_dig
        + WEIGHT_LOCATION_JACCARD * loc_jacc
    )


class CandidateRanker:
    """
    Configurable candidate ranker and pruner for entity resolution.
    Ingests raw candidate IDs from Champion v2 blocker and returns Top-K candidates.
    Supports target features stored as dicts or memory-efficient 4-tuples:
    (core, tokens, digits, loc_tokens).
    """

    def __init__(
        self,
        target_features: Optional[Dict[str, any]] = None,
        default_k: int = 50,
        weight_exact_name: float = WEIGHT_EXACT_NAME,
        weight_name_jaccard: float = WEIGHT_NAME_JACCARD,
        weight_shared_digits: float = WEIGHT_SHARED_DIGITS,
        weight_location_jaccard: float = WEIGHT_LOCATION_JACCARD,
    ):
        """
        Initialize CandidateRanker with an optional precomputed target feature store.

        Args:
            target_features: Dict mapping target entity_id to its feature dict or 4-tuple.
            default_k: Default candidate cap K (default: 50).
            weight_exact_name: Weight for exact core name match (default: 5.0).
            weight_name_jaccard: Weight for name token Jaccard (default: 4.0).
            weight_shared_digits: Weight for shared street digits (default: 2.5).
            weight_location_jaccard: Weight for location token Jaccard (default: 1.5).
        """
        self.target_features: Dict[str, any] = target_features if target_features is not None else {}
        self.default_k: int = default_k
        self.w_exact: float = weight_exact_name
        self.w_name_jacc: float = weight_name_jaccard
        self.w_shared_dig: float = weight_shared_digits
        self.w_loc_jacc: float = weight_location_jaccard

    def register_target_features(self, target_id: str, target_feat: any):
        """Register precomputed feature dict or tuple for a target entity."""
        self.target_features[target_id] = target_feat

    def register_target_store(self, target_features: Dict[str, any]):
        """Register or update complete target feature store."""
        self.target_features.update(target_features)

    def score_pair(self, s1_feat, target_feat) -> float:
        """Score an (s1, target) pair using configured weights."""
        if target_feat is None:
            return 0.0
        exact = compute_exact_name(s1_feat, target_feat)
        name_jacc = compute_name_jaccard(s1_feat, target_feat)
        shared_dig = compute_shared_digits(s1_feat, target_feat)
        loc_jacc = compute_location_jaccard(s1_feat, target_feat)

        return (
            self.w_exact * exact
            + self.w_name_jacc * name_jacc
            + self.w_shared_dig * shared_dig
            + self.w_loc_jacc * loc_jacc
        )

    def score_candidates(
        self, s1_feat: dict, candidate_ids: Iterable[str]
    ) -> List[Tuple[str, float]]:
        """
        Score and deterministically sort all candidate IDs for a given S1 entity.

        Tie-breaking rule:
        1. Score descending (-score)
        2. Candidate entity ID ascending (lexicographical string sort)

        Returns:
            List of (candidate_id, score) sorted deterministically.
        """
        # Precompute query sets once per S1 query
        s1_core = s1_feat.get('core', '') if isinstance(s1_feat, dict) else s1_feat[0]
        s1_tok = s1_feat.get('tokens', ()) if isinstance(s1_feat, dict) else s1_feat[1]
        s1_tokens_set = set(s1_tok) if s1_tok else set()
        s1_dig = s1_feat.get('digits', ()) if isinstance(s1_feat, dict) else s1_feat[2]
        s1_digits_set = set(s1_dig) if s1_dig else set()
        s1_loc = s1_feat.get('loc_tokens', ()) if isinstance(s1_feat, dict) else s1_feat[3]
        s1_loc_set = set(s1_loc) if s1_loc else set()

        w_exact = self.w_exact
        w_name = self.w_name_jacc
        w_dig = self.w_shared_dig
        w_loc = self.w_loc_jacc
        target_features = self.target_features

        scored: List[Tuple[str, float]] = []
        for tid in candidate_ids:
            t_feat = target_features.get(tid)
            if t_feat is None:
                scored.append((tid, 0.0))
                continue

            if isinstance(t_feat, tuple):
                t_core = t_feat[0]
                t_tokens = set(t_feat[1]) if t_feat[1] else set()
                t_digits = set(t_feat[2]) if t_feat[2] else set()
                t_loc = set(t_feat[3]) if t_feat[3] else set()
            elif isinstance(t_feat, dict):
                t_core = t_feat.get('core', '')
                t_tokens = set(t_feat.get('tokens', ()))
                t_digits = set(t_feat.get('digits', ()))
                t_loc = set(t_feat.get('loc_tokens', ()))
            else:
                scored.append((tid, 0.0))
                continue

            # Exact Name
            exact = 1.0 if (s1_core and s1_core == t_core) else 0.0

            # Name Jaccard
            if not s1_tokens_set and not t_tokens:
                name_jacc = 0.0
            else:
                inter_name = len(s1_tokens_set & t_tokens)
                union_name = len(s1_tokens_set) + len(t_tokens) - inter_name
                name_jacc = inter_name / union_name if union_name else 0.0

            # Shared Digits
            shared_dig = 1.0 if (s1_digits_set and t_digits and not s1_digits_set.isdisjoint(t_digits)) else 0.0

            # Location Jaccard
            if not s1_loc_set and not t_loc:
                loc_jacc = 0.0
            else:
                inter_loc = len(s1_loc_set & t_loc)
                union_loc = len(s1_loc_set) + len(t_loc) - inter_loc
                loc_jacc = inter_loc / union_loc if union_loc else 0.0

            score = w_exact * exact + w_name * name_jacc + w_dig * shared_dig + w_loc * loc_jacc
            scored.append((tid, score))

        # Deterministic ranking: score descending, then candidate_id ascending
        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored

    def rank_candidates(
        self, s1_feat: dict, candidate_ids: Iterable[str], k: Optional[int] = None
    ) -> List[str]:
        """
        Rank raw candidate IDs and prune to Top-K.

        Args:
            s1_feat: Extracted feature dictionary for S1 query entity.
            candidate_ids: Iterable of target entity IDs from Champion v2 blocker.
            k: Top-K limit. If None, uses self.default_k.

        Returns:
            List of Top-K candidate IDs in descending rank order.
        """
        cand_list = list(candidate_ids) if not isinstance(candidate_ids, list) else candidate_ids
        if not cand_list:
            return []

        limit = self.default_k if k is None else k
        if limit <= 0:
            return []

        scored = self.score_candidates(s1_feat, cand_list)
        return [cid for cid, _ in scored[:limit]]

    def rank_and_prune(
        self, s1_feat: dict, candidate_ids: Iterable[str], k: Optional[int] = None
    ) -> List[str]:
        """Alias for rank_candidates."""
        return self.rank_candidates(s1_feat, candidate_ids, k=k)


class CandidateHeapItem:
    """
    Min-heap item for global Top-K ranking across target shards.
    Order is inverted so that the WORST candidate has the smallest key
    and is evicted first from a Python min-heap.

    Evaluation:
    - Lower score is worse.
    - Equal score: larger candidate_entity_id is worse (lexicographical tie-breaker).
    """
    __slots__ = ('score', 'entity_id')

    def __init__(self, score: float, entity_id: str):
        self.score: float = score
        self.entity_id: str = entity_id

    def __lt__(self, other: 'CandidateHeapItem') -> bool:
        # Returns True if self is WORSE than other
        if self.score != other.score:
            return self.score < other.score
        return self.entity_id > other.entity_id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CandidateHeapItem):
            return False
        return self.score == other.score and self.entity_id == other.entity_id

    def __repr__(self) -> str:
        return f"CandidateHeapItem(score={self.score:.4f}, entity_id={self.entity_id!r})"


import heapq


class GlobalTopKHeap:
    """
    Maintains a cross-shard global Top-K heap for a single query entity.
    Guarantees exact mathematical equivalence to monolithic Top-K ranking
    without materializing all cross-shard candidates simultaneously.
    """

    def __init__(self, k: int = 1000):
        self.k: int = k
        self.heap: List[CandidateHeapItem] = []

    def push(self, score: float, entity_id: str):
        """Push a scored candidate into the global Top-K heap."""
        if self.k <= 0:
            return

        item = CandidateHeapItem(score, entity_id)
        if len(self.heap) < self.k:
            heapq.heappush(self.heap, item)
        elif item > self.heap[0]:
            # item is better than the current worst item at the root
            heapq.heapreplace(self.heap, item)

    def push_candidates(self, scored_candidates: Iterable[Tuple[str, float]]):
        """Batch push (candidate_id, score) pairs into the heap."""
        for cid, score in scored_candidates:
            self.push(score, cid)

    def to_ranked_list(self) -> List[str]:
        """
        Extract the Top-K candidate IDs in deterministic descending rank order:
        1. Score descending (-score)
        2. Candidate entity ID ascending (lexicographical)
        """
        if not self.heap:
            return []
        sorted_items = sorted(self.heap, key=lambda item: (-item.score, item.entity_id))
        return [item.entity_id for item in sorted_items]

    def __len__(self) -> int:
        return len(self.heap)
