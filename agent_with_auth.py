"""
Agente que usa autenticación y recibe solo capacidades filtradas
"""

import json
from typing import Dict, Any, Optional

from api_knowledge_base import APIKnowledgeBase, ClientCapabilitiesAnnouncer
from credentials_vault import CredentialsVault, CredentialCapabilitiesAnnouncer
from auth.agent_auth import AgentAuth, AgentAuthMiddleware
from rag_catalog import ComponentRAG, ComponentIndexer


class AuthenticatedWorkflowAgent:
    """
    Agente que requiere autenticación y recibe solo capacidades asignadas
    """
    
    def __init__(
        self,
        agent_id: str,
        api_key: Optional[str] = None,
        token: Optional[str] = None,
        api_kb: Optional[APIKnowledgeBase] = None,
        vault: Optional[CredentialsVault] = None,
        auth: Optional[AgentAuth] = None,
        rag_system: Optional[ComponentRAG] = None
    ):
        """
        Inicializa agente autenticado
        
        Args:
            agent_id: ID del agente
            api_key: API key para autenticación
            token: JWT token para autenticación
            api_kb: Base de conocimiento de APIs
            vault: Vault de credenciales
            auth: Sistema de autenticación
            rag_system: Sistema RAG
        """
        self.agent_id = agent_id
        self.api_key = api_key
        self.token = token
        self.api_kb = api_kb
        self.vault = vault
        self.auth = auth or AgentAuth()
        self.rag = rag_system
        
        # Autenticar
        self._authenticate()
    
    def _authenticate(self):
        """Autentica el agente"""
        if self.api_key:
            authenticated_id = self.auth.authenticate(self.api_key)
            if authenticated_id != self.agent_id:
                raise ValueError(f"Authentication failed: Agent ID mismatch")
        elif self.token:
            authenticated_id = self.auth.verify_token(self.token)
            if authenticated_id != self.agent_id:
                raise ValueError(f"Authentication failed: Invalid token")
        else:
            raise ValueError("Either api_key or token must be provided")
    
    def get_capabilities_for_llm(self) -> Dict[str, Any]:
        """
        Obtiene capacidades filtradas para este agente específico
        Solo incluye recursos asignados al agente
        """
        # Obtener todas las capacidades
        api_announcer = ClientCapabilitiesAnnouncer(self.api_kb) if self.api_kb else None
        cred_announcer = CredentialCapabilitiesAnnouncer(self.vault) if self.vault else None
        
        all_apis = {}
        all_credentials = []
        all_operations = []
        
        if api_announcer:
            api_capabilities = api_announcer.build_capabilities_message()
            all_apis = api_capabilities["workflowCapabilities"]["availableApis"]
            all_operations = api_capabilities["workflowCapabilities"]["supportedOperations"]
        
        if cred_announcer:
            cred_capabilities = cred_announcer.build_capabilities_message()
            all_credentials = cred_capabilities["availableCredentials"]
        
        # Filtrar por permisos del agente
        filtered = self.auth.filter_capabilities(
            agent_id=self.agent_id,
            all_apis=all_apis,
            all_credentials=all_credentials,
            all_operations=all_operations
        )
        
        # Construir respuesta
        capabilities = {
            "agent_id": self.agent_id,
            "availableOperations": filtered["supportedOperations"],
            "availableApis": filtered["availableApis"],
            "availableCredentials": filtered["availableCredentials"],
            "securityConstraints": {
                "maxExecutionTime": 30000,
                "maxOperations": 20
            }
        }
        
        return capabilities
    
    def validate_workflow(self, workflow_jsonl: str) -> tuple[bool, Optional[str]]:
        """
        Valida que el workflow solo use recursos permitidos para este agente
        """
        import json
        
        lines = workflow_jsonl.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                return False, f"Invalid JSON: {line}"
            
            if "operationUpdate" in message:
                operations = message["operationUpdate"].get("operations", [])
                
                for op in operations:
                    op_type = list(op.get("operation", {}).keys())[0]
                    
                    # Validar operación permitida
                    if not self.auth.is_operation_allowed(self.agent_id, op_type):
                        return False, f"Operation '{op_type}' not allowed for agent '{self.agent_id}'"
                    
                    # Si es ApiCall, validar API
                    if op_type == "ApiCall":
                        config = op["operation"]["ApiCall"]
                        url = config.get("url", "")
                        
                        # Extraer API ID de la URL (simplificado)
                        # En producción, mapear URL a API ID
                        # Por ahora, validar dominio
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        domain = parsed.netloc
                        
                        # Validar que el agente tiene acceso a alguna API de este dominio
                        permissions = self.auth.get_agent_permissions(self.agent_id)
                        allowed_apis = permissions.get("allowed_apis", [])
                        
                        if allowed_apis:  # Si hay restricciones
                            # Verificar que alguna API permitida tiene este dominio
                            if self.api_kb:
                                has_access = False
                                for api_id in allowed_apis:
                                    api_info = self.api_kb.get_api_info(api_id)
                                    if api_info:
                                        api_domain = urlparse(api_info["baseUrl"]).netloc
                                        if domain == api_domain:
                                            has_access = True
                                            break
                                
                                if not has_access:
                                    return False, f"API domain '{domain}' not allowed for agent '{self.agent_id}'"
                    
                    # Validar credenciales usadas
                    if op_type == "ApiCall":
                        config = op["operation"]["ApiCall"]
                        headers = config.get("headers", {})
                        for key, value in headers.items():
                            if isinstance(value, dict) and "credentialRef" in value:
                                cred_id = value["credentialRef"].get("id")
                                if cred_id and not self.auth.is_credential_allowed(self.agent_id, cred_id):
                                    return False, f"Credential '{cred_id}' not allowed for agent '{self.agent_id}'"
        
        return True, None


# Ejemplo de uso
def main():
    from api_knowledge_base import create_example_knowledge_base
    from credentials_vault import CredentialsVault
    
    # Crear sistemas
    api_kb = create_example_knowledge_base()
    vault = CredentialsVault()
    auth = AgentAuth()
    
    # Registrar agente con permisos específicos
    api_key = auth.register_agent(
        agent_id="agent-123",
        name="User Data Agent",
        allowed_apis=["user-api"],  # Solo puede usar user-api
        allowed_credentials=["user-api-token"],  # Solo puede usar este token
        allowed_operations=["ApiCall", "FilterData"]  # Solo estas operaciones
    )
    
    print(f"Agent registered with API key: {api_key}\n")
    
    # Crear agente autenticado
    agent = AuthenticatedWorkflowAgent(
        agent_id="agent-123",
        api_key=api_key,
        api_kb=api_kb,
        vault=vault,
        auth=auth
    )
    
    # Obtener capacidades (solo las asignadas)
    capabilities = agent.get_capabilities_for_llm()
    print("Capabilities for this agent:")
    print(json.dumps(capabilities, indent=2))
    
    # Validar workflow
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "headers": {
        "Authorization": {"credentialRef": {"id": "user-api-token"}}
      }
    }
  }}
]}}
"""
    
    is_valid, error = agent.validate_workflow(workflow)
    print(f"\nWorkflow validation: {'✓ Valid' if is_valid else f'✗ Invalid: {error}'}")


if __name__ == "__main__":
    main()

