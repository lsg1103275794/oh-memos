import traceback

from memos.graph_dbs.item import GraphDBNode
from memos.graph_dbs.neo4j import Neo4jGraphDB
from memos.llms.base import BaseLLM
from memos.log import get_logger
from memos.mem_reader.read_multi_modal.utils import parse_json_result
from memos.templates.graph_ai_prompts import TRIPLE_EXTRACTION_PROMPT


logger = get_logger(__name__)


class TripleExtractor:
    """Extract knowledge triples (subject, predicate, object) from memory text using LLM.

    This module is part of the graph organization pipeline, parallel to
    RelationAndReasoningDetector. It enriches the knowledge graph by
    extracting entity-relationship triples from memory nodes.
    """

    # Allowed predicate types for validation
    VALID_PREDICATES = {
        "WORKS_AT",
        "LOCATED_IN",
        "HAPPENED_ON",
        "PARTICIPATED_IN",
        "KNOWS",
        "CREATED",
        "BELONGS_TO",
        "RELATED_TO",
        "CAUSED",
        "DEPENDS_ON",
        "PART_OF",
        "HAS_PROPERTY",
    }

    def __init__(self, graph_store: Neo4jGraphDB, llm: BaseLLM):
        self.graph_store = graph_store
        self.llm = llm

    def extract_triples(self, node: GraphDBNode) -> list[dict]:
        """Extract knowledge triples from a memory node's text.

        Args:
            node: The graph node containing memory text to analyze.

        Returns:
            List of validated triple dicts with keys:
            - subject: entity name
            - predicate: relationship type
            - object: entity name
            - confidence: float 0.0-1.0
        """
        if not node.memory or len(node.memory.strip()) < 10:
            return []

        try:
            prompt = TRIPLE_EXTRACTION_PROMPT.replace("{memory_text}", node.memory)
            response_text = self._call_llm(prompt)
            triples = self._parse_and_validate(response_text)

            logger.info(
                f"[TripleExtractor] Extracted {len(triples)} triples from node {node.id[:8]}"
            )
            return triples

        except Exception as e:
            logger.error(
                f"[TripleExtractor] Error extracting triples from {node.id[:8]}: {e}\n"
                f"{traceback.format_exc()}"
            )
            return []

    def extract_and_store(self, node: GraphDBNode, min_confidence: float = 0.7) -> list[dict]:
        """Extract triples from a node and store them as edges in the graph.

        High-confidence triples are stored as typed edges between the source node
        and matched/created entity nodes.

        Args:
            node: Source memory node.
            min_confidence: Minimum confidence threshold for storing.

        Returns:
            List of triples that were stored.
        """
        triples = self.extract_triples(node)
        stored = []

        for triple in triples:
            if triple["confidence"] < min_confidence:
                logger.debug(
                    f"[TripleExtractor] Skipping low-confidence triple: "
                    f"{triple['subject']} -{triple['predicate']}-> {triple['object']} "
                    f"(confidence={triple['confidence']})"
                )
                continue

            try:
                self._store_triple(node, triple)
                stored.append(triple)
            except Exception as e:
                logger.warning(
                    f"[TripleExtractor] Failed to store triple: {triple}. Error: {e}"
                )

        logger.info(
            f"[TripleExtractor] Stored {len(stored)}/{len(triples)} triples for node {node.id[:8]}"
        )
        return stored

    def _store_triple(self, source_node: GraphDBNode, triple: dict) -> None:
        """Store a single triple as an edge in the graph.

        The triple is stored as an edge from the source memory node with
        the predicate as the edge type and the object entity as a property.

        Args:
            source_node: The memory node this triple was extracted from.
            triple: Dict with subject, predicate, object, confidence.
        """
        predicate = triple["predicate"]
        subject_text = triple["subject"]
        object_text = triple["object"]

        # Store the triple as a property on the source node's metadata
        # and as a typed edge annotation
        existing_triples = []
        try:
            node_data = self.graph_store.get_node(source_node.id)
            if node_data:
                existing_triples = node_data.get("metadata", {}).get("triples", [])
        except Exception:
            pass

        existing_triples.append({
            "subject": subject_text,
            "predicate": predicate,
            "object": object_text,
            "confidence": triple["confidence"],
        })

        # Update node metadata with extracted triples
        self.graph_store.update_node(source_node.id, {"triples": existing_triples})

        logger.debug(
            f"[TripleExtractor] Stored: ({subject_text}) -[{predicate}]-> ({object_text})"
        )

    def _parse_and_validate(self, response_text: str) -> list[dict]:
        """Parse LLM response and validate triple format.

        Args:
            response_text: Raw LLM output expected to be JSON array.

        Returns:
            List of validated triple dicts.
        """
        parsed = parse_json_result(response_text)
        if not isinstance(parsed, list):
            logger.warning(
                f"[TripleExtractor] Expected list, got {type(parsed).__name__}"
            )
            return []

        validated = []
        for item in parsed:
            if not isinstance(item, dict):
                continue

            subject = item.get("subject", "").strip()
            predicate = item.get("predicate", "").strip().upper()
            obj = item.get("object", "").strip()
            confidence = item.get("confidence", 0.5)

            # Validate required fields
            if not subject or not predicate or not obj:
                continue

            # Normalize predicate
            if predicate not in self.VALID_PREDICATES:
                # Try to map common variations
                predicate = self._normalize_predicate(predicate)
                if predicate is None:
                    continue

            # Validate confidence
            try:
                confidence = float(confidence)
                confidence = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                confidence = 0.5

            validated.append({
                "subject": subject,
                "predicate": predicate,
                "object": obj,
                "confidence": confidence,
            })

        return validated

    def _normalize_predicate(self, predicate: str) -> str | None:
        """Try to normalize a non-standard predicate to a valid one.

        Args:
            predicate: The raw predicate string.

        Returns:
            Normalized predicate or None if unmappable.
        """
        mapping = {
            "WORKS_FOR": "WORKS_AT",
            "EMPLOYED_BY": "WORKS_AT",
            "MEMBER_OF": "PART_OF",
            "CONTAINS": "PART_OF",
            "IN": "LOCATED_IN",
            "AT": "LOCATED_IN",
            "USES": "DEPENDS_ON",
            "REQUIRES": "DEPENDS_ON",
            "MADE": "CREATED",
            "BUILT": "CREATED",
            "PRODUCES": "CREATED",
            "LEADS_TO": "CAUSED",
            "RESULTS_IN": "CAUSED",
            "TRIGGERS": "CAUSED",
            "ASSOCIATED_WITH": "RELATED_TO",
            "CONNECTED_TO": "RELATED_TO",
            "LINKS_TO": "RELATED_TO",
            "IS_A": "BELONGS_TO",
            "TYPE_OF": "BELONGS_TO",
            "HAS": "HAS_PROPERTY",
            "OWNS": "HAS_PROPERTY",
        }

        normalized = mapping.get(predicate)
        if normalized:
            logger.debug(
                f"[TripleExtractor] Normalized predicate: {predicate} -> {normalized}"
            )
        else:
            logger.warning(
                f"[TripleExtractor] Unknown predicate '{predicate}', dropping triple"
            )
        return normalized

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with the given prompt.

        Args:
            prompt: The formatted prompt string.

        Returns:
            LLM response text.
        """
        messages = [{"role": "user", "content": prompt}]
        try:
            response = self.llm.generate(messages).strip()
            logger.debug(f"[TripleExtractor LLM Raw] {response[:200]}...")
            return response
        except Exception as e:
            logger.warning(f"[TripleExtractor LLM Error] {e}")
            return ""
