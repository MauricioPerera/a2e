"""
Ejemplo completo de uso de A2E
Muestra el flujo completo desde configuración hasta ejecución
"""

import asyncio
import json
from pathlib import Path

# Importar componentes
from api_knowledge_base import APIKnowledgeBase, create_example_knowledge_base
from credentials_vault import CredentialsVault
from auth.agent_auth import AgentAuth
from workflow_executor_with_responses import RobustWorkflowExecutor
from validation.workflow_validator import WorkflowValidator, ValidationLevel
from monitoring.audit_logger import AuditLogger
from responses.response_formatter import ResponseFormat
from agent_with_validation import ValidatedWorkflowAgent


async def main():
    """
    Ejemplo completo de uso de A2E
    """
    print("="*60)
    print("A2E Complete Example")
    print("="*60)
    
    # ============================================================
    # 1. CONFIGURACIÓN INICIAL (Normalmente hecho por humano)
    # ============================================================
    print("\n1. Setting up system...")
    
    # Crear vault y almacenar credenciales
    vault = CredentialsVault()
    vault.store_credential(
        credential_id="api-token",
        credential_type="bearer-token",
        value="secret-token-12345",
        metadata={"api": "user-api", "description": "Token for user API"}
    )
    print("   ✓ Credentials stored")
    
    # Crear base de conocimiento de APIs
    api_kb = create_example_knowledge_base()
    print("   ✓ API knowledge base created")
    
    # Registrar agente con permisos
    auth = AgentAuth()
    api_key = auth.register_agent(
        agent_id="example-agent",
        name="Example Agent",
        allowed_apis=["user-api"],
        allowed_credentials=["api-token"],
        allowed_operations=["ApiCall", "FilterData", "StoreData"]
    )
    print(f"   ✓ Agent registered (API Key: {api_key[:20]}...)")
    
    # ============================================================
    # 2. AGENTE SE CONECTA Y OBTIENE CAPACIDADES
    # ============================================================
    print("\n2. Agent connecting and getting capabilities...")
    
    from agent_with_validation import ValidatedWorkflowAgent
    
    agent = ValidatedWorkflowAgent(
        agent_id="example-agent",
        api_key=api_key,
        api_kb=api_kb,
        vault=vault,
        auth=auth,
        validation_level=ValidationLevel.MODERATE
    )
    
    capabilities = agent.get_capabilities_for_llm()
    print(f"   ✓ Capabilities received:")
    print(f"     - APIs: {list(capabilities['availableApis'].keys())}")
    print(f"     - Credentials: {[c['id'] for c in capabilities['availableCredentials']]}")
    print(f"     - Operations: {capabilities['availableOperations']}")
    
    # ============================================================
    # 3. AGENTE GENERA WORKFLOW (Simulado)
    # ============================================================
    print("\n3. Agent generating workflow...")
    
    # En producción, esto vendría del LLM
    workflow_jsonl = """
{"operationUpdate": {"workflowId": "user-filter", "operations": [
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
  }},
  {"id": "filter", "operation": {
    "FilterData": {
      "inputPath": "/workflow/users",
      "conditions": [
        {"field": "points", "operator": ">", "value": 100}
      ],
      "outputPath": "/workflow/filtered"
    }
  }},
  {"id": "store", "operation": {
    "StoreData": {
      "inputPath": "/workflow/filtered",
      "storage": "localStorage",
      "key": "active-users"
    }
  }}
]}}
{"beginExecution": {"workflowId": "user-filter", "root": "fetch"}}
"""
    
    print("   ✓ Workflow generated")
    
    # ============================================================
    # 4. VALIDAR WORKFLOW
    # ============================================================
    print("\n4. Validating workflow...")
    
    is_valid, report = agent.validate_and_suggest(workflow_jsonl)
    
    if not is_valid:
        print(f"   ✗ Validation failed ({report['errors']} errors, {report['warnings']} warnings)")
        for issue in report["issues"]:
            print(f"     - {issue['severity']}: {issue['message']}")
            if issue.get('suggestion'):
                print(f"       → {issue['suggestion']}")
        return
    else:
        print("   ✓ Workflow is valid")
    
    # ============================================================
    # 5. EJECUTAR WORKFLOW
    # ============================================================
    print("\n5. Executing workflow...")
    
    # Simular datos de API (en producción, esto vendría de la API real)
    executor = RobustWorkflowExecutor(
        audit_logger=AuditLogger(log_dir="logs"),
        response_format=ResponseFormat.SUMMARY
    )
    executor.set_agent_context("example-agent")
    
    # Simular respuesta de API
    executor.workflow_state = {
        "workflow": {
            "users": [
                {"id": "1", "name": "Alice", "points": 150},
                {"id": "2", "name": "Bob", "points": 50},
                {"id": "3", "name": "Charlie", "points": 200}
            ]
        }
    }
    
    executor.load_workflow(workflow_jsonl, agent_id="example-agent")
    response = await executor.execute()
    
    print(f"   ✓ Execution completed")
    print(f"     Status: {response['status']}")
    
    if response["status"] == "success":
        print(f"     Operations: {len(response.get('operations', {}))}")
        if "data" in response:
            print(f"     Data keys: {list(response['data'].keys())}")
    
    # ============================================================
    # 6. CONSULTAR RESULTADOS
    # ============================================================
    print("\n6. Querying execution details...")
    
    execution_id = response.get("execution_id")
    if execution_id:
        from monitoring.audit_logger import AuditLogger
        logger = AuditLogger(log_dir="logs")
        details = logger.get_execution_details(execution_id)
        
        if details:
            print(f"   ✓ Execution details retrieved")
            print(f"     Operations: {len(details['operations'])}")
            print(f"     Credentials used: {len(details['credentials_used'])}")
            if details['credentials_used']:
                for cred in details['credentials_used']:
                    print(f"       - {cred['credential_id']} ({cred['credential_type']})")
    
    # ============================================================
    # 7. RESUMEN
    # ============================================================
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("✓ System configured")
    print("✓ Agent authenticated")
    print("✓ Capabilities received (filtered)")
    print("✓ Workflow generated")
    print("✓ Workflow validated")
    print("✓ Workflow executed")
    print("✓ Results retrieved")
    print("\nA2E workflow completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())

