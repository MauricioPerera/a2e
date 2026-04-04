# Executor Architecture

## Overview

The `WorkflowExecutor` is the core runtime of A2E. It loads workflow definitions,
resolves operation dependencies into a DAG, and executes them with full middleware
support for auditing, caching, credential injection, and resilience. The architecture
uses a mixin pattern: each category of operations lives in its own handler module,
and the executor inherits from all of them.

## File Structure

```
executor/
    __init__.py              # Public exports (WorkflowExecutor, middlewares, CircuitBreaker)
    workflow_executor.py     # Core class (~400 lines)
    middleware.py            # Middleware base + AuditMiddleware, CacheMiddleware, VaultMiddleware
    circuit_breaker.py       # Circuit breaker pattern for external calls
    handlers/
        __init__.py          # OPERATION_HANDLERS registry + mixin re-exports
        api.py               # ApiCall, ExecuteN8nWorkflow
        data.py              # FilterData, TransformData, MergeData, StoreData, SetData
        datetime_ops.py      # DateTime, GetCurrentDateTime, ConvertTimezone, DateCalculation
        text.py              # FormatText, ExtractText
        validation.py        # ValidateData
        math_ops.py          # Calculate
        encoding.py          # EncodeDecode
        flow.py              # Wait, Loop, Conditional
```

## Workflow Formats

Two input formats are supported. `load_workflow()` auto-detects which one it receives.

**JSONL (legacy)** -- one JSON object per line, using `operationUpdate` and
`beginExecution` message types:

```jsonl
{"type":"operationUpdate","operationId":"op1","operationType":"SetData","config":{"value":"hello"},"outputPath":"/workflow/op1/result"}
{"type":"operationUpdate","operationId":"op2","operationType":"FormatText","config":{"template":"{{input}}"},"outputPath":"/workflow/op2/result"}
{"type":"beginExecution","execution_order":["op1","op2"]}
```

**Compact JSON** -- a single object with an `operations` array:

```json
{
  "operations": [
    {"operationId": "op1", "operationType": "SetData", "config": {"value": "hello"}, "outputPath": "/workflow/op1/result"},
    {"operationId": "op2", "operationType": "FormatText", "config": {"template": "{{input}}"}, "outputPath": "/workflow/op2/result"}
  ],
  "execution_order": ["op1", "op2"]
}
```

## Execution Pipeline

### 1. Loading

`load_workflow()` detects the format (JSONL vs. compact JSON), parses each operation
into its internal registry, and records the declared `execution_order`.

### 2. Dependency Resolution

- `_build_dependency_graph()` scans every operation config for `/workflow/<opId>/...`
  path references to determine which operations depend on which.
- `_topological_levels()` applies Kahn's algorithm to group operations into parallel
  levels -- operations within the same level have no inter-dependencies.
- Operations referenced only via `onError` are excluded from the normal DAG so they
  do not run unless a failure triggers them.

### 3. Execution

- **DAG parallel mode**: independent operations within each topological level run
  concurrently via `asyncio.gather`.
- **Fallback sequential mode**: if DAG construction fails (e.g., cycles), the executor
  falls back to the declared `execution_order` and runs operations one at a time.
- **Per-operation lifecycle**: middleware `process_config` -> handler execute ->
  middleware `process_result`, with `on_operation_start` / `on_operation_complete` /
  `on_operation_error` hooks at each stage.

### 4. Data Model

All inter-operation data flows through a shared dictionary accessed via JSON
pointer-style paths:

- `_get_data("/workflow/op1/result")` -- read a value written by another operation.
- `_set_data("/workflow/op2/result", value)` -- store a result at the operation's
  `outputPath`.
- `_resolve_path(config)` -- recursively resolve all path references inside a config
  dict before execution.

## Middleware System

### Base Class

```python
class ExecutorMiddleware:
    def on_execution_start(self, execution_id, workflow_jsonl, agent_id=None): ...
    def on_operation_start(self, execution_id, op_id, op_type, config): ...
    def on_operation_complete(self, execution_id, op_id, op_type, result, duration_ms): ...
    def on_operation_error(self, execution_id, op_id, op_type, error, duration_ms): ...
    def on_execution_complete(self, execution_id, results, duration_ms): ...
    def process_config(self, op_type, config) -> config: ...
    def process_result(self, op_type, config, result) -> result: ...
```

All methods are no-ops by default; subclass and override only what you need.

### Built-in Middlewares

| Middleware | Purpose |
|---|---|
| `AuditMiddleware` | Logs execution start/end, per-operation timing, and credential usage. |
| `CacheMiddleware` | LRU result caching with configurable TTL. Skips re-execution for identical configs. |
| `VaultMiddleware` | Injects credentials into `ApiCall` configs from a secure vault before execution. |
| `CircuitBreakerMiddleware` | Wraps external calls with a circuit breaker to prevent cascading failures. |

### Usage

```python
from executor import WorkflowExecutor, AuditMiddleware, CircuitBreakerMiddleware

executor = WorkflowExecutor(middlewares=[
    AuditMiddleware(audit_logger),
    CircuitBreakerMiddleware(failure_threshold=5, recovery_timeout=30),
])
result = await executor.execute(workflow_jsonl)
```

## Circuit Breaker

The `CircuitBreaker` class implements the standard three-state pattern:

```
CLOSED --(failures >= threshold)--> OPEN --(recovery_timeout elapsed)--> HALF_OPEN
   ^                                                                        |
   +----(successes >= success_threshold)------------------------------------+
```

- **CLOSED**: requests pass through normally; failures are counted.
- **OPEN**: requests are rejected immediately with `CircuitOpenError`.
- **HALF_OPEN**: a limited number of requests are allowed through to test recovery.

`CircuitBreakerMiddleware` applies this automatically to `ApiCall` and
`ExecuteN8nWorkflow` operations, tracking circuits per host.

## Handler Mixin Pattern

Each handler file exports a mixin class. `WorkflowExecutor` inherits from all eight:

```python
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
```

Handler methods access the executor's shared data model through `self._get_data()`,
`self._set_data()`, and `self._resolve_path()`. The `OPERATION_HANDLERS` dict in
`handlers/__init__.py` maps each operation type string to its handler method name:

```python
OPERATION_HANDLERS = {
    "ApiCall": "_execute_api_call",
    "FilterData": "_execute_filter_data",
    "TransformData": "_execute_transform_data",
    # ... 16 total entries
}
```

### Adding a New Operation

1. Write the handler method in the appropriate mixin (or create a new mixin file under
   `handlers/`).
2. Register it in `OPERATION_HANDLERS` in `handlers/__init__.py`.
3. (Optional) Add an n8n node mapping in `n8n_bridge/node_mapping.py` if the operation
   corresponds to an n8n node.
4. Add a schema entry in `workflow_catalog.json` so the LLM planner can discover it.

## Error Handling

- **onError fallback**: any operation can declare an `onError` field pointing to another
  operation ID. If the primary operation fails, the fallback operation executes instead.
- **Transparent downstream access**: the fallback result is stored under the original
  operation's `outputPath`, so downstream operations that reference it do not need to
  know a fallback occurred.
- **Audit trail**: when a fallback fires, the audit result includes a `_fallback: true`
  flag for observability.
