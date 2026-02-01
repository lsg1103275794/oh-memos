"""
Search handler for memory search functionality (Class-based version).

This module provides a class-based implementation of search handlers,
using dependency injection for better modularity and testability.
"""

import time

from typing import Any

from memos.api.handlers.base_handler import BaseHandler, HandlerDependencies
from memos.api.handlers.formatters_handler import rerank_knowledge_mem
from memos.api.product_models import APISearchRequest, SearchResponse
from memos.log import get_logger
from memos.memories.textual.tree_text_memory.organize.context_aware_searcher import (
    ContextAwareSearcher,
)
from memos.memories.textual.tree_text_memory.retrieve.retrieve_utils import (
    cosine_similarity_matrix,
)
from memos.multi_mem_cube.composite_cube import CompositeCubeView
from memos.multi_mem_cube.single_cube import SingleCubeView
from memos.multi_mem_cube.views import MemCubeView


logger = get_logger(__name__)


class SearchHandler(BaseHandler):
    """
    Handler for memory search operations.

    Provides fast, fine-grained, and mixture-based search modes.
    Now enhanced with context-aware search capabilities.
    """

    def __init__(self, dependencies: HandlerDependencies):
        """
        Initialize search handler.

        Args:
            dependencies: HandlerDependencies instance
        """
        super().__init__(dependencies)
        self._validate_dependencies(
            "naive_mem_cube", "mem_scheduler", "searcher", "deepsearch_agent"
        )
        # Lazy-initialized context-aware searcher
        self._context_aware_searcher: ContextAwareSearcher | None = None

    @property
    def context_aware_searcher(self) -> ContextAwareSearcher | None:
        """Get or create the context-aware searcher."""
        if self._context_aware_searcher is None and self.llm is not None:
            self._context_aware_searcher = ContextAwareSearcher(self.llm)
        return self._context_aware_searcher

    def handle_search_memories(self, search_req: APISearchRequest) -> SearchResponse:
        """
        Main handler for search memories endpoint.

        Orchestrates the search process based on the requested search mode,
        supporting both text and preference memory searches.

        Args:
            search_req: Search request containing query and parameters

        Returns:
            SearchResponse with formatted results
        """
        self.logger.info(f"[SearchHandler] Search Req is: {search_req}")

        # Increase recall pool if deduplication is enabled to ensure diversity
        original_top_k = search_req.top_k
        if search_req.dedup == "sim":
            search_req.top_k = original_top_k * 5

        cube_view = self._build_cube_view(search_req)

        results = cube_view.search_memories(search_req)
        if search_req.dedup == "sim":
            results = self._dedup_text_memories(results, original_top_k)
            self._strip_embeddings(results)
            # Restore original top_k for downstream logic or response metadata
            search_req.top_k = original_top_k

        start_time = time.time()
        text_mem = results["text_mem"]
        results["text_mem"] = rerank_knowledge_mem(
            self.reranker,
            query=search_req.query,
            text_mem=text_mem,
            top_k=original_top_k,
            file_mem_proportion=0.5,
        )
        rerank_time = time.time() - start_time

        self.logger.info(f"[Knowledge_replace_memory_time] Rerank time: {rerank_time} seconds")
        self.logger.info(
            f"[SearchHandler] Final search results: count={len(results)} results={results}"
        )

        return SearchResponse(
            message="Search completed successfully",
            data=results,
        )

    def _dedup_text_memories(self, results: dict[str, Any], target_top_k: int) -> dict[str, Any]:
        buckets = results.get("text_mem", [])
        if not buckets:
            return results

        flat: list[tuple[int, dict[str, Any], float]] = []
        for bucket_idx, bucket in enumerate(buckets):
            for mem in bucket.get("memories", []):
                score = mem.get("metadata", {}).get("relativity", 0.0)
                flat.append((bucket_idx, mem, score))

        if len(flat) <= 1:
            return results

        embeddings = self._extract_embeddings([mem for _, mem, _ in flat])
        if embeddings is None:
            documents = [mem.get("memory", "") for _, mem, _ in flat]
            embeddings = self.searcher.embedder.embed(documents)

        similarity_matrix = cosine_similarity_matrix(embeddings)

        indices_by_bucket: dict[int, list[int]] = {i: [] for i in range(len(buckets))}
        for flat_index, (bucket_idx, _, _) in enumerate(flat):
            indices_by_bucket[bucket_idx].append(flat_index)

        selected_global: list[int] = []
        selected_by_bucket: dict[int, list[int]] = {i: [] for i in range(len(buckets))}

        ordered_indices = sorted(range(len(flat)), key=lambda idx: flat[idx][2], reverse=True)
        for idx in ordered_indices:
            bucket_idx = flat[idx][0]
            if len(selected_by_bucket[bucket_idx]) >= target_top_k:
                continue
            # Use 0.92 threshold strictly
            if self._is_unrelated(idx, selected_global, similarity_matrix, 0.92):
                selected_by_bucket[bucket_idx].append(idx)
                selected_global.append(idx)

        # Removed the 'filling' logic that was pulling back similar items.
        # Now it will only return items that truly pass the 0.92 threshold,
        # up to target_top_k.

        for bucket_idx, bucket in enumerate(buckets):
            selected_indices = selected_by_bucket.get(bucket_idx, [])
            bucket["memories"] = [flat[i][1] for i in selected_indices]
        return results

    @staticmethod
    def _is_unrelated(
        index: int,
        selected_indices: list[int],
        similarity_matrix: list[list[float]],
        similarity_threshold: float,
    ) -> bool:
        return all(similarity_matrix[index][j] <= similarity_threshold for j in selected_indices)

    @staticmethod
    def _max_similarity(
        index: int, selected_indices: list[int], similarity_matrix: list[list[float]]
    ) -> float:
        if not selected_indices:
            return 0.0
        return max(similarity_matrix[index][j] for j in selected_indices)

    @staticmethod
    def _extract_embeddings(memories: list[dict[str, Any]]) -> list[list[float]] | None:
        embeddings: list[list[float]] = []
        for mem in memories:
            embedding = mem.get("metadata", {}).get("embedding")
            if not embedding:
                return None
            embeddings.append(embedding)
        return embeddings

    @staticmethod
    def _strip_embeddings(results: dict[str, Any]) -> None:
        for bucket in results.get("text_mem", []):
            for mem in bucket.get("memories", []):
                metadata = mem.get("metadata", {})
                if "embedding" in metadata:
                    metadata["embedding"] = []
        for bucket in results.get("tool_mem", []):
            for mem in bucket.get("memories", []):
                metadata = mem.get("metadata", {})
                if "embedding" in metadata:
                    metadata["embedding"] = []

    def _resolve_cube_ids(self, search_req: APISearchRequest) -> list[str]:
        """
        Normalize target cube ids from search_req.
        Priority:
        1) readable_cube_ids (deprecated mem_cube_id is converted to this in model validator)
        2) fallback to user_id
        """
        if search_req.readable_cube_ids:
            return list(dict.fromkeys(search_req.readable_cube_ids))

        return [search_req.user_id]

    def _build_cube_view(self, search_req: APISearchRequest) -> MemCubeView:
        cube_ids = self._resolve_cube_ids(search_req)

        if len(cube_ids) == 1:
            cube_id = cube_ids[0]
            return SingleCubeView(
                cube_id=cube_id,
                naive_mem_cube=self.naive_mem_cube,
                mem_reader=self.mem_reader,
                mem_scheduler=self.mem_scheduler,
                logger=self.logger,
                searcher=self.searcher,
                deepsearch_agent=self.deepsearch_agent,
            )
        else:
            single_views = [
                SingleCubeView(
                    cube_id=cube_id,
                    naive_mem_cube=self.naive_mem_cube,
                    mem_reader=self.mem_reader,
                    mem_scheduler=self.mem_scheduler,
                    logger=self.logger,
                    searcher=self.searcher,
                    deepsearch_agent=self.deepsearch_agent,
                )
                for cube_id in cube_ids
            ]
            return CompositeCubeView(cube_views=single_views, logger=self.logger)

    def handle_context_aware_search(
        self,
        search_req: APISearchRequest,
        chat_context: list[dict[str, str]] | None = None,
    ) -> SearchResponse:
        """
        Context-aware search that uses LLM to analyze intent and expand queries.

        This enhanced search:
        1. Analyzes the query + conversation context to understand intent
        2. Extracts entities and generates expanded queries
        3. Performs the standard search with enhanced parameters
        4. Merges and deduplicates results from original + expanded queries

        Args:
            search_req: Standard search request
            chat_context: Recent conversation messages for context

        Returns:
            SearchResponse with enhanced results
        """
        if not self.context_aware_searcher:
            self.logger.warning(
                "[SearchHandler] Context-aware searcher unavailable (no LLM), "
                "falling back to standard search"
            )
            return self.handle_search_memories(search_req)

        # Step 1: Analyze intent
        start_time = time.time()
        enhanced_params = self.context_aware_searcher.enhance_search_params(
            query=search_req.query,
            context=chat_context or (
                [{"role": m.get("role", "user"), "content": m.get("content", "")}
                 for m in search_req.chat_history]
                if search_req.chat_history else None
            ),
            base_top_k=search_req.top_k,
        )
        intent_time = time.time() - start_time
        self.logger.info(
            f"[SearchHandler] Intent analysis took {intent_time:.2f}s: "
            f"type={enhanced_params['intent'].intent_type}, "
            f"entities={enhanced_params['core_entities']}, "
            f"expansions={len(enhanced_params['expanded_queries'])}"
        )

        # Step 2: Perform primary search with original query
        primary_results = self.handle_search_memories(search_req)

        # Step 3: Perform expanded searches (limit to 2 extra queries)
        expanded_queries = enhanced_params.get("expanded_queries", [])[:2]
        if not expanded_queries:
            # Add intent metadata to response
            return self._enrich_response_with_intent(primary_results, enhanced_params)

        all_memory_ids = self._extract_memory_ids(primary_results)

        for exp_query in expanded_queries:
            try:
                exp_req = search_req.model_copy()
                exp_req.query = exp_query
                exp_req.top_k = max(3, search_req.top_k // 2)

                exp_results = self.handle_search_memories(exp_req)

                # Merge unique results
                self._merge_results(primary_results, exp_results, all_memory_ids)

            except Exception as e:
                self.logger.warning(
                    f"[SearchHandler] Expanded search failed for '{exp_query[:30]}...': {e}"
                )

        return self._enrich_response_with_intent(primary_results, enhanced_params)

    def _extract_memory_ids(self, response: SearchResponse) -> set[str]:
        """Extract all memory IDs from a search response."""
        ids = set()
        if not response.data:
            return ids

        data = response.data
        if isinstance(data, dict):
            for bucket in data.get("text_mem", []):
                for mem in bucket.get("memories", []):
                    mem_id = mem.get("id") or mem.get("metadata", {}).get("id")
                    if mem_id:
                        ids.add(mem_id)
        return ids

    def _merge_results(
        self,
        primary: SearchResponse,
        expanded: SearchResponse,
        seen_ids: set[str],
    ) -> None:
        """Merge expanded search results into primary results, avoiding duplicates."""
        if not expanded.data or not primary.data:
            return

        primary_data = primary.data
        expanded_data = expanded.data

        if not isinstance(primary_data, dict) or not isinstance(expanded_data, dict):
            return

        primary_buckets = primary_data.get("text_mem", [])
        expanded_buckets = expanded_data.get("text_mem", [])

        # Match buckets by cube_id and append new memories
        for exp_bucket in expanded_buckets:
            exp_cube_id = exp_bucket.get("cube_id", "")

            # Find matching primary bucket
            matched_bucket = None
            for p_bucket in primary_buckets:
                if p_bucket.get("cube_id", "") == exp_cube_id:
                    matched_bucket = p_bucket
                    break

            if matched_bucket is None and primary_buckets:
                matched_bucket = primary_buckets[0]

            if matched_bucket is None:
                continue

            for mem in exp_bucket.get("memories", []):
                mem_id = mem.get("id") or mem.get("metadata", {}).get("id")
                if mem_id and mem_id not in seen_ids:
                    seen_ids.add(mem_id)
                    matched_bucket.setdefault("memories", []).append(mem)

    @staticmethod
    def _enrich_response_with_intent(
        response: SearchResponse,
        enhanced_params: dict[str, Any],
    ) -> SearchResponse:
        """Add intent analysis metadata to the search response."""
        # We don't modify the response model structure, but log the enhancement
        intent = enhanced_params.get("intent")
        if intent:
            logger.info(
                f"[SearchHandler] Context-aware search completed: "
                f"intent={intent.intent_type}, "
                f"entities={intent.core_entities}, "
                f"expanded_queries={intent.expanded_queries}"
            )
        return response
