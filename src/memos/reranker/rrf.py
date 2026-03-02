"""Reciprocal Rank Fusion (RRF) local reranker -- zero HTTP calls."""

from __future__ import annotations

from typing import TYPE_CHECKING

from memos.utils import timed

from .base import BaseReranker

if TYPE_CHECKING:
    from memos.memories.textual.item import TextualMemoryItem


class RRFReranker(BaseReranker):
    """Score items using Reciprocal Rank Fusion.

    RRF assigns each document a score based solely on its position in the
    input list:

        score(d) = 1 / (k + rank)

    where *rank* is the 1-based position and *k* is a smoothing constant
    (default 60, following Cormack, Clarke & Buettcher, 2009).

    Because the score is a monotonically decreasing function of rank, the
    output order matches the input order -- but each item now carries a
    normalized score that can be combined with other ranked lists in a
    multi-signal fusion pipeline.

    Parameters
    ----------
    k : int, optional
        Smoothing constant.  Higher values dampen the advantage of
        top-ranked items.  The standard value is 60.
    """

    def __init__(self, k: int = 60) -> None:
        self.k = k

    @timed
    def rerank(
        self,
        query: str,
        graph_results: list[TextualMemoryItem],
        top_k: int,
        search_filter: dict | None = None,
        **kwargs,
    ) -> list[tuple[TextualMemoryItem, float]]:
        """Return *top_k* items scored by RRF.

        Items are scored in input order (rank 1 = first element) and
        returned sorted by score descending (highest first).
        """
        scored = [
            (item, 1.0 / (self.k + rank))
            for rank, item in enumerate(graph_results, start=1)
        ]
        # Already sorted descending by construction; just truncate.
        return scored[:top_k]
