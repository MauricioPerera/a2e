# A2E: Agent-to-Execution Protocol

**Version**: 2.0.0
**Status**: Stable
**License**: Apache 2.0

A2E (Agent-to-Execution) is a declarative protocol that enables AI agents to generate and execute workflows without arbitrary code execution. Inspired by A2UI and MCP protocols, A2E provides a secure, controlled environment for agent-driven task automation.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -e .

# Start server
python server/a2e_server.py --config a2e_config.json --port 8000

# Run tests
pytest tests/ -v
```

## 📚 Documentation

### Protocol Specification

- **[SPECIFICATION.md](./SPECIFICATION.md)** - Complete protocol specification (v2.0.0)
- **[docs/PROTOCOL_OVERVIEW.md](./docs/PROTOCOL_OVERVIEW.md)** - Protocol overview
- **[docs/SPECIFICATION_JSON_SCHEMAS.md](./docs/SPECIFICATION_JSON_SCHEMAS.md)** - JSON Schema definitions

### Implementation Guides

- **[docs/guides/QUICK_START.md](./docs/guides/QUICK_START.md)** - Quick start guide
- **[docs/guides/LLM_INTEGRATION_GUIDE.md](./docs/guides/LLM_INTEGRATION_GUIDE.md)** - LLM integration guide
- **[docs/guides/DASHBOARD_GUIDE.md](./docs/guides/DASHBOARD_GUIDE.md)** - Dashboard guide
- **[docs/guides/RAG_SETUP.md](./docs/guides/RAG_SETUP.md)** - RAG setup guide
- **[docs/guides/EXECUTOR_ARCHITECTURE.md](./docs/guides/EXECUTOR_ARCHITECTURE.md)** - Executor architecture

### Integrations

- **[docs/integrations/CLOUDFLARE_AGENT_GUIDE.md](./docs/integrations/CLOUDFLARE_AGENT_GUIDE.md)** - Cloudflare Workers
- **[docs/integrations/GOOGLE_ADK_GUIDE.md](./docs/integrations/GOOGLE_ADK_GUIDE.md)** - Google ADK
- **[docs/integrations/N8N_BRIDGE_GUIDE.md](./docs/integrations/N8N_BRIDGE_GUIDE.md)** - n8n Integration

## ✨ Features

- ✅ **Declarative Protocol**: Agents describe *what* to do, not *how*
- ✅ **Secure Execution**: Only pre-defined operations can be executed
- ✅ **RAG Integration**: Semantic search reduces token usage by 60-80%
- ✅ **HNSW Index**: Efficient vector search for large datasets
- ✅ **Rate Limiting**: Per-agent and per-operation limits
- ✅ **Retry Logic**: Automatic retries with exponential backoff
- ✅ **Caching**: Operation result caching with TTL
- ✅ **Knowledge Bases**: Semantic search for APIs, endpoints, and general knowledge
- ✅ **Credentials Vault**: Secure, encrypted credential storage
- ✅ **Authentication & Authorization**: Fine-grained permission system
- ✅ **Monitoring & Auditing**: Comprehensive execution logging
- ✅ **n8n Integration**: Bidirectional bridge (translate A2E→n8n, execute n8n from A2E, enrich catalog)
- ✅ **DAG Parallel Execution**: Independent operations execute concurrently
- ✅ **Circuit Breaker**: Resilience pattern for external API calls
- ✅ **Compact JSON Format**: Simplified workflow format alongside JSONL
- ✅ **Agent Shell Integration**: TypeScript commands for semantic discovery

## 📋 Operations

A2E supports 19 operations organized by category:

**Core**
- **ApiCall** - HTTP requests
- **FilterData** - Array filtering
- **TransformData** - Data transformation
- **MergeData** - Data merging
- **StoreData** - Persistent storage
- **SetData** - Variable assignment

**Flow Control**
- **Conditional** - Conditional execution
- **Loop** - Array iteration
- **Wait** - Execution delay

**DateTime**
- **DateTime** - Date/time parsing and formatting
- **GetCurrentDateTime** - Current timestamp
- **ConvertTimezone** - Timezone conversion
- **DateCalculation** - Date arithmetic

**Text**
- **FormatText** - Text formatting and templating
- **ExtractText** - Text extraction with patterns

**Utility**
- **ValidateData** - Data validation
- **Calculate** - Mathematical expressions
- **EncodeDecode** - Encoding/decoding (Base64, URL, etc.)

**Integration**
- **ExecuteN8nWorkflow** - Execute n8n workflows

## 🔒 Security

- API key authentication
- Operation whitelist
- API whitelist
- Encrypted credential storage
- Environment-based vault key management (`A2E_VAULT_MASTER_KEY`)
- Workflow validation
- Comprehensive audit logging
- Circuit breaker for external service resilience

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/MauricioPerera/a2e.git
cd a2e

# Install dependencies
pip install -e .

# Install RAG dependencies (optional but recommended)
pip install tf-keras torch transformers
```

## 🏗️ Architecture

```
Agent (LLM)
    |
A2E Server (Flask REST API)
    |
WorkflowExecutor + Middlewares
    |-- AuditMiddleware      (logging, monitoring)
    |-- CacheMiddleware      (result caching)
    |-- VaultMiddleware      (credential injection)
    |-- CircuitBreakerMiddleware (resilience)
    |
Operation Handlers (19 operations via mixin architecture)
    |-- ApiHandlerMixin      (ApiCall, ExecuteN8nWorkflow)
    |-- DataHandlerMixin     (FilterData, TransformData, MergeData, StoreData, SetData)
    |-- DateTimeHandlerMixin (DateTime, GetCurrentDateTime, ConvertTimezone, DateCalculation)
    |-- TextHandlerMixin     (FormatText, ExtractText)
    |-- ValidationHandlerMixin (ValidateData)
    |-- MathHandlerMixin     (Calculate)
    |-- EncodingHandlerMixin (EncodeDecode)
    |-- FlowHandlerMixin     (Wait, Loop, Conditional)
    |
Results
```

### Project Structure

```
a2e/
|-- executor/           # Workflow executor (refactored)
|   |-- handlers/       # Operation handler mixins (8 modules)
|   |-- middleware.py    # Middleware classes
|   |-- circuit_breaker.py # Circuit breaker pattern
|-- n8n_bridge/         # n8n integration (NEW)
|   |-- translator.py   # A2E -> n8n workflow translation
|   |-- node_mapping.py # 19 operation mappings
|   |-- n8n_client.py   # n8n REST API client
|   |-- catalog_enricher.py # n8n -> A2E catalog enrichment
|-- server/             # Flask REST API + dashboard metrics
|-- auth/               # Authentication & authorization
|-- vault/              # Encrypted credential storage
|-- knowledge/          # API & general knowledge bases
|-- sql/                # SQL query management
|-- monitoring/         # Audit logging
|-- responses/          # Response formatting & error handling
|-- rate_limiting/      # Rate limiting
|-- retry/              # Retry with exponential backoff
|-- cache/              # Result caching with LRU
|-- cli/                # CLI tools
|-- validation/         # Workflow validation
|-- tests/              # Test suite (222+ tests)
|-- examples/           # Usage examples
|-- docs/               # Documentation
```

## 📖 Example

### JSONL Format

```jsonl
{"type":"operationUpdate","operationId":"fetch-users","operation":{"ApiCall":{"method":"GET","url":"https://api.example.com/users","outputPath":"/workflow/users"}}}
{"type":"operationUpdate","operationId":"filter-active","operation":{"FilterData":{"inputPath":"/workflow/users","conditions":[{"field":"status","operator":"==","value":"active"}],"outputPath":"/workflow/active-users"}}}
{"type":"beginExecution","executionId":"exec-1","operationOrder":["fetch-users","filter-active"]}
```

### Compact JSON Format

```json
{
  "operations": [
    {"id": "fetch", "op": "ApiCall", "method": "GET", "url": "https://api.example.com/users"},
    {"id": "filter", "op": "FilterData", "input": "fetch", "conditions": [{"field": "status", "operator": "==", "value": "active"}]},
    {"id": "transform", "op": "TransformData", "input": "filter", "type": "pick", "config": {"fields": ["name", "email"]}}
  ],
  "execute": "fetch"
}
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=executor --cov=n8n_bridge --cov-report=term-missing

# Run n8n live integration tests (requires running n8n)
pytest tests/test_n8n_live.py -v

# Run specific module tests
pytest tests/test_n8n_bridge.py tests/test_n8n_execute_and_enrich.py -v
```

## 📝 License

Apache 2.0 License

## 🤝 Contributing

Contributions are welcome! Please read the specification and follow the code style.

## 📧 Contact

For questions or issues, please open an issue on GitHub.

---

**A2E Protocol v2.0.0** - [Full Specification](./SPECIFICATION.md)
