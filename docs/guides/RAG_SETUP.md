# Configuración de RAG en A2E

## Estado Actual

✅ **Código de integración completo**
⚠️ **Requiere configuración de minimemory**

## Modelo de Embeddings

A2E usa **intfloat/multilingual-e5-small** como modelo de embeddings:

| Propiedad | Valor |
|-----------|-------|
| Modelo | `intfloat/multilingual-e5-small` |
| Dimensiones | 384 |
| Idiomas | 100+ |
| Tamaño | ~100M parámetros |
| Prefijos | `query:` para búsquedas, `passage:` para contenido indexado |

Los prefijos se aplican automáticamente en `_remember()` y `_recall()`.

## Pasos para Habilitar RAG

### 1. Instalar minimemory SDK

```bash
pip install minimemory
```

### 2. Configurar Variables de Entorno

```bash
export MINIMEMORY_URL="https://your-minimemory-instance.com"
export MINIMEMORY_API_KEY="your-api-key"
export MINIMEMORY_NAMESPACE="a2e"  # opcional, default "a2e"
```

### 3. Verificar Instalación

```bash
python -c "from rag_integration import A2ERAGSystem; print('RAG OK')"
```

## Uso

```python
from rag_integration import A2ERAGSystem

# Inicializar (usa minimemory + multilingual-e5-small)
rag = A2ERAGSystem()

# Indexar catálogo de operaciones
rag.index_operations_catalog("workflow_catalog.json")

# Búsqueda semántica (funciona en 100+ idiomas)
operations = rag.search_operations("consulta API", top_k=5)
endpoints = rag.search_endpoints("obtener usuarios", top_k=3)

# Búsqueda de SQL queries
queries = rag.search_sql_queries("ventas por mes", database="analytics")
```

## Soporte Multilingue

Gracias a multilingual-e5-small, las búsquedas funcionan en cualquier idioma:

```python
# Español
rag.search_operations("filtrar datos de un array")

# English
rag.search_operations("filter data from an array")

# Deutsch
rag.search_operations("Daten aus einem Array filtern")
```

## Sin RAG

Si minimemory no está configurado, A2E funciona sin RAG:

```python
from api_knowledge_base import APIKnowledgeBase

api_kb = APIKnowledgeBase(use_rag=False)
endpoints = api_kb.search_endpoints("usuarios")  # Búsqueda por keywords
```

## Solución de Problemas

### "Could not import minimemory SDK"

**Causa**: minimemory no está instalado

**Solución**: `pip install minimemory`

### "RAG components not configured"

**Causa**: Variables de entorno MINIMEMORY_URL / MINIMEMORY_API_KEY no están definidas

**Solución**: Configurar las variables de entorno o pasar `base_url` y `api_key` al constructor

### "RAG system not available"

**Causa**: RAG no pudo inicializarse

**Solución**: Verificar que minimemory está instalado y las credenciales son correctas

