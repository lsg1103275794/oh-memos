import uuid

from unittest.mock import MagicMock

import numpy as np
import pytest

from memos.memories.textual.item import TextualMemoryItem, TreeNodeTextualMemoryMetadata
from memos.memories.textual.tree_text_memory.retrieve.reranker import (
    MemoryReranker,
    batch_cosine_similarity,
)
from memos.memories.textual.tree_text_memory.retrieve.retrieval_mid_structs import ParsedTaskGoal


def test_batch_cosine_similarity_basic():
    query_vec = [1, 0]
    candidate_vecs = [
        [1, 0],
        [0, 1],
        [1, 1],
    ]
    sims = batch_cosine_similarity(query_vec, candidate_vecs)
    assert len(sims) == 3
    np.testing.assert_allclose(sims[0], 1.0, atol=1e-5)
    np.testing.assert_allclose(sims[1], 0.0, atol=1e-5)
    np.testing.assert_allclose(sims[2], 0.7071, atol=1e-3)


@pytest.fixture
def mock_reranker():
    llm = MagicMock()
    embedder = MagicMock()
    reranker = MemoryReranker(llm, embedder)
    # For consistent test, make weights explicit
    reranker.level_weights = {
        "topic": 2.0,
        "concept": 1.5,
        "fact": 1.0,
    }
    return reranker


def make_item(embedding, level):
    return TextualMemoryItem(
        id=str(uuid.uuid4()),
        memory="test",
        metadata=TreeNodeTextualMemoryMetadata(embedding=embedding, background=level),
    )


def test_rerank_with_structural_weight(mock_reranker):
    query_emb = [1, 0]
    items = [
        make_item([1, 0], "topic"),  # similarity=1, weight=2.0 → score=2.0
        make_item([1, 0], "fact"),  # similarity=1, weight=1.0 → score=1.0
        make_item([0, 1], "concept"),  # similarity=0, weight=1.5 → score=0.0
    ]
    goal = ParsedTaskGoal(keys=[], tags=[])

    result = mock_reranker.rerank(
        query="test",
        query_embedding=query_emb,
        graph_results=items,
        top_k=2,
        parsed_goal=goal,
    )
    assert len(result) == 2
    top_item, top_score = result[0]
    assert top_score >= result[1][1]
    assert isinstance(top_item, TextualMemoryItem)
    # Highest score should be the topic one (2.0)
    assert np.isclose(top_score, 2.0, atol=1e-3)


def test_rerank_no_embeddings(mock_reranker):
    # If no embeddings, fallback to top_k original
    items = [
        make_item(None, "fact"),
        make_item(None, "concept"),
    ]
    goal = ParsedTaskGoal(keys=[], tags=[])
    result = mock_reranker.rerank(
        query="test",
        query_embedding=[1, 0],
        graph_results=items,
        top_k=1,
        parsed_goal=goal,
    )
    assert len(result) == 1
    assert isinstance(result[0], TextualMemoryItem) or isinstance(result[0][0], TextualMemoryItem)


def test_rerank_with_fallback(mock_reranker):
    # Only 1 with embedding, top_k=2 => fallback needed
    with_emb = make_item([1, 0], "topic")
    no_emb = make_item(None, "concept")

    goal = ParsedTaskGoal(keys=[], tags=[])
    result = mock_reranker.rerank(
        query="test",
        query_embedding=[1, 0],
        graph_results=[with_emb, no_emb],
        top_k=2,
        parsed_goal=goal,
    )
    assert len(result) == 2
    # One must have valid score, one fallback with -1
    scores = [score for _, score in result]
    assert any(s == -1.0 for s in scores)
