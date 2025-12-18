# Base de Conocimiento de APIs para Workflows

## Concepto

El agente necesita conocer:
1. **Qué operaciones puede ejecutar** (ApiCall, FilterData, etc.)
2. **Qué APIs están disponibles** (endpoints, métodos, parámetros)
3. **Restricciones de seguridad** (dominios permitidos, límites)

## Flujo de Información

```
┌─────────────────────────────────────────────────┐
│           CLIENTE                               │
│                                                 │
│  1. Define APIs permitidas                      │
│  2. Define operaciones disponibles              │
│  3. Anuncia capacidades al agente               │
└─────────────────────────────────────────────────┘
                    ↓
          [workflowCapabilities]
                    ↓
┌─────────────────────────────────────────────────┐
│           AGENTE                                │
│                                                 │
│  1. Recibe capacidades del cliente              │
│  2. Usa RAG para buscar APIs relevantes         │
│  3. Genera workflow usando solo APIs permitidas │
└─────────────────────────────────────────────────┘
```

## Estructura de Capacidades

### Mensaje del Cliente al Agente

```json
{
  "metadata": {
    "workflowCapabilities": {
      "supportedOperations": ["ApiCall", "FilterData", "StoreData"],
      "availableApis": {
        "user-api": {
          "baseUrl": "https://api.example.com",
          "endpoints": [
            {
              "path": "/users",
              "method": "GET",
              "description": "Obtiene lista de usuarios",
              "parameters": [...]
            }
          ]
        }
      },
      "securityConstraints": {
        "allowedDomains": ["api.example.com"],
        "maxExecutionTime": 30000,
        "maxOperations": 20
      }
    }
  }
}
```

## Integración con RAG

El sistema RAG puede indexar las APIs:

```python
# Indexar APIs en RAG
indexer = ComponentIndexer()
indexer.index_catalog("workflow_catalog.json")  # Operaciones
indexer.index_apis("api_definitions.json")      # APIs

# Buscar APIs relevantes
rag = ComponentRAG(indexer.get_database(), indexer.get_vector_index())
apis = rag.search_components("obtener usuarios", top_k=3)
# Encuentra: GET /users, GET /users/{id}, etc.
```

## Ejemplo Completo

### 1. Cliente Define APIs

```python
api_kb = APIKnowledgeBase()
api_kb.add_api(
    api_id="user-api",
    base_url="https://api.example.com",
    endpoints=[...]
)
```

### 2. Cliente Anuncia al Agente

```python
capabilities = ClientCapabilitiesAnnouncer(api_kb)
message = capabilities.build_capabilities_message()
# Enviar al agente en metadata
```

### 3. Agente Busca APIs Relevantes

```python
agent = WorkflowAgent(api_kb, rag_system)
relevant_apis = agent.search_relevant_apis("obtener usuarios con puntos")
# Encuentra: GET /users con parámetro minPoints
```

### 4. Agente Genera Workflow

```jsonl
{"operationUpdate": {"operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users?minPoints=100",
      "outputPath": "/workflow/users"
    }
  }}
]}}
```

### 5. Cliente Valida

```python
is_valid, error = agent.validate_workflow(workflow_jsonl)
# Valida que:
# - Operación ApiCall está permitida ✅
# - URL está en dominio permitido ✅
# - Método GET está permitido ✅
```

## Ventajas

1. **Seguridad**: Solo APIs pre-definidas
2. **Descubrimiento**: Agente encuentra APIs relevantes
3. **Validación**: Cliente valida antes de ejecutar
4. **RAG integrado**: Búsqueda semántica de APIs

## Próximos Pasos

1. Integrar con sistema RAG existente
2. Agregar indexación de APIs
3. Implementar validación de seguridad
4. Crear sistema de anuncio de capacidades

