"""
Agente A2E usando Google ADK
Integra Google Agent Development Kit con el servidor A2E
"""

from google.adk import LlmAgent
from google.adk.core import AgentConfig, ModelConfig
from typing import Optional, Dict, Any
import os

from a2e_tools import (
    initialize_a2e_client,
    A2E_TOOLS
)


class A2EAgent:
    """
    Agente de Google ADK que se conecta al servidor A2E
    
    Este agente puede:
    - Obtener capacidades del servidor A2E
    - Buscar conocimiento usando RAG
    - Buscar consultas SQL
    - Validar y ejecutar workflows
    - Gestionar ejecuciones
    """
    
    def __init__(
        self,
        a2e_server_url: str,
        api_key: Optional[str] = None,
        token: Optional[str] = None,
        model_name: str = "gemini-2.0-flash-exp",
        project_id: Optional[str] = None,
        location: str = "us-central1"
    ):
        """
        Inicializa el agente A2E
        
        Args:
            a2e_server_url: URL del servidor A2E (ej: "http://localhost:8000")
            api_key: API key para autenticación con A2E
            token: JWT token para autenticación con A2E
            model_name: Nombre del modelo LLM a usar (default: gemini-2.0-flash-exp)
            project_id: ID del proyecto de Google Cloud (opcional, puede venir de env)
            location: Ubicación del modelo (default: us-central1)
        """
        # Inicializar cliente A2E
        initialize_a2e_client(a2e_server_url, api_key, token)
        
        # Configurar modelo
        if project_id is None:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        
        model_config = ModelConfig(
            model_name=model_name,
            project_id=project_id,
            location=location
        )
        
        # Configurar agente
        agent_config = AgentConfig(
            model=model_config,
            tools=A2E_TOOLS,
            system_instruction=self._get_system_instruction()
        )
        
        # Crear agente LLM
        self.agent = LlmAgent(config=agent_config)
        self.a2e_server_url = a2e_server_url
    
    def _get_system_instruction(self) -> str:
        """Obtiene la instrucción del sistema para el agente"""
        return """Eres un agente especializado en ejecutar workflows declarativos usando el protocolo A2E (Agent-to-Execution).

Tu función es ayudar a los usuarios a:
1. Descubrir capacidades disponibles (APIs, credenciales, operaciones)
2. Buscar conocimiento relevante usando RAG
3. Buscar consultas SQL predefinidas
4. Validar workflows antes de ejecutarlos
5. Ejecutar workflows declarativos en formato JSONL
6. Consultar el estado y resultados de ejecuciones

Los workflows A2E están en formato JSONL (JSON Lines), donde cada línea es un objeto JSON:
- Primera línea: {"operationUpdate": {"workflowId": "...", "operations": [...]}}
- Segunda línea: {"beginExecution": {"workflowId": "...", "root": "operation-id"}}

Operaciones disponibles:
- ApiCall: Llamadas HTTP a APIs
- FilterData: Filtrar datos
- TransformData: Transformar datos
- StoreData: Almacenar datos
- Wait: Esperar un tiempo
- Loop: Iterar sobre datos
- Conditional: Ejecución condicional
- MergeData: Combinar datos

Siempre valida los workflows antes de ejecutarlos para evitar errores."""
    
    async def run(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta el agente con una entrada del usuario
        
        Args:
            user_input: Entrada del usuario
            **kwargs: Argumentos adicionales para el agente
        
        Returns:
            Respuesta del agente
        """
        return await self.agent.run(user_input, **kwargs)
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Obtiene las capacidades disponibles del servidor A2E"""
        from a2e_tools import get_a2e_client
        client = get_a2e_client()
        return client.get_capabilities()
    
    def execute_workflow_direct(self, workflow_jsonl: str, validate: bool = True) -> Dict[str, Any]:
        """
        Ejecuta un workflow directamente sin pasar por el LLM
        
        Args:
            workflow_jsonl: Workflow en formato JSONL
            validate: Si validar antes de ejecutar
        
        Returns:
            Resultado de la ejecución
        """
        from a2e_tools import get_a2e_client
        client = get_a2e_client()
        return client.execute_workflow(workflow_jsonl, validate)


# Función helper para crear un agente fácilmente
def create_a2e_agent(
    a2e_server_url: Optional[str] = None,
    api_key: Optional[str] = None,
    token: Optional[str] = None,
    model_name: str = "gemini-2.0-flash-exp",
    **kwargs
) -> A2EAgent:
    """
    Crea un agente A2E con configuración por defecto
    
    Args:
        a2e_server_url: URL del servidor A2E (default: de env A2E_SERVER_URL)
        api_key: API key (default: de env A2E_API_KEY)
        token: JWT token (default: de env A2E_TOKEN)
        model_name: Nombre del modelo LLM
        **kwargs: Argumentos adicionales para A2EAgent
    
    Returns:
        Instancia de A2EAgent configurada
    """
    if a2e_server_url is None:
        a2e_server_url = os.getenv("A2E_SERVER_URL", "http://localhost:8000")
    
    if api_key is None:
        api_key = os.getenv("A2E_API_KEY")
    
    if token is None:
        token = os.getenv("A2E_TOKEN")
    
    return A2EAgent(
        a2e_server_url=a2e_server_url,
        api_key=api_key,
        token=token,
        model_name=model_name,
        **kwargs
    )

