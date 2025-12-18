"""
Tests para Workflow Executor
"""

import pytest
import asyncio
from workflow_executor import WorkflowExecutor


@pytest.fixture
def executor():
    """Fixture para crear un ejecutor limpio"""
    return WorkflowExecutor()


@pytest.mark.asyncio
async def test_simple_workflow(executor):
    """Test workflow simple con una operación"""
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "wait", "operation": {"Wait": {"duration": 10}}}
]}}
{"beginExecution": {"workflowId": "test", "root": "wait"}}
"""
    
    executor.load_workflow(workflow)
    results = await executor.execute()
    
    assert "wait" in results
    assert results["wait"] is None  # Wait no retorna nada


@pytest.mark.asyncio
async def test_workflow_with_data_flow(executor):
    """Test workflow con flujo de datos"""
    # Simular datos en el data model
    executor.workflow_state = {
        "workflow": {
            "users": [
                {"id": "1", "name": "Alice", "points": 100},
                {"id": "2", "name": "Bob", "points": 200}
            ]
        }
    }
    
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "filter", "operation": {
    "FilterData": {
      "inputPath": "/workflow/users",
      "conditions": [{"field": "points", "operator": ">", "value": 150}],
      "outputPath": "/workflow/filtered"
    }
  }}
]}}
{"beginExecution": {"workflowId": "test", "root": "filter"}}
"""
    
    executor.load_workflow(workflow)
    results = await executor.execute()
    
    assert "filter" in results
    filtered = executor._get_data("/workflow/filtered")
    assert len(filtered) == 1
    assert filtered[0]["name"] == "Bob"


@pytest.mark.asyncio
async def test_workflow_execution_order(executor):
    """Test que las operaciones se ejecutan en orden correcto"""
    execution_order = []
    
    # Mock de operaciones para rastrear orden
    original_execute = executor._execute_operation
    
    async def tracked_execute(op_type, config):
        execution_order.append(op_type)
        return await original_execute(op_type, config)
    
    executor._execute_operation = tracked_execute
    
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "op1", "operation": {"Wait": {"duration": 10}}},
  {"id": "op2", "operation": {"Wait": {"duration": 10}}}
]}}
{"beginExecution": {"workflowId": "test", "root": "op1"}}
"""
    
    executor.load_workflow(workflow)
    await executor.execute()
    
    assert len(execution_order) == 2
    assert execution_order[0] == "Wait"
    assert execution_order[1] == "Wait"


@pytest.mark.asyncio
async def test_workflow_with_error(executor):
    """Test workflow que falla en una operación"""
    workflow = """
{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "invalid", "operation": {
    "InvalidOperation": {"config": "invalid"}
  }}
]}}
{"beginExecution": {"workflowId": "test", "root": "invalid"}}
"""
    
    executor.load_workflow(workflow)
    results = await executor.execute()
    
    assert "invalid" in results
    assert "error" in results["invalid"]


def test_data_model_set_get(executor):
    """Test operaciones de data model"""
    executor._set_data("/test/path", "value")
    value = executor._get_data("/test/path")
    assert value == "value"
    
    executor._set_data("/test/nested/deep", 123)
    value = executor._get_data("/test/nested/deep")
    assert value == 123


def test_path_resolution(executor):
    """Test resolución de paths con variables"""
    executor.workflow_state = {
        "config": {
            "apiToken": "token-123"
        }
    }
    
    url = executor._resolve_path("https://api.example.com/users?token={config/apiToken}")
    assert "token-123" in url

