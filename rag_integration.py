"""
Integración de RAG con minimemory para A2E
Proporciona búsqueda semántica para operaciones, APIs, endpoints y knowledge bases
Reemplaza la dependencia de rag_catalog (LokiDatabase + VectorIndex) con minimemory SDK
"""

import asyncio
import json
import logging
import os
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Default embedding model — multilingual-e5-small supports 100 languages
# and requires query:/passage: prefixes for optimal performance
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

# Intentar importar minimemory
MiniMemoryClient = None
SearchMode = None
MemoryType = None

try:
    from minimemory import MiniMemoryClient, SearchMode, MemoryType
except ImportError:
    pass

if MiniMemoryClient is None:
    logger.warning(
        "Could not import minimemory SDK. "
        "RAG features will be disabled. "
        "To enable: pip install minimemory"
    )


def _run_async(coro):
    """Bridge async→sync: run a coroutine from synchronous code."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Already inside an async context — create a new thread to avoid deadlock
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class A2ERAGSystem:
    """
    Sistema RAG unificado para A2E
    Usa minimemory como backend para almacenamiento vectorial y búsqueda semántica
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        use_hnsw: bool = True,
        max_elements: int = 50000,
        ef_construction: int = 200,
        M: int = 16,
        ef_search: int = 50,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        namespace: Optional[str] = None,
    ):
        """
        Inicializa el sistema RAG

        Args:
            db_path: (legacy, ignorado) Ruta para persistir la base de datos
            embedding_model: (legacy, ignorado) Modelo de embeddings — minimemory genera los suyos
            use_hnsw: (legacy, ignorado) HNSW está integrado en minimemory
            max_elements: (legacy, ignorado)
            ef_construction: (legacy, ignorado)
            M: (legacy, ignorado)
            ef_search: (legacy, ignorado)
            base_url: URL del servicio minimemory (o env MINIMEMORY_URL)
            api_key: API key (o env MINIMEMORY_API_KEY)
            namespace: Namespace (o env MINIMEMORY_NAMESPACE, default "a2e")

        Raises:
            ImportError: Si minimemory no está disponible
        """
        if MiniMemoryClient is None:
            raise ImportError(
                "RAG components not available. "
                "Install minimemory: pip install minimemory"
            )

        self._base_url = base_url or os.environ.get("MINIMEMORY_URL", "")
        self._api_key = api_key or os.environ.get("MINIMEMORY_API_KEY", "")
        self._namespace = namespace or os.environ.get("MINIMEMORY_NAMESPACE", "a2e")

        if not self._base_url or not self._api_key:
            raise ImportError(
                "RAG components not configured. "
                "Set MINIMEMORY_URL and MINIMEMORY_API_KEY environment variables, "
                "or pass base_url and api_key to A2ERAGSystem()."
            )

        self._client = MiniMemoryClient(
            base_url=self._base_url,
            api_key=self._api_key,
            namespace=self._namespace,
        )

        # In-memory index for fast filtering by collection type
        # Maps collection_type → [{ id, metadata, content }]
        self._local_index: Dict[str, List[Dict[str, Any]]] = {
            "operations": [],
            "apis": [],
            "endpoints": [],
            "knowledge": [],
            "sql_queries": [],
        }

        logger.info(
            f"A2E RAG System initialized with minimemory "
            f"(url={self._base_url}, namespace={self._namespace}, "
            f"model={DEFAULT_EMBEDDING_MODEL})"
        )

    async def _remember(self, content: str, metadata: Dict[str, Any]) -> str:
        """Store a memory and return its ID.

        Prepends 'passage: ' prefix required by multilingual-e5-small
        for optimal embedding quality on indexed content.
        """
        memory, _, _ = await self._client.remember(
            f"passage: {content}",
            type=MemoryType.KNOWLEDGE,
            importance=0.7,
            metadata=metadata,
            generate_embedding=True,
        )
        return memory.id

    async def _recall(
        self,
        query: str,
        top_k: int = 10,
        mode: str = "hybrid",
    ) -> List[Dict[str, Any]]:
        """Search memories and return results as dicts.

        Prepends 'query: ' prefix required by multilingual-e5-small
        for optimal embedding quality on search queries.
        """
        search_mode = {
            "hybrid": SearchMode.HYBRID,
            "vector": SearchMode.VECTOR,
            "keyword": SearchMode.KEYWORD,
        }.get(mode, SearchMode.HYBRID)

        results, _ = await self._client.recall(
            f"query: {query}",
            limit=top_k,
            mode=search_mode,
            type=MemoryType.KNOWLEDGE,
        )
        return [
            {
                "id": r.id,
                "content": r.content,
                "score": r.score,
                "metadata": r.metadata or {},
            }
            for r in results
        ]

    # ============ Indexing Methods ============

    def index_operations_catalog(self, catalog_path: str):
        """
        Indexa el catálogo de operaciones en RAG

        Args:
            catalog_path: Ruta al archivo workflow_catalog.json
        """
        logger.info(f"Indexing operations catalog: {catalog_path}")

        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        operations = catalog.get("operations", {})

        async def _index_all():
            for op_name, op_schema in operations.items():
                description = op_schema.get("description", "")
                properties = op_schema.get("properties", {})

                # Build search text
                text = f"{op_name}: {description}"
                if properties:
                    prop_names = ", ".join(properties.keys())
                    text += f" Properties: {prop_names}"

                metadata = {
                    "_collection": "operations",
                    "type": "operation",
                    "name": op_name,
                    "description": description,
                    "schema": op_schema,
                    "category": self._categorize_operation(op_name),
                }

                mem_id = await self._remember(text, metadata)

                self._local_index["operations"].append({
                    "id": mem_id,
                    "name": op_name,
                    "description": description,
                    "schema": op_schema,
                    "category": metadata["category"],
                })

        _run_async(_index_all())
        logger.info(f"Indexed {len(operations)} operations")

    def index_api(self, api_id: str, api_info: Dict[str, Any]):
        """Indexa una API en RAG"""
        base_url = api_info.get("baseUrl", "")
        text = f"{api_id} API at {base_url}"

        metadata = {
            "_collection": "apis",
            "type": "api",
            "id": api_id,
            "baseUrl": base_url,
            "info": api_info,
        }

        mem_id = _run_async(self._remember(text, metadata))

        self._local_index["apis"].append({
            "id": mem_id,
            "api_id": api_id,
            "baseUrl": base_url,
            "info": api_info,
        })

        logger.info(f"Indexed API: {api_id}")

    def index_endpoint(
        self,
        api_id: str,
        endpoint: Dict[str, Any],
        base_url: str,
    ):
        """Indexa un endpoint en RAG"""
        path = endpoint.get("path", "")
        method = endpoint.get("method", "GET")
        description = endpoint.get("description", "")

        text = f"{method} {path}: {description}"
        if endpoint.get("parameters"):
            params = ", ".join(
                [p.get("name", "") for p in endpoint.get("parameters", [])]
            )
            text += f" Parameters: {params}"

        metadata = {
            "_collection": "endpoints",
            "type": "endpoint",
            "apiId": api_id,
            "path": path,
            "method": method,
            "description": description,
            "endpoint": endpoint,
            "baseUrl": base_url,
        }

        mem_id = _run_async(self._remember(text, metadata))

        self._local_index["endpoints"].append({
            "id": mem_id,
            "apiId": api_id,
            "path": path,
            "method": method,
            "description": description,
            "endpoint": endpoint,
            "baseUrl": base_url,
        })

        logger.debug(f"Indexed endpoint: {method} {path}")

    def index_knowledge(
        self,
        knowledge_id: str,
        knowledge_type: str,
        content: Dict[str, Any],
        description: str = "",
    ):
        """Indexa conocimiento general en RAG"""
        text = f"{knowledge_type}: {description}"
        if isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, str) and len(value) < 200:
                    text += f" {key}: {value}"

        metadata = {
            "_collection": "knowledge",
            "type": "knowledge",
            "id": knowledge_id,
            "knowledgeType": knowledge_type,
            "description": description,
            "content": content,
        }

        mem_id = _run_async(self._remember(text, metadata))

        self._local_index["knowledge"].append({
            "id": mem_id,
            "knowledge_id": knowledge_id,
            "type": knowledge_type,
            "description": description,
            "content": content,
        })

        logger.info(f"Indexed knowledge: {knowledge_id}")

    def index_sql_query(
        self,
        query_id: str,
        sql_query: str,
        description: str,
        database: Optional[str] = None,
        category: Optional[str] = None,
        parameters: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Indexa una consulta SQL en RAG"""
        text = f"SQL Query: {description}"
        if database:
            text += f" Database: {database}"
        if category:
            text += f" Category: {category}"
        if parameters:
            text += f" Parameters: {', '.join(parameters)}"

        query_keywords = self._extract_sql_keywords(sql_query)
        if query_keywords:
            text += f" Keywords: {', '.join(query_keywords)}"

        mem_metadata = {
            "_collection": "sql_queries",
            "type": "sql_query",
            "id": query_id,
            "database": database or "default",
            "category": category or "general",
            "description": description,
        }

        mem_id = _run_async(self._remember(text, mem_metadata))

        doc = {
            "id": mem_id,
            "query_id": query_id,
            "sql": sql_query,
            "description": description,
            "database": database or "default",
            "category": category or "general",
            "parameters": parameters or [],
        }
        if metadata:
            doc["metadata"] = metadata

        self._local_index["sql_queries"].append(doc)

        logger.info(f"Indexed SQL query: {query_id}")

    # ============ Search Methods ============

    def search_operations(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Busca operaciones relevantes usando búsqueda semántica"""
        results = _run_async(self._recall(query, top_k=top_k * 2))

        operations = []
        seen = set()

        for result in results:
            meta = result["metadata"]
            if meta.get("_collection") == "operations" or meta.get("type") == "operation":
                op_name = meta.get("name")
                if op_name and op_name not in seen:
                    operations.append({
                        "name": op_name,
                        "description": meta.get("description", ""),
                        "schema": meta.get("schema", {}),
                        "score": result["score"],
                    })
                    seen.add(op_name)
                    if len(operations) >= top_k:
                        break

        # Fallback: also check local index if remote returned few results
        if len(operations) < top_k:
            query_lower = query.lower()
            for doc in self._local_index["operations"]:
                name = doc.get("name", "")
                if name not in seen and query_lower in (
                    name.lower() + " " + doc.get("description", "").lower()
                ):
                    operations.append({
                        "name": name,
                        "description": doc.get("description", ""),
                        "schema": doc.get("schema", {}),
                        "score": 0.5,
                    })
                    seen.add(name)
                    if len(operations) >= top_k:
                        break

        return operations

    def search_apis(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Busca APIs relevantes usando búsqueda semántica"""
        results = _run_async(self._recall(query, top_k=top_k * 2))

        apis = []
        seen = set()

        for result in results:
            meta = result["metadata"]
            if meta.get("_collection") == "apis" or meta.get("type") == "api":
                api_id = meta.get("id")
                if api_id and api_id not in seen:
                    apis.append({
                        "id": api_id,
                        "baseUrl": meta.get("baseUrl", ""),
                        "info": meta.get("info", {}),
                        "score": result["score"],
                    })
                    seen.add(api_id)
                    if len(apis) >= top_k:
                        break

        return apis

    def search_endpoints(
        self,
        query: str,
        api_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Busca endpoints relevantes usando búsqueda semántica"""
        results = _run_async(self._recall(query, top_k=top_k * 3))

        endpoints = []
        seen = set()

        for result in results:
            meta = result["metadata"]
            if meta.get("_collection") == "endpoints" or meta.get("type") == "endpoint":
                path = meta.get("path", "")
                method = meta.get("method", "")
                key = f"{meta.get('apiId')}:{method}:{path}"

                if key not in seen:
                    if api_id and meta.get("apiId") != api_id:
                        continue

                    endpoints.append({
                        "apiId": meta.get("apiId"),
                        "baseUrl": meta.get("baseUrl", ""),
                        "path": path,
                        "method": method,
                        "description": meta.get("description", ""),
                        "endpoint": meta.get("endpoint", {}),
                        "score": result["score"],
                    })
                    seen.add(key)
                    if len(endpoints) >= top_k:
                        break

        return endpoints

    def search_knowledge(
        self,
        query: str,
        knowledge_type: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Busca conocimiento relevante usando búsqueda semántica"""
        results = _run_async(self._recall(query, top_k=top_k * 2))

        knowledge = []
        seen = set()

        for result in results:
            meta = result["metadata"]
            if meta.get("_collection") == "knowledge" or meta.get("type") == "knowledge":
                knowledge_id = meta.get("id")

                if knowledge_id and knowledge_id not in seen:
                    if knowledge_type and meta.get("knowledgeType") != knowledge_type:
                        continue

                    knowledge.append({
                        "id": knowledge_id,
                        "type": meta.get("knowledgeType", ""),
                        "description": meta.get("description", ""),
                        "content": meta.get("content", {}),
                        "score": result["score"],
                    })
                    seen.add(knowledge_id)
                    if len(knowledge) >= top_k:
                        break

        return knowledge

    def search_sql_queries(
        self,
        query: str,
        database: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Busca consultas SQL relevantes usando búsqueda semántica"""
        results = _run_async(self._recall(query, top_k=top_k * 2))

        sql_queries = []
        seen = set()

        for result in results:
            meta = result["metadata"]
            if meta.get("_collection") == "sql_queries" or meta.get("type") == "sql_query":
                query_id = meta.get("id")

                if query_id and query_id not in seen:
                    if database and meta.get("database") != database:
                        continue
                    if category and meta.get("category") != category:
                        continue

                    # Find full doc in local index
                    local_doc = next(
                        (d for d in self._local_index["sql_queries"]
                         if d.get("query_id") == query_id),
                        {},
                    )

                    sql_queries.append({
                        "id": query_id,
                        "sql": local_doc.get("sql", ""),
                        "description": meta.get("description", ""),
                        "database": meta.get("database", ""),
                        "category": meta.get("category", ""),
                        "parameters": local_doc.get("parameters", []),
                        "metadata": local_doc.get("metadata", {}),
                        "score": result["score"],
                    })
                    seen.add(query_id)
                    if len(sql_queries) >= top_k:
                        break

        return sql_queries

    # ============ Utility Methods ============

    def build_partial_schema(
        self,
        operations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Construye un schema parcial solo con las operaciones relevantes"""
        schema = {
            "type": "object",
            "properties": {
                "operations": {
                    "type": "object",
                    "properties": {},
                }
            },
        }

        for op in operations:
            op_name = op.get("name")
            op_schema = op.get("schema", {})
            if op_name and op_schema:
                schema["properties"]["operations"]["properties"][op_name] = op_schema

        return schema

    def _categorize_operation(self, op_name: str) -> str:
        """Categoriza una operación"""
        if "Api" in op_name or "Call" in op_name:
            return "api"
        elif "Filter" in op_name or "Transform" in op_name:
            return "data"
        elif "Store" in op_name or "Save" in op_name:
            return "storage"
        elif "Wait" in op_name or "Delay" in op_name:
            return "control"
        elif "Conditional" in op_name or "If" in op_name:
            return "control"
        elif "Loop" in op_name:
            return "control"
        else:
            return "other"

    def _extract_sql_keywords(self, sql_query: str) -> List[str]:
        """Extrae palabras clave de una consulta SQL"""
        keywords = []
        sql_lower = sql_query.lower()

        sql_keywords = [
            "select", "from", "where", "join", "inner", "left", "right", "outer",
            "group by", "order by", "having", "limit", "offset",
            "insert", "update", "delete", "create", "alter", "drop",
            "count", "sum", "avg", "max", "min", "distinct",
            "union", "intersect", "except",
        ]

        for keyword in sql_keywords:
            if keyword in sql_lower:
                keywords.append(keyword)

        table_patterns = [
            r'from\s+(\w+)',
            r'join\s+(\w+)',
            r'into\s+(\w+)',
            r'update\s+(\w+)',
        ]

        for pattern in table_patterns:
            matches = re.findall(pattern, sql_lower)
            keywords.extend(matches)

        return list(set(keywords))

    def save(self, path: str):
        """Persiste datos (no-op: minimemory persiste automáticamente en el servidor)"""
        logger.info(f"Data persisted by minimemory server (save path ignored: {path})")

    def load(self, path: str):
        """Carga datos (no-op: minimemory carga automáticamente del servidor)"""
        logger.info(f"Data loaded from minimemory server (load path ignored: {path})")

    def close(self):
        """Cierra la conexión con minimemory"""
        _run_async(self._client.close())
