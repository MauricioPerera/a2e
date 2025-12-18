# Gestión de Bases de Conocimiento en A2E

## Estado: ✅ COMPLETAMENTE IMPLEMENTADO

A2E incluye un **sistema completo de gestión de bases de conocimiento** usando:
- ✅ **LokiJS Database** para almacenamiento
- ✅ **Embeddings locales** para búsqueda semántica
- ✅ **CLI tools** para gestión
- ✅ **API programática** para integración

## Componentes

### 1. KnowledgeBaseManager (`knowledge_base_manager.py`)

Gestor principal de bases de conocimiento:

- ✅ Carga bases de conocimiento desde archivos JSON
- ✅ Agrega items de conocimiento programáticamente
- ✅ Búsqueda semántica usando RAG
- ✅ Búsqueda por keywords (fallback)
- ✅ Exportación de bases de conocimiento
- ✅ Listado y consulta de bases de conocimiento

### 2. CLI Tools (`cli/kb_cli.py`)

Herramientas de línea de comandos:

- ✅ `add` - Agregar item de conocimiento
- ✅ `load` - Cargar base de conocimiento desde archivo
- ✅ `search` - Buscar conocimiento
- ✅ `list` - Listar bases de conocimiento
- ✅ `export` - Exportar base de conocimiento

## Uso

### Programático

```python
from knowledge_base_manager import KnowledgeBaseManager

# Crear gestor (usa RAG automáticamente)
manager = KnowledgeBaseManager(use_rag=True)

# Cargar base de conocimiento
manager.load_knowledge_base(
    kb_id="workflow-patterns",
    kb_path="knowledge_base.json",
    kb_type="pattern"
)

# Agregar item
manager.add_knowledge_item(
    kb_id="workflow-patterns",
    item_id="pattern-1",
    item={
        "title": "Patrón API",
        "description": "Consulta API y procesa datos",
        "content": {...}
    },
    knowledge_type="pattern"
)

# Buscar conocimiento
results = manager.search_knowledge(
    query="consulta API y filtra",
    top_k=5
)
```

### CLI

```bash
# Cargar base de conocimiento
python cli/kb_cli.py load --kb-id patterns --path knowledge_base.json

# Buscar conocimiento
python cli/kb_cli.py search --query "consulta API" --top-k 5

# Agregar item
python cli/kb_cli.py add \
  --kb-id patterns \
  --item-id pattern-1 \
  --title "Patrón API" \
  --description "Consulta API y procesa"

# Listar bases
python cli/kb_cli.py list

# Exportar
python cli/kb_cli.py export --kb-id patterns --output exported.json
```

## Formato de Base de Conocimiento

```json
{
  "id": "workflow-patterns",
  "type": "pattern",
  "description": "Patrones comunes de workflows",
  "items": [
    {
      "id": "pattern-1",
      "title": "Patrón API → Filtrar",
      "description": "Consulta API y filtra resultados",
      "content": {
        "operations": ["ApiCall", "FilterData"],
        "example": "..."
      }
    }
  ]
}
```

## Integración con RAG

El sistema usa RAG automáticamente cuando está disponible:

1. **Indexación**: Cada item se indexa en LokiJS con embeddings
2. **Búsqueda Semántica**: Encuentra conocimiento relevante por significado
3. **Fallback**: Si RAG no está disponible, usa búsqueda por keywords

## Casos de Uso

### 1. Patrones de Workflows

Almacenar patrones comunes que el LLM puede usar:

```python
manager.add_knowledge_item(
    kb_id="patterns",
    item_id="api-filter-store",
    item={
        "title": "API → Filtrar → Almacenar",
        "pattern": {
            "operations": ["ApiCall", "FilterData", "StoreData"]
        }
    }
)
```

### 2. Documentación

Almacenar documentación de APIs, operaciones, etc.:

```python
manager.load_knowledge_base(
    kb_id="api-docs",
    kb_path="api_documentation.json",
    kb_type="documentation"
)
```

### 3. Ejemplos

Almacenar ejemplos de workflows exitosos:

```python
manager.add_knowledge_item(
    kb_id="examples",
    item_id="user-filter-example",
    item={
        "title": "Ejemplo: Filtrar Usuarios",
        "workflow": {...},
        "description": "Workflow que filtra usuarios activos"
    }
)
```

## Ventajas

1. **Búsqueda Inteligente**: Encuentra conocimiento relevante semánticamente
2. **Almacenamiento Eficiente**: LokiJS es rápido y ligero
3. **Sin Servicios Externos**: Todo funciona localmente
4. **Flexible**: Funciona con o sin RAG
5. **Escalable**: Puede almacenar miles de items

## Ejemplo Completo

Ver `examples/knowledge_base_usage.py` para un ejemplo completo.

## Próximos Pasos

1. ⏳ Integrar con el agente para usar conocimiento en generación de workflows
2. ⏳ Agregar versionado de bases de conocimiento
3. ⏳ Agregar validación de esquemas para items
4. ⏳ Agregar sincronización automática

