"""
Base de conocimiento de APIs y operaciones permitidas
El cliente anuncia qué APIs y operaciones soporta, similar a cómo anuncia catálogos
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


class APIKnowledgeBase:
    """
    Base de conocimiento de APIs y operaciones permitidas
    Usa LokiJS para almacenamiento y embeddings locales para búsqueda semántica
    """
    
    def __init__(
        self,
        rag_system: Optional[A2ERAGSystem] = None,
        operations_catalog_path: Optional[str] = None,
        use_rag: bool = True
    ):
        """
        Inicializa la base de conocimiento
        
        Args:
            rag_system: Sistema RAG (se crea uno nuevo si es None y use_rag=True)
            operations_catalog_path: Ruta al catálogo de operaciones (workflow_catalog.json)
            use_rag: Si usar RAG para búsqueda semántica
        """
        self.use_rag = use_rag
        
        if use_rag:
            if A2ERAGSystem is None:
                logger.warning("RAG system not available. Install a2ui-rag-catalog or ensure rag_catalog is in path.")
                self.use_rag = False
                self.rag = None
            else:
                self.rag = rag_system or A2ERAGSystem()
            
            # Indexar catálogo de operaciones si se proporciona
            if operations_catalog_path:
                self.rag.index_operations_catalog(operations_catalog_path)
        else:
            self.rag = None
        
        # Almacenamiento tradicional (también se guarda en LokiJS)
        self.apis: Dict[str, Dict[str, Any]] = {}
        self.operations: Dict[str, Dict[str, Any]] = {}
    
    def load_api_definitions(self, api_definitions_path: str):
        """
        Carga definiciones de APIs desde un archivo JSON
        También las indexa en RAG si está habilitado
        """
        with open(api_definitions_path, "r", encoding="utf-8") as f:
            definitions = json.load(f)
        
        self.apis = definitions.get("apis", {})
        logger.info(f"Loaded {len(self.apis)} API definitions")
        
        # Indexar en RAG si está habilitado
        if self.use_rag and self.rag:
            for api_id, api_info in self.apis.items():
                self.rag.index_api(api_id, api_info)
                
                # Indexar endpoints
                base_url = api_info.get("baseUrl", "")
                for endpoint in api_info.get("endpoints", []):
                    self.rag.index_endpoint(api_id, endpoint, base_url)
    
    def add_api(
        self,
        api_id: str,
        base_url: str,
        endpoints: List[Dict[str, Any]],
        authentication: Optional[Dict[str, Any]] = None
    ):
        """
        Agrega una definición de API
        También la indexa en RAG si está habilitado
        
        Args:
            api_id: Identificador único de la API
            base_url: URL base de la API
            endpoints: Lista de endpoints disponibles
            authentication: Configuración de autenticación (opcional)
        """
        api_info = {
            "id": api_id,
            "baseUrl": base_url,
            "endpoints": endpoints,
            "authentication": authentication or {}
        }
        
        self.apis[api_id] = api_info
        
        # Indexar en RAG si está habilitado
        if self.use_rag and self.rag:
            self.rag.index_api(api_id, api_info)
            for endpoint in endpoints:
                self.rag.index_endpoint(api_id, endpoint, base_url)
    
    def add_endpoint(
        self,
        api_id: str,
        endpoint_path: str,
        method: str,
        description: str,
        parameters: Optional[List[Dict[str, Any]]] = None,
        response_schema: Optional[Dict[str, Any]] = None
    ):
        """
        Agrega un endpoint a una API existente
        """
        if api_id not in self.apis:
            raise ValueError(f"API {api_id} not found")
        
        endpoint = {
            "path": endpoint_path,
            "method": method,
            "description": description,
            "parameters": parameters or [],
            "responseSchema": response_schema
        }
        
        if "endpoints" not in self.apis[api_id]:
            self.apis[api_id]["endpoints"] = []
        
        self.apis[api_id]["endpoints"].append(endpoint)
    
    def get_available_apis(self) -> List[str]:
        """
        Retorna lista de IDs de APIs disponibles
        """
        return list(self.apis.keys())
    
    def get_api_info(self, api_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene información de una API
        """
        return self.apis.get(api_id)
    
    def search_endpoints(
        self,
        query: str,
        api_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca endpoints relevantes usando RAG (búsqueda semántica) o keywords
        """
        # Usar RAG si está habilitado
        if self.use_rag and self.rag:
            results = self.rag.search_endpoints(query, api_id=api_id, top_k=top_k)
            # Convertir formato
            return [
                {
                    "apiId": r["apiId"],
                    "baseUrl": r["baseUrl"],
                    "path": r["path"],
                    "method": r["method"],
                    "description": r["description"],
                    "endpoint": r["endpoint"],
                    "_score": r["score"]
                }
                for r in results
            ]
        
        # Fallback a búsqueda por keywords
        results = []
        apis_to_search = [api_id] if api_id else list(self.apis.keys())
        
        for api_id in apis_to_search:
            api = self.apis.get(api_id)
            if not api:
                continue
            
            for endpoint in api.get("endpoints", []):
                description = endpoint.get("description", "").lower()
                path = endpoint.get("path", "").lower()
                
                query_lower = query.lower()
                score = 0
                
                for word in query_lower.split():
                    if word in description:
                        score += 2
                    if word in path:
                        score += 1
                
                if score > 0:
                    endpoint_copy = endpoint.copy()
                    endpoint_copy["apiId"] = api_id
                    endpoint_copy["baseUrl"] = api["baseUrl"]
                    endpoint_copy["_score"] = score
                    results.append(endpoint_copy)
        
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results[:top_k]
    
    def search_operations(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca operaciones relevantes usando RAG (búsqueda semántica)
        
        Args:
            query: Query de búsqueda
            top_k: Número de resultados
        
        Returns:
            Lista de operaciones relevantes
        """
        if self.use_rag and self.rag:
            return self.rag.search_operations(query, top_k=top_k)
        return []
    
    def search_apis(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca APIs relevantes usando RAG (búsqueda semántica)
        
        Args:
            query: Query de búsqueda
            top_k: Número de resultados
        
        Returns:
            Lista de APIs relevantes
        """
        if self.use_rag and self.rag:
            return self.rag.search_apis(query, top_k=top_k)
        return []
    
    def build_partial_schema(
        self,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Construye un schema parcial solo con las operaciones relevantes
        
        Args:
            operations: Lista de operaciones relevantes
        
        Returns:
            Schema parcial
        """
        if self.use_rag and self.rag:
            return self.rag.build_partial_schema(operations)
        
        # Fallback: construir schema manualmente
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
    
    def build_api_catalog_for_agent(self) -> Dict[str, Any]:
        """
        Construye un catálogo de APIs para enviar al agente
        Similar a cómo se envía el catálogo de componentes
        """
        catalog = {
            "apis": {},
            "operations": list(self.operations.keys())
        }
        
        for api_id, api_info in self.apis.items():
            catalog["apis"][api_id] = {
                "baseUrl": api_info["baseUrl"],
                "endpoints": [
                    {
                        "path": ep["path"],
                        "method": ep["method"],
                        "description": ep.get("description", ""),
                        "parameters": ep.get("parameters", [])
                    }
                    for ep in api_info.get("endpoints", [])
                ]
            }
        
        return catalog


class ClientCapabilitiesAnnouncer:
    """
    Anuncia las capacidades del cliente al agente
    Similar a a2uiClientCapabilities pero para workflows
    """
    
    def __init__(self, api_kb: APIKnowledgeBase):
        self.api_kb = api_kb
    
    def build_capabilities_message(self) -> Dict[str, Any]:
        """
        Construye mensaje de capacidades para enviar al agente
        """
        return {
            "workflowCapabilities": {
                "supportedOperations": list(self.api_kb.operations.keys()),
                "availableApis": self.api_kb.build_api_catalog_for_agent(),
                "securityConstraints": {
                    "allowedDomains": self._get_allowed_domains(),
                    "maxExecutionTime": 30000,  # 30 segundos
                    "maxOperations": 20
                }
            }
        }
    
    def _get_allowed_domains(self) -> List[str]:
        """
        Extrae dominios permitidos de las APIs
        """
        domains = set()
        for api in self.api_kb.apis.values():
            base_url = api.get("baseUrl", "")
            if base_url:
                from urllib.parse import urlparse
                parsed = urlparse(base_url)
                if parsed.netloc:
                    domains.add(parsed.netloc)
        return list(domains)


# Ejemplo de uso
def create_example_knowledge_base():
    """
    Crea una base de conocimiento de ejemplo
    """
    kb = APIKnowledgeBase()
    
    # Agregar API de usuarios
    kb.add_api(
        api_id="user-api",
        base_url="https://api.example.com",
        endpoints=[],
        authentication={"type": "bearer", "tokenPath": "/config/apiToken"}
    )
    
    kb.add_endpoint(
        api_id="user-api",
        endpoint_path="/users",
        method="GET",
        description="Obtiene lista de usuarios. Soporta filtros por status y puntos.",
        parameters=[
            {"name": "status", "type": "string", "optional": True},
            {"name": "minPoints", "type": "number", "optional": True}
        ],
        response_schema={"type": "array", "items": {"type": "object"}}
    )
    
    kb.add_endpoint(
        api_id="user-api",
        endpoint_path="/users/{userId}",
        method="GET",
        description="Obtiene información de un usuario específico por ID",
        parameters=[
            {"name": "userId", "type": "string", "required": True, "in": "path"}
        ]
    )
    
    # Agregar API de productos
    kb.add_api(
        api_id="product-api",
        base_url="https://api.example.com",
        endpoints=[]
    )
    
    kb.add_endpoint(
        api_id="product-api",
        endpoint_path="/products",
        method="GET",
        description="Obtiene lista de productos con filtros opcionales",
        parameters=[
            {"name": "category", "type": "string", "optional": True},
            {"name": "priceMin", "type": "number", "optional": True},
            {"name": "priceMax", "type": "number", "optional": True}
        ]
    )
    
    return kb


if __name__ == "__main__":
    # Ejemplo de uso
    kb = create_example_knowledge_base()
    
    # Buscar endpoints
    results = kb.search_endpoints("obtener usuarios con puntos")
    print("Endpoints encontrados:")
    for ep in results:
        print(f"  - {ep['method']} {ep['baseUrl']}{ep['path']}: {ep['description']}")
    
    # Construir catálogo para agente
    catalog = kb.build_api_catalog_for_agent()
    print("\nCatálogo para agente:")
    print(json.dumps(catalog, indent=2))

