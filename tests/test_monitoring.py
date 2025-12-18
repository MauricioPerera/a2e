"""
Tests para Monitoreo y Auditoría
"""

import pytest
import tempfile
import os
from monitoring.audit_logger import AuditLogger, ExecutionStatus
from datetime import datetime


@pytest.fixture
def logger():
    """Fixture para crear logger con directorio temporal"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield AuditLogger(log_dir=tmpdir)


def test_log_execution_start(logger):
    """Test registrar inicio de ejecución"""
    logger.log_execution_start(
        execution_id="test-123",
        agent_id="agent-123",
        workflow_id="workflow-123",
        workflow_jsonl='{"test": "data"}'
    )
    
    # Verificar que se escribió en el log
    executions = logger.query_executions(limit=1)
    assert len(executions) > 0
    assert executions[0]["execution_id"] == "test-123"
    assert executions[0]["agent_id"] == "agent-123"


def test_log_operation_start(logger):
    """Test registrar inicio de operación"""
    logger.log_operation_start(
        execution_id="test-123",
        operation_id="op-1",
        operation_type="ApiCall",
        operation_config={"url": "https://api.example.com"}
    )
    
    details = logger.get_execution_details("test-123")
    assert details is not None
    assert len(details["operations"]) > 0
    assert details["operations"][0]["operation_id"] == "op-1"


def test_log_credential_usage(logger):
    """Test registrar uso de credencial"""
    logger.log_credential_usage(
        execution_id="test-123",
        operation_id="op-1",
        credential_id="api-token",
        credential_type="bearer-token",
        usage_context="Authorization header"
    )
    
    details = logger.get_execution_details("test-123")
    assert len(details["credentials_used"]) > 0
    assert details["credentials_used"][0]["credential_id"] == "api-token"


def test_log_operation_result(logger):
    """Test registrar resultado de operación"""
    logger.log_operation_result(
        execution_id="test-123",
        operation_id="op-1",
        status=ExecutionStatus.SUCCESS,
        result={"data": [1, 2, 3]},
        duration_ms=100.5
    )
    
    details = logger.get_execution_details("test-123")
    operations = [op for op in details["operations"] if op.get("operation_id") == "op-1"]
    assert len(operations) > 0
    assert operations[0]["status"] == "success"
    assert operations[0].get("duration_ms") == 100.5


def test_log_execution_complete(logger):
    """Test registrar finalización de ejecución"""
    logger.log_execution_complete(
        execution_id="test-123",
        status=ExecutionStatus.SUCCESS,
        results={"op-1": {"data": [1, 2, 3]}},
        total_duration_ms=150.0,
        summary={"total_operations": 1}
    )
    
    executions = logger.query_executions(limit=1)
    assert len(executions) > 0
    assert executions[0]["status"] == "success"
    assert executions[0]["total_duration_ms"] == 150.0


def test_query_executions_by_agent(logger):
    """Test consultar ejecuciones por agente"""
    logger.log_execution_start("exec-1", "agent-1", "workflow-1", "{}")
    logger.log_execution_start("exec-2", "agent-2", "workflow-2", "{}")
    
    results = logger.query_executions(agent_id="agent-1", limit=10)
    assert len(results) > 0
    assert all(exec["agent_id"] == "agent-1" for exec in results)


def test_query_executions_by_status(logger):
    """Test consultar ejecuciones por estado"""
    logger.log_execution_complete("exec-1", ExecutionStatus.SUCCESS, {}, 100.0)
    logger.log_execution_complete("exec-2", ExecutionStatus.FAILED, {}, 100.0)
    
    results = logger.query_executions(status=ExecutionStatus.SUCCESS, limit=10)
    assert len(results) > 0
    assert all(exec["status"] == "success" for exec in results)


def test_get_execution_details(logger):
    """Test obtener detalles completos de ejecución"""
    logger.log_execution_start("exec-1", "agent-1", "workflow-1", "{}")
    logger.log_operation_start("exec-1", "op-1", "ApiCall", {})
    logger.log_credential_usage("exec-1", "op-1", "token-1", "bearer-token", "header")
    logger.log_operation_result("exec-1", "op-1", ExecutionStatus.SUCCESS, {}, 100.0)
    logger.log_execution_complete("exec-1", ExecutionStatus.SUCCESS, {}, 100.0)
    
    details = logger.get_execution_details("exec-1")
    assert details is not None
    assert details["execution_id"] == "exec-1"
    assert len(details["operations"]) > 0
    assert len(details["credentials_used"]) > 0
    assert len(details["timeline"]) > 0

