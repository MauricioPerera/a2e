# A2E: Agent-to-Execution - Concepto

## Idea Central

**A2E** (Agent-to-Execution) es un protocolo de **ejecución de workflows/tareas**, inspirado en la filosofía de **A2UI** (Agent-to-User Interface), que a su vez se inspira en el protocolo **MCP** (Model Context Protocol).

A2E extiende la filosofía de A2UI:

**A2UI**:
- Componentes UI → Renderizar en pantalla

**A2E** (inspirado en A2UI):
- Operaciones → Ejecutar código/funciones

## Arquitectura Propuesta

```
┌─────────────────────────────────────────────────┐
│           AGENTE (LLM)                         │
│                                                 │
│  Genera JSONL con plan de ejecución:           │
│  {"operationUpdate": {"operations": [           │
│    {"id": "step1", "operation": {               │
│      "ApiCall": {"endpoint": "...", ...}        │
│    }},                                          │
│    {"id": "step2", "operation": {              │
│      "FilterData": {"input": "step1", ...}      │
│    }}                                           │
│  ]}}                                            │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│           CLIENTE (Executor)                    │
│                                                 │
│  1. Recibe JSONL                                │
│  2. Parsea operaciones                          │
│  3. Ejecuta secuencialmente                     │
│     - step1: ApiCall → resultado                │
│     - step2: FilterData(resultado) → filtrado   │
│  4. Retorna resultados                         │
└─────────────────────────────────────────────────┘
```

## Catálogo de Operaciones (en lugar de Componentes UI)

### Operaciones Básicas

```json
{
  "ApiCall": {
    "type": "object",
    "properties": {
      "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
      "url": {"type": "string"},
      "headers": {"type": "object"},
      "body": {"type": "object"},
      "outputPath": {"type": "string"}  // Dónde guardar resultado
    },
    "required": ["method", "url", "outputPath"]
  },
  
  "FilterData": {
    "type": "object",
    "properties": {
      "inputPath": {"type": "string"},  // De dónde leer datos
      "filter": {"type": "object"},     // Condiciones de filtrado
      "outputPath": {"type": "string"}  // Dónde guardar resultado
    },
    "required": ["inputPath", "outputPath"]
  },
  
  "TransformData": {
    "type": "object",
    "properties": {
      "inputPath": {"type": "string"},
      "transform": {"type": "string"},  // "map", "reduce", "sort", etc.
      "outputPath": {"type": "string"}
    }
  },
  
  "Conditional": {
    "type": "object",
    "properties": {
      "condition": {"type": "object"},  // Condición a evaluar
      "ifTrue": {"type": "string"},     // ID de operación si true
      "ifFalse": {"type": "string"}     // ID de operación si false
    }
  },
  
  "StoreData": {
    "type": "object",
    "properties": {
      "inputPath": {"type": "string"},
      "storage": {"type": "string", "enum": ["localStorage", "sessionStorage", "database"]},
      "key": {"type": "string"}
    }
  }
}
```

## Ejemplo de Workflow

### Query del Usuario:
"Consulta la API de usuarios, filtra los que tienen más de 100 puntos, y guárdalos"

### JSONL Generado por Agente:

```jsonl
{"operationUpdate": {"workflowId": "user-filter", "operations": [
  {"id": "fetch-users", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "headers": {"Authorization": "Bearer {token}"},
      "outputPath": "/workflow/users"
    }
  }},
  {"id": "filter-active", "operation": {
    "FilterData": {
      "inputPath": "/workflow/users",
      "filter": {
        "field": "points",
        "operator": ">",
        "value": 100
      },
      "outputPath": "/workflow/filtered-users"
    }
  }},
  {"id": "store-result", "operation": {
    "StoreData": {
      "inputPath": "/workflow/filtered-users",
      "storage": "localStorage",
      "key": "active-users"
    }
  }}
]}}

{"beginExecution": {"workflowId": "user-filter", "root": "fetch-users"}}
```

### Ejecución en Cliente:

```typescript
// 1. Ejecutar fetch-users
const users = await fetch("https://api.example.com/users", {
  headers: {"Authorization": "Bearer token"}
}).then(r => r.json());
dataModel.set("/workflow/users", users);

// 2. Ejecutar filter-active
const filtered = users.filter(u => u.points > 100);
dataModel.set("/workflow/filtered-users", filtered);

// 3. Ejecutar store-result
localStorage.setItem("active-users", JSON.stringify(filtered));
```

## Ventajas

1. **Inspirado en A2UI**: Reutiliza la filosofía y estructura de A2UI
2. **Seguridad**: Solo operaciones pre-aprobadas (como componentes UI en A2UI)
3. **LLM-friendly**: Mismo formato JSONL fácil de generar
4. **Extensible**: Agregar nuevas operaciones como componentes
5. **Misma filosofía**: Seguridad primero, declarativo, catálogo de confianza

## Consideraciones de Seguridad

- **Sandboxing**: Ejecutar operaciones en entorno aislado
- **Whitelist de APIs**: Solo endpoints permitidos
- **Validación**: Validar todas las operaciones antes de ejecutar
- **Rate limiting**: Limitar ejecuciones por tiempo

## Comparación con A2UI

| Aspecto | A2UI (UI) | A2E (Ejecución) |
|---------|-----------|-----------------|
| **Catálogo** | Componentes UI (Text, Button) | Operaciones (ApiCall, Filter) |
| **Ejecución** | Renderizar componentes | Ejecutar operaciones |
| **Resultado** | UI visible | Datos/resultados |
| **Flujo** | Visual (árbol de componentes) | Secuencial (workflow) |
| **Datos** | Data Model (estado UI) | Workflow State (resultados) |
| **Inspiración** | MCP | A2UI (que se inspira en MCP) |

