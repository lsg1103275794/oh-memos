"""
Context-Aware Searcher for intelligent memory retrieval.

This module provides context-aware search enhancement that uses LLM to:
1. Analyze search intent from query and conversation context
2. Extract explicit and implied entities
3. Generate query expansions for better recall
4. Suggest filters for more precise results
"""

import traceback

from dataclasses import dataclass, field
from typing import Any

from memos.llms.base import BaseLLM
from memos.log import get_logger
from memos.mem_reader.read_multi_modal.utils import parse_json_result
from memos.templates.graph_ai_prompts import SEARCH_INTENT_PROMPT


logger = get_logger(__name__)


@dataclass
class SearchIntent:
    """Structured representation of analyzed search intent."""

    intent_type: str = "exploratory"  # factual, relational, temporal, causal, exploratory
    core_entities: list[str] = field(default_factory=list)
    implied_entities: list[str] = field(default_factory=list)
    time_scope: str | None = None
    expanded_queries: list[str] = field(default_factory=list)
    suggested_filters: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)


class ContextAwareSearcher:
    """Enhances search with context awareness using LLM analysis.

    This class analyzes the user's search query along with recent conversation
    context to understand the true intent and provide:
    - Query expansions for better recall
    - Entity extraction for graph-based filtering
    - Temporal awareness for time-sensitive searches
    - Filter suggestions for precision

    Usage:
        searcher = ContextAwareSearcher(llm)
        intent = searcher.analyze_intent(
            query="What was the error?",
            context=[
                {"role": "user", "content": "I'm debugging the login module"},
                {"role": "assistant", "content": "Let me help with that."}
            ]
        )
        # Use intent.expanded_queries for additional searches
        # Use intent.suggested_filters for filtering
    """

    # Maximum context messages to include
    MAX_CONTEXT_MESSAGES = 10

    # Maximum context character length
    MAX_CONTEXT_LENGTH = 2000

    def __init__(self, llm: BaseLLM):
        """Initialize with an LLM instance.

        Args:
            llm: Language model for intent analysis.
        """
        self.llm = llm

    def analyze_intent(
        self,
        query: str,
        context: list[dict[str, str]] | None = None,
    ) -> SearchIntent:
        """Analyze search intent from query and conversation context.

        Args:
            query: The user's search query.
            context: Recent conversation history as list of message dicts
                     with 'role' and 'content' keys.

        Returns:
            SearchIntent with analysis results.
        """
        if not query or not query.strip():
            return SearchIntent()

        try:
            context_text = self._format_context(context)
            prompt = SEARCH_INTENT_PROMPT.replace("{query}", query).replace(
                "{context}", context_text or "(No context provided)"
            )

            response_text = self._call_llm(prompt)
            parsed = self._parse_intent_response(response_text)

            intent = SearchIntent(
                intent_type=parsed.get("intent_type", "exploratory"),
                core_entities=parsed.get("core_entities", []),
                implied_entities=parsed.get("implied_entities", []),
                time_scope=parsed.get("time_scope"),
                expanded_queries=parsed.get("expanded_queries", []),
                suggested_filters=parsed.get("suggested_filters", {}),
                raw_response=parsed,
            )

            logger.info(
                f"[ContextAwareSearcher] Analyzed intent for '{query[:50]}...': "
                f"type={intent.intent_type}, entities={intent.core_entities}"
            )
            return intent

        except Exception as e:
            logger.error(
                f"[ContextAwareSearcher] Error analyzing intent: {e}\n"
                f"{traceback.format_exc()}"
            )
            return SearchIntent()

    def enhance_search_params(
        self,
        query: str,
        context: list[dict[str, str]] | None = None,
        base_top_k: int = 10,
    ) -> dict[str, Any]:
        """Generate enhanced search parameters based on intent analysis.

        This method analyzes the query and context, then returns enhanced
        search parameters that can be passed to the search system.

        Args:
            query: The user's search query.
            context: Recent conversation history.
            base_top_k: Base number of results to return.

        Returns:
            Dict with enhanced search parameters:
            - original_query: The original query
            - expanded_queries: Additional queries to search
            - combined_query: All queries combined for embedding
            - filter: Suggested filter conditions
            - top_k: Adjusted top_k based on intent
            - intent: The full SearchIntent object
        """
        intent = self.analyze_intent(query, context)

        # Combine original query with expansions for better recall
        all_queries = [query] + intent.expanded_queries[:3]
        combined_query = " | ".join(all_queries)

        # Adjust top_k based on intent type
        adjusted_top_k = base_top_k
        if intent.intent_type == "exploratory":
            adjusted_top_k = int(base_top_k * 1.5)  # More results for exploration
        elif intent.intent_type == "factual":
            adjusted_top_k = max(5, base_top_k // 2)  # Fewer, more precise results

        # Build filter from suggested filters
        search_filter = None
        if intent.suggested_filters:
            filter_conditions = []

            # Handle memory_type filter
            memory_type = intent.suggested_filters.get("memory_type")
            if memory_type:
                filter_conditions.append({"memory_type": memory_type})

            # Handle date_range filter
            date_range = intent.suggested_filters.get("date_range", {})
            if date_range.get("start"):
                filter_conditions.append({"created_at": {"gte": date_range["start"]}})
            if date_range.get("end"):
                filter_conditions.append({"created_at": {"lte": date_range["end"]}})

            if filter_conditions:
                search_filter = {"and": filter_conditions} if len(filter_conditions) > 1 else filter_conditions[0]

        return {
            "original_query": query,
            "expanded_queries": intent.expanded_queries,
            "combined_query": combined_query,
            "filter": search_filter,
            "top_k": adjusted_top_k,
            "intent": intent,
            "core_entities": intent.core_entities,
            "implied_entities": intent.implied_entities,
        }

    def extract_entities_for_graph_search(
        self,
        query: str,
        context: list[dict[str, str]] | None = None,
    ) -> list[str]:
        """Extract entities suitable for graph-based search.

        Combines core and implied entities from intent analysis,
        useful for finding related nodes in the knowledge graph.

        Args:
            query: The user's search query.
            context: Recent conversation history.

        Returns:
            List of entity names for graph traversal.
        """
        intent = self.analyze_intent(query, context)
        entities = intent.core_entities + intent.implied_entities
        # Deduplicate while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity.lower() not in seen:
                seen.add(entity.lower())
                unique_entities.append(entity)
        return unique_entities

    def _format_context(self, context: list[dict[str, str]] | None) -> str:
        """Format conversation context for the prompt.

        Args:
            context: List of message dicts.

        Returns:
            Formatted context string.
        """
        if not context:
            return ""

        # Take only recent messages
        recent = context[-self.MAX_CONTEXT_MESSAGES :]

        lines = []
        total_length = 0

        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Truncate individual messages if needed
            if len(content) > 500:
                content = content[:500] + "..."

            line = f"{role}: {content}"
            if total_length + len(line) > self.MAX_CONTEXT_LENGTH:
                break

            lines.append(line)
            total_length += len(line)

        return "\n".join(lines)

    def _parse_intent_response(self, response_text: str) -> dict[str, Any]:
        """Parse the LLM response into structured data.

        Args:
            response_text: Raw LLM output.

        Returns:
            Parsed dict with intent fields.
        """
        parsed = parse_json_result(response_text)

        if not isinstance(parsed, dict):
            logger.warning(
                f"[ContextAwareSearcher] Expected dict, got {type(parsed).__name__}"
            )
            return {}

        # Validate and normalize fields
        result = {}

        # Intent type
        intent_type = parsed.get("intent_type", "").lower()
        valid_types = {"factual", "relational", "temporal", "causal", "exploratory"}
        result["intent_type"] = intent_type if intent_type in valid_types else "exploratory"

        # Entities
        result["core_entities"] = self._validate_string_list(
            parsed.get("core_entities", [])
        )
        result["implied_entities"] = self._validate_string_list(
            parsed.get("implied_entities", [])
        )

        # Time scope
        result["time_scope"] = parsed.get("time_scope")

        # Expanded queries
        result["expanded_queries"] = self._validate_string_list(
            parsed.get("expanded_queries", [])
        )

        # Suggested filters
        filters = parsed.get("suggested_filters", {})
        if isinstance(filters, dict):
            result["suggested_filters"] = filters
        else:
            result["suggested_filters"] = {}

        return result

    @staticmethod
    def _validate_string_list(value: Any) -> list[str]:
        """Validate and convert to list of strings.

        Args:
            value: Input value to validate.

        Returns:
            List of non-empty strings.
        """
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if item and str(item).strip()]

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt.

        Args:
            prompt: The formatted prompt.

        Returns:
            LLM response text.
        """
        messages = [{"role": "user", "content": prompt}]
        try:
            response = self.llm.generate(messages).strip()
            logger.debug(f"[ContextAwareSearcher LLM Raw] {response[:300]}...")
            return response
        except Exception as e:
            logger.warning(f"[ContextAwareSearcher LLM Error] {e}")
            return ""
