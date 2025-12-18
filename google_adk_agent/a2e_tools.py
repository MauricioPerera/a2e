"""
Herramientas A2E para Google ADK
Proporciona herramientas que los agentes de ADK pueden usar para interactuar con el servidor A2E
"""

from typing import Dict, Any, Optional, List
from google.adk import Tool
from google.adk.core import ToolResult
import requests
import json


class A2EClient:
    """
    Cliente HTTP para comunicarse con el servidor A2E
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.token = token
        
        if not api_key and not token:
            raise ValueError("Either api_key or token must be provided")
    
    def _get_headers(self) -> Dict[str, str]:
        """Obtiene headers de autenticación"""
        headers = {"Content-Type": "application/json"}
        
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        return headers
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Obtiene las capacidades disponibles del servidor A2E"""
        response = requests.get(
            f"{self.base_url}/api/v1/capabilities",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def validate_workflow(self, workflow_jsonl: str) -> Dict[str, Any]:
        """Valida un workflow antes de ejecutarlo"""
        response = requests.post(
            f"{self.base_url}/api/v1/workflows/validate",
            headers=self._get_headers(),
            json={"workflow": workflow_jsonl}
        )
        response.raise_for_status()
        return response.json()
    
    def execute_workflow(self, workflow_jsonl: str, validate: bool = True) -> Dict[str, Any]:
        """Ejecuta un workflow en el servidor A2E"""
        response = requests.post(
            f"{self.base_url}/api/v1/workflows/execute",
            headers=self._get_headers(),
            json={
                "workflow": workflow_jsonl,
                "validate": validate
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_execution(self, execution_id: str) -> Dict[str, Any]:
        """Obtiene detalles de una ejecución"""
        response = requests.get(
            f"{self.base_url}/api/v1/executions/{execution_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def list_executions(self, limit: int = 100, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista ejecuciones del agente"""
        params = {"limit": limit}
        if status:
            params["status"] = status
        
        response = requests.get(
            f"{self.base_url}/api/v1/executions",
            headers=self._get_headers(),
            params=params
        )
        response.raise_for_status()
        data = response.json()
        return data.get("executions", [])
    
    def search_knowledge(self, query: str, kb_id: Optional[str] = None, 
                        knowledge_type: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Busca conocimiento relevante usando RAG"""
        response = requests.post(
            f"{self.base_url}/api/v1/knowledge/search",
            headers=self._get_headers(),
            json={
                "query": query,
                "kb_id": kb_id,
                "type": knowledge_type,
                "top_k": top_k
            }
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    
    def search_sql_queries(self, query: str, database: Optional[str] = None,
                          category: Optional[str] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """Busca consultas SQL relevantes"""
        response = requests.post(
            f"{self.base_url}/api/v1/sql-queries/search",
            headers=self._get_headers(),
            json={
                "query": query,
                "database": database,
                "category": category,
                "top_k": top_k
            }
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])


# Instancia global del cliente (se inicializa en el agente)
_a2e_client: Optional[A2EClient] = None


def initialize_a2e_client(base_url: str, api_key: Optional[str] = None, token: Optional[str] = None):
    """Inicializa el cliente A2E global"""
    global _a2e_client
    _a2e_client = A2EClient(base_url, api_key, token)


def get_a2e_client() -> A2EClient:
    """Obtiene el cliente A2E global"""
    if _a2e_client is None:
        raise RuntimeError("A2E client not initialized. Call initialize_a2e_client() first.")
    return _a2e_client


# ============================================================================
# Herramientas ADK para A2E
# ============================================================================

@Tool(
    name="a2e_get_capabilities",
    description="Obtiene las capacidades disponibles del servidor A2E, incluyendo APIs, credenciales y operaciones soportadas."
)
def get_capabilities() -> ToolResult:
    """Obtiene capacidades disponibles del servidor A2E"""
    try:
        client = get_a2e_client()
        capabilities = client.get_capabilities()
        return ToolResult(
            content=json.dumps(capabilities, indent=2),
            is_error=False
        )
    except Exception as e:
        return ToolResult(
            content=f"Error obteniendo capacidades: {str(e)}",
            is_error=True
        )


@Tool(
    name="a2e_search_knowledge",
    description="Busca conocimiento relevante usando RAG (Retrieval Augmented Generation). Útil para encontrar información sobre APIs, operaciones y documentación."
)
def search_knowledge(
    query: str,
    kb_id: Optional[str] = None,
    knowledge_type: Optional[str] = None,
    top_k: int = 5
) -> ToolResult:
    """Busca conocimiento relevante usando RAG"""
    try:
        client = get_a2e_client()
        results = client.search_knowledge(query, kb_id, knowledge_type, top_k)
        return ToolResult(
            content=json.dumps({
                "query": query,
                "results": results,
                "count": len(results)
            }, indent=2),
            is_error=False
        )
    except Exception as e:
        return ToolResult(
            content=f"Error buscando conocimiento: {str(e)}",
            is_error=True
        )


@Tool(
    name="a2e_search_sql_queries",
    description="Busca consultas SQL predefinidas relevantes. Útil para encontrar consultas SQL que pueden ser ejecutadas."
)
def search_sql_queries(
    query: str,
    database: Optional[str] = None,
    category: Optional[str] = None,
    top_k: int = 5
) -> ToolResult:
    """Busca consultas SQL relevantes"""
    try:
        client = get_a2e_client()
        results = client.search_sql_queries(query, database, category, top_k)
        return ToolResult(
            content=json.dumps({
                "query": query,
                "results": results,
                "count": len(results)
            }, indent=2),
            is_error=False
        )
    except Exception as e:
        return ToolResult(
            content=f"Error buscando consultas SQL: {str(e)}",
            is_error=True
        )


@Tool(
    name="a2e_validate_workflow",
    description="Valida un workflow A2E antes de ejecutarlo. Verifica que las operaciones, APIs y credenciales sean válidas."
)
def validate_workflow(workflow_jsonl: str) -> ToolResult:
    """Valida un workflow A2E"""
    try:
        client = get_a2e_client()
        validation = client.validate_workflow(workflow_jsonl)
        return ToolResult(
            content=json.dumps(validation, indent=2),
            is_error=False
        )
    except Exception as e:
        return ToolResult(
            content=f"Error validando workflow: {str(e)}",
            is_error=True
        )


@Tool(
    name="a2e_execute_workflow",
    description="Ejecuta un workflow A2E. El workflow debe estar en formato JSONL. Opcionalmente valida antes de ejecutar."
)
def execute_workflow(workflow_jsonl: str, validate: bool = True) -> ToolResult:
    """Ejecuta un workflow A2E"""
    try:
        client = get_a2e_client()
        result = client.execute_workflow(workflow_jsonl, validate)
        return ToolResult(
            content=json.dumps(result, indent=2),
            is_error=False
        )
    except Exception as e:
        return ToolResult(
            content=f"Error ejecutando workflow: {str(e)}",
            is_error=True
        )


@Tool(
    name="a2e_get_execution",
    description="Obtiene detalles de una ejecución específica usando su execution_id."
)
def get_execution(execution_id: str) -> ToolResult:
    """Obtiene detalles de una ejecución"""
    try:
        client = get_a2e_client()
        execution = client.get_execution(execution_id)
        return ToolResult(
            content=json.dumps(execution, indent=2),
            is_error=False
        )
    except Exception as e:
        return ToolResult(
            content=f"Error obteniendo ejecución: {str(e)}",
            is_error=True
        )


@Tool(
    name="a2e_list_executions",
    description="Lista las ejecuciones del agente. Puede filtrar por estado y limitar el número de resultados."
)
def list_executions(limit: int = 100, status: Optional[str] = None) -> ToolResult:
    """Lista ejecuciones del agente"""
    try:
        client = get_a2e_client()
        executions = client.list_executions(limit, status)
        return ToolResult(
            content=json.dumps({
                "executions": executions,
                "count": len(executions)
            }, indent=2),
            is_error=False
        )
    except Exception as e:
        return ToolResult(
            content=f"Error listando ejecuciones: {str(e)}",
            is_error=True
        )


# Lista de todas las herramientas A2E
A2E_TOOLS = [
    get_capabilities,
    search_knowledge,
    search_sql_queries,
    validate_workflow,
    execute_workflow,
    get_execution,
    list_executions,
]

