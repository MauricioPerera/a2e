"""
Gestor de Consultas SQL para A2E
Permite a los clientes registrar consultas SQL que los agentes pueden buscar y usar
Usa LokiJS para almacenamiento y embeddings locales para búsqueda semántica
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    from rag_integration import A2ERAGSystem
except ImportError:
    A2ERAGSystem = None

logger = logging.getLogger(__name__)


class SQLQueryManager:
    """
    Gestor de consultas SQL para A2E
    Almacena y busca consultas SQL usando LokiJS y embeddings locales
    """
    
    def __init__(
        self,
        rag_system: Optional[A2ERAGSystem] = None,
        use_rag: bool = True
    ):
        """
        Inicializa el gestor de consultas SQL
        
        Args:
            rag_system: Sistema RAG (se crea uno nuevo si es None y use_rag=True)
            use_rag: Si usar RAG para búsqueda semántica
        """
        self.use_rag = use_rag
        
        if use_rag:
            if A2ERAGSystem is None:
                logger.warning("RAG system not available. SQL queries will use keyword search only.")
                self.use_rag = False
                self.rag = None
            else:
                self.rag = rag_system or A2ERAGSystem()
        else:
            self.rag = None
        
        # Almacenamiento tradicional (fallback)
        self.sql_queries: Dict[str, Dict[str, Any]] = {}
    
    def add_sql_query(
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
        Agrega una consulta SQL al catálogo
        
        Args:
            query_id: ID único de la consulta
            sql_query: La consulta SQL completa
            description: Descripción de qué hace la consulta
            database: Nombre de la base de datos (opcional)
            category: Categoría de la consulta (ej: "select", "insert", "update", "analytics")
            parameters: Lista de parámetros que acepta la consulta (opcional)
            metadata: Metadatos adicionales (opcional)
        """
        query_data = {
            "id": query_id,
            "sql": sql_query,
            "description": description,
            "database": database or "default",
            "category": category or "general",
            "parameters": parameters or [],
            "metadata": metadata or {}
        }
        
        # Guardar en almacenamiento tradicional
        self.sql_queries[query_id] = query_data
        
        # Indexar en RAG si está habilitado
        if self.use_rag and self.rag:
            self.rag.index_sql_query(
                query_id=query_id,
                sql_query=sql_query,
                description=description,
                database=database,
                category=category,
                parameters=parameters,
                metadata=metadata
            )
        
        logger.info(f"Added SQL query: {query_id}")
    
    def load_sql_queries_from_file(self, file_path: str):
        """
        Carga consultas SQL desde un archivo JSON
        
        Args:
            file_path: Ruta al archivo JSON con consultas SQL
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = json.load(f)
        
        queries = content.get("queries", [])
        
        for query_data in queries:
            self.add_sql_query(
                query_id=query_data.get("id"),
                sql_query=query_data.get("sql"),
                description=query_data.get("description", ""),
                database=query_data.get("database"),
                category=query_data.get("category"),
                parameters=query_data.get("parameters", []),
                metadata=query_data.get("metadata", {})
            )
        
        logger.info(f"Loaded {len(queries)} SQL queries from {file_path}")
    
    def search_sql_queries(
        self,
        query: str,
        database: Optional[str] = None,
        category: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca consultas SQL relevantes usando búsqueda semántica o keywords
        
        Args:
            query: Query de búsqueda (ej: "obtener usuarios activos")
            database: Filtrar por base de datos (opcional)
            category: Filtrar por categoría (opcional)
            top_k: Número de resultados
        
        Returns:
            Lista de consultas SQL relevantes
        """
        # Usar RAG si está habilitado
        if self.use_rag and self.rag:
            results = self.rag.search_sql_queries(
                query=query,
                database=database,
                category=category,
                top_k=top_k
            )
            return results
        
        # Fallback a búsqueda por keywords
        results = []
        query_lower = query.lower()
        
        for query_id, query_data in self.sql_queries.items():
            # Filtrar por base de datos si se especifica
            if database and query_data.get("database") != database:
                continue
            
            # Filtrar por categoría si se especifica
            if category and query_data.get("category") != category:
                continue
            
            # Búsqueda simple por keywords
            description = query_data.get("description", "").lower()
            sql = query_data.get("sql", "").lower()
            
            score = 0
            for word in query_lower.split():
                if word in description:
                    score += 3
                if word in sql:
                    score += 1
            
            if score > 0:
                query_copy = query_data.copy()
                query_copy["_score"] = score
                results.append(query_copy)
        
        # Ordenar por score y retornar top_k
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results[:top_k]
    
    def get_sql_query(self, query_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una consulta SQL específica
        
        Args:
            query_id: ID de la consulta
        
        Returns:
            Consulta SQL o None si no existe
        """
        return self.sql_queries.get(query_id)
    
    def list_sql_queries(
        self,
        database: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista todas las consultas SQL (con filtros opcionales)
        
        Args:
            database: Filtrar por base de datos (opcional)
            category: Filtrar por categoría (opcional)
        
        Returns:
            Lista de consultas SQL con metadatos
        """
        results = []
        
        for query_id, query_data in self.sql_queries.items():
            # Filtrar por base de datos si se especifica
            if database and query_data.get("database") != database:
                continue
            
            # Filtrar por categoría si se especifica
            if category and query_data.get("category") != category:
                continue
            
            results.append({
                "id": query_data["id"],
                "description": query_data.get("description", ""),
                "database": query_data.get("database", ""),
                "category": query_data.get("category", ""),
                "parameters": query_data.get("parameters", [])
            })
        
        return results
    
    def update_sql_query(
        self,
        query_id: str,
        sql_query: Optional[str] = None,
        description: Optional[str] = None,
        database: Optional[str] = None,
        category: Optional[str] = None,
        parameters: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Actualiza una consulta SQL existente
        
        Args:
            query_id: ID de la consulta a actualizar
            sql_query: Nueva consulta SQL (opcional)
            description: Nueva descripción (opcional)
            database: Nueva base de datos (opcional)
            category: Nueva categoría (opcional)
            parameters: Nuevos parámetros (opcional)
            metadata: Nuevos metadatos (opcional)
        """
        if query_id not in self.sql_queries:
            raise ValueError(f"SQL query {query_id} not found")
        
        query_data = self.sql_queries[query_id]
        
        # Actualizar campos si se proporcionan
        if sql_query is not None:
            query_data["sql"] = sql_query
        if description is not None:
            query_data["description"] = description
        if database is not None:
            query_data["database"] = database
        if category is not None:
            query_data["category"] = category
        if parameters is not None:
            query_data["parameters"] = parameters
        if metadata is not None:
            query_data["metadata"] = {**query_data.get("metadata", {}), **metadata}
        
        # Re-indexar en RAG si está habilitado
        if self.use_rag and self.rag:
            self.rag.index_sql_query(
                query_id=query_id,
                sql_query=query_data["sql"],
                description=query_data["description"],
                database=query_data.get("database"),
                category=query_data.get("category"),
                parameters=query_data.get("parameters", []),
                metadata=query_data.get("metadata", {})
            )
        
        logger.info(f"Updated SQL query: {query_id}")
    
    def delete_sql_query(self, query_id: str):
        """
        Elimina una consulta SQL del catálogo
        
        Args:
            query_id: ID de la consulta a eliminar
        """
        if query_id not in self.sql_queries:
            raise ValueError(f"SQL query {query_id} not found")
        
        # Eliminar de almacenamiento tradicional
        del self.sql_queries[query_id]
        
        # Eliminar de RAG si está habilitado (requiere implementación en A2ERAGSystem)
        # Por ahora, solo eliminamos del almacenamiento tradicional
        # TODO: Implementar eliminación en RAG
        
        logger.info(f"Deleted SQL query: {query_id}")
    
    def export_sql_queries(
        self,
        output_path: str,
        database: Optional[str] = None,
        category: Optional[str] = None
    ):
        """
        Exporta consultas SQL a un archivo JSON
        
        Args:
            output_path: Ruta donde guardar el archivo
            database: Filtrar por base de datos (opcional)
            category: Filtrar por categoría (opcional)
        """
        queries = []
        
        for query_id, query_data in self.sql_queries.items():
            # Filtrar por base de datos si se especifica
            if database and query_data.get("database") != database:
                continue
            
            # Filtrar por categoría si se especifica
            if category and query_data.get("category") != category:
                continue
            
            queries.append({
                "id": query_data["id"],
                "sql": query_data["sql"],
                "description": query_data.get("description", ""),
                "database": query_data.get("database", ""),
                "category": query_data.get("category", ""),
                "parameters": query_data.get("parameters", []),
                "metadata": query_data.get("metadata", {})
            })
        
        export_data = {
            "queries": queries,
            "count": len(queries)
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(queries)} SQL queries to {output_path}")


def create_example_sql_query_manager():
    """
    Crea un gestor de consultas SQL de ejemplo
    """
    manager = SQLQueryManager(use_rag=True)
    
    # Agregar consultas de ejemplo
    manager.add_sql_query(
        query_id="get-active-users",
        sql_query="SELECT id, name, email, status FROM users WHERE status = 'active' ORDER BY name",
        description="Obtiene todos los usuarios activos ordenados por nombre",
        database="main_db",
        category="select",
        parameters=["status"]
    )
    
    manager.add_sql_query(
        query_id="get-user-by-id",
        sql_query="SELECT * FROM users WHERE id = ?",
        description="Obtiene un usuario específico por su ID",
        database="main_db",
        category="select",
        parameters=["id"]
    )
    
    manager.add_sql_query(
        query_id="count-orders-by-status",
        sql_query="""
        SELECT status, COUNT(*) as count 
        FROM orders 
        WHERE created_at >= ? 
        GROUP BY status
        """,
        description="Cuenta órdenes agrupadas por estado desde una fecha",
        database="main_db",
        category="analytics",
        parameters=["created_at"]
    )
    
    manager.add_sql_query(
        query_id="update-user-status",
        sql_query="UPDATE users SET status = ? WHERE id = ?",
        description="Actualiza el estado de un usuario",
        database="main_db",
        category="update",
        parameters=["status", "id"]
    )
    
    return manager


if __name__ == "__main__":
    # Ejemplo de uso
    manager = create_example_sql_query_manager()
    
    # Buscar consultas
    results = manager.search_sql_queries("obtener usuarios activos", top_k=3)
    print("SQL Queries encontradas:")
    for r in results:
        print(f"  - {r.get('id')}: {r.get('description')}")
        print(f"    SQL: {r.get('sql')[:60]}...")
        print(f"    Score: {r.get('score', r.get('_score', 0))}")
        print()

