# Guía de Consultas SQL en A2E

## Descripción

A2E permite a los **clientes** registrar consultas SQL en un catálogo que los **agentes** pueden buscar y usar. Las consultas SQL se indexan usando RAG (Retrieval-Augmented Generation) con embeddings locales, permitiendo búsqueda semántica.

## Características

- ✅ **Búsqueda Semántica**: Los agentes pueden buscar consultas usando lenguaje natural
- ✅ **Indexación con RAG**: Usa LokiJS y embeddings locales para búsqueda eficiente
- ✅ **Filtrado**: Por base de datos, categoría, etc.
- ✅ **Metadatos**: Cada consulta puede incluir descripción, parámetros, categoría, etc.
- ✅ **API REST**: Endpoints para gestionar y buscar consultas SQL

## Arquitectura

```
Cliente (registra consultas SQL)
    ↓
SQLQueryManager (indexa en RAG)
    ↓
A2ERAGSystem (LokiJS + Vector Index)
    ↓
Agente (busca consultas relevantes)
```

## Uso Básico

### 1. Registrar Consultas SQL (Cliente)

```python
from sql_query_manager import SQLQueryManager

# Crear gestor
manager = SQLQueryManager(use_rag=True)

# Registrar una consulta
manager.add_sql_query(
    query_id="get-active-users",
    sql_query="SELECT id, name, email FROM users WHERE status = 'active'",
    description="Obtiene todos los usuarios activos",
    database="main_db",
    category="select",
    parameters=["status"]
)
```

### 2. Buscar Consultas SQL (Agente)

```python
# Búsqueda semántica
results = manager.search_sql_queries(
    query="obtener usuarios activos",
    top_k=5
)

for result in results:
    print(f"ID: {result['id']}")
    print(f"SQL: {result['sql']}")
    print(f"Descripción: {result['description']}")
    print(f"Score: {result['score']}")
```

### 3. Uso desde Cliente A2E

```python
from client.a2e_client import A2EClient

client = A2EClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# Buscar consultas SQL
results = client.search_sql_queries(
    query="obtener usuarios activos",
    top_k=5
)

# Listar todas las consultas
all_queries = client.list_sql_queries(database="main_db")

# Obtener una consulta específica
query = client.get_sql_query("get-active-users")
```

## Formato de Consultas SQL

### Estructura Básica

```json
{
  "id": "query-id-unique",
  "sql": "SELECT * FROM users WHERE id = ?",
  "description": "Descripción de qué hace la consulta",
  "database": "main_db",
  "category": "select",
  "parameters": ["id"],
  "metadata": {
    "author": "admin",
    "created_at": "2025-01-01"
  }
}
```

### Categorías Comunes

- `select`: Consultas SELECT
- `insert`: Consultas INSERT
- `update`: Consultas UPDATE
- `delete`: Consultas DELETE
- `analytics`: Consultas analíticas (agregaciones, GROUP BY, etc.)
- `general`: Categoría por defecto

## Cargar desde Archivo

### Formato JSON

```json
{
  "queries": [
    {
      "id": "get-users",
      "sql": "SELECT * FROM users",
      "description": "Obtiene todos los usuarios",
      "database": "main_db",
      "category": "select",
      "parameters": []
    }
  ]
}
```

### Cargar Archivo

```python
manager = SQLQueryManager(use_rag=True)
manager.load_sql_queries_from_file("sql_queries.json")
```

## API REST

### Buscar Consultas SQL

```http
POST /api/v1/sql-queries/search
Authorization: Bearer <token>
Content-Type: application/json

{
  "query": "obtener usuarios activos",
  "database": "main_db",
  "category": "select",
  "top_k": 5
}
```

**Respuesta:**
```json
{
  "query": "obtener usuarios activos",
  "results": [
    {
      "id": "get-active-users",
      "sql": "SELECT * FROM users WHERE status = 'active'",
      "description": "Obtiene usuarios activos",
      "database": "main_db",
      "category": "select",
      "parameters": ["status"],
      "score": 0.95
    }
  ],
  "count": 1
}
```

### Listar Consultas SQL

```http
GET /api/v1/sql-queries?database=main_db&category=select
Authorization: Bearer <token>
```

**Respuesta:**
```json
{
  "sqlQueries": [
    {
      "id": "get-active-users",
      "description": "Obtiene usuarios activos",
      "database": "main_db",
      "category": "select",
      "parameters": ["status"]
    }
  ],
  "count": 1
}
```

### Obtener Consulta Específica

```http
GET /api/v1/sql-queries/get-active-users
Authorization: Bearer <token>
```

**Respuesta:**
```json
{
  "id": "get-active-users",
  "sql": "SELECT * FROM users WHERE status = 'active'",
  "description": "Obtiene usuarios activos",
  "database": "main_db",
  "category": "select",
  "parameters": ["status"],
  "metadata": {}
}
```

## Configuración del Servidor

### En `a2e_config.json`

```json
{
  "sqlQueries": {
    "file": "sql_queries.json"
  }
}
```

El servidor cargará automáticamente las consultas SQL desde el archivo especificado al iniciar.

## Búsqueda Semántica

La búsqueda semántica permite encontrar consultas SQL usando lenguaje natural:

### Ejemplos de Búsquedas

| Búsqueda | Consultas Encontradas |
|----------|----------------------|
| "obtener usuarios activos" | `get-active-users` |
| "contar órdenes por estado" | `count-orders-by-status` |
| "productos más vendidos" | `get-top-products` |
| "actualizar estado de usuario" | `update-user-status` |

### Cómo Funciona

1. **Indexación**: Cada consulta SQL se indexa con:
   - Descripción
   - Palabras clave extraídas de la consulta SQL
   - Categoría y base de datos
   - Parámetros

2. **Embeddings**: Se genera un embedding vectorial usando `sentence-transformers`

3. **Búsqueda**: La query del agente se convierte en embedding y se busca por similitud

4. **Ranking**: Los resultados se ordenan por score de similitud

## Mejores Prácticas

### 1. Descripciones Claras

✅ **Bueno:**
```python
description="Obtiene todos los usuarios activos ordenados por nombre"
```

❌ **Malo:**
```python
description="get users"
```

### 2. Categorías Consistentes

Usa categorías estándar: `select`, `insert`, `update`, `delete`, `analytics`

### 3. Parámetros Documentados

Lista todos los parámetros que la consulta acepta:

```python
parameters=["user_id", "status", "limit"]
```

### 4. Metadatos Útiles

Incluye metadatos relevantes:

```python
metadata={
    "author": "admin",
    "created_at": "2025-01-01",
    "version": "1.0",
    "tags": ["users", "active"]
}
```

## Ejemplos Completos

Ver `examples/sql_queries_example.py` para ejemplos completos de uso.

## Integración con Agentes

Los agentes pueden usar las consultas SQL encontradas en sus workflows:

```python
# 1. Buscar consulta SQL relevante
results = client.search_sql_queries("obtener usuarios activos")
query = results[0]

# 2. Usar la consulta SQL en un workflow
# (La consulta SQL se ejecutaría en una operación ExecuteSQL)
```

## Limitaciones

- Las consultas SQL se almacenan como texto, no se validan sintácticamente
- La búsqueda semántica puede no ser perfecta para consultas muy específicas
- Los parámetros se documentan pero no se validan automáticamente

## Próximas Mejoras

- [ ] Validación sintáctica de consultas SQL
- [ ] Ejecución directa de consultas SQL desde workflows
- [ ] Caché de resultados de consultas
- [ ] Versionado de consultas SQL
- [ ] Permisos por consulta SQL

