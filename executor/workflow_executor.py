"""
Ejecutor consolidado de workflows A2E
Reemplaza los 5 ejecutores separados con un modulo unico basado en composicion (middleware)

Refactored: handlers extracted into executor/handlers/, middleware into executor/middleware.py
"""

import asyncio
import json
import logging
import re
import time
import uuid
from typing import Dict, Any, List, Optional, Set

from .handlers import OPERATION_HANDLERS
from .handlers import (
    ApiHandlerMixin,
    DataHandlerMixin,
    DateTimeHandlerMixin,
    TextHandlerMixin,
    ValidationHandlerMixin,
    MathHandlerMixin,
    EncodingHandlerMixin,
    FlowHandlerMixin,
)
from .middleware import (
    ExecutorMiddleware,
    AuditMiddleware,
    CacheMiddleware,
    VaultMiddleware,
)

logger = logging.getLogger(__name__)

# Intentar importar pytz, pero no fallar si no esta disponible
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    logger.warning("pytz not available. Timezone operations will be limited.")


# ---------------------------------------------------------------------------
# Ejecutor principal
# ---------------------------------------------------------------------------

class WorkflowExecutor(
    ApiHandlerMixin,
    DataHandlerMixin,
    DateTimeHandlerMixin,
    TextHandlerMixin,
    ValidationHandlerMixin,
    MathHandlerMixin,
    EncodingHandlerMixin,
    FlowHandlerMixin,
):
    """
    Ejecuta workflows definidos en formato A2E.
    Soporta middlewares opcionales para auditoria, cache, vault, etc.
    """

    def __init__(self, middlewares=None):
        self.workflow_state: Dict[str, Any] = {}
        self.operations: Dict[str, Dict[str, Any]] = {}
        self.execution_order: List[str] = []
        self._middlewares: List[ExecutorMiddleware] = middlewares or []

        # Compatibilidad con MonitoredWorkflowExecutor
        self.current_execution_id: Optional[str] = None
        self.current_agent_id: Optional[str] = None

    # -- contexto de agente (compatibilidad) ---------------------------------

    def set_agent_context(self, agent_id: str):
        """Establece el contexto del agente para logging"""
        self.current_agent_id = agent_id

    # -- carga de workflow ---------------------------------------------------

    def load_workflow(self, workflow_jsonl: str, agent_id: Optional[str] = None):
        """Carga un workflow desde JSONL (legacy) o formato compacto (single JSON object)"""
        stripped = workflow_jsonl.strip()

        # Detect compact format: single JSON object with "operations" key
        if stripped.startswith("{"):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict) and "operations" in parsed:
                    self._load_compact_workflow(parsed)
                else:
                    # Single-line legacy JSONL
                    self._load_legacy_workflow(stripped)
            except json.JSONDecodeError:
                # Multi-line JSONL that happens to start with '{'
                self._load_legacy_workflow(stripped)
        else:
            self._load_legacy_workflow(stripped)

        # Generar ID de ejecucion
        self.current_execution_id = str(uuid.uuid4())
        if agent_id:
            self.current_agent_id = agent_id

        # Notificar middlewares
        for mw in self._middlewares:
            mw.on_execution_start(
                self.current_execution_id,
                workflow_jsonl,
                agent_id=self.current_agent_id,
            )

    def _load_legacy_workflow(self, workflow_jsonl: str):
        """Carga un workflow desde formato JSONL legacy"""
        lines = workflow_jsonl.strip().split('\n')

        for line in lines:
            if not line.strip():
                continue

            message = json.loads(line)

            if "operationUpdate" in message:
                self._process_operation_update(message["operationUpdate"])
            elif "beginExecution" in message:
                self._process_begin_execution(message["beginExecution"])

    def _load_compact_workflow(self, workflow: Dict[str, Any]):
        """
        Carga un workflow desde formato compacto (single JSON object).

        Compact format:
            {
              "operations": [
                {"id": "fetch", "op": "ApiCall", "url": "...", "method": "GET"},
                {"id": "filter", "op": "FilterData", "input": "fetch", ...}
              ],
              "execute": "fetch"
            }

        - "op" field specifies the operation type (flat, not nested)
        - "input" is a shorthand for inputPath: "/workflow/{input}"
        - outputPath defaults to "/workflow/{id}" when not specified
        - If "input" is omitted, implicitly uses the previous operation's output
        """
        ops = workflow.get("operations", [])
        prev_id = None

        for op_def in ops:
            op_id = op_def.get("id")
            op_type = op_def.get("op")
            if not op_id or not op_type:
                continue

            # Build operation config from all keys except id and op
            config = {}
            for key, value in op_def.items():
                if key in ("id", "op"):
                    continue
                config[key] = value

            # Resolve "input" shorthand to "inputPath"
            if "input" in config:
                input_ref = config.pop("input")
                config["inputPath"] = f"/workflow/{input_ref}"
            elif prev_id is not None and "inputPath" not in config:
                # Implicit piping: use previous operation's output,
                # but only if the operation doesn't already have its own data source
                _source_fields = ("value", "url", "sources", "expression", "text", "input_value")
                has_own_source = any(f in config for f in _source_fields)
                if not has_own_source:
                    config["inputPath"] = f"/workflow/{prev_id}"

            # Default outputPath to /workflow/{id}
            if "outputPath" not in config:
                config["outputPath"] = f"/workflow/{op_id}"

            # Store in internal format (same as legacy)
            self.operations[op_id] = {
                "id": op_id,
                "operation": {op_type: config}
            }
            logger.info(f"Loaded operation (compact): {op_id}")
            prev_id = op_id

        # Set execution order from array order, with root first
        root_id = workflow.get("execute")
        if root_id:
            self.execution_order = self._build_execution_order(root_id)
        else:
            self.execution_order = [op_def.get("id") for op_def in ops if op_def.get("id")]

    def _process_operation_update(self, update: Dict[str, Any]):
        """Procesa actualizacion de operaciones"""
        operations = update.get("operations", [])

        for op in operations:
            op_id = op.get("id")
            if op_id:
                self.operations[op_id] = op
                logger.info(f"Loaded operation: {op_id}")

    def _process_begin_execution(self, begin: Dict[str, Any]):
        """Procesa inicio de ejecucion"""
        root_id = begin.get("root")
        if root_id:
            self.execution_order = self._build_execution_order(root_id)
            logger.info(f"Execution order: {self.execution_order}")

    def _build_execution_order(self, root_id: str) -> List[str]:
        """Construye el orden de ejecucion basandose en dependencias"""
        order = []
        visited = set()

        def traverse(op_id: str):
            if op_id in visited or op_id not in self.operations:
                return
            visited.add(op_id)
            order.append(op_id)

        traverse(root_id)

        # Agregar operaciones restantes
        for op_id in self.operations:
            if op_id not in visited:
                order.append(op_id)

        return order

    # -- dependency graph & parallel execution --------------------------------

    def _extract_workflow_refs(self, obj: Any) -> Set[str]:
        """Recursively scan *obj* for ``/workflow/<op_id>`` references and
        return the set of referenced operation IDs."""
        refs: Set[str] = set()
        if isinstance(obj, str):
            for m in re.finditer(r'/workflow/([A-Za-z0-9_-]+)', obj):
                refs.add(m.group(1))
        elif isinstance(obj, dict):
            for v in obj.values():
                refs.update(self._extract_workflow_refs(v))
        elif isinstance(obj, list):
            for item in obj:
                refs.update(self._extract_workflow_refs(item))
        return refs

    def _collect_on_error_targets(self) -> Set[str]:
        """Return the set of operation IDs that are referenced ONLY as onError
        fallback targets."""
        on_error_targets: Set[str] = set()
        regular_refs: Set[str] = set()

        for op_id, op in self.operations.items():
            op_body = op.get("operation", {})
            if not op_body:
                continue
            op_type = list(op_body.keys())[0]
            config = op_body.get(op_type, {}) or {}
            on_error = config.get("onError")
            if isinstance(on_error, str):
                on_error_targets.add(on_error)

            path_refs = self._extract_workflow_refs(
                {k: v for k, v in config.items() if k != "onError"}
            )
            regular_refs.update(path_refs)

        return on_error_targets

    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build ``{op_id: set_of_dependency_op_ids}`` by inspecting each
        operation's config for ``/workflow/`` references."""
        on_error_only = self._collect_on_error_targets()
        all_op_ids = set(self.operations.keys()) - on_error_only
        graph: Dict[str, Set[str]] = {op_id: set() for op_id in all_op_ids}

        # Build outputPath-segment -> op_id mapping
        path_to_op: Dict[str, str] = {}
        for op_id, op in self.operations.items():
            path_to_op[op_id] = op_id
            op_body = op.get("operation", {})
            if op_body:
                op_type = list(op_body.keys())[0]
                config = op_body.get(op_type, {}) or {}
                output_path = config.get("outputPath", "")
                if isinstance(output_path, str) and output_path.startswith("/workflow/"):
                    segment = output_path.split("/")[2] if len(output_path.split("/")) > 2 else ""
                    if segment:
                        path_to_op[segment] = op_id

        for op_id, op in self.operations.items():
            if op_id not in all_op_ids:
                continue

            op_body = op.get("operation", {})
            if not op_body:
                continue

            op_type = list(op_body.keys())[0] if op_body else None
            config = op_body.get(op_type, {}) if op_type else {}

            scan_config = {k: v for k, v in config.items() if k != "onError"}
            path_refs = self._extract_workflow_refs(scan_config)

            input_ref = config.get("input")
            if isinstance(input_ref, str):
                path_refs.add(input_ref)

            resolved: Set[str] = set()
            for ref in path_refs:
                if ref in all_op_ids:
                    resolved.add(ref)
                elif ref in path_to_op and path_to_op[ref] in all_op_ids:
                    resolved.add(path_to_op[ref])

            resolved.discard(op_id)
            graph[op_id] = resolved

        return graph

    def _topological_levels(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Return a list of levels where each level contains operation IDs
        that can execute in parallel (Kahn's algorithm grouped by depth)."""
        in_degree: Dict[str, int] = {node: 0 for node in graph}
        for node, deps in graph.items():
            in_degree[node] = len(deps)

        current_level = [n for n, d in in_degree.items() if d == 0]
        levels: List[List[str]] = []

        visited: Set[str] = set()

        while current_level:
            levels.append(sorted(current_level))
            visited.update(current_level)
            next_level: List[str] = []
            for node in graph:
                if node in visited:
                    continue
                if graph[node] <= visited:
                    next_level.append(node)
            current_level = next_level

        # Safety: any nodes not placed (cycles) go in a final level
        remaining = [n for n in graph if n not in visited]
        if remaining:
            levels.append(sorted(remaining))

        return levels

    # -- ejecucion principal -------------------------------------------------

    async def _execute_single_op(self, op_id: str, results: Dict[str, Any]):
        """Execute a single operation with full middleware support."""
        if op_id not in self.operations:
            logger.warning(f"Operation {op_id} not found")
            return

        op = self.operations[op_id]
        operation_type = list(op.get("operation", {}).keys())[0]
        operation_config = op["operation"][operation_type]

        logger.info(f"Executing {op_id}: {operation_type}")

        # Notify middlewares -- operation start
        for mw in self._middlewares:
            mw.on_operation_start(
                self.current_execution_id, op_id, operation_type, operation_config
            )

        # Pre-process config with middlewares
        config = operation_config
        for mw in self._middlewares:
            config = mw.process_config(operation_type, config)

        # Execute
        op_start = time.time()
        try:
            result = await self._execute_operation(operation_type, config)
            duration_ms = (time.time() - op_start) * 1000

            # Post-process result with middlewares
            for mw in self._middlewares:
                result = mw.process_result(operation_type, config, result)

            # Notify middlewares -- operation complete
            for mw in self._middlewares:
                mw.on_operation_complete(
                    self.current_execution_id, op_id, operation_type, result, duration_ms
                )

            results[op_id] = result

        except Exception as e:
            duration_ms = (time.time() - op_start) * 1000
            logger.error(f"Error executing {op_id}: {e}")

            # Notify middlewares -- operation error
            for mw in self._middlewares:
                mw.on_operation_error(
                    self.current_execution_id, op_id, operation_type, e, duration_ms
                )

            # --- onError fallback handling ---
            on_error_target = operation_config.get("onError")
            if isinstance(on_error_target, str) and on_error_target in self.operations:
                logger.info(
                    f"onError fallback triggered for {op_id} -> executing {on_error_target}"
                )
                fallback_op = self.operations[on_error_target]
                fb_type = list(fallback_op.get("operation", {}).keys())[0]
                fb_config = fallback_op["operation"][fb_type]

                try:
                    fb_result = await self._execute_operation(fb_type, fb_config)

                    original_output_path = operation_config.get("outputPath")
                    fb_output_path = fb_config.get("outputPath")
                    if original_output_path and fb_output_path and original_output_path != fb_output_path:
                        fb_data = self._get_data(fb_output_path)
                        if fb_data is not None:
                            self._set_data(original_output_path, fb_data)
                    elif original_output_path and not fb_output_path:
                        self._set_data(original_output_path, fb_result)

                    if isinstance(fb_result, dict):
                        audit_result = dict(fb_result)
                        audit_result["_fallback"] = True
                    elif isinstance(fb_result, list):
                        audit_result = {"_value": fb_result, "_fallback": True}
                    else:
                        audit_result = {"_value": fb_result, "_fallback": True}

                    results[op_id] = audit_result
                    return
                except Exception as fb_err:
                    logger.error(
                        f"onError fallback {on_error_target} also failed: {fb_err}"
                    )
                    results[op_id] = {"error": str(e), "fallback_error": str(fb_err)}
                    return

            results[op_id] = {"error": str(e)}

    async def execute(self) -> Dict[str, Any]:
        """Ejecuta el workflow completo.

        Attempts DAG-based parallel execution first. Falls back
        to the legacy sequential execution_order if graph building fails.
        """
        if not self.current_execution_id:
            self.current_execution_id = str(uuid.uuid4())

        start_time = time.time()
        results: Dict[str, Any] = {}

        try:
            graph = self._build_dependency_graph()
            levels = self._topological_levels(graph)
            logger.info(f"DAG levels: {levels}")

            for level in levels:
                if len(level) == 1:
                    await self._execute_single_op(level[0], results)
                else:
                    await asyncio.gather(
                        *(self._execute_single_op(op_id, results) for op_id in level)
                    )
        except Exception:
            logger.warning("DAG execution failed, falling back to sequential", exc_info=True)
            for op_id in self.execution_order:
                await self._execute_single_op(op_id, results)

        # Notificar middlewares
        total_duration_ms = (time.time() - start_time) * 1000
        for mw in self._middlewares:
            mw.on_execution_complete(self.current_execution_id, results, total_duration_ms)

        return results

    # -- despacho de operaciones (registro) ----------------------------------

    async def _execute_operation(self, operation_type: str, config: Dict[str, Any]) -> Any:
        """Ejecuta una operacion especifica usando el registro de handlers"""
        handler_name = OPERATION_HANDLERS.get(operation_type)
        if handler_name is None:
            raise ValueError(f"Unknown operation type: {operation_type}")

        handler = getattr(self, handler_name)

        # Verificar resultado cacheado (inyectado por CacheMiddleware)
        cached = config.get("_cached_result")
        if cached is not None:
            output_path = config.get("outputPath")
            if output_path:
                self._set_data(output_path, cached)
            return cached

        if asyncio.iscoroutinefunction(handler):
            return await handler(config)
        else:
            return handler(config)

    # -- helpers del data model ----------------------------------------------

    def _resolve_path(self, path: str) -> str:
        """Resuelve variables en paths usando data model"""
        pattern = r'\{([^}]+)\}'

        def replace(match):
            var_path = match.group(1)
            value = self._get_data(f"/{var_path}")
            return str(value) if value is not None else match.group(0)

        return re.sub(pattern, replace, path)

    def _resolve_object(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Resuelve paths en objetos"""
        resolved = {}
        for key, value in obj.items():
            if isinstance(value, dict) and "path" in value:
                resolved[key] = self._get_data(value["path"])
            elif isinstance(value, str) and value.startswith("/"):
                resolved[key] = self._get_data(value)
            else:
                resolved[key] = value
        return resolved

    def _resolve_value(self, value: Any) -> Any:
        """Resuelve un valor (puede ser literal o path)"""
        if isinstance(value, dict) and "path" in value:
            return self._get_data(value["path"])
        return value

    def _evaluate_condition(self, left: Any, operator: str, right: Any) -> bool:
        """Evalua una condicion"""
        if operator == "==":
            return left == right
        elif operator == "!=":
            return left != right
        elif operator == ">":
            return left > right
        elif operator == "<":
            return left < right
        elif operator == ">=":
            return left >= right
        elif operator == "<=":
            return left <= right
        elif operator == "contains":
            return right in str(left)
        else:
            return False

    def _get_data(self, path: str) -> Any:
        """Obtiene datos del data model usando JSON Pointer"""
        if not path.startswith("/"):
            path = "/" + path

        parts = path.strip("/").split("/")
        current = self.workflow_state

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    return None
            else:
                return None

            if current is None:
                return None

        return current

    def _set_data(self, path: str, value: Any):
        """Establece datos en el data model"""
        if not path.startswith("/"):
            path = "/" + path

        parts = path.strip("/").split("/")
        current = self.workflow_state

        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value
