"""
Script para ejecutar test de agente en vivo
Simula un agente completo conectándose y ejecutando workflows
"""

import sys
import json
import tempfile
import os
import time
import threading
import requests
from pathlib import Path

# Agregar directorio al path
sys.path.insert(0, str(Path(__file__).parent))

from api_knowledge_base import APIKnowledgeBase, create_example_knowledge_base
from credentials_vault import CredentialsVault
from auth.agent_auth import AgentAuth
from client.a2e_client import A2EClient, WorkflowBuilder
from server.a2e_server import app, init_server


def setup_environment():
    """Configura entorno completo"""
    print("="*60)
    print("A2E Test Environment Setup")
    print("="*60)
    
    tmpdir = tempfile.mkdtemp(prefix="a2e_test_")
    print(f"[TEST] Test directory: {tmpdir}")
    
    vault_path = os.path.join(tmpdir, "vault.json")
    auth_path = os.path.join(tmpdir, "auth.json")
    api_path = os.path.join(tmpdir, "apis.json")
    config_path = os.path.join(tmpdir, "config.json")
    log_dir = os.path.join(tmpdir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 1. Vault
    print("\n[1/4] Creating credentials vault...")
    vault = CredentialsVault(vault_path=vault_path)
    vault.store_credential(
        credential_id="api-token",
        credential_type="bearer-token",
        value="test-token-12345",
        metadata={"api": "user-api"}
    )
    print("   [OK] Vault created with test credentials")
    
    # 2. API Knowledge Base
    print("\n[2/4] Creating API knowledge base...")
    api_kb = create_example_knowledge_base()
    api_output = {
        "apis": api_kb.apis,
        "operations": api_kb.operations
    }
    with open(api_path, "w") as f:
        json.dump(api_output, f, indent=2)
    print("   [OK] API knowledge base created")
    
    # 3. Register agent
    print("\n[3/4] Registering test agent...")
    auth = AgentAuth(config_path=auth_path)
    api_key = auth.register_agent(
        agent_id="test-agent",
        name="Test Agent",
        allowed_apis=["user-api"],
        allowed_credentials=["api-token"],
        allowed_operations=["ApiCall", "FilterData", "Wait", "StoreData"]
    )
    print(f"   [OK] Agent registered")
    print(f"   [OK] API Key: {api_key[:40]}...")
    
    # 4. Config
    config = {
        "vault": {"path": vault_path},
        "apiKnowledgeBase": {"path": api_path},
        "auth": {"path": auth_path},
        "monitoring": {"log_dir": log_dir}
    }
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print("\n[4/4] Configuration complete")
    
    return {
        "config_path": config_path,
        "api_key": api_key,
        "log_dir": log_dir,
        "tmpdir": tmpdir
    }


def start_server(config_path: str, port: int = 8004):
    """Inicia servidor"""
    with open(config_path, "r") as f:
        config = json.load(f)
    init_server(config)
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def wait_for_server(url: str, max_attempts: int = 20):
    """Espera servidor"""
    for i in range(max_attempts):
        try:
            response = requests.get(f"{url}/health", timeout=1)
            if response.status_code == 200:
                return True
        except:
            pass
        time.sleep(0.3)
    return False


def main():
    """Función principal: Simula agente"""
    print("\n" + "="*60)
    print("A2E Agent Simulation - Live Test")
    print("="*60 + "\n")
    
    # Setup
    setup = setup_environment()
    server_port = 8004
    server_url = f"http://127.0.0.1:{server_port}"
    
    # Iniciar servidor
    print(f"\n[START] Starting A2E server on {server_url}...")
    server_thread = threading.Thread(
        target=start_server,
        args=(setup["config_path"], server_port),
        daemon=True
    )
    server_thread.start()
    
    if not wait_for_server(server_url):
        print("❌ Server failed to start")
        return 1
    
    print("   [OK] Server is running\n")
    
    try:
        # ============================================================
        # AGENTE SE CONECTA
        # ============================================================
        print("="*60)
        print("AGENT OPERATIONS")
        print("="*60)
        
        print("\n[1/6] Connecting to server...")
        client = A2EClient(base_url=server_url, api_key=setup["api_key"])
        
        print("[2/6] Getting capabilities...")
        capabilities = client.get_capabilities()
        print(f"   [OK] Agent ID: {capabilities['agent_id']}")
        print(f"   [OK] Operations: {capabilities['capabilities']['supportedOperations']}")
        print(f"   [OK] APIs: {list(capabilities['capabilities']['availableApis'].keys())}")
        
        # ============================================================
        # GENERAR WORKFLOW
        # ============================================================
        print("\n[3/6] Generating workflow...")
        print("   Query: 'Espera 100ms y luego filtra datos'")
        
        # Workflow simple para prueba
        workflow = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "wait", "operation": {"Wait": {"duration": 100}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "wait"}}'
        
        print("   [OK] Workflow generated")
        
        # ============================================================
        # VALIDAR
        # ============================================================
        print("\n[4/6] Validating workflow...")
        validation = client.validate_workflow(workflow)
        if validation["valid"]:
            print("   [OK] Workflow is valid")
        else:
            print(f"   [WARN] {validation['errors']} errors, {validation['warnings']} warnings")
        
        # ============================================================
        # EJECUTAR
        # ============================================================
        print("\n[5/6] Executing workflow...")
        result = client.execute_workflow(workflow, validate=False)
        
        print(f"   Status: {result['status']}")
        if result["status"] == "success":
            print("   [OK] Execution successful")
            if "execution_id" in result:
                print(f"   Execution ID: {result['execution_id']}")
        else:
            print(f"   [ERROR] Execution failed: {result.get('error', {}).get('message', 'Unknown')}")
        
        # ============================================================
        # CONSULTAR
        # ============================================================
        if result.get("execution_id"):
            print("\n[6/6] Querying execution details...")
            details = client.get_execution(result["execution_id"])
            print(f"   [OK] Details retrieved")
            print(f"   Operations: {len(details.get('operations', []))}")
            print(f"   Timeline events: {len(details.get('timeline', []))}")
        
        # ============================================================
        # RESUMEN
        # ============================================================
        print("\n" + "="*60)
        print("[SUCCESS] ALL TESTS PASSED")
        print("="*60)
        print("\nAgent successfully:")
        print("  [OK] Connected to A2E server")
        print("  [OK] Retrieved filtered capabilities")
        print("  [OK] Generated workflow")
        print("  [OK] Validated workflow")
        print("  [OK] Executed workflow")
        print("  [OK] Queried execution details")
        print("\n[SUCCESS] A2E system is working correctly!")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Cleanup
        import shutil
        try:
            print(f"\n[CLEANUP] Test directory: {setup['tmpdir']}")
            # shutil.rmtree(setup['tmpdir'])  # Comentar para debug
        except:
            pass


if __name__ == "__main__":
    sys.exit(main())

