# A2E Protocol Specification

**Version**: 2.0.0
**Status**: Stable
**Last Updated**: 2026-04-04

## Table of Contents

1. [Overview](#overview)
2. [Protocol Architecture](#protocol-architecture)
3. [Message Format](#message-format)
4. [Compact Workflow Format](#compact-workflow-format)
5. [Operations Catalog](#operations-catalog)
6. [Execution Model](#execution-model)
7. [Parallel Execution (DAG)](#parallel-execution-dag)
8. [Error Fallback (onError)](#error-fallback-onerror)
9. [Middleware Architecture](#middleware-architecture)
10. [Data Model](#data-model)
11. [Security](#security)
12. [Validation](#validation)
13. [Error Handling](#error-handling)
14. [Rate Limiting](#rate-limiting)
15. [Retry Logic](#retry-logic)
16. [Caching](#caching)
17. [RAG Integration](#rag-integration)
18. [API Reference](#api-reference)
19. [Examples](#examples)

---

## Overview

**A2E (Agent-to-Execution)** is a declarative protocol that enables AI agents to generate and execute workflows without arbitrary code execution. Inspired by A2UI and MCP protocols, A2E provides a secure, controlled environment for agent-driven task automation.

### Key Principles

1. **Declarative**: Agents describe *what* to do, not *how* to do it
2. **Secure**: Only pre-defined operations can be executed
3. **Controlled**: All operations are validated and monitored
4. **Extensible**: New operations can be added to the catalog
5. **Efficient**: RAG-based operation discovery reduces token usage
6. **Parallel**: Independent operations execute concurrently via DAG scheduling

### Protocol Flow

```
┌─────────────┐
│    Agent     │
│   (LLM)     │
└──────┬──────┘
       │ 1. Query capabilities
       │ 2. Generate workflow (JSONL or compact JSON)
       │ 3. Validate workflow
       │ 4. Execute workflow
       ▼
┌─────────────────────┐
│   A2E Server        │
│  - Validation       │
│  - Execution        │
│  - Monitoring       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Workflow Executor   │
│  - Parse JSONL/JSON │
│  - Build DAG        │
│  - Execute ops      │
│  - Return results   │
└─────────────────────┘
```

---

## Protocol Architecture

### Components

1. **Agent**: AI model that generates workflows
2. **A2E Server**: Validates and executes workflows
3. **Workflow Executor**: Interprets and runs operations (with middleware pipeline)
4. **Operations Catalog**: Whitelist of available operations (18 registered handlers)
5. **API Knowledge Base**: Repository of permitted APIs
6. **Credentials Vault**: Secure credential storage
7. **RAG System**: Semantic search for operations/APIs (backed by minimemory)

### Message Transport

A2E supports two workflow formats:

- **JSONL (legacy)**: Each line is a valid JSON object; messages are processed sequentially
- **Compact JSON**: A single JSON object with an `operations` array and `execute` field

---

## Message Format

### JSONL Structure (Legacy)

A2E workflows can be defined as JSONL streams with the following message types:

#### 1. Operation Update

Defines or updates operations in the workflow.

```json
{
  "operationUpdate": {
    "workflowId": "my-workflow",
    "operations": [
      {
        "id": "op-1",
        "operation": {
          "ApiCall": {
            "method": "GET",
            "url": "https://api.example.com/users",
            "outputPath": "/workflow/users"
          }
        }
      }
    ]
  }
}
```

#### 2. Begin Execution

Signals the start of workflow execution.

```json
{
  "beginExecution": {
    "root": "op-1"
  }
}
```

The `root` field specifies the entry-point operation. The executor builds execution order from dependencies automatically.

### Complete JSONL Workflow Example

```jsonl
{"operationUpdate":{"workflowId":"demo","operations":[{"id":"fetch-users","operation":{"ApiCall":{"method":"GET","url":"https://api.example.com/users","outputPath":"/workflow/users"}}},{"id":"filter-active","operation":{"FilterData":{"inputPath":"/workflow/users","conditions":[{"field":"status","operator":"==","value":"active"}],"outputPath":"/workflow/active-users"}}}]}}
{"beginExecution":{"root":"fetch-users"}}
```

---

## Compact Workflow Format

The compact format is an alternative to JSONL that reduces verbosity. It is a single JSON object with an `operations` array and an `execute` field.

### Structure

```json
{
  "operations": [
    {"id": "op-id", "op": "OperationType", "param1": "value1", ...}
  ],
  "execute": "root-operation-id"
}
```

### Rules

- **`op`** field specifies the operation type (flat, not nested)
- **`input`** is a shorthand for `inputPath: "/workflow/{input}"` — reference another operation by ID
- **`outputPath`** defaults to `"/workflow/{id}"` when omitted
- **Implicit piping**: when `input` is omitted and the operation has no own data source (`value`, `url`, `sources`, etc.), it automatically receives the previous operation's output
- **`execute`** specifies the root operation; execution order is derived from dependencies

### Before/After Comparison

**JSONL (verbose)**:
```jsonl
{"operationUpdate":{"operations":[{"id":"fetch","operation":{"ApiCall":{"method":"GET","url":"https://api.example.com/users","outputPath":"/workflow/fetch"}}},{"id":"filter","operation":{"FilterData":{"inputPath":"/workflow/fetch","conditions":[{"field":"active","operator":"==","value":true}],"outputPath":"/workflow/filter"}}}]}}
{"beginExecution":{"root":"fetch"}}
```

**Compact JSON (equivalent)**:
```json
{
  "operations": [
    {"id": "fetch", "op": "ApiCall", "method": "GET", "url": "https://api.example.com/users"},
    {"id": "filter", "op": "FilterData", "conditions": [{"field": "active", "operator": "==", "value": true}]}
  ],
  "execute": "fetch"
}
```

In the compact version:
- `filter` implicitly receives `inputPath: "/workflow/fetch"` (previous operation)
- Both operations get auto-generated `outputPath` values (`/workflow/fetch`, `/workflow/filter`)

---

## Operations Catalog

A2E supports 18 registered operation types, organized into four categories.

### Core Operations

#### 1. ApiCall

Executes an HTTP request.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `method` | yes | HTTP method (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`) |
| `url` | yes | Endpoint URL (supports path references: `{/workflow/data}`) |
| `headers` | no | HTTP headers (supports credential references) |
| `body` | no | Request body (for POST/PUT) |
| `outputPath` | yes | Data model path to store response |
| `timeout` | no | Timeout in milliseconds |

```json
{
  "ApiCall": {
    "method": "GET",
    "url": "https://api.example.com/users",
    "headers": {
      "Authorization": {"credentialRef": {"id": "api-key-123"}}
    },
    "outputPath": "/workflow/users"
  }
}
```

#### 2. FilterData

Filters an array based on conditions.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `inputPath` | yes | Path to input array |
| `conditions` | yes | Array of `{field, operator, value}` conditions |
| `outputPath` | yes | Path to store filtered results |

**Operators**: `==`, `!=`, `>`, `<`, `>=`, `<=`, `contains`, `startsWith`, `endsWith`

```json
{
  "FilterData": {
    "inputPath": "/workflow/users",
    "conditions": [
      {"field": "points", "operator": ">", "value": 100}
    ],
    "outputPath": "/workflow/filtered-users"
  }
}
```

#### 3. TransformData

Transforms data using common operations.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `inputPath` | yes | Path to input data |
| `transform` | yes | Transform type: `map`, `sort`, `pick`, `flatten`, `group`, `unique`, `reverse`, `slice` |
| `config` | no | Transform-specific configuration |
| `outputPath` | yes | Path to store result |

Transform configs:
- `map`: `{fields: string[]}` — extract fields from each array element
- `sort`: `{field?: string, reverse?: boolean}`
- `pick`: `{fields: string[]}` — select fields from an object
- `flatten`: no config — flattens nested arrays one level
- `group`: `{field: string}` — group elements by field
- `unique`: no config — remove duplicates
- `reverse`: no config — reverse array order
- `slice`: `{start?: number, end?: number}`

#### 4. StoreData

Stores data persistently.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `inputPath` | yes | Path to data |
| `storage` | yes | Storage type (`localStorage`, `sessionStorage`, `indexedDB`, `database`) |
| `key` | yes | Storage key/path |
| `format` | no | Format: `json`, `string`, `binary` |

#### 5. Wait

Pauses execution for a specified duration.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `duration` | yes | Duration in milliseconds |

#### 6. Conditional

Conditional execution based on data evaluation.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `condition` | yes | `{path, operator, value}` — operators: `==`, `!=`, `>`, `<`, `exists`, `isEmpty` |
| `ifTrue` | yes | ID of operation to execute if true |
| `ifFalse` | no | ID of operation to execute if false |

#### 7. MergeData

Merges multiple data sources.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `sources` | yes | Array of input paths |
| `strategy` | yes | Merge strategy: `merge`, `concat`, `intersect`, `union` |
| `outputPath` | yes | Path to store merged data |

#### 8. Loop

Iterates over an array, executing operations for each item.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `inputPath` | yes | Path to array |
| `operations` | yes | IDs of operations to execute per item |
| `outputPath` | no | Path to store loop results |

### Utility Operations

#### 9. Calculate

Performs mathematical operations.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `inputPath` | yes | Path to number(s) |
| `operation` | yes | `add`, `subtract`, `multiply`, `divide`, `power`, `modulo`, `round`, `ceil`, `floor`, `abs`, `max`, `min`, `sum`, `average` |
| `operand` | no | Second operand (for binary operations), number or path |
| `precision` | no | Decimal precision for `round` |
| `outputPath` | yes | Path to store result |

#### 10. EncodeDecode

Encodes or decodes data.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `inputPath` | yes | Path to data |
| `operation` | yes | `encode` or `decode` |
| `encoding` | yes | `base64`, `url`, `html` |
| `outputPath` | yes | Path to store result |

#### 11. ExtractText

Extracts information from text using regular expressions.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `inputPath` | yes | Path to text |
| `pattern` | yes | Regular expression |
| `extractAll` | no | Extract all matches (true) or first only (false) |
| `outputPath` | yes | Path to store extracted results |

#### 12. FormatText

Formats text using templates or transformations.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `inputPath` | yes | Path to text or data |
| `format` | yes | `template`, `upper`, `lower`, `title`, `capitalize`, `trim`, `replace` |
| `template` | no | Template string (for `template` format), uses `{field}` placeholders |
| `replacements` | no | Key-value map of replacements (for `replace` format) |
| `outputPath` | yes | Path to store formatted text |

#### 13. ValidateData

Validates data against predefined rules.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `inputPath` | yes | Path to data |
| `validationType` | yes | `email`, `url`, `number`, `integer`, `phone`, `date`, `custom` |
| `pattern` | no | Regex for `custom` validation |
| `outputPath` | yes | Path to store validation result (`{valid, value, error?}`) |

### DateTime Operations

#### 14. DateTime (unified)

Unified date/time operation supporting three modes.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `mode` | yes | `now`, `convert`, or `calculate` |
| `timezone` | no | Timezone (e.g. `UTC`, `America/New_York`) |
| `format` | no | Output format: `iso8601` (default), `timestamp`, `custom` |
| `formatString` | no | Custom strftime format string (only if `format=custom`) |
| `input` | no | Path to input date (required for `convert` and `calculate` modes) |
| `amount` | no | Time units to add/subtract (only for `calculate` mode) |
| `unit` | no | `years`, `months`, `days`, `hours`, `minutes`, `seconds` (only for `calculate`) |
| `operation` | no | `add` or `subtract` (only for `calculate` mode) |
| `outputPath` | yes | Path to store result |

```json
{
  "DateTime": {
    "mode": "now",
    "timezone": "America/New_York",
    "format": "iso8601",
    "outputPath": "/workflow/current-time"
  }
}
```

#### 15. GetCurrentDateTime (deprecated)

Gets current date/time. **Use `DateTime` with `mode: "now"` instead.**

#### 16. ConvertTimezone (deprecated)

Converts a date/time between timezones. **Use `DateTime` with `mode: "convert"` instead.**

#### 17. DateCalculation (deprecated)

Performs date arithmetic. **Use `DateTime` with `mode: "calculate"` instead.**

### Data Operations

#### 18. SetData

Stores a literal value directly in the workflow data model, without requiring an input path.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `value` | yes | The literal value to store (any JSON type) |
| `outputPath` | yes | Path in data model where to store the value |

```json
{
  "SetData": {
    "value": {"name": "Alice", "role": "admin"},
    "outputPath": "/workflow/default-user"
  }
}
```

---

## Execution Model

### Data Flow

Operations communicate through the shared data model using `inputPath` and `outputPath`:

```
Operation 1 → /workflow/data1
    ↓
Operation 2 → /workflow/data2 (reads /workflow/data1)
    ↓
Operation 3 → /workflow/data3 (reads /workflow/data1, /workflow/data2)
```

### Path Resolution

Paths in the data model use `/workflow/` prefix:

- `/workflow/users` — Result from operation with `outputPath: "/workflow/users"`
- `/workflow/users[0]` — First element of array
- `/workflow/users[0].name` — Nested property access

---

## Parallel Execution (DAG)

The executor builds a **dependency graph** (DAG) from `inputPath`/`outputPath` references and executes independent operations in parallel.

### How It Works

1. **Graph construction**: For each operation, the executor scans all config fields for `/workflow/<op_id>` references. These references become edges in the dependency graph.
2. **Topological sorting**: Operations are grouped into levels using Kahn's algorithm. Each level contains operations whose dependencies have all been satisfied.
3. **Parallel execution**: Operations within the same level run concurrently via `asyncio.gather`.
4. **Sequential fallback**: If DAG construction fails (e.g. malformed references), execution falls back to the legacy sequential order.

### Example

Given three operations where `B` depends on `A`, and `C` depends on `A`:

```
Level 0: [A]          ← executes first
Level 1: [B, C]       ← execute in parallel
```

```json
{
  "operations": [
    {"id": "A", "op": "ApiCall", "method": "GET", "url": "https://api.example.com/data"},
    {"id": "B", "op": "FilterData", "input": "A", "conditions": [{"field": "type", "operator": "==", "value": "x"}]},
    {"id": "C", "op": "TransformData", "input": "A", "transform": "sort", "field": "name"}
  ],
  "execute": "A"
}
```

Here `B` and `C` both depend only on `A`, so after `A` completes they run concurrently.

---

## Error Fallback (onError)

Any operation can specify an `onError` field pointing to another operation ID. If the primary operation fails, the fallback operation executes instead and its result is propagated to downstream operations transparently.

### Behavior

1. The operation fails with an exception.
2. The executor checks for `onError` in the operation config.
3. If present and the target operation exists, the fallback operation executes.
4. The fallback result is stored under the **original** operation's `outputPath`, so downstream operations receive the data without changes.
5. The result is marked with `_fallback: true` for audit purposes.
6. If the fallback also fails, both the original error and the fallback error are recorded.
7. Fallback operations are excluded from the normal DAG execution graph — they only execute when triggered.

### Example

```json
{
  "operations": [
    {"id": "fetch-live", "op": "ApiCall", "method": "GET", "url": "https://api.example.com/data", "onError": "fetch-cached"},
    {"id": "fetch-cached", "op": "SetData", "value": {"data": [], "source": "cache"}},
    {"id": "process", "op": "FilterData", "input": "fetch-live", "conditions": [{"field": "active", "operator": "==", "value": true}]}
  ],
  "execute": "fetch-live"
}
```

If `fetch-live` fails, `fetch-cached` executes and its value is written to `/workflow/fetch-live`. The `process` operation receives the cached data without knowing a fallback occurred.

---

## Middleware Architecture

The executor uses a middleware pipeline for cross-cutting concerns. Middlewares are registered at executor construction time and receive hooks throughout the execution lifecycle.

### Middleware Protocol

All middlewares extend `ExecutorMiddleware` and can override these hooks:

| Hook | When Called |
|------|------------|
| `on_execution_start(execution_id, workflow_jsonl, agent_id)` | Workflow execution begins |
| `on_operation_start(execution_id, op_id, op_type, config)` | Before each operation |
| `on_operation_complete(execution_id, op_id, op_type, result, duration_ms)` | After successful operation |
| `on_operation_error(execution_id, op_id, op_type, error, duration_ms)` | After failed operation |
| `on_execution_complete(execution_id, results, duration_ms)` | Workflow execution ends |
| `process_config(op_type, config) -> config` | Pre-process operation config (e.g. inject credentials) |
| `process_result(op_type, config, result) -> result` | Post-process operation result (e.g. cache it) |

### Built-in Middlewares

#### AuditMiddleware

Logs execution events, operation timing, credential usage, and results through the audit logger. Replaces the legacy `MonitoredWorkflowExecutor`.

#### CacheMiddleware

Stores and retrieves operation results from a cache. On `process_config`, checks for a cached result and injects it as `_cached_result`. On `process_result`, stores the result in cache.

#### VaultMiddleware

Injects credentials into `ApiCall` operations. Resolves `credentialRef` references to actual values at runtime via the `CredentialInjector`.

### Usage

```python
from executor.workflow_executor import WorkflowExecutor, AuditMiddleware, CacheMiddleware, VaultMiddleware

executor = WorkflowExecutor(middlewares=[
    AuditMiddleware(audit_logger),
    CacheMiddleware(cache),
    VaultMiddleware(vault),
])
executor.load_workflow(workflow_json)
results = await executor.execute()
```

---

## Data Model

### Structure

The data model is a hierarchical JSON structure:

```json
{
  "/workflow": {
    "users": [...],
    "filtered-users": [...],
    "results": {...}
  }
}
```

### Path Syntax

- `/workflow/key` — Direct access
- `/workflow/array[0]` — Array index
- `/workflow/object.field` — Property access
- `/workflow/array[0].field` — Nested access

### Type System

- **String**: Text data
- **Number**: Numeric values
- **Boolean**: True/false
- **Array**: Ordered lists
- **Object**: Key-value pairs
- **Null**: Empty values

---

## Security

### Authentication

Agents authenticate using API keys:

```
Authorization: Bearer <api-key>
```

### Authorization

- **Operation Permissions**: Agents can only use permitted operations
- **API Permissions**: Agents can only call permitted APIs
- **Credential Access**: Agents reference credentials by ID, never see values

### Credential Handling

Credentials are stored encrypted and injected at runtime by `VaultMiddleware`:

```json
{
  "headers": {
    "Authorization": {
      "credentialRef": {
        "id": "api-key-123"
      }
    }
  }
}
```

The executor resolves `credentialRef` to actual values without exposing them to the agent.

---

## Validation

All workflows are validated before execution. The validator supports both JSONL and compact formats.

### Validation Steps

1. **Structural Validation**: Each operation must have a unique `id` and exactly one operation type
2. **Operation Type Validation**: Operation types are checked against the executor's registered `OPERATION_HANDLERS` — unknown types are rejected
3. **Dependency Validation**: All `inputPath` references must point to existing operations
4. **Data Type Validation**: Operations that require arrays (e.g. `FilterData`) are checked for compatible input types
5. **API Compatibility**: URLs are validated against the API knowledge base (if configured)
6. **Credential Validation**: Credential references are verified against the vault (if configured)
7. **Pattern Detection**: Common problematic patterns (e.g. unbounded loops, empty inputs) are flagged

### Validation Levels

| Level | Behavior |
|-------|----------|
| `STRICT` | Includes warnings as errors |
| `MODERATE` (default) | Only hard errors |
| `LENIENT` | Only errors with "will fail" certainty |

---

## Error Handling

### Error Types

1. **ValidationError**: Workflow structure invalid
2. **PermissionError**: Agent lacks required permissions
3. **ExecutionError**: Operation execution failed
4. **TimeoutError**: Operation exceeded timeout
5. **DataError**: Invalid data format or missing path

### Error Response Format

```json
{
  "error": {
    "type": "ExecutionError",
    "message": "API call failed",
    "operationId": "op-1",
    "details": {
      "statusCode": 500,
      "response": "..."
    },
    "suggestions": [
      "Check API endpoint availability",
      "Verify credentials are valid"
    ]
  }
}
```

---

## Rate Limiting

### Limits

Rate limits are applied per agent:

- **Requests per minute**: Default 60
- **Requests per hour**: Default 1000
- **Requests per day**: Default 10000
- **API calls per minute**: Default 30
- **API calls per hour**: Default 500

### Response Headers

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1702848000
Retry-After: 15
```

### 429 Response

```json
{
  "error": "Rate limit exceeded",
  "message": "Rate limit exceeded: 60 requests per minute",
  "retry_after": 15
}
```

---

## Retry Logic

### Automatic Retries

Operations are automatically retried on transient failures:

- **Max Retries**: Default 3
- **Initial Delay**: 1 second
- **Backoff**: Exponential (base 2)
- **Max Delay**: 60 seconds
- **Jitter**: Enabled to prevent thundering herd

### Retryable Errors

- Connection errors
- Timeout errors
- HTTP 5xx errors
- HTTP 429 (Rate Limited)
- HTTP 408 (Request Timeout)

### Non-Retryable Errors

- HTTP 4xx (except 408, 429)
- Validation errors
- Permission errors
- NonRetryableError exceptions

---

## Caching

### Cache Strategy

Results are cached by operation type and configuration:

- **ApiCall**: 5 minutes TTL
- **FilterData**: 1 minute TTL
- **TransformData**: 1 minute TTL
- **StoreData**: No caching
- **Wait**: No caching
- **Loop**: No caching
- **Conditional**: No caching

### Cache Key

Cache keys are generated from:
- Operation type
- Operation configuration (serialized and hashed)

### Cache Invalidation

- Automatic: TTL expiration
- Manual: `invalidate()` method
- On write operations: Related caches invalidated

Cache behavior is implemented via `CacheMiddleware` (see [Middleware Architecture](#middleware-architecture)).

---

## RAG Integration

The RAG system provides semantic search for operations, APIs, endpoints, and knowledge bases. It uses **minimemory** as the vector storage and search backend.

### Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `MINIMEMORY_URL` | URL of the minimemory service |
| `MINIMEMORY_API_KEY` | API key for authentication |
| `MINIMEMORY_NAMESPACE` | Namespace for data isolation (default: `a2e`) |

### Usage

```python
from rag_integration import A2ERAGSystem

rag = A2ERAGSystem(
    base_url="https://minimemory.example.com",
    api_key="your-api-key",
    namespace="a2e"
)
```

The RAG system indexes operations from the catalog and API definitions, enabling agents to discover relevant operations via natural language queries.

---

## API Reference

### REST Endpoints

#### GET /health

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "service": "a2e-server"
}
```

#### GET /api/v1/capabilities

Get available capabilities for authenticated agent.

**Headers**:
```
Authorization: Bearer <api-key>
```

**Response**:
```json
{
  "agent_id": "agent-123",
  "capabilities": {
    "availableApis": [...],
    "availableCredentials": [...],
    "supportedOperations": ["ApiCall", "FilterData", ...],
    "knowledgeBases": [...],
    "securityConstraints": {
      "maxExecutionTime": 30000,
      "maxOperations": 20
    }
  }
}
```

#### POST /api/v1/workflows/validate

Validate a workflow before execution. Accepts both JSONL and compact JSON formats.

**Request**:
```json
{
  "workflow": "<JSONL string or compact JSON string>"
}
```

**Response**:
```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

#### POST /api/v1/workflows/execute

Execute a workflow. Accepts both JSONL and compact JSON formats.

**Request**:
```json
{
  "workflow": "<JSONL string or compact JSON string>"
}
```

**Response**:
```json
{
  "execution_id": "exec-123",
  "status": "success",
  "results": {
    "op-1": {...},
    "op-2": {...}
  },
  "duration_ms": 1234
}
```

#### GET /api/v1/executions/{execution_id}

Get execution status and results.

**Response**:
```json
{
  "execution_id": "exec-123",
  "status": "success",
  "results": {...},
  "started_at": "2025-12-17T10:00:00Z",
  "completed_at": "2025-12-17T10:00:15Z"
}
```

#### GET /api/v1/rate-limit/status

Get rate limit status for authenticated agent.

**Response**:
```json
{
  "agent_id": "agent-123",
  "limits": {
    "requests_per_minute": 60,
    "requests_per_hour": 1000
  },
  "usage": {
    "requests_last_minute": 15,
    "requests_last_hour": 200
  },
  "remaining": {
    "requests_per_minute": 45,
    "requests_per_hour": 800
  }
}
```

---

## Examples

### Example 1: Simple API Call (compact)

```json
{
  "operations": [
    {"id": "fetch-data", "op": "ApiCall", "method": "GET", "url": "https://api.example.com/data"}
  ],
  "execute": "fetch-data"
}
```

### Example 2: API Call + Filter + Transform (compact with implicit piping)

```json
{
  "operations": [
    {"id": "fetch-users", "op": "ApiCall", "method": "GET", "url": "https://api.example.com/users"},
    {"id": "filter-active", "op": "FilterData", "conditions": [{"field": "status", "operator": "==", "value": "active"}]},
    {"id": "sort-by-name", "op": "TransformData", "transform": "sort", "field": "name"}
  ],
  "execute": "fetch-users"
}
```

`filter-active` implicitly receives `/workflow/fetch-users`, and `sort-by-name` implicitly receives `/workflow/filter-active`.

### Example 3: Parallel operations with SetData

```json
{
  "operations": [
    {"id": "set-config", "op": "SetData", "value": {"threshold": 100}},
    {"id": "fetch-a", "op": "ApiCall", "method": "GET", "url": "https://api.example.com/a"},
    {"id": "fetch-b", "op": "ApiCall", "method": "GET", "url": "https://api.example.com/b"},
    {"id": "merge", "op": "MergeData", "sources": ["/workflow/fetch-a", "/workflow/fetch-b"], "strategy": "concat"}
  ],
  "execute": "set-config"
}
```

`set-config`, `fetch-a`, and `fetch-b` have no inter-dependencies, so they execute in parallel. `merge` waits for both fetches to complete.

### Example 4: onError fallback

```json
{
  "operations": [
    {"id": "fetch-live", "op": "ApiCall", "method": "GET", "url": "https://api.example.com/data", "onError": "fallback"},
    {"id": "fallback", "op": "SetData", "value": []},
    {"id": "process", "op": "FilterData", "input": "fetch-live", "conditions": [{"field": "active", "operator": "==", "value": true}]}
  ],
  "execute": "fetch-live"
}
```

If `fetch-live` fails, `fallback` provides an empty array to `/workflow/fetch-live`, and `process` continues normally.

### Example 5: DateTime operations

```json
{
  "operations": [
    {"id": "now", "op": "DateTime", "mode": "now", "timezone": "UTC"},
    {"id": "next-week", "op": "DateTime", "mode": "calculate", "input": "/workflow/now", "operation": "add", "amount": 7, "unit": "days"}
  ],
  "execute": "now"
}
```

---

## Version History

- **2.0.0** (2026-04-04): Major update
  - Compact JSON workflow format as alternative to JSONL
  - DAG-based parallel execution with topological scheduling
  - `onError` fallback mechanism for operation-level error recovery
  - Middleware architecture (AuditMiddleware, CacheMiddleware, VaultMiddleware)
  - 10 new operations: Calculate, EncodeDecode, ExtractText, FormatText, ValidateData, DateTime, SetData, GetCurrentDateTime, ConvertTimezone, DateCalculation
  - Unified `DateTime` operation (deprecates GetCurrentDateTime, ConvertTimezone, DateCalculation)
  - Validation now checks operation types against executor's registered handlers
  - RAG system backed by minimemory

- **1.0.0** (2025-12-17): Initial stable release
  - Core operations: ApiCall, FilterData, TransformData, Conditional, Loop, StoreData, Wait, MergeData
  - Rate limiting
  - Retry logic
  - Caching
  - RAG integration

---

## References

- **A2UI Protocol**: Inspiration for declarative approach
- **MCP Protocol**: Model Context Protocol reference
- **JSON Lines**: JSONL format specification
- **JSON Schema**: Schema validation standard
- **minimemory**: Vector storage backend for RAG

---

**A2E Protocol Specification v2.0.0**
Copyright (c) 2025-2026 A2E Contributors
