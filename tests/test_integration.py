"""
Tests de Integración Completa
"""

import pytest
import asyncio
import tempfile
import os
from workflow_executor_with_responses import RobustWorkflowExecutor
from api_knowledge_base import APIKnowledgeBase
from credentials_vault import CredentialsVault
from auth.agent_auth import AgentAuth
from validation.workflow_validator import WorkflowValidator, ValidationLevel
from monitoring.audit_logger import AuditLogger
from responses.response_formatter import ResponseFormat


@pytest.fixture
def full_system():
    """Fixture para crear sistema completo"""
    # Directorios temporales
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = os.path.join(tmpdir, "vault.json")
        auth_path = os.path.join(tmpdir, "auth.json")
        log_dir = os.path.join(tmpdir, "logs")
        
        # Crear componentes
        vault = CredentialsVault(vault_path=vault_path)
        api_kb = APIKnowledgeBase()
        auth = AgentAuth(config_path=auth_path)
        logger = AuditLogger(log_dir=log_dir)
        
        # Configurar
        vault.store_credential("api-token", "bearer-token", "secret-token-123")
        api_kb.add_api("test-api", "https://api.example.com", [])
        api_key = auth.register_agent(
            "agent-123",
            "Test Agent",
            allowed_apis=["test-api"],
            allowed_credentials=["api-token"]
        )
        
        executor = RobustWorkflowExecutor(
            audit_logger=logger,
            response_format=ResponseFormat.SUMMARY
        )
        executor.set_agent_context("agent-123")
        
        yield {
            "executor": executor,
            "vault": vault,
            "api_kb": api_kb,
            "auth": auth,
            "logger": logger,
            "api_key": api_key
        }


@pytest.mark.asyncio
async def test_full_workflow_execution(full_system):
    """Test ejecución completa de workflow"""
    executor = full_system["executor"]
    
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "wait", "operation": {"Wait": {"duration": 10}}}
]}}
{"beginExecution": {"workflowId": "test", "root": "wait"}}
"""
    
    executor.load_workflow(workflow, agent_id="agent-123")
    response = await executor.execute()
    
    assert response["status"] == "success"
    assert "execution_id" in response


@pytest.mark.asyncio
async def test_workflow_with_validation(full_system):
    """Test workflow con validación previa"""
    validator = WorkflowValidator(
        api_kb=full_system["api_kb"],
        vault=full_system["vault"],
        auth=full_system["auth"],
        level=ValidationLevel.MODERATE
    )
    
    # Workflow válido
    valid_workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "wait", "operation": {"Wait": {"duration": 10}}}
]}}
"""
    
    is_valid, errors = validator.validate_workflow(valid_workflow, agent_id="agent-123")
    assert is_valid is True
    
    # Workflow inválido (operación sin ID)
    invalid_workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"operation": {"Wait": {"duration": 10}}}
]}}
"""
    
    is_valid, errors = validator.validate_workflow(invalid_workflow, agent_id="agent-123")
    assert is_valid is False


def test_agent_authentication_flow(full_system):
    """Test flujo completo de autenticación"""
    auth = full_system["auth"]
    api_key = full_system["api_key"]
    
    # Autenticar
    agent_id = auth.authenticate(api_key)
    assert agent_id == "agent-123"
    
    # Obtener permisos
    permissions = auth.get_agent_permissions(agent_id)
    assert "test-api" in permissions["allowed_apis"]
    assert "api-token" in permissions["allowed_credentials"]


def test_capabilities_filtering(full_system):
    """Test filtrado de capacidades por agente"""
    auth = full_system["auth"]
    api_kb = full_system["api_kb"]
    vault = full_system["vault"]
    
    # Agregar más APIs y credenciales
    api_kb.add_api("other-api", "https://other.com", [])
    vault.store_credential("other-token", "bearer-token", "other-secret")
    
    all_apis = api_kb.build_api_catalog_for_agent()["apis"]
    all_credentials = [{"id": "api-token"}, {"id": "other-token"}]
    all_operations = ["ApiCall", "FilterData", "StoreData"]
    
    # Filtrar para agente con permisos limitados
    filtered = auth.filter_capabilities(
        agent_id="agent-123",
        all_apis=all_apis,
        all_credentials=all_credentials,
        all_operations=all_operations
    )
    
    # Solo debe ver lo permitido
    assert "test-api" in filtered["availableApis"]
    assert "other-api" not in filtered["availableApis"]
    assert len(filtered["availableCredentials"]) == 1
    assert filtered["availableCredentials"][0]["id"] == "api-token"


@pytest.mark.asyncio
async def test_error_handling_in_execution(full_system):
    """Test manejo de errores durante ejecución"""
    executor = full_system["executor"]
    
    # Workflow con operación inválida
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "invalid", "operation": {
    "InvalidOperation": {"config": "invalid"}
  }}
]}}
{"beginExecution": {"workflowId": "test", "root": "invalid"}}
"""
    
    executor.load_workflow(workflow, agent_id="agent-123")
    response = await executor.execute()
    
    # Debe retornar error estructurado
    assert response["status"] == "error" or response["status"] == "partial_success"
    if response["status"] == "error":
        assert "error" in response
        assert "suggestions" in response.get("error", {})


def test_monitoring_integration(full_system):
    """Test integración con monitoreo"""
    logger = full_system["logger"]
    
    # Registrar ejecución
    logger.log_execution_start("exec-1", "agent-123", "workflow-1", "{}")
    logger.log_operation_start("exec-1", "op-1", "ApiCall", {})
    logger.log_credential_usage("exec-1", "op-1", "api-token", "bearer-token", "header")
    logger.log_operation_result("exec-1", "op-1", ExecutionStatus.SUCCESS, {}, 100.0)
    logger.log_execution_complete("exec-1", ExecutionStatus.SUCCESS, {}, 100.0)
    
    # Consultar
    executions = logger.query_executions(agent_id="agent-123", limit=10)
    assert len(executions) > 0
    
    details = logger.get_execution_details("exec-1")
    assert details is not None
    assert len(details["credentials_used"]) > 0

