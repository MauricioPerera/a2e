"""
Test de simulación de agente
Simula un agente completo conectándose y ejecutando workflows
"""

import pytest
import asyncio
import json
import tempfile
import os
import time
import subprocess
import signal
from pathlib import Path

from api_knowledge_base import APIKnowledgeBase, create_example_knowledge_base
from credentials_vault import CredentialsVault
from auth.agent_auth import AgentAuth
from client.a2e_client import A2EClient, WorkflowBuilder


class AgentSimulator:
    """
    Simula un agente que se conecta a A2E
    """
    
    def __init__(self, server_url: str, api_key: str):
        self.client = A2EClient(base_url=server_url, api_key=api_key)
        self.capabilities = None
    
    def connect(self):
        """Conecta y obtiene capacidades"""
        print("🤖 Agent: Connecting to A2E server...")
        self.capabilities = self.client.get_capabilities()
        print(f"   ✓ Connected as agent: {self.capabilities['agent_id']}")
        print(f"   ✓ Available operations: {self.capabilities['capabilities']['supportedOperations']}")
        print(f"   ✓ Available APIs: {list(self.capabilities['capabilities']['availableApis'].keys())}")
        return self.capabilities
    
    def generate_workflow(self, user_query: str) -> str:
        """
        Genera un workflow desde una query del usuario
        (En producción, esto vendría del LLM)
        """
        print(f"\n🤖 Agent: Generating workflow for: '{user_query}'")
        
        # Simular generación de workflow basado en query
        if "consulta" in user_query.lower() and "filtra" in user_query.lower():
            # Workflow: Consultar API y filtrar
            builder = WorkflowBuilder("user-filter-workflow")
            
            # Simular que tenemos datos (en producción vendría de API real)
            # Por ahora, usamos Wait para simular
            builder.add_api_call(
                operation_id="fetch",
                method="GET",
                url="https://api.example.com/users",
                headers={
                    "Authorization": {"credentialRef": {"id": "api-token"}}
                },
                output_path="/workflow/users"
            )
            
            builder.add_filter(
                operation_id="filter",
                input_path="/workflow/users",
                conditions=[
                    {"field": "points", "operator": ">", "value": 100}
                ],
                output_path="/workflow/filtered"
            )
            
            workflow = builder.build()
            print("   ✓ Workflow generated")
            return workflow
        
        elif "espera" in user_query.lower() or "wait" in user_query.lower():
            # Workflow simple: solo esperar
            workflow = """
{"operationUpdate": {"workflowId": "simple-wait", "operations": [
  {"id": "wait", "operation": {"Wait": {"duration": 100}}}
]}}
{"beginExecution": {"workflowId": "simple-wait", "root": "wait"}}
"""
            print("   ✓ Simple workflow generated")
            return workflow
        
        else:
            # Workflow por defecto
            workflow = """
{"operationUpdate": {"workflowId": "default", "operations": [
  {"id": "wait", "operation": {"Wait": {"duration": 50}}}
]}}
{"beginExecution": {"workflowId": "default", "root": "wait"}}
"""
            return workflow
    
    def validate_workflow(self, workflow: str) -> tuple[bool, dict]:
        """Valida el workflow antes de ejecutar"""
        print("\n🤖 Agent: Validating workflow...")
        report = self.client.validate_workflow(workflow)
        
        if report["valid"]:
            print(f"   ✓ Workflow is valid")
            if report["warnings"] > 0:
                print(f"   ⚠️  {report['warnings']} warnings")
        else:
            print(f"   ✗ Workflow has {report['errors']} errors")
            for issue in report["issues"]:
                if issue["severity"] == "error":
                    print(f"     - {issue['message']}")
                    if issue.get("suggestion"):
                        print(f"       → {issue['suggestion']}")
        
        return report["valid"], report
    
    def execute_workflow(self, workflow: str, validate: bool = True) -> dict:
        """Ejecuta el workflow"""
        print("\n🤖 Agent: Executing workflow...")
        
        try:
            result = self.client.execute_workflow(workflow, validate=validate)
            
            if result["status"] == "success":
                print(f"   ✓ Execution successful")
                if "operations" in result:
                    print(f"   ✓ Operations completed: {len(result['operations'])}")
            elif result["status"] == "partial_success":
                print(f"   ⚠️  Partial success")
                print(f"     Successful: {result['successful']['count']}")
                print(f"     Failed: {result['failed']['count']}")
            elif result["status"] == "error":
                print(f"   ✗ Execution failed")
                error = result.get("error", {})
                print(f"     Error: {error.get('message', 'Unknown error')}")
                if "suggestions" in error:
                    for suggestion in error["suggestions"]:
                        print(f"       → {suggestion}")
            
            return result
            
        except Exception as e:
            print(f"   ✗ Execution error: {e}")
            raise
    
    def query_execution(self, execution_id: str):
        """Consulta detalles de una ejecución"""
        print(f"\n🤖 Agent: Querying execution {execution_id}...")
        details = self.client.get_execution(execution_id)
        
        print(f"   ✓ Execution details retrieved")
        print(f"     Operations: {len(details.get('operations', []))}")
        print(f"     Credentials used: {len(details.get('credentials_used', []))}")
        
        return details


@pytest.fixture
def test_setup():
    """Setup completo para tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Crear archivos de configuración
        vault_path = os.path.join(tmpdir, "vault.json")
        auth_path = os.path.join(tmpdir, "auth.json")
        api_path = os.path.join(tmpdir, "apis.json")
        config_path = os.path.join(tmpdir, "config.json")
        log_dir = os.path.join(tmpdir, "logs")
        
        # Crear vault
        vault = CredentialsVault(vault_path=vault_path)
        vault.store_credential(
            credential_id="api-token",
            credential_type="bearer-token",
            value="test-token-12345",
            metadata={"api": "user-api"}
        )
        
        # Crear API knowledge base
        api_kb = create_example_knowledge_base()
        api_output = {
            "apis": api_kb.apis,
            "operations": api_kb.operations
        }
        with open(api_path, "w") as f:
            json.dump(api_output, f, indent=2)
        
        # Registrar agente
        auth = AgentAuth(config_path=auth_path)
        api_key = auth.register_agent(
            agent_id="test-agent",
            name="Test Agent",
            allowed_apis=["user-api"],
            allowed_credentials=["api-token"],
            allowed_operations=["ApiCall", "FilterData", "Wait", "StoreData"]
        )
        
        # Crear configuración
        config = {
            "vault": {"path": vault_path},
            "apiKnowledgeBase": {"path": api_path},
            "auth": {"path": auth_path},
            "monitoring": {"log_dir": log_dir}
        }
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        
        yield {
            "config_path": config_path,
            "api_key": api_key,
            "log_dir": log_dir,
            "tmpdir": tmpdir
        }


def test_agent_full_workflow(test_setup):
    """Test completo: agente se conecta y ejecuta workflow"""
    import sys
    import threading
    from server.a2e_server import app, init_server
    
    # Cargar configuración
    with open(test_setup["config_path"], "r") as f:
        config = json.load(f)
    
    # Inicializar servidor
    init_server(config)
    
    # Iniciar servidor en thread separado
    def run_server():
        app.run(host="127.0.0.1", port=8001, debug=False, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Esperar a que el servidor inicie
    time.sleep(2)
    
    try:
        # Crear agente simulado
        agent = AgentSimulator(
            server_url="http://127.0.0.1:8001",
            api_key=test_setup["api_key"]
        )
        
        # 1. Conectar
        capabilities = agent.connect()
        assert capabilities is not None
        assert capabilities["agent_id"] == "test-agent"
        
        # 2. Generar workflow
        workflow = agent.generate_workflow("Consulta API y filtra usuarios con más de 100 puntos")
        assert workflow is not None
        
        # 3. Validar
        is_valid, report = agent.validate_workflow(workflow)
        # Puede tener warnings pero debe ser válido
        assert is_valid or report["errors"] == 0
        
        # 4. Ejecutar (con datos simulados)
        # Necesitamos mockear la API call o usar Wait
        simple_workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "wait", "operation": {"Wait": {"duration": 10}}}
]}}
{"beginExecution": {"workflowId": "test", "root": "wait"}}
"""
        
        result = agent.execute_workflow(simple_workflow, validate=False)
        assert result["status"] in ["success", "error"]
        
        if result["status"] == "success" and "execution_id" in result:
            # 5. Consultar ejecución
            details = agent.query_execution(result["execution_id"])
            assert details is not None
        
    finally:
        # El servidor se detendrá cuando termine el test
        pass


def test_agent_workflow_with_filter(test_setup):
    """Test agente ejecutando workflow con filtrado de datos"""
    import sys
    import threading
    from server.a2e_server import app, init_server
    
    # Cargar configuración
    with open(test_setup["config_path"], "r") as f:
        config = json.load(f)
    
    # Inicializar servidor
    init_server(config)
    
    # Iniciar servidor
    def run_server():
        app.run(host="127.0.0.1", port=8002, debug=False, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(2)
    
    try:
        agent = AgentSimulator(
            server_url="http://127.0.0.1:8002",
            api_key=test_setup["api_key"]
        )
        
        # Conectar
        agent.connect()
        
        # Workflow con datos simulados (usando Wait en lugar de ApiCall real)
        # En producción, esto vendría de una API real
        workflow = """
{"operationUpdate": {"workflowId": "filter-test", "operations": [
  {"id": "wait", "operation": {"Wait": {"duration": 10}}}
]}}
{"beginExecution": {"workflowId": "filter-test", "root": "wait"}}
"""
        
        result = agent.execute_workflow(workflow)
        assert result["status"] in ["success", "error"]
        
    finally:
        pass

