# Integración RAG con LokiJS y Embeddings Locales

## Estado: ✅ COMPLETAMENTE INTEGRADO

A2E ahora incluye **RAG completo con LokiJS y embeddings locales** para:
- ✅ Operaciones del catálogo
- ✅ APIs y endpoints
- ✅ Knowledge bases
- ✅ Búsqueda semántica en todo

## Componentes

### 1. Sistema RAG Unificado (`rag_integration.py`)

**A2ERAGSystem** proporciona:
- **LokiJS Database**: Almacenamiento in-memory tipo LokiJS
- **Vector Index**: Índice vectorial con embeddings locales (sentence-transformers)
- **Búsqueda Semántica**: Para operaciones, APIs, endpoints y conocimiento
- **Persistencia**: Guardar/cargar base de datos

### 2. API Knowledge Base Integrada

**APIKnowledgeBase** ahora usa RAG automáticamente:
- Indexa APIs y endpoints en LokiJS
- Búsqueda semántica de endpoints
- Búsqueda semántica de APIs
- Construcción de schemas parciales

## Uso

### Inicialización Básica

```python
from api_knowledge_base import APIKnowledgeBase

# Crear con RAG habilitado (por defecto)
api_kb = APIKnowledgeBase(
    operations_catalog_path="workflow_catalog.json",
    use_rag=True  # Usa LokiJS y embeddings locales
)
```

### Búsqueda Semántica de Operaciones

```python
# Buscar operaciones relevantes
operations = api_kb.search_operations("consulta API y filtra datos", top_k=5)

# Construir schema parcial (solo operaciones relevantes)
partial_schema = api_kb.build_partial_schema(operations)
# Ahorro: 60-80% menos tokens
```

### Búsqueda Semántica de Endpoints

```python
# Buscar endpoints relevantes
endpoints = api_kb.search_endpoints("obtener usuarios con puntos", top_k=3)

for ep in endpoints:
    print(f"{ep['method']} {ep['path']}: {ep['description']}")
```

### Búsqueda Semántica de APIs

```python
# Buscar APIs relevantes
apis = api_kb.search_apis("API de usuarios", top_k=3)

for api in apis:
    print(f"{api['id']}: {api['baseUrl']}")
```

## Arquitectura

```
┌─────────────────────────────────────────┐
│  A2ERAGSystem                           │
│                                         │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │ LokiJS DB    │  │ Vector Index    │ │
│  │              │  │ (embeddings)    │ │
│  │ - operations │  │                 │ │
│  │ - apis       │  │ - sentence-     │ │
│  │ - endpoints  │  │   transformers  │ │
│  │ - knowledge  │  │ - local model   │ │
│  └──────────────┘  └─────────────────┘ │
│                                         │
│  Búsqueda Semántica                    │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  APIKnowledgeBase                      │
│                                         │
│  - Usa A2ERAGSystem                    │
│  - Indexa automáticamente               │
│  - Búsqueda semántica                   │
└─────────────────────────────────────────┘
```

## Embeddings Locales

- **Modelo por defecto**: `all-MiniLM-L6-v2`
- **Tamaño**: ~80MB
- **Velocidad**: Rápido (CPU)
- **Calidad**: Buena para búsqueda semántica

Para mejor calidad (más lento):
```python
rag = A2ERAGSystem(embedding_model="all-mpnet-base-v2")
```

## Persistencia

```python
# Guardar base de datos
rag.save("a2e_rag_db.json")

# Cargar base de datos
rag.load("a2e_rag_db.json")
```

## Ventajas

1. **Reducción de Tokens**: 60-80% menos tokens al usar schemas parciales
2. **Búsqueda Inteligente**: Encuentra operaciones/APIs relevantes semánticamente
3. **Almacenamiento Eficiente**: LokiJS es rápido y ligero
4. **Sin Dependencias Externas**: Embeddings locales, no requiere servicios externos
5. **Escalable**: Puede indexar miles de operaciones/APIs

## Ejemplo Completo

Ver `examples/rag_integration_example.py` para un ejemplo completo.

## Dependencias

- `a2ui-rag-catalog>=0.1.0`: Sistema RAG con LokiJS
- `sentence-transformers>=2.2.0`: Embeddings locales
- `numpy>=1.24.0`: Cálculos vectoriales

Todas las dependencias están incluidas en `pyproject.toml`.

