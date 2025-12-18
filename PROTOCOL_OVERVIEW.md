# A2E Protocol Overview

## What is A2E?

**A2E (Agent-to-Execution)** is a declarative protocol that enables AI agents to safely generate and execute workflows without arbitrary code execution.

### Key Features

- ✅ **Secure**: Only pre-defined operations can be executed
- ✅ **Declarative**: Agents describe *what* to do, not *how*
- ✅ **Controlled**: All operations validated and monitored
- ✅ **Efficient**: RAG-based discovery reduces token usage
- ✅ **Extensible**: New operations can be added to catalog

## How It Works

### 1. Agent Queries Capabilities

```python
capabilities = client.get_capabilities()
# Returns: available operations, APIs, credentials
```

### 2. Agent Generates Workflow

Agent uses RAG to find relevant operations, then generates JSONL:

```jsonl
{"type":"operationUpdate","operationId":"fetch","operation":{"ApiCall":{...}}}
{"type":"operationUpdate","operationId":"filter","operation":{"FilterData":{...}}}
{"type":"beginExecution","executionId":"exec-1","operationOrder":["fetch","filter"]}
```

### 3. Server Validates

```python
validation = client.validate_workflow(workflow_jsonl)
# Checks: structure, permissions, dependencies
```

### 4. Server Executes

```python
result = client.execute_workflow(workflow_jsonl)
# Returns: execution results with data
```

## Protocol Format

### JSON Lines (JSONL)

Each line is a JSON object:

```
{"type":"operationUpdate",...}
{"type":"operationUpdate",...}
{"type":"beginExecution",...}
```

### Message Types

1. **operationUpdate**: Define/update an operation
2. **beginExecution**: Start workflow execution

## Operations

### Core Operations

- **ApiCall**: HTTP requests
- **FilterData**: Filter arrays
- **TransformData**: Transform data (map, sort, etc.)
- **Conditional**: Conditional execution
- **Loop**: Iterate over arrays
- **StoreData**: Persistent storage
- **Wait**: Delay execution
- **MergeData**: Combine data sources

## Security Model

### Authentication

```
Authorization: Bearer <api-key>
```

### Authorization

- Operation whitelist
- API whitelist
- Credential access control

### Validation

- Structural validation
- Permission validation
- Dependency validation
- Type validation

## Production Features

### Rate Limiting

- Per-agent limits
- Per-operation limits
- Throttling

### Retry Logic

- Automatic retries
- Exponential backoff
- Error detection

### Caching

- Operation result caching
- TTL-based expiration
- LRU eviction

## Example Workflow

```jsonl
{"type":"operationUpdate","operationId":"fetch-users","operation":{"ApiCall":{"method":"GET","url":"https://api.example.com/users","outputPath":"/workflow/users"}}}
{"type":"operationUpdate","operationId":"filter-active","operation":{"FilterData":{"inputPath":"/workflow/users","conditions":[{"field":"status","operator":"==","value":"active"}],"outputPath":"/workflow/active-users"}}}
{"type":"beginExecution","executionId":"exec-1","operationOrder":["fetch-users","filter-active"]}
```

**Result**:
```json
{
  "execution_id": "exec-1",
  "status": "success",
  "results": {
    "fetch-users": {...},
    "filter-active": [...]
  }
}
```

## Documentation

- **SPECIFICATION.md**: Complete protocol specification
- **SPECIFICATION_JSON_SCHEMAS.md**: JSON Schema definitions
- **README.md**: Implementation guide
- **README_PHASE2.md**: Production features

## Version

**A2E Protocol v1.0.0** (Stable)

---

For complete details, see [SPECIFICATION.md](./SPECIFICATION.md)

