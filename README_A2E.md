# A2E: Agent-to-Execution

## ¿Qué es A2E?

**A2E** es un protocolo declarativo que permite a agentes generar workflows/tareas ejecutables de forma segura, inspirado en la filosofía de **A2UI** (Agent-to-User Interface).

## Inspiración y Filosofía

### Cadena de Inspiración

```
MCP (Model Context Protocol)
  └── A2UI (Agent-to-User Interface)
      └── A2E (Agent-to-Execution)
```

### Filosofía Compartida

A2E adopta los mismos principios de diseño que A2UI:

1. **Seguridad primero**: Solo operaciones pre-aprobadas del catálogo
2. **Declarativo, no ejecutable**: El agente describe intención, el cliente ejecuta
3. **LLM-friendly**: Formato JSONL fácil de generar incrementalmente
4. **Catálogo de confianza**: Cliente controla qué se puede ejecutar
5. **Framework-agnostic**: Separación entre intención y ejecución

## Diferencias con A2UI

| Aspecto | A2UI | A2E |
|---------|------|-----|
| **Propósito** | Generar UIs | Ejecutar workflows |
| **Resultado** | Componentes visuales | Datos/resultados |
| **Catálogo** | Componentes UI | Operaciones |
| **Mensajes** | `surfaceUpdate`, `beginRendering` | `operationUpdate`, `beginExecution` |
| **Ejecución** | Renderizado | Código ejecutado |

## Principios de Diseño

### 1. Seguridad por Catálogo

El agente solo puede usar operaciones del catálogo pre-definido:

```json
{
  "ApiCall": {...},
  "FilterData": {...},
  "StoreData": {...}
}
```

### 2. Referencias, No Valores

Para credenciales, el agente solo referencia IDs:

```json
{
  "headers": {
    "Authorization": {
      "credentialRef": {"id": "api-token"}
    }
  }
}
```

El cliente inyecta el valor real (nunca visto por el agente).

### 3. RAG para Optimización

Usa RAG para buscar solo operaciones relevantes, reduciendo tokens del LLM:

```python
# Buscar operaciones relevantes
operations = rag.search_components("consulta API", top_k=3)
# Construir schema parcial (solo 3 operaciones vs 20+)
schema = rag.build_partial_schema(operations)
```

### 4. Base de Conocimiento de APIs

El cliente anuncia qué APIs están disponibles:

```json
{
  "workflowCapabilities": {
    "availableApis": {
      "user-api": {
        "baseUrl": "https://api.example.com",
        "endpoints": [...]
      }
    }
  }
}
```

## Arquitectura

```
┌─────────────────────────────────────────────────┐
│           AGENTE (LLM)                          │
│                                                 │
│  Genera JSONL A2E con:                          │
│  - Operaciones del catálogo                     │
│  - Referencias a credenciales                   │
│  - Referencias a APIs permitidas                │
└─────────────────────────────────────────────────┘
                    ↓
          [Protocolo A2A/HTTP]
                    ↓
┌─────────────────────────────────────────────────┐
│           CLIENTE (Executor)                    │
│                                                 │
│  1. Valida operaciones                          │
│  2. Resuelve credenciales                      │
│  3. Valida APIs                                │
│  4. Ejecuta código pre-definido                │
└─────────────────────────────────────────────────┘
```

## Componentes

1. **Workflow Executor**: Ejecuta operaciones del catálogo
2. **API Knowledge Base**: Base de conocimiento de APIs permitidas
3. **Credentials Vault**: Almacenamiento seguro de credenciales
4. **RAG System**: Búsqueda semántica de operaciones

## Ejemplo

### Agente Genera (A2E)
```jsonl
{"operationUpdate": {"operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "headers": {
        "Authorization": {
          "credentialRef": {"id": "api-token"}
        }
      },
      "outputPath": "/workflow/users"
    }
  }},
  {"id": "filter", "operation": {
    "FilterData": {
      "inputPath": "/workflow/users",
      "conditions": [{"field": "points", "operator": ">", "value": 100}],
      "outputPath": "/workflow/filtered"
    }
  }}
]}}
{"beginExecution": {"workflowId": "example", "root": "fetch"}}
```

### Cliente Ejecuta
```python
executor = SecureWorkflowExecutor(vault)
executor.load_workflow(workflow_jsonl)
results = await executor.execute()
# Resultado: Datos filtrados en /workflow/filtered
```

## Relación con A2UI

A2E **no es** A2UI, pero:
- ✅ Reutiliza la misma filosofía de diseño
- ✅ Reutiliza el mismo formato JSONL
- ✅ Reutiliza el mismo sistema de catálogos
- ✅ Reutiliza el mismo sistema RAG
- ✅ Complementa A2UI (pueden usarse juntos)

## Referencias

- **A2UI**: [https://github.com/google/a2ui](https://github.com/google/a2ui)
- **MCP**: [Model Context Protocol](https://modelcontextprotocol.io/)

