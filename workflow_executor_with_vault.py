"""
Ejecutor de workflows con integración de vault de credenciales
"""

import json
import logging
from typing import Dict, Any, Optional

from workflow_executor import WorkflowExecutor
from credentials_vault import CredentialsVault, CredentialInjector

logger = logging.getLogger(__name__)


class SecureWorkflowExecutor(WorkflowExecutor):
    """
    Ejecutor de workflows con vault de credenciales integrado
    """
    
    def __init__(self, vault: Optional[CredentialsVault] = None):
        super().__init__()
        self.vault = vault or CredentialsVault()
        self.injector = CredentialInjector(self.vault)
    
    async def _execute_api_call(self, config: Dict[str, Any]) -> Any:
        """
        Ejecuta llamada a API con inyección automática de credenciales
        """
        import aiohttp
        
        # Inyectar credenciales antes de ejecutar
        config = self.injector.inject_into_operation(config, "ApiCall")
        
        method = config["method"]
        url = self._resolve_path(config["url"])
        headers = self._resolve_object(config.get("headers", {}))
        body = self._resolve_object(config.get("body")) if config.get("body") else None
        
        logger.info(f"Executing {method} {url} with injected credentials")
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=body) as response:
                result = await response.json()
                
                output_path = config["outputPath"]
                self._set_data(output_path, result)
                
                return result
    
    def _resolve_object(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resuelve paths y referencias a credenciales en objetos
        """
        resolved = {}
        for key, value in obj.items():
            # Si es referencia a credencial, resolverla
            if isinstance(value, dict) and "credentialRef" in value:
                cred_value = self.vault.resolve_credential_reference(value)
                if cred_value:
                    # Formatear según tipo
                    cred_id = value["credentialRef"]["id"]
                    cred_metadata = self.vault.get_credential_metadata(cred_id)
                    cred_type = cred_metadata.get("type") if cred_metadata else None
                    
                    if cred_type == "bearer-token":
                        resolved[key] = f"Bearer {cred_value}"
                    elif cred_type == "api-key":
                        resolved[key] = cred_value
                    else:
                        resolved[key] = cred_value
                else:
                    logger.warning(f"Could not resolve credential reference: {value}")
                    resolved[key] = None
            elif isinstance(value, dict) and "path" in value:
                resolved[key] = self._get_data(value["path"])
            elif isinstance(value, str) and value.startswith("/"):
                resolved[key] = self._get_data(value)
            else:
                resolved[key] = value
        
        return resolved


# Ejemplo de uso
async def main():
    # Crear vault y almacenar credenciales
    vault = CredentialsVault()
    vault.store_credential(
        credential_id="api-token",
        credential_type="bearer-token",
        value="secret-token-123",
        metadata={"api": "user-api"}
    )
    
    # Crear ejecutor con vault
    executor = SecureWorkflowExecutor(vault)
    
    # Workflow que usa credencial (agente solo ve referencia)
    workflow_jsonl = """
{"operationUpdate": {"workflowId": "secure-api", "operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "headers": {
        "Authorization": {
          "credentialRef": {"id": "api-token"}
        }
      },
      "outputPath": "/workflow/users"
    }
  }}
]}}
{"beginExecution": {"workflowId": "secure-api", "root": "fetch"}}
"""
    
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("Results:", json.dumps(results, indent=2))
    # El agente nunca vio el valor "secret-token-123"
    # Solo la referencia {"credentialRef": {"id": "api-token"}}


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

