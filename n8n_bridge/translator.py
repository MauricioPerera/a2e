"""
A2E → n8n Workflow Translator

Takes an A2E workflow (JSONL or compact format) and produces
n8n-compatible workflow JSON that can be imported or pushed via API.

This module is read-only with respect to A2E — it imports the executor
only to reuse its parsing logic, never modifies it.
"""

import json
import uuid
import logging
from typing import Any, Dict, List, Optional, Tuple

from .node_mapping import NODE_MAPPING

logger = logging.getLogger(__name__)


class A2EToN8nTranslator:
    """
    Translates A2E workflow definitions into n8n workflow JSON.

    Supports both A2E formats:
      - JSONL (operationUpdate + beginExecution messages)
      - Compact (single JSON with operations array)

    Usage:
        translator = A2EToN8nTranslator()
        n8n_workflow = translator.translate(a2e_workflow_str)
        # n8n_workflow is a dict ready for n8n API or JSON export
    """

    # Layout constants for visual positioning in n8n canvas
    X_START = 250
    X_SPACING = 250
    Y_CENTER = 300
    Y_BRANCH_OFFSET = 150

    def __init__(self, workflow_name: Optional[str] = None):
        self.workflow_name = workflow_name or "A2E Translated Workflow"
        self._warnings: List[str] = []

    def translate(
        self,
        a2e_workflow: str,
        *,
        name: Optional[str] = None,
        add_manual_trigger: bool = True,
    ) -> Dict[str, Any]:
        """
        Translate an A2E workflow string into n8n workflow JSON.

        Args:
            a2e_workflow: A2E workflow as JSONL or compact JSON string.
            name: Optional workflow name override.
            add_manual_trigger: Whether to prepend a Manual Trigger node.

        Returns:
            n8n workflow dict with nodes, connections, and metadata.
        """
        self._warnings = []
        operations, execution_root = self._parse_a2e(a2e_workflow)

        if not operations:
            raise ValueError("No operations found in A2E workflow")

        # Build ordered operation list starting from root
        ordered = self._resolve_execution_order(operations, execution_root)

        # Translate each operation to n8n node
        nodes = []
        node_names: Dict[str, str] = {}  # op_id → node_name

        if add_manual_trigger:
            trigger_node = self._make_trigger_node()
            nodes.append(trigger_node)

        for idx, (op_id, op_type, config) in enumerate(ordered):
            node = self._translate_operation(op_id, op_type, config, idx)
            if node:
                nodes.append(node)
                node_names[op_id] = node["name"]
            else:
                self._warnings.append(
                    f"Operation '{op_id}' ({op_type}) could not be translated"
                )

        # Build connections
        connections = self._build_connections(
            ordered, node_names, add_manual_trigger
        )

        wf_name = name or self.workflow_name

        return {
            "name": wf_name,
            "nodes": nodes,
            "connections": connections,
            "settings": {
                "executionOrder": "v1",
            },
            "_a2e_meta": {
                "a2e_source": True,
            },
            "_a2e_translation": {
                "warnings": self._warnings,
                "operation_count": len(ordered),
                "node_count": len(nodes),
            },
        }

    @property
    def warnings(self) -> List[str]:
        """Warnings generated during last translation."""
        return self._warnings

    # ─── Parsing ──────────────────────────────────────────────────────

    def _parse_a2e(
        self, workflow_str: str
    ) -> Tuple[Dict[str, Tuple[str, Dict]], Optional[str]]:
        """
        Parse A2E workflow string into operations dict and root ID.

        Returns:
            (operations, root_id) where operations is {id: (op_type, config)}
        """
        stripped = workflow_str.strip()

        # Try compact format first
        if stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict) and "operations" in parsed:
                    return self._parse_compact(parsed)
            except json.JSONDecodeError:
                pass

        # JSONL format
        return self._parse_jsonl(stripped)

    def _parse_compact(
        self, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Tuple[str, Dict]], Optional[str]]:
        """Parse compact format."""
        operations = {}
        for op_def in data.get("operations", []):
            op_id = op_def.get("id", str(uuid.uuid4())[:8])
            op_type = op_def.get("op", "")
            # Config is everything except id and op
            config = {k: v for k, v in op_def.items() if k not in ("id", "op")}
            operations[op_id] = (op_type, config)

        root = data.get("execute")
        return operations, root

    def _parse_jsonl(
        self, workflow_str: str
    ) -> Tuple[Dict[str, Tuple[str, Dict]], Optional[str]]:
        """Parse JSONL format (operationUpdate + beginExecution)."""
        operations = {}
        root = None

        for line in workflow_str.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError as e:
                logger.warning("Skipping invalid JSONL line: %s — content: %.120s", e, line)
                self._warnings.append(f"Invalid JSONL line (skipped): {line[:80]}")
                continue

            if "operationUpdate" in msg:
                for op_def in msg["operationUpdate"].get("operations", []):
                    op_id = op_def.get("id")
                    operation = op_def.get("operation", {})
                    if op_id and operation:
                        # operation is {OpType: config}
                        for op_type, config in operation.items():
                            operations[op_id] = (op_type, config)
                            break

            elif "beginExecution" in msg:
                root = msg["beginExecution"].get("root")

        return operations, root

    # ─── Execution order ──────────────────────────────────────────────

    def _resolve_execution_order(
        self,
        operations: Dict[str, Tuple[str, Dict]],
        root: Optional[str],
    ) -> List[Tuple[str, str, Dict]]:
        """
        Resolve execution order as list of (op_id, op_type, config).
        Uses DAG dependencies when available, falls back to insertion order.
        """
        # Build dependency graph from inputPath references
        deps: Dict[str, List[str]] = {op_id: [] for op_id in operations}
        output_map: Dict[str, str] = {}  # path_segment → op_id

        for op_id, (op_type, config) in operations.items():
            output_path = config.get("outputPath", f"/workflow/{op_id}")
            segments = [s for s in output_path.split("/") if s and s != "workflow"]
            if segments:
                output_map[segments[-1]] = op_id

        for op_id, (op_type, config) in operations.items():
            input_path = config.get("inputPath", "")
            if input_path:
                segments = [
                    s for s in input_path.split("/") if s and s != "workflow"
                ]
                if segments:
                    dep_id = output_map.get(segments[-1])
                    if dep_id and dep_id != op_id:
                        deps[op_id].append(dep_id)

        # Topological sort
        ordered_ids = []
        visited = set()
        temp = set()

        def visit(node_id: str):
            if node_id in temp:
                return  # cycle — skip
            if node_id in visited:
                return
            temp.add(node_id)
            for dep in deps.get(node_id, []):
                visit(dep)
            temp.discard(node_id)
            visited.add(node_id)
            ordered_ids.append(node_id)

        # Start from root if specified
        if root and root in operations:
            visit(root)
        # Then visit remaining
        for op_id in operations:
            if op_id not in visited:
                visit(op_id)

        return [
            (op_id, operations[op_id][0], operations[op_id][1])
            for op_id in ordered_ids
        ]

    # ─── Node translation ─────────────────────────────────────────────

    def _make_trigger_node(self) -> Dict[str, Any]:
        """Create the Manual Trigger start node."""
        return {
            "parameters": {},
            "id": str(uuid.uuid4()),
            "name": "Manual Trigger",
            "type": "n8n-nodes-base.manualTrigger",
            "typeVersion": 1,
            "position": [self.X_START, self.Y_CENTER],
        }

    def _translate_operation(
        self,
        op_id: str,
        op_type: str,
        config: Dict[str, Any],
        index: int,
    ) -> Optional[Dict[str, Any]]:
        """Translate a single A2E operation into an n8n node."""
        mapping = NODE_MAPPING.get(op_type)
        if not mapping:
            self._warnings.append(
                f"No n8n mapping for operation type '{op_type}'"
            )
            # Fallback: use Code node with a comment
            return self._make_fallback_node(op_id, op_type, config, index)

        translate_fn = mapping["translate"]
        try:
            parameters = translate_fn(config)
        except Exception as e:
            self._warnings.append(
                f"Error translating '{op_id}' ({op_type}): {e}"
            )
            return self._make_fallback_node(op_id, op_type, config, index)

        # Sanitize node name (n8n requires unique names)
        node_name = self._make_node_name(op_id, op_type)

        return {
            "parameters": parameters,
            "id": str(uuid.uuid4()),
            "name": node_name,
            "type": mapping["n8n_type"],
            "typeVersion": mapping["type_version"],
            "position": [
                self.X_START + (index + 1) * self.X_SPACING,
                self.Y_CENTER,
            ],
        }

    def _make_fallback_node(
        self,
        op_id: str,
        op_type: str,
        config: Dict[str, Any],
        index: int,
    ) -> Dict[str, Any]:
        """Create a Code node placeholder for unsupported operations."""
        return {
            "parameters": {
                "jsCode": (
                    f"// A2E operation: {op_type} (id: {op_id})\n"
                    f"// Original config: {json.dumps(config, indent=2)}\n"
                    f"// TODO: Implement this operation in n8n\n"
                    f"return items;"
                ),
                "mode": "runOnceForAllItems",
            },
            "id": str(uuid.uuid4()),
            "name": self._make_node_name(op_id, op_type),
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [
                self.X_START + (index + 1) * self.X_SPACING,
                self.Y_CENTER,
            ],
        }

    def _make_node_name(self, op_id: str, op_type: str) -> str:
        """Generate a readable n8n node name from A2E op."""
        return f"{op_type} ({op_id})"

    # ─── Connections ──────────────────────────────────────────────────

    def _build_connections(
        self,
        ordered: List[Tuple[str, str, Dict]],
        node_names: Dict[str, str],
        has_trigger: bool,
    ) -> Dict[str, Any]:
        """
        Build n8n connections dict.
        Linear chain: trigger → op1 → op2 → ... → opN
        Conditional nodes get true/false branches.
        """
        connections: Dict[str, Any] = {}
        names_list = []

        if has_trigger:
            names_list.append("Manual Trigger")

        for op_id, op_type, config in ordered:
            if op_id in node_names:
                names_list.append(node_names[op_id])

        # Connect sequentially
        for i in range(len(names_list) - 1):
            source = names_list[i]
            target = names_list[i + 1]
            connections[source] = {
                "main": [
                    [{"node": target, "type": "main", "index": 0}]
                ]
            }

        # For Conditional nodes, add second output (false branch)
        for op_id, op_type, config in ordered:
            if op_type == "Conditional" and op_id in node_names:
                node_name = node_names[op_id]
                then_id = config.get("then")
                else_id = config.get("else")
                if then_id and then_id in node_names:
                    true_conn = [{"node": node_names[then_id], "type": "main", "index": 0}]
                else:
                    true_conn = connections.get(node_name, {}).get("main", [[]])[0]
                false_conn = []
                if else_id and else_id in node_names:
                    false_conn = [{"node": node_names[else_id], "type": "main", "index": 0}]
                connections[node_name] = {
                    "main": [true_conn if isinstance(true_conn, list) else [true_conn], false_conn]
                }

        return connections

    # ─── Convenience methods ──────────────────────────────────────────

    def translate_to_json(
        self, a2e_workflow: str, *, indent: int = 2, **kwargs
    ) -> str:
        """Translate and return as formatted JSON string."""
        result = self.translate(a2e_workflow, **kwargs)
        return json.dumps(result, indent=indent, ensure_ascii=False)

    def translate_file(
        self, input_path: str, output_path: str, **kwargs
    ) -> Dict[str, Any]:
        """Read A2E workflow from file, write n8n workflow to file."""
        with open(input_path, "r", encoding="utf-8") as f:
            a2e_content = f.read()

        result = self.translate(a2e_content, **kwargs)

        # Remove internal metadata before writing
        export = {k: v for k, v in result.items() if not k.startswith("_")}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2, ensure_ascii=False)

        return result

    @staticmethod
    def supported_operations() -> List[str]:
        """List A2E operations that have n8n mappings."""
        return sorted(NODE_MAPPING.keys())
