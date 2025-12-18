"""
Cliente SDK para A2E
Facilita la integración de agentes con el servidor A2E
"""

import requests
from typing import Dict, Any, Optional, List
import json


class A2EClient:
    """
    Cliente para conectarse al servidor A2E
    """
    
    def __init__(self, base_url: str, api_key: Optional[str] = None, token: Optional[str] = None):
        """
        Inicializa el cliente
        
        Args:
            base_url: URL base del servidor A2E (ej: "http://localhost:8000")
            api_key: API key para autenticación
            token: JWT token para autenticación
        """
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
        """
        Obtiene capacidades disponibles para este agente
        
        Returns:
            Diccionario con capacidades (APIs, credenciales, operaciones)
        """
        response = requests.get(
            f"{self.base_url}/api/v1/capabilities",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def validate_workflow(self, workflow_jsonl: str) -> Dict[str, Any]:
        """
        Valida un workflow antes de ejecutarlo
        
        Args:
            workflow_jsonl: Workflow en formato JSONL
        
        Returns:
            Reporte de validación
        """
        response = requests.post(
            f"{self.base_url}/api/v1/workflows/validate",
            headers=self._get_headers(),
            json={"workflow": workflow_jsonl}
        )
        response.raise_for_status()
        return response.json()
    
    def execute_workflow(
        self,
        workflow_jsonl: str,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Ejecuta un workflow
        
        Args:
            workflow_jsonl: Workflow en formato JSONL
            validate: Si validar antes de ejecutar (default: True)
        
        Returns:
            Respuesta de ejecución
        """
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
        """
        Obtiene detalles de una ejecución
        
        Args:
            execution_id: ID de la ejecución
        
        Returns:
            Detalles de la ejecución
        """
        response = requests.get(
            f"{self.base_url}/api/v1/executions/{execution_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def list_executions(
        self,
        limit: int = 100,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lista ejecuciones del agente
        
        Args:
            limit: Límite de resultados
            status: Filtrar por estado (opcional)
        
        Returns:
            Lista de ejecuciones
        """
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
    
    def search_knowledge(
        self,
        query: str,
        kb_id: Optional[str] = None,
        knowledge_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca conocimiento relevante
        
        Args:
            query: Query de búsqueda
            kb_id: Filtrar por base de conocimiento (opcional)
            knowledge_type: Filtrar por tipo (opcional)
            top_k: Número de resultados
        
        Returns:
            Lista de conocimiento relevante
        """
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
    
    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """
        Lista bases de conocimiento disponibles
        
        Returns:
            Lista de bases de conocimiento
        """
        response = requests.get(
            f"{self.base_url}/api/v1/knowledge/bases",
            headers=self._get_headers()
        )
        response.raise_for_status()
        data = response.json()
        return data.get("knowledgeBases", [])


class WorkflowBuilder:
    """
    Helper para construir workflows de forma más fácil
    """
    
    def __init__(self, workflow_id: str = "default"):
        self.workflow_id = workflow_id
        self.operations = []
    
    def add_api_call(
        self,
        operation_id: str,
        method: str,
        url: str,
        headers: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        output_path: str = "/workflow/result"
    ) -> 'WorkflowBuilder':
        """Agrega una operación ApiCall"""
        op = {
            "id": operation_id,
            "operation": {
                "ApiCall": {
                    "method": method,
                    "url": url,
                    "outputPath": output_path
                }
            }
        }
        
        if headers:
            op["operation"]["ApiCall"]["headers"] = headers
        if body:
            op["operation"]["ApiCall"]["body"] = body
        
        self.operations.append(op)
        return self
    
    def add_filter(
        self,
        operation_id: str,
        input_path: str,
        conditions: List[Dict[str, Any]],
        output_path: str = "/workflow/filtered"
    ) -> 'WorkflowBuilder':
        """Agrega una operación FilterData"""
        op = {
            "id": operation_id,
            "operation": {
                "FilterData": {
                    "inputPath": input_path,
                    "conditions": conditions,
                    "outputPath": output_path
                }
            }
        }
        self.operations.append(op)
        return self
    
    def add_store(
        self,
        operation_id: str,
        input_path: str,
        storage: str,
        key: str
    ) -> 'WorkflowBuilder':
        """Agrega una operación StoreData"""
        op = {
            "id": operation_id,
            "operation": {
                "StoreData": {
                    "inputPath": input_path,
                    "storage": storage,
                    "key": key
                }
            }
        }
        self.operations.append(op)
        return self
    
    def build(self) -> str:
        """Construye el workflow en formato JSONL"""
        lines = []
        
        # Operation update
        operation_update = {
            "operationUpdate": {
                "workflowId": self.workflow_id,
                "operations": self.operations
            }
        }
        lines.append(json.dumps(operation_update))
        
        # Begin execution (si hay operaciones)
        if self.operations:
            root_id = self.operations[0]["id"]
            begin_execution = {
                "beginExecution": {
                    "workflowId": self.workflow_id,
                    "root": root_id
                }
            }
            lines.append(json.dumps(begin_execution))
        
        return "\n".join(lines)


# Ejemplo de uso
if __name__ == "__main__":
    # Crear cliente
    client = A2EClient(
        base_url="http://localhost:8000",
        api_key="your-api-key-here"
    )
    
    # Obtener capacidades
    capabilities = client.get_capabilities()
    print("Available APIs:", list(capabilities["capabilities"]["availableApis"].keys()))
    
    # Construir workflow
    builder = WorkflowBuilder(workflow_id="test")
    builder.add_api_call(
        operation_id="fetch",
        method="GET",
        url="https://api.example.com/users",
        headers={
            "Authorization": {"credentialRef": {"id": "api-token"}}
        },
        output_path="/workflow/users"
    )
    
    workflow = builder.build()
    
    # Validar
    validation = client.validate_workflow(workflow)
    if validation["valid"]:
        # Ejecutar
        result = client.execute_workflow(workflow)
        print("Result:", result)
    else:
        print("Validation errors:", validation["issues"])

