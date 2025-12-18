# A2E Protocol Specification

**Version**: 1.0.0  
**Status**: Stable  
**Last Updated**: 2025-12-17

## Table of Contents

1. [Overview](#overview)
2. [Protocol Architecture](#protocol-architecture)
3. [Message Format](#message-format)
4. [Operations Catalog](#operations-catalog)
5. [Execution Model](#execution-model)
6. [Data Model](#data-model)
7. [Security](#security)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)
10. [Retry Logic](#retry-logic)
11. [Caching](#caching)
12. [API Reference](#api-reference)
13. [Examples](#examples)

---

## Overview

**A2E (Agent-to-Execution)** is a declarative protocol that enables AI agents to generate and execute workflows without arbitrary code execution. Inspired by A2UI and MCP protocols, A2E provides a secure, controlled environment for agent-driven task automation.

### Key Principles

1. **Declarative**: Agents describe *what* to do, not *how* to do it
2. **Secure**: Only pre-defined operations can be executed
3. **Controlled**: All operations are validated and monitored
4. **Extensible**: New operations can be added to the catalog
5. **Efficient**: RAG-based operation discovery reduces token usage

### Protocol Flow

```
┌─────────────┐
│    Agent    │
│   (LLM)     │
└──────┬──────┘
       │ 1. Query capabilities
       │ 2. Generate workflow (JSONL)
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
│  - Parse JSONL      │
│  - Execute ops       │
│  - Return results    │
└─────────────────────┘
```

---

## Protocol Architecture

### Components

1. **Agent**: AI model that generates workflows
2. **A2E Server**: Validates and executes workflows
3. **Workflow Executor**: Interprets and runs operations
4. **Operations Catalog**: Whitelist of available operations
5. **API Knowledge Base**: Repository of permitted APIs
6. **Credentials Vault**: Secure credential storage
7. **RAG System**: Semantic search for operations/APIs

### Message Transport

A2E uses **JSON Lines (JSONL)** format for streaming workflow definitions:

- Each line is a valid JSON object
- Messages are processed sequentially
- Supports incremental workflow building

---

## Message Format

### JSONL Structure

A2E workflows are defined as JSONL streams with the following message types:

#### 1. Operation Update

Defines or updates an operation in the workflow.

```json
{
  "type": "operationUpdate",
  "operationId": "op-1",
  "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "headers": {},
      "outputPath": "/workflow/users"
    }
  }
}
```

**Schema**:
```json
{
  "type": "object",
  "required": ["type", "operationId", "operation"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["operationUpdate"]
    },
    "operationId": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9_-]+$"
    },
    "operation": {
      "type": "object",
      "minProperties": 1,
      "maxProperties": 1,
      "additionalProperties": false
    }
  }
}
```

#### 2. Begin Execution

Signals the start of workflow execution.

```json
{
  "type": "beginExecution",
  "executionId": "exec-123",
  "operationOrder": ["op-1", "op-2", "op-3"]
}
```

**Schema**:
```json
{
  "type": "object",
  "required": ["type", "executionId", "operationOrder"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["beginExecution"]
    },
    "executionId": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9_-]+$"
    },
    "operationOrder": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "minItems": 1
    }
  }
}
```

### Complete Workflow Example

```jsonl
{"type":"operationUpdate","operationId":"fetch-users","operation":{"ApiCall":{"method":"GET","url":"https://api.example.com/users","outputPath":"/workflow/users"}}}
{"type":"operationUpdate","operationId":"filter-active","operation":{"FilterData":{"inputPath":"/workflow/users","conditions":[{"field":"status","operator":"==","value":"active"}],"outputPath":"/workflow/active-users"}}}
{"type":"beginExecution","executionId":"exec-123","operationOrder":["fetch-users","filter-active"]}
```

---

## Operations Catalog

### Operation Types

#### 1. ApiCall

Executes an HTTP request.

**Properties**:
- `method` (required): HTTP method (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`)
- `url` (required): Endpoint URL (supports path references: `{/workflow/data}`)
- `headers` (optional): HTTP headers (supports credential references)
- `body` (optional): Request body (for POST/PUT)
- `outputPath` (required): Data model path to store response
- `timeout` (optional): Timeout in milliseconds (default: 30000)

**Example**:
```json
{
  "ApiCall": {
    "method": "GET",
    "url": "https://api.example.com/users",
    "headers": {
      "Authorization": {
        "credentialRef": {
          "id": "api-key-123"
        }
      }
    },
    "outputPath": "/workflow/users"
  }
}
```

#### 2. FilterData

Filters an array based on conditions.

**Properties**:
- `inputPath` (required): Path to input array
- `conditions` (required): Array of filter conditions
- `outputPath` (required): Path to store filtered results

**Condition Format**:
```json
{
  "field": "status",
  "operator": "==",
  "value": "active"
}
```

**Operators**: `==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `contains`, `startsWith`, `endsWith`

**Example**:
```json
{
  "FilterData": {
    "inputPath": "/workflow/users",
    "conditions": [
      {"field": "points", "operator": ">", "value": 100},
      {"field": "status", "operator": "==", "value": "active"}
    ],
    "outputPath": "/workflow/filtered-users"
  }
}
```

#### 3. TransformData

Transforms data (map, sort, group, etc.).

**Properties**:
- `inputPath` (required): Path to input data
- `transform` (required): Transformation type
- `config` (optional): Transformation-specific configuration
- `outputPath` (required): Path to store transformed data

**Transform Types**:
- `map`: Apply function to each element
- `sort`: Sort array by field
- `group`: Group by field
- `aggregate`: Calculate aggregations
- `select`: Select specific fields

**Example**:
```json
{
  "TransformData": {
    "inputPath": "/workflow/users",
    "transform": "sort",
    "config": {
      "field": "points",
      "order": "desc"
    },
    "outputPath": "/workflow/sorted-users"
  }
}
```

#### 4. Conditional

Conditional execution based on data.

**Properties**:
- `condition` (required): Condition to evaluate
- `ifTrue` (required): Operations to execute if true
- `ifFalse` (optional): Operations to execute if false

**Example**:
```json
{
  "Conditional": {
    "condition": {
      "path": "/workflow/count",
      "operator": ">",
      "value": 0
    },
    "ifTrue": ["op-process"],
    "ifFalse": ["op-skip"]
  }
}
```

#### 5. Loop

Iterate over an array.

**Properties**:
- `inputPath` (required): Path to array
- `operations` (required): Operations to execute for each item
- `outputPath` (optional): Path to store results

**Example**:
```json
{
  "Loop": {
    "inputPath": "/workflow/users",
    "operations": ["op-process-user"],
    "outputPath": "/workflow/processed-users"
  }
}
```

#### 6. StoreData

Store data persistently.

**Properties**:
- `inputPath` (required): Path to data
- `storage` (required): Storage type (`localStorage`, `sessionStorage`, `file`)
- `key` (required): Storage key/path

**Example**:
```json
{
  "StoreData": {
    "inputPath": "/workflow/results",
    "storage": "localStorage",
    "key": "workflow-results"
  }
}
```

#### 7. Wait

Wait for a specified duration.

**Properties**:
- `duration` (required): Duration in milliseconds

**Example**:
```json
{
  "Wait": {
    "duration": 1000
  }
}
```

#### 8. MergeData

Merge multiple data sources.

**Properties**:
- `sources` (required): Array of input paths
- `strategy` (required): Merge strategy (`concat`, `union`, `intersect`, `deepMerge`)
- `outputPath` (required): Path to store merged data

**Example**:
```json
{
  "MergeData": {
    "sources": ["/workflow/users", "/workflow/profiles"],
    "strategy": "deepMerge",
    "outputPath": "/workflow/merged"
  }
}
```

---

## Execution Model

### Execution Order

Operations are executed in the order specified in `operationOrder`:

1. **Sequential**: Operations execute one after another
2. **Dependency Resolution**: Operations can reference previous results via paths
3. **Error Handling**: Failed operations stop execution (configurable)

### Data Flow

```
Operation 1 → /workflow/data1
    ↓
Operation 2 → /workflow/data2 (can reference /workflow/data1)
    ↓
Operation 3 → /workflow/data3 (can reference /workflow/data1, /workflow/data2)
```

### Path Resolution

Paths in the data model use `/workflow/` prefix:

- `/workflow/users` - Result from operation with `outputPath: "/workflow/users"`
- `/workflow/users[0]` - First element of array
- `/workflow/users[0].name` - Nested property access

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

- `/workflow/key` - Direct access
- `/workflow/array[0]` - Array index
- `/workflow/object.field` - Property access
- `/workflow/array[0].field` - Nested access

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

### Validation

All workflows are validated before execution:

1. **Structural Validation**: JSON schema compliance
2. **Operation Validation**: Operations must exist in catalog
3. **Permission Validation**: Agent has permission for operations
4. **Dependency Validation**: All referenced paths exist
5. **Type Validation**: Data types match expected formats

### Credential Handling

Credentials are stored encrypted and injected at runtime:

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

Validate a workflow before execution.

**Request**:
```json
{
  "workflow": "{\"type\":\"operationUpdate\",...}\n{...}"
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

Execute a workflow.

**Request**:
```json
{
  "workflow": "{\"type\":\"operationUpdate\",...}\n{...}"
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

### Example 1: Simple API Call

```jsonl
{"type":"operationUpdate","operationId":"fetch-data","operation":{"ApiCall":{"method":"GET","url":"https://api.example.com/data","outputPath":"/workflow/data"}}}
{"type":"beginExecution","executionId":"exec-1","operationOrder":["fetch-data"]}
```

### Example 2: API Call + Filter

```jsonl
{"type":"operationUpdate","operationId":"fetch-users","operation":{"ApiCall":{"method":"GET","url":"https://api.example.com/users","outputPath":"/workflow/users"}}}
{"type":"operationUpdate","operationId":"filter-active","operation":{"FilterData":{"inputPath":"/workflow/users","conditions":[{"field":"status","operator":"==","value":"active"}],"outputPath":"/workflow/active-users"}}}
{"type":"beginExecution","executionId":"exec-2","operationOrder":["fetch-users","filter-active"]}
```

### Example 3: Conditional Execution

```jsonl
{"type":"operationUpdate","operationId":"check-count","operation":{"ApiCall":{"method":"GET","url":"https://api.example.com/count","outputPath":"/workflow/count"}}}
{"type":"operationUpdate","operationId":"process-if-needed","operation":{"Conditional":{"condition":{"path":"/workflow/count","operator":">","value":0},"ifTrue":["process-data"],"ifFalse":["skip"]}}}
{"type":"beginExecution","executionId":"exec-3","operationOrder":["check-count","process-if-needed"]}
```

---

## Version History

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

---

**A2E Protocol Specification v1.0.0**  
Copyright © 2025 A2E Contributors

