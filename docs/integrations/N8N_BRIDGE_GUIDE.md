# n8n Integration Guide

## Overview

A2E provides bidirectional integration with n8n through the `n8n_bridge` module. This standalone module does not modify the original A2E executor and offers three capabilities:

1. **Translate** -- Convert A2E workflows (compact or JSONL format) into n8n-compatible workflow JSON.
2. **Execute** -- Invoke n8n workflows from within A2E using the `ExecuteN8nWorkflow` operation.
3. **Enrich** -- Import n8n workflows into the A2E catalog so agents can discover and use them as native operations.

## Installation

The translator is pure Python with no additional dependencies:

```python
from n8n_bridge import A2EToN8nTranslator  # works out of the box
```

For pushing workflows to n8n via the REST API:

```bash
pip install requests
```

For the `ExecuteN8nWorkflow` async operation:

```bash
pip install aiohttp
```

---

## 1. Translating A2E Workflows to n8n

### Basic Usage

```python
from n8n_bridge import A2EToN8nTranslator

translator = A2EToN8nTranslator()
result = translator.translate(a2e_workflow_str)
# result is a dict with nodes, connections, settings, and metadata
```

### Supported Operations (all 19)

| A2E Operation        | n8n Node Type                        | Notes                              |
|----------------------|--------------------------------------|------------------------------------|
| ApiCall              | n8n-nodes-base.httpRequest           | Maps method, url, headers, body    |
| FilterData           | n8n-nodes-base.filter                | Condition-based row filtering      |
| TransformData        | n8n-nodes-base.code                  | Pick/omit/rename via Code node     |
| StoreData            | n8n-nodes-base.set                   | Persists data to workflow context   |
| Wait                 | n8n-nodes-base.wait                  | Duration-based pause               |
| DateTime             | n8n-nodes-base.dateTime              | Generic date/time formatting       |
| GetCurrentDateTime   | n8n-nodes-base.dateTime              | Current timestamp retrieval        |
| ConvertTimezone      | n8n-nodes-base.dateTime              | Timezone conversion                |
| DateCalculation      | n8n-nodes-base.dateTime              | Date arithmetic (add/subtract)     |
| SetData              | n8n-nodes-base.set                   | Set fields on output items         |
| Conditional          | n8n-nodes-base.if                    | Boolean branching                  |
| Loop                 | n8n-nodes-base.splitInBatches        | Iterates over items in batches     |
| MergeData            | n8n-nodes-base.merge                 | Combines two input streams         |
| FormatText           | n8n-nodes-base.code                  | Template string formatting         |
| ExtractText          | n8n-nodes-base.code                  | Regex/pattern extraction           |
| ValidateData         | n8n-nodes-base.code                  | Schema or rule validation          |
| Calculate            | n8n-nodes-base.code                  | Math expressions via Code node     |
| EncodeDecode         | n8n-nodes-base.code                  | Base64, URL encoding, etc.         |
| ExecuteN8nWorkflow   | n8n-nodes-base.executeWorkflow       | Calls another n8n workflow by ID   |

### Compact Format Example

The compact format uses a single JSON object with an `operations` array:

```python
import json
from n8n_bridge import A2EToN8nTranslator

a2e = json.dumps({
    "operations": [
        {
            "id": "fetch-users",
            "op": "ApiCall",
            "method": "GET",
            "url": "https://jsonplaceholder.typicode.com/users",
            "headers": {"Accept": "application/json"},
        },
        {
            "id": "active-only",
            "op": "FilterData",
            "input": "fetch-users",
            "conditions": [
                {"field": "active", "operator": "==", "value": True}
            ],
        },
        {
            "id": "pick-fields",
            "op": "TransformData",
            "input": "active-only",
            "type": "pick",
            "config": {"fields": ["name", "email", "company"]},
        },
    ],
    "execute": "fetch-users",
})

translator = A2EToN8nTranslator()
n8n_wf = translator.translate(a2e, name="User Pipeline")
```

### JSONL Format Example

JSONL workflows use `operationUpdate` messages with a `beginExecution` line:

```python
from n8n_bridge import A2EToN8nTranslator

a2e_jsonl = (
    '{"operationUpdate": {"workflowId": "datetime-demo", "operations": ['
    '{"id": "get-utc", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/utc_time"}}},'
    '{"id": "to-madrid", "operation": {"ConvertTimezone": {"inputPath": "/workflow/utc_time", "fromTimezone": "UTC", "toTimezone": "Europe/Madrid", "format": "iso8601", "outputPath": "/workflow/madrid_time"}}}'
    ']}}\n'
    '{"beginExecution": {"rootOperation": "get-utc"}}\n'
)

translator = A2EToN8nTranslator()
n8n_wf = translator.translate(a2e_jsonl, name="DateTime Demo")
```

### Options

The `translate()` method accepts two keyword arguments:

- **name** (`str`, optional) -- Override the workflow name. Defaults to `"A2E Translated Workflow"` or the name set in the constructor.
- **add_manual_trigger** (`bool`, default `True`) -- When enabled, a Manual Trigger node is prepended so the workflow can be started from the n8n UI.

### Output Format

The returned dict has the following structure:

```python
{
    "name": "My Workflow",
    "nodes": [
        # List of n8n node dicts, each with name, type, typeVersion,
        # position, parameters, and a unique id.
    ],
    "connections": {
        # Keyed by source node name, maps outputs to target node inputs.
    },
    "settings": {
        "executionOrder": "v1",
    },
    "_a2e_meta": {
        "a2e_source": True,
    },
    "_a2e_translation": {
        "warnings": [],        # Any translation warnings
        "operation_count": 3,  # Number of A2E operations processed
        "node_count": 4,       # Total n8n nodes (includes trigger)
    },
}
```

Keys prefixed with `_` are internal metadata and are automatically stripped when pushing to n8n via `N8nClient`.

---

## 2. Pushing to n8n (N8nClient)

### Connection

```python
from n8n_bridge.n8n_client import N8nClient

client = N8nClient("http://localhost:5678", api_key="your-key")
```

The client authenticates using the `X-N8N-API-KEY` header against n8n's REST API v1.

### CRUD Operations

```python
# Check that n8n is reachable
status = client.health_check()
# Returns {"status": "healthy"}, {"status": "unhealthy", "code": "..."}, or
#         {"status": "unreachable", "error": "..."}

# List workflows (handles pagination automatically)
all_wfs = client.list_workflows()                  # all workflows
active_wfs = client.list_workflows(active=True)    # active only
page = client.list_workflows(limit=10)             # limit per page

# Create a workflow from a translated dict
created = client.create_workflow(n8n_wf)
workflow_id = created["id"]

# Update an existing workflow
updated = client.update_workflow(workflow_id, modified_wf)

# Activate a workflow
client.activate_workflow(workflow_id)

# Execute a workflow
result = client.execute_workflow(workflow_id, payload={"key": "value"})

# Delete a workflow
client.delete_workflow(workflow_id)
```

### End-to-End Pipeline

`A2EToN8nPipeline` combines translation, creation, and optional execution in a single call:

```python
from n8n_bridge.n8n_client import A2EToN8nPipeline

pipeline = A2EToN8nPipeline(n8n_url="http://localhost:5678", n8n_api_key="your-key")

# Translate and create
result = pipeline.run(a2e_workflow_str, name="My Pipeline")

# Translate, create, activate, and execute
result = pipeline.run(a2e_workflow_str, name="My Pipeline", activate=True, execute=True)
```

The returned dict contains:

```python
{
    "translation_warnings": [],
    "created_workflow": {
        "id": "abc123",
        "name": "My Pipeline",
        "node_count": 4,
    },
    "activated": True,          # present if activate=True
    "execution": {              # present if execute=True
        "id": "exec-456",
        "status": "success",
        "finished": True,
    },
}
```

---

## 3. Executing n8n Workflows from A2E (ExecuteN8nWorkflow)

### As A2E Operation

Include `ExecuteN8nWorkflow` directly in an A2E workflow to call an n8n workflow at runtime:

```json
{
  "operations": [
    {
      "id": "run-n8n",
      "op": "ExecuteN8nWorkflow",
      "workflowId": "abc123",
      "payload": {"key": "value"},
      "n8nUrl": "http://localhost:5678",
      "n8nApiKey": "your-key"
    }
  ]
}
```

### Environment Variable Fallback

If `n8nUrl` or `n8nApiKey` are not specified in the operation config, the executor falls back to environment variables:

- `N8N_URL` -- Base URL of the n8n instance (e.g., `http://localhost:5678`).
- `N8N_API_KEY` -- API key for authentication.

### Config Options

| Option               | Required | Default | Description                                      |
|----------------------|----------|---------|--------------------------------------------------|
| workflowId           | Yes      | --      | The n8n workflow ID to execute                    |
| payload              | No       | `{}`    | JSON payload passed to the workflow               |
| n8nUrl               | No       | env var | n8n instance URL (falls back to `N8N_URL`)        |
| n8nApiKey            | No       | env var | API key (falls back to `N8N_API_KEY`)             |
| waitForCompletion    | No       | `true`  | Wait for the workflow to finish before returning  |
| timeoutMs            | No       | `30000` | Timeout in milliseconds for the execution request |
| outputPath           | No       | --      | Path in workflow context to store the result      |

---

## 4. Enriching A2E Catalog from n8n (N8nCatalogEnricher)

The enricher reads n8n workflows and converts them into `ExecuteN8nWorkflow` catalog entries so A2E agents can discover and invoke them.

### From n8n API

```python
from n8n_bridge import N8nCatalogEnricher

enricher = N8nCatalogEnricher(n8n_url="http://localhost:5678", api_key="your-key")
entries = enricher.from_api(active_only=True)
# entries is a list of A2E catalog dicts
```

### From n8n-cli Catalog

If you use n8n-cli locally, the enricher can read its cached catalog files at `~/.n8n-cli/catalog/{profile}.json`:

```python
enricher = N8nCatalogEnricher()
entries = enricher.from_cli_catalog(profile="local")
```

### Merging into A2E Catalog

Write enriched entries into an existing A2E workflow catalog file (uses atomic write for safety):

```python
enricher.merge_into_catalog("workflow_catalog.json")
```

### Searching

Search enriched entries by keyword:

```python
results = enricher.search("email notification")
```

---

## 5. Testing

### Unit Tests

The unit tests cover translation, execution, and catalog enrichment with mocked dependencies:

```bash
pytest tests/test_n8n_bridge.py tests/test_n8n_execute_and_enrich.py -v
```

### Live Tests (requires running n8n)

Live integration tests connect to a real n8n instance:

```bash
pytest tests/test_n8n_live.py -v
```

### n8n-cli Configuration

Live tests read connection details from `~/.n8n-cli/config.json`. This file is created by the n8n-cli tool and typically contains:

```json
{
  "profiles": {
    "local": {
      "url": "http://localhost:5678",
      "apiKey": "your-api-key-here"
    }
  },
  "activeProfile": "local"
}
```

If this file is missing or the n8n instance is unreachable, live tests are automatically skipped.
