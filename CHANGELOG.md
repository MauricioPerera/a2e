# A2E Protocol Changelog

All notable changes to the A2E protocol will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-04-04

### Added

#### n8n Integration (n8n_bridge/)
- **A2E-to-n8n Translator**: Converts A2E workflows to n8n-compatible JSON (19 operation mappings)
- **ExecuteN8nWorkflow operation**: Native A2E operation to invoke n8n workflows via API
- **N8nCatalogEnricher**: Bidirectional catalog — imports n8n workflows as A2E catalog entries
- **N8nClient**: Python REST client for n8n API v1 (CRUD workflows, pagination)
- **A2EToN8nPipeline**: End-to-end translate -> create -> execute pipeline
- Live integration tests against real n8n instances

#### New Operations (11 added, total 19)
- **DateTime**: Unified date/time handler with modes (now, convert, calculate)
- **GetCurrentDateTime**: Current time with timezone support
- **ConvertTimezone**: Timezone conversion
- **DateCalculation**: Date arithmetic (add/subtract years, months, days, hours, etc.)
- **FormatText**: Text formatting (upper, lower, title, template, replace)
- **ExtractText**: Regex-based text extraction
- **ValidateData**: Data validation (email, url, number, phone, date, custom regex)
- **Calculate**: Mathematical operations (arithmetic, aggregation, rounding)
- **EncodeDecode**: Base64, URL, HTML encoding/decoding
- **SetData**: Store literal values in data model
- **ExecuteN8nWorkflow**: Execute n8n workflows from A2E

#### Executor Architecture Refactor
- Refactored monolithic executor (1855 lines) into modular mixin-based architecture
- Extracted 8 handler modules in executor/handlers/ (api, data, datetime_ops, text, validation, math_ops, encoding, flow)
- Extracted middleware classes to executor/middleware.py
- DAG-based parallel execution for independent operations (asyncio.gather)
- Topological sort using Kahn's algorithm grouped by depth

#### Circuit Breaker Pattern
- New CircuitBreaker class with CLOSED/OPEN/HALF_OPEN states
- CircuitBreakerMiddleware for ApiCall and ExecuteN8nWorkflow operations
- Per-host tracking with configurable failure threshold and recovery timeout
- Uses time.monotonic() for reliable timing

#### Security Improvements
- Vault master key externalized via A2E_VAULT_MASTER_KEY environment variable
- Vault salt configurable via A2E_VAULT_SALT environment variable
- Warning logged when using generated random key (non-persistent)
- JS string injection fix in n8n node_mapping.py (json.dumps escaping)

#### Compact Workflow Format
- Single JSON object format alongside legacy JSONL
- Implicit piping between operations
- "input" shorthand for inputPath references
- Auto-generated outputPath defaults

#### Agent Shell Integration (agent-shell/)
- 8 commands in a2e: namespace (health, capabilities, catalog, validate, execute, execution, translate, build)
- TypeScript adapter for A2E REST API
- Semantic vector search for command discovery
- Combined A2E + n8n mode with --with-n8n flag

### Changed
- Operations count increased from 8 to 19
- Workflow translator strips internal _a2e_* metadata before n8n API submission
- N8nClient timeouts increased to 30s for workflow create/update
- Catalog enricher keys now include SHA-256 hash suffix to prevent collisions
- Catalog file writes use atomic tempfile + os.replace pattern
- N8nClient.list_workflows() now supports cursor-based pagination

### Fixed
- Silent JSONL parsing failures now log warnings and populate translation warnings
- JS injection vulnerabilities in n8n node_mapping.py (RegExp, template literal, field names)
- Unicode arrow characters in examples replaced with ASCII for Windows compatibility
- n8n API rejection of 'active' and 'meta' fields in translated workflows

### Testing
- 222+ tests total (161 core + 61 n8n integration)
- pytest-cov configuration added to pyproject.toml
- Live n8n integration tests with skip marker for CI
- Reads n8n credentials from ~/.n8n-cli/config.json

---

## [1.0.0] - 2025-12-17

### Added

#### Protocol Specification
- Complete protocol specification document
- JSON Schema definitions for all message types
- Protocol overview and quick reference
- Comprehensive API reference

#### Core Operations
- **ApiCall**: HTTP request execution
- **FilterData**: Array filtering with conditions
- **TransformData**: Data transformation (map, sort, group, aggregate, select)
- **Conditional**: Conditional execution based on data
- **Loop**: Iteration over arrays
- **StoreData**: Persistent data storage
- **Wait**: Execution delay
- **MergeData**: Data source merging

#### Security Features
- Agent authentication via API keys
- Operation-level authorization
- API whitelist system
- Credentials vault with encrypted storage
- Workflow validation (structural, permission, dependency, type)

#### Production Features
- **Rate Limiting**: Per-agent and per-operation limits
- **Retry Logic**: Automatic retries with exponential backoff
- **Caching**: Operation result caching with TTL

#### RAG Integration
- Semantic search for operations
- Semantic search for APIs and endpoints
- Semantic search for knowledge bases
- Semantic search for credentials
- HNSW index for efficient vector search
- LokiJS database for metadata storage

#### Knowledge Management
- API Knowledge Base with RAG
- General Knowledge Base Manager
- CLI tools for knowledge base management
- REST API endpoints for knowledge search

#### Monitoring & Auditing
- Comprehensive audit logging
- Execution tracking
- Credential usage logging
- Performance metrics
- CLI tools for log analysis

#### Response & Error Handling
- Structured error responses
- Contextual error messages
- Suggestions for error resolution
- Response formatting (summary, detailed, raw)

#### Validation
- Proactive workflow validation
- Structural validation
- Dependency validation
- Type validation
- Permission validation

#### Developer Tools
- REST API server
- Python client SDK
- CLI tools for configuration
- Comprehensive test suite
- Example implementations

### Documentation
- Protocol specification (SPECIFICATION.md)
- JSON Schema definitions (SPECIFICATION_JSON_SCHEMAS.md)
- Protocol overview (PROTOCOL_OVERVIEW.md)
- LLM integration guide
- Quick start guide
- Component-specific documentation
- API reference

### Technical Details

#### Message Format
- JSON Lines (JSONL) format
- Two message types: `operationUpdate`, `beginExecution`
- Path-based data model references

#### Data Model
- Hierarchical JSON structure
- Path syntax: `/workflow/key`, `/workflow/array[0]`, `/workflow/object.field`
- Type system: String, Number, Boolean, Array, Object, Null

#### Execution Model
- Sequential operation execution
- Dependency resolution via paths
- Error handling with configurable behavior

#### Rate Limiting
- Default limits: 60 req/min, 1000 req/hour, 10000 req/day
- Per-operation limits (ApiCall: 30/min, 500/hour)
- HTTP headers: X-RateLimit-*, Retry-After
- 429 response for rate limit exceeded

#### Retry Logic
- Default: 3 retries, 1s initial delay, exponential backoff
- Max delay: 60 seconds
- Jitter enabled
- Retryable: 5xx, 408, 429, connection errors, timeouts
- Non-retryable: 4xx (except 408, 429), validation errors

#### Caching
- TTL-based expiration
- LRU eviction
- Operation-specific TTLs
- Cache statistics (hits, misses, hit rate)

### Security

- API key authentication
- Operation whitelist
- API whitelist
- Encrypted credential storage
- Credential reference system (agents never see values)
- Workflow validation before execution
- Audit logging of all operations

### Performance

- RAG reduces token usage by 60-80%
- HNSW index for fast vector search
- Operation result caching
- Batch processing support

---

## Version History

- **2.0.0** (2026-04-04): n8n integration, 11 new operations, executor refactor, circuit breaker, compact format, agent-shell integration
- **1.0.0** (2025-12-17): Initial stable release

---

## Future Versions

### Planned for 2.1.0

- Webhooks/Notifications
- Dashboard/UI
- Versioning system
- Distributed execution
- Streaming execution
- Workflow templates
- Workflow composition

### Under Consideration

- Multi-engine orchestration (beyond n8n)
- Visual workflow editor
- Real-time collaboration on workflows

---

**A2E Protocol Changelog**  
For detailed specifications, see [SPECIFICATION.md](./SPECIFICATION.md)

