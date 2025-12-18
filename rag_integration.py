"""
Integración de RAG con LokiJS y embeddings locales para A2E
Proporciona búsqueda semántica para operaciones, APIs, endpoints y knowledge bases
"""

import json
import logging
import sys
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

# Agregar path de rag_catalog al sys.path
_current_file = Path(__file__).resolve()
_current_dir = _current_file.parent
# workflow_executor -> adk -> rag_catalog
rag_catalog_path = _current_dir.parent / "rag_catalog"
rag_catalog_path = rag_catalog_path.resolve()

if str(rag_catalog_path) not in sys.path and rag_catalog_path.exists():
    sys.path.insert(0, str(rag_catalog_path))

# Intentar múltiples formas de importación
LokiDatabase = None
VectorIndex = None

# Método 1: Importación directa desde el path agregado
try:
    from loki_db import LokiDatabase
    from vector_index import VectorIndex
except ImportError:
    pass

# Método 2: Importación relativa
if LokiDatabase is None:
    try:
        import importlib.util
        loki_db_path = rag_catalog_path / "loki_db.py"
        vector_index_path = rag_catalog_path / "vector_index.py"
        
        if loki_db_path.exists():
            spec = importlib.util.spec_from_file_location("loki_db", loki_db_path)
            loki_db_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(loki_db_module)
            LokiDatabase = loki_db_module.LokiDatabase
        
        if vector_index_path.exists():
            spec = importlib.util.spec_from_file_location("vector_index", vector_index_path)
            vector_index_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(vector_index_module)
            VectorIndex = vector_index_module.VectorIndex
    except Exception:
        pass

# Método 3: Intentar como paquete instalado
if LokiDatabase is None or VectorIndex is None:
    try:
        from rag_catalog.loki_db import LokiDatabase
        from rag_catalog.vector_index import VectorIndex
    except ImportError:
        pass

# Configurar logger primero
logger = logging.getLogger(__name__)

# Verificar que ambas clases están disponibles
if LokiDatabase is None or VectorIndex is None:
    # No lanzar error inmediatamente, permitir uso sin RAG
    logger.warning(
        f"Could not import rag_catalog components. "
        f"Tried path: {rag_catalog_path} "
        f"Path exists: {rag_catalog_path.exists()}. "
        f"RAG features will be disabled. "
        f"To enable: install a2ui-rag-catalog or add rag_catalog to PYTHONPATH."
    )
    # Las clases se definirán como None, y el código verificará antes de usar


class A2ERAGSystem:
    """
    Sistema RAG unificado para A2E
    Usa LokiJS para almacenamiento y embeddings locales para búsqueda semántica
    """
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        use_hnsw: bool = True,
        max_elements: int = 50000,
        ef_construction: int = 200,
        M: int = 16,
        ef_search: int = 50
    ):
        """
        Inicializa el sistema RAG
        
        Args:
            db_path: Ruta para persistir la base de datos (opcional)
            embedding_model: Modelo de embeddings a usar
            use_hnsw: Si usar HNSW para búsqueda vectorial (más eficiente)
            max_elements: Número máximo de elementos para HNSW
            ef_construction: Parámetro de construcción HNSW
            M: Número de conexiones bidireccionales HNSW
            ef_search: Parámetro de búsqueda HNSW
        
        Raises:
            ImportError: Si rag_catalog no está disponible
        """
        if LokiDatabase is None or VectorIndex is None:
            raise ImportError(
                "RAG components not available. "
                "Install a2ui-rag-catalog or add rag_catalog to PYTHONPATH."
            )
        
        # Base de datos LokiJS
        self.db = LokiDatabase("a2e_rag_db")
        
        # Índice vectorial con embeddings locales (HNSW si está disponible)
        self.vector_index = VectorIndex(
            model_name=embedding_model,
            use_hnsw=use_hnsw,
            max_elements=max_elements,
            ef_construction=ef_construction,
            M=M,
            ef_search=ef_search
        )
        
        # Colecciones
        self.operations_collection = self.db.add_collection(
            "operations",
            unique_index="id"
        )
        self.apis_collection = self.db.add_collection(
            "apis",
            unique_index="id"
        )
        self.endpoints_collection = self.db.add_collection(
            "endpoints",
            unique_index=None
        )
        self.knowledge_collection = self.db.add_collection(
            "knowledge",
            unique_index="id"
        )
        self.sql_queries_collection = self.db.add_collection(
            "sql_queries",
            unique_index="id"
        )
        
        # Índices adicionales
        self.operations_collection.ensure_index("category")
        self.apis_collection.ensure_index("baseUrl")
        self.endpoints_collection.ensure_index("apiId")
        self.endpoints_collection.ensure_index("method")
        self.knowledge_collection.ensure_index("type")
        self.sql_queries_collection.ensure_index("database")
        self.sql_queries_collection.ensure_index("category")
        
        logger.info(f"A2E RAG System initialized with model: {embedding_model}")
    
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
        
        for op_name, op_schema in operations.items():
            # Crear documento para la operación
            description = op_schema.get("description", "")
            properties = op_schema.get("properties", {})
            
            # Texto para embedding
            text = f"{op_name}: {description}"
            if properties:
                prop_names = ", ".join(properties.keys())
                text += f" Properties: {prop_names}"
            
            # Generar embedding
            embedding = self.vector_index.model.encode(text)
            vector_id = self.vector_index.add(text, {
                "type": "operation",
                "name": op_name,
                "description": description,
                "schema": op_schema
            }, embedding)
            
            # Guardar en LokiJS
            self.operations_collection.insert({
                "id": op_name,
                "name": op_name,
                "description": description,
                "schema": op_schema,
                "vector_id": vector_id,
                "category": self._categorize_operation(op_name)
            })
        
        logger.info(f"Indexed {len(operations)} operations")
    
    def index_api(self, api_id: str, api_info: Dict[str, Any]):
        """
        Indexa una API en RAG
        
        Args:
            api_id: ID de la API
            api_info: Información de la API
        """
        base_url = api_info.get("baseUrl", "")
        description = f"API {api_id} at {base_url}"
        
        # Generar embedding para la API
        text = f"{api_id} API: {description}"
        embedding = self.vector_index.model.encode(text)
        vector_id = self.vector_index.add(text, {
            "type": "api",
            "id": api_id,
            "info": api_info
        }, embedding)
        
        # Guardar en LokiJS
        self.apis_collection.insert({
            "id": api_id,
            "baseUrl": base_url,
            "info": api_info,
            "vector_id": vector_id
        })
        
        logger.info(f"Indexed API: {api_id}")
    
    def index_endpoint(
        self,
        api_id: str,
        endpoint: Dict[str, Any],
        base_url: str
    ):
        """
        Indexa un endpoint en RAG
        
        Args:
            api_id: ID de la API
            endpoint: Información del endpoint
            base_url: URL base de la API
        """
        path = endpoint.get("path", "")
        method = endpoint.get("method", "GET")
        description = endpoint.get("description", "")
        
        # Texto para embedding
        text = f"{method} {path}: {description}"
        if endpoint.get("parameters"):
            params = ", ".join([p.get("name", "") for p in endpoint.get("parameters", [])])
            text += f" Parameters: {params}"
        
        # Generar embedding
        embedding = self.vector_index.model.encode(text)
        vector_id = self.vector_index.add(text, {
            "type": "endpoint",
            "apiId": api_id,
            "endpoint": endpoint,
            "baseUrl": base_url
        }, embedding)
        
        # Guardar en LokiJS
        self.endpoints_collection.insert({
            "apiId": api_id,
            "path": path,
            "method": method,
            "description": description,
            "endpoint": endpoint,
            "baseUrl": base_url,
            "vector_id": vector_id
        })
        
        logger.debug(f"Indexed endpoint: {method} {path}")
    
    def index_knowledge(
        self,
        knowledge_id: str,
        knowledge_type: str,
        content: Dict[str, Any],
        description: str = ""
    ):
        """
        Indexa conocimiento general en RAG
        
        Args:
            knowledge_id: ID único del conocimiento
            knowledge_type: Tipo de conocimiento (ej: "documentation", "example")
            content: Contenido del conocimiento
            description: Descripción del conocimiento
        """
        text = f"{knowledge_type}: {description}"
        if isinstance(content, dict):
            # Agregar campos relevantes al texto
            for key, value in content.items():
                if isinstance(value, str) and len(value) < 200:
                    text += f" {key}: {value}"
        
        # Generar embedding
        embedding = self.vector_index.model.encode(text)
        vector_id = self.vector_index.add(text, {
            "type": "knowledge",
            "id": knowledge_id,
            "knowledgeType": knowledge_type,
            "content": content
        }, embedding)
        
        # Guardar en LokiJS
        self.knowledge_collection.insert({
            "id": knowledge_id,
            "type": knowledge_type,
            "description": description,
            "content": content,
            "vector_id": vector_id
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
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Indexa una consulta SQL en RAG
        
        Args:
            query_id: ID único de la consulta
            sql_query: La consulta SQL completa
            description: Descripción de qué hace la consulta
            database: Nombre de la base de datos (opcional)
            category: Categoría de la consulta (ej: "select", "insert", "update", "analytics")
            parameters: Lista de parámetros que acepta la consulta (opcional)
            metadata: Metadatos adicionales (opcional)
        """
        # Texto para embedding: descripción + query + parámetros
        text = f"SQL Query: {description}"
        if database:
            text += f" Database: {database}"
        if category:
            text += f" Category: {category}"
        if parameters:
            text += f" Parameters: {', '.join(parameters)}"
        # Incluir partes clave de la query (sin incluir toda la query para evitar ruido)
        # Extraer palabras clave de la query
        query_keywords = self._extract_sql_keywords(sql_query)
        if query_keywords:
            text += f" Keywords: {', '.join(query_keywords)}"
        
        # Generar embedding
        embedding = self.vector_index.model.encode(text)
        vector_id = self.vector_index.add(text, {
            "type": "sql_query",
            "id": query_id,
            "database": database,
            "category": category,
            "description": description
        }, embedding)
        
        # Guardar en LokiJS
        query_doc = {
            "id": query_id,
            "sql": sql_query,
            "description": description,
            "database": database or "default",
            "category": category or "general",
            "parameters": parameters or [],
            "vector_id": vector_id
        }
        
        if metadata:
            query_doc["metadata"] = metadata
        
        self.sql_queries_collection.insert(query_doc)
        
        logger.info(f"Indexed SQL query: {query_id}")
    
    def _extract_sql_keywords(self, sql_query: str) -> List[str]:
        """Extrae palabras clave de una consulta SQL"""
        keywords = []
        sql_lower = sql_query.lower()
        
        # Palabras clave SQL comunes
        sql_keywords = [
            "select", "from", "where", "join", "inner", "left", "right", "outer",
            "group by", "order by", "having", "limit", "offset",
            "insert", "update", "delete", "create", "alter", "drop",
            "count", "sum", "avg", "max", "min", "distinct",
            "union", "intersect", "except"
        ]
        
        for keyword in sql_keywords:
            if keyword in sql_lower:
                keywords.append(keyword)
        
        # Extraer nombres de tablas (después de FROM, JOIN, etc.)
        import re
        table_patterns = [
            r'from\s+(\w+)',
            r'join\s+(\w+)',
            r'into\s+(\w+)',
            r'update\s+(\w+)'
        ]
        
        for pattern in table_patterns:
            matches = re.findall(pattern, sql_lower)
            keywords.extend(matches)
        
        return list(set(keywords))  # Eliminar duplicados
    
    def search_operations(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca operaciones relevantes usando búsqueda semántica
        
        Args:
            query: Query de búsqueda
            top_k: Número de resultados a retornar
        
        Returns:
            Lista de operaciones relevantes
        """
        # Búsqueda semántica en el índice vectorial
        results = self.vector_index.search(query, top_k=top_k * 2)  # Buscar más para filtrar
        
        operations = []
        seen = set()
        
        for result in results:
            metadata = result["metadata"]
            if metadata.get("type") == "operation":
                op_name = metadata.get("name")
                if op_name and op_name not in seen:
                    # Obtener de LokiJS
                    op_doc = self.operations_collection.find_one({"id": op_name})
                    if op_doc:
                        operations.append({
                            "name": op_name,
                            "description": op_doc.get("description", ""),
                            "schema": op_doc.get("schema", {}),
                            "score": result["score"]
                        })
                        seen.add(op_name)
                        if len(operations) >= top_k:
                            break
        
        return operations
    
    def search_apis(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca APIs relevantes usando búsqueda semántica
        
        Args:
            query: Query de búsqueda
            top_k: Número de resultados a retornar
        
        Returns:
            Lista de APIs relevantes
        """
        results = self.vector_index.search(query, top_k=top_k * 2)
        
        apis = []
        seen = set()
        
        for result in results:
            metadata = result["metadata"]
            if metadata.get("type") == "api":
                api_id = metadata.get("id")
                if api_id and api_id not in seen:
                    api_doc = self.apis_collection.find_one({"id": api_id})
                    if api_doc:
                        apis.append({
                            "id": api_id,
                            "baseUrl": api_doc.get("baseUrl", ""),
                            "info": api_doc.get("info", {}),
                            "score": result["score"]
                        })
                        seen.add(api_id)
                        if len(apis) >= top_k:
                            break
        
        return apis
    
    def search_endpoints(
        self,
        query: str,
        api_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca endpoints relevantes usando búsqueda semántica
        
        Args:
            query: Query de búsqueda
            api_id: Filtrar por API (opcional)
            top_k: Número de resultados a retornar
        
        Returns:
            Lista de endpoints relevantes
        """
        results = self.vector_index.search(query, top_k=top_k * 3)
        
        endpoints = []
        seen = set()
        
        for result in results:
            metadata = result["metadata"]
            if metadata.get("type") == "endpoint":
                endpoint_info = metadata.get("endpoint", {})
                path = endpoint_info.get("path", "")
                method = endpoint_info.get("method", "")
                key = f"{metadata.get('apiId')}:{method}:{path}"
                
                if key not in seen:
                    # Filtrar por API si se especifica
                    if api_id and metadata.get("apiId") != api_id:
                        continue
                    
                    endpoints.append({
                        "apiId": metadata.get("apiId"),
                        "baseUrl": metadata.get("baseUrl", ""),
                        "path": path,
                        "method": method,
                        "description": endpoint_info.get("description", ""),
                        "endpoint": endpoint_info,
                        "score": result["score"]
                    })
                    seen.add(key)
                    if len(endpoints) >= top_k:
                        break
        
        return endpoints
    
    def search_knowledge(
        self,
        query: str,
        knowledge_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca conocimiento relevante usando búsqueda semántica
        
        Args:
            query: Query de búsqueda
            knowledge_type: Filtrar por tipo (opcional)
            top_k: Número de resultados a retornar
        
        Returns:
            Lista de conocimiento relevante
        """
        results = self.vector_index.search(query, top_k=top_k * 2)
        
        knowledge = []
        seen = set()
        
        for result in results:
            # result es una tupla (metadata, score)
            if isinstance(result, tuple):
                metadata, score = result
            else:
                # Compatibilidad con formato dict (HNSW)
                metadata = result.get("metadata", result)
                score = result.get("score", 0.0)
            
            if metadata.get("type") == "knowledge":
                knowledge_id = metadata.get("id")
                
                if knowledge_id and knowledge_id not in seen:
                    # Filtrar por tipo si se especifica
                    if knowledge_type and metadata.get("knowledgeType") != knowledge_type:
                        continue
                    
                    knowledge_doc = self.knowledge_collection.find_one({"id": knowledge_id})
                    if knowledge_doc:
                        knowledge.append({
                            "id": knowledge_id,
                            "type": knowledge_doc.get("type", ""),
                            "description": knowledge_doc.get("description", ""),
                            "content": knowledge_doc.get("content", {}),
                            "score": float(score)
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
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca consultas SQL relevantes usando búsqueda semántica
        
        Args:
            query: Query de búsqueda (ej: "obtener usuarios activos")
            database: Filtrar por base de datos (opcional)
            category: Filtrar por categoría (opcional)
            top_k: Número de resultados a retornar
        
        Returns:
            Lista de consultas SQL relevantes
        """
        results = self.vector_index.search(query, top_k=top_k * 2)
        
        sql_queries = []
        seen = set()
        
        for result in results:
            # result es una tupla (metadata, score)
            if isinstance(result, tuple):
                metadata, score = result
            else:
                # Compatibilidad con formato dict (HNSW)
                metadata = result.get("metadata", result)
                score = result.get("score", 0.0)
            
            if metadata.get("type") == "sql_query":
                query_id = metadata.get("id")
                
                if query_id and query_id not in seen:
                    # Filtrar por base de datos si se especifica
                    if database and metadata.get("database") != database:
                        continue
                    
                    # Filtrar por categoría si se especifica
                    if category and metadata.get("category") != category:
                        continue
                    
                    query_doc = self.sql_queries_collection.find_one({"id": query_id})
                    if query_doc:
                        sql_queries.append({
                            "id": query_id,
                            "sql": query_doc.get("sql", ""),
                            "description": query_doc.get("description", ""),
                            "database": query_doc.get("database", ""),
                            "category": query_doc.get("category", ""),
                            "parameters": query_doc.get("parameters", []),
                            "metadata": query_doc.get("metadata", {}),
                            "score": float(score)
                        })
                        seen.add(query_id)
                        if len(sql_queries) >= top_k:
                            break
        
        return sql_queries
    
    def build_partial_schema(
        self,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Construye un schema parcial solo con las operaciones relevantes
        
        Args:
            operations: Lista de operaciones relevantes
        
        Returns:
            Schema parcial con solo las operaciones relevantes
        """
        schema = {
            "type": "object",
            "properties": {
                "operations": {
                    "type": "object",
                    "properties": {}
                }
            }
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
    
    def save(self, path: str):
        """Persiste la base de datos"""
        self.db.save(path)
        logger.info(f"Database saved to {path}")
    
    def load(self, path: str):
        """Carga la base de datos"""
        self.db.load(path)
        logger.info(f"Database loaded from {path}")

