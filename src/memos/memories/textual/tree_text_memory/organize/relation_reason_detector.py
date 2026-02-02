import json
import os
import traceback

from memos.embedders.factory import OllamaEmbedder
from memos.graph_dbs.item import GraphDBNode
from memos.graph_dbs.neo4j import Neo4jGraphDB
from memos.llms.base import BaseLLM
from memos.log import get_logger
from memos.mem_reader.read_multi_modal.utils import parse_json_result
from memos.memories.textual.item import TreeNodeTextualMemoryMetadata
from memos.templates.tree_reorganize_prompts import (
    AGGREGATE_PROMPT,
    BATCH_PAIRWISE_RELATION_PROMPT,
    INFER_FACT_PROMPT,
)


logger = get_logger(__name__)


class RelationAndReasoningDetector:
    def __init__(self, graph_store: Neo4jGraphDB, llm: BaseLLM, embedder: OllamaEmbedder):
        self.graph_store = graph_store
        self.llm = llm
        self.embedder = embedder
        self.relation_parse_strict = os.getenv("MOS_RELATION_PARSE_STRICT", "false").lower() == "true"
        self.relation_parse_retry = os.getenv("MOS_RELATION_PARSE_RETRY", "false").lower() == "true"

    def process_node(self, node: GraphDBNode, exclude_ids: list[str], top_k: int = 5):
        """
        Unified pipeline for:
        1) Pairwise relations (cause, condition, conflict, relate)
        2) Inferred nodes
        3) Sequence links
        4) Aggregate concepts
        """
        results = {
            "relations": [],
            "inferred_nodes": [],
            "sequence_links": [],
            "aggregate_nodes": [],
        }
        try:
            if node.metadata.type == "reasoning":
                logger.info(f"Skip reasoning for inferred node {node.id}")
                return {
                    "relations": [],
                    "inferred_nodes": [],
                    "sequence_links": [],
                    "aggregate_nodes": [],
                }

            # Get nearby nodes by tag overlap
            nearest = self.graph_store.get_neighbors_by_tag(
                tags=node.metadata.tags,
                exclude_ids=exclude_ids,
                top_k=top_k,
                min_overlap=2,
            )
            nearest = [GraphDBNode(**cand_data) for cand_data in nearest]

            # 1) Pairwise relations (including CAUSE/CONDITION/CONFLICT)
            pairwise = self._detect_pairwise_causal_condition_relations(node, nearest)
            results["relations"].extend(pairwise["relations"])

            # 2) Inferred nodes (from causal/condition)
            inferred = self._infer_fact_nodes_from_relations(pairwise)
            results["inferred_nodes"].extend(inferred)

            # 3) Sequence (FOLLOWS relations based on timestamps)
            seq = self._detect_sequence_links(node, nearest)
            results["sequence_links"].extend(seq)

            # 4) Aggregate
            # agg = self._detect_aggregate_node_for_group(node, nearest, min_group_size=5)
            # if agg:
            #     results["aggregate_nodes"].append(agg)

        except Exception as e:
            logger.error(
                f"Error {e} while process struct reorganize: trace: {traceback.format_exc()}"
            )
        return results

    def _detect_pairwise_causal_condition_relations(
        self, node: GraphDBNode, nearest_nodes: list[GraphDBNode]
    ):
        """
        Vector/tag search ➜ Batch use LLM to decide:
        - CAUSE
        - CONDITION
        - RELATE
        - CONFLICT
        """
        results = {"relations": []}
        if not nearest_nodes:
            return results

        node_pairs = []
        for idx, candidate in enumerate(nearest_nodes):
            node_pairs.append({"id": idx, "node1": node.memory, "node2": candidate.memory})

        prompt = BATCH_PAIRWISE_RELATION_PROMPT.replace("{node_pairs}", json.dumps(node_pairs, ensure_ascii=False))
        response_text = self._call_llm(prompt)
        batch_results = self._parse_json_result(response_text)

        if not isinstance(batch_results, list):
            if self.relation_parse_retry:
                response_text = self._call_llm(
                    "Only output a JSON array of objects with keys pair_id and relation.\n" + prompt
                )
                batch_results = self._parse_json_result(response_text)

        if not isinstance(batch_results, list) or len(batch_results) == 0:
            self._log_parse_failure(
                "pairwise",
                node,
                response_text,
                len(nearest_nodes),
            )
            if self.relation_parse_strict:
                raise ValueError("Relation parse failed in pairwise relation detection")
            return results

        for res in batch_results:
            pair_id = res.get("pair_id")
            relation_type = res.get("relation", "NONE").upper()

            if pair_id is not None and 0 <= pair_id < len(nearest_nodes):
                candidate = nearest_nodes[pair_id]
                if relation_type in {"CAUSE", "CONDITION", "RELATE", "CONFLICT"}:
                    results["relations"].append(
                        {
                            "source_id": node.id,
                            "target_id": candidate.id,
                            "relation_type": relation_type,
                        }
                    )
                    logger.info(
                        f"[RelationDetector] Detected batch relation: {relation_type} between {node.id[:8]} and {candidate.id[:8]}"
                    )

        return results

    def _infer_fact_nodes_from_relations(self, pairwise_results: dict):
        inferred_nodes = []
        for rel in pairwise_results["relations"]:
            if rel["relation_type"] in ("CAUSE", "CONDITION"):
                src = self.graph_store.get_node(rel["source_id"])
                tgt = self.graph_store.get_node(rel["target_id"])
                if not src or not tgt:
                    continue

                prompt = (
                    INFER_FACT_PROMPT.replace("{source}", src["memory"])
                    .replace("{target}", tgt["memory"])
                    .replace("{relation_type}", rel["relation_type"])
                )
                response_text = self._call_llm(prompt).strip()
                if not response_text:
                    continue
                embedding = self.embedder.embed([response_text])[0]

                inferred_nodes.append(
                    GraphDBNode(
                        memory=response_text,
                        metadata=src["metadata"].__class__(
                            user_id="",
                            session_id="",
                            memory_type="LongTermMemory",
                            status="activated",
                            key=f"InferredFact:{rel['relation_type']}",
                            tags=["inferred"],
                            embedding=embedding,
                            usage=[],
                            sources=[src["id"], tgt["id"]],
                            background=f"Inferred from {rel['relation_type']}",
                            confidence=0.9,
                            type="reasoning",
                        ),
                    )
                )
        return inferred_nodes

    def _detect_sequence_links(self, node: GraphDBNode, nearest_nodes: list[GraphDBNode]):
        """
        If node has timestamp, find other nodes to link FOLLOWS edges.
        Only link if they are temporally close (e.g., within 24 hours) or share specific tags.
        """
        results = []
        if not node.metadata.updated_at:
            return results

        for cand in nearest_nodes:
            if not cand.metadata.updated_at:
                continue
            
            # Simple temporal ordering
            if cand.metadata.updated_at < node.metadata.updated_at:
                results.append({"from_id": cand.id, "to_id": node.id})
                logger.info(f"[RelationDetector] Sequence link: {cand.id[:8]} FOLLOWS {node.id[:8]}")
            elif cand.metadata.updated_at > node.metadata.updated_at:
                results.append({"from_id": node.id, "to_id": cand.id})
                logger.info(f"[RelationDetector] Sequence link: {node.id[:8]} FOLLOWS {cand.id[:8]}")
        return results

    def _detect_aggregate_node_for_group(
        self, node: GraphDBNode, nearest_nodes: list[GraphDBNode], min_group_size: int = 3
    ):
        """
        If nodes share overlapping tags, LLM checks if they should be summarized into a new concept.
        """
        if len(nearest_nodes) < min_group_size:
            return None
        combined_nodes = [node, *nearest_nodes]

        joined = "\n".join(f"- {n.memory}" for n in combined_nodes)
        prompt = AGGREGATE_PROMPT.replace("{joined}", joined)
        response_text = self._call_llm(prompt)
        summary = self._parse_json_result(response_text)
        if not summary:
            return None
        embedding = self.embedder.embed([summary["value"]])[0]

        parent_node = GraphDBNode(
            memory=summary["value"],
            metadata=TreeNodeTextualMemoryMetadata(
                user_id="",  # TODO: summarized node: no user_id
                session_id="",  # TODO: summarized node: no session_id
                memory_type=node.metadata.memory_type,
                status="activated",
                key=summary["key"],
                tags=summary.get("tags", []),
                embedding=embedding,
                usage=[],
                sources=[n.id for n in nearest_nodes],
                background=summary.get("background", ""),
                confidence=0.99,
                type="reasoning",
            ),
        )
        return parent_node

    def _call_llm(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        try:
            response = self.llm.generate(messages).strip()
            logger.debug(f"[LLM Raw] {response}")
            return response
        except Exception as e:
            logger.warning(f"[LLM Error] {e}")
            return ""

    def _parse_json_result(self, response_text):
        return parse_json_result(response_text)

    def _log_parse_failure(
        self,
        stage: str,
        node: GraphDBNode,
        response_text: str,
        pair_count: int,
    ) -> None:
        snippet = (response_text or "").strip().replace("\n", " ")[:300]
        logger.warning(
            "[RelationDetector] JSON parse failed at %s for node=%s pairs=%s response_len=%s response_snippet=%s",
            stage,
            node.id,
            pair_count,
            len(response_text or ""),
            snippet,
        )

    def _parse_relation_result(self, response_text: str) -> str:
        """
        Normalize and validate the LLM relation type output.
        Extract only the first word from the response (LLM may include explanations).
        """
        valid = {"CAUSE", "CONDITION", "RELATE", "CONFLICT", "NONE"}

        # Get first line and first word only (LLM may add explanations after)
        first_line = response_text.strip().split('\n')[0].strip()
        # Extract first word, removing any markdown formatting
        first_word = first_line.split()[0].strip('*:.,') if first_line.split() else ""
        relation = first_word.upper()

        if relation not in valid:
            logger.warning(
                f"[RelationDetector] Unexpected relation type: {relation} (from: {first_line[:50]}...). Fallback to NONE."
            )
            return "NONE"

        logger.info(f"[RelationDetector] Detected relation: {relation}")
        return relation
