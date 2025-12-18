# A2E: Agent-to-Execution Protocol

**Version**: 1.0.0  
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

- **[PROTOCOL_OVERVIEW.md](./PROTOCOL_OVERVIEW.md)** - Protocol overview
- **[SPECIFICATION.md](./SPECIFICATION.md)** - Complete protocol specification (v1.0.0)
- **[SPECIFICATION_JSON_SCHEMAS.md](./SPECIFICATION_JSON_SCHEMAS.md)** - JSON Schema definitions
- **[PROTOCOL_INDEX.md](./PROTOCOL_INDEX.md)** - Documentation index

### Implementation Guides

- **[QUICK_START.md](./QUICK_START.md)** - Quick start guide
- **[LLM_INTEGRATION_GUIDE.md](./LLM_INTEGRATION_GUIDE.md)** - LLM integration guide
- **[README_PHASE2.md](./README_PHASE2.md)** - Production features (Rate Limiting, Retry, Cache)

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

## 📋 Operations

A2E supports 8 core operations:

1. **ApiCall** - HTTP requests
2. **FilterData** - Array filtering
3. **TransformData** - Data transformation
4. **Conditional** - Conditional execution
5. **Loop** - Array iteration
6. **StoreData** - Persistent storage
7. **Wait** - Execution delay
8. **MergeData** - Data merging

## 🔒 Security

- API key authentication
- Operation whitelist
- API whitelist
- Encrypted credential storage
- Workflow validation
- Comprehensive audit logging

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
    ↓
A2E Server (Validation, Execution, Monitoring)
    ↓
Workflow Executor (Operation Execution)
    ↓
Results
```

## 📖 Example

```jsonl
{"type":"operationUpdate","operationId":"fetch-users","operation":{"ApiCall":{"method":"GET","url":"https://api.example.com/users","outputPath":"/workflow/users"}}}
{"type":"operationUpdate","operationId":"filter-active","operation":{"FilterData":{"inputPath":"/workflow/users","conditions":[{"field":"status","operator":"==","value":"active"}],"outputPath":"/workflow/active-users"}}}
{"type":"beginExecution","executionId":"exec-1","operationOrder":["fetch-users","filter-active"]}
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_phase2.py -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

## 📝 License

Apache 2.0 License

## 🤝 Contributing

Contributions are welcome! Please read the specification and follow the code style.

## 📧 Contact

For questions or issues, please open an issue on GitHub.

---

**A2E Protocol v1.0.0** - [Full Specification](./SPECIFICATION.md)
