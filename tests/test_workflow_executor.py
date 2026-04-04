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
    workflow = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "wait", "operation": {"Wait": {"duration": 10}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "wait"}}'
    
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
    
    workflow = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "filter", "operation": {"FilterData": {"inputPath": "/workflow/users", "conditions": [{"field": "points", "operator": ">", "value": 150}], "outputPath": "/workflow/filtered"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "filter"}}'
    
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
    
    workflow = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "op1", "operation": {"Wait": {"duration": 10}}}, {"id": "op2", "operation": {"Wait": {"duration": 10}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "op1"}}'
    
    executor.load_workflow(workflow)
    await executor.execute()
    
    assert len(execution_order) == 2
    assert execution_order[0] == "Wait"
    assert execution_order[1] == "Wait"


@pytest.mark.asyncio
async def test_workflow_with_error(executor):
    """Test workflow que falla en una operación"""
    workflow = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "invalid", "operation": {"InvalidOperation": {"config": "invalid"}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "invalid"}}'
    
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


# ---------------------------------------------------------------------------
# Compact format tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compact_format_basic(executor):
    """Test compact format with a simple 2-operation workflow"""
    import json

    workflow = json.dumps({
        "operations": [
            {"id": "wait1", "op": "Wait", "duration": 10},
            {"id": "wait2", "op": "Wait", "duration": 20}
        ],
        "execute": "wait1"
    })

    executor.load_workflow(workflow)

    # Verify operations were loaded in internal format
    assert "wait1" in executor.operations
    assert "wait2" in executor.operations
    assert "Wait" in executor.operations["wait1"]["operation"]
    assert executor.operations["wait1"]["operation"]["Wait"]["duration"] == 10
    assert executor.operations["wait2"]["operation"]["Wait"]["duration"] == 20

    # Verify execution works
    results = await executor.execute()
    assert "wait1" in results
    assert "wait2" in results


@pytest.mark.asyncio
async def test_compact_format_implicit_piping(executor):
    """Test that omitting 'input' uses the previous operation's output"""
    import json

    executor.workflow_state = {
        "workflow": {
            "users": [
                {"id": "1", "name": "Alice", "active": True},
                {"id": "2", "name": "Bob", "active": False},
                {"id": "3", "name": "Charlie", "active": True}
            ]
        }
    }

    workflow = json.dumps({
        "operations": [
            {
                "id": "setdata",
                "op": "SetData",
                "outputPath": "/workflow/setdata",
                "value": [
                    {"id": "1", "name": "Alice", "active": True},
                    {"id": "2", "name": "Bob", "active": False}
                ]
            },
            {
                "id": "filter",
                "op": "FilterData",
                "conditions": [{"field": "active", "operator": "==", "value": True}]
            }
        ],
        "execute": "setdata"
    })

    executor.load_workflow(workflow)

    # filter should have inputPath pointing to previous op (setdata)
    filter_config = executor.operations["filter"]["operation"]["FilterData"]
    assert filter_config["inputPath"] == "/workflow/setdata"


def test_compact_format_auto_output_path(executor):
    """Test that outputPath defaults to /workflow/{id}"""
    import json

    workflow = json.dumps({
        "operations": [
            {"id": "fetch", "op": "ApiCall", "url": "https://example.com", "method": "GET"},
            {"id": "filter", "op": "FilterData", "input": "fetch",
             "conditions": [{"field": "active", "operator": "==", "value": True}]}
        ],
        "execute": "fetch"
    })

    executor.load_workflow(workflow)

    # Both operations should have auto-generated outputPath
    fetch_config = executor.operations["fetch"]["operation"]["ApiCall"]
    assert fetch_config["outputPath"] == "/workflow/fetch"

    filter_config = executor.operations["filter"]["operation"]["FilterData"]
    assert filter_config["outputPath"] == "/workflow/filter"

    # filter should resolve input to inputPath
    assert filter_config["inputPath"] == "/workflow/fetch"


@pytest.mark.asyncio
async def test_legacy_format_still_works(executor):
    """Test that old JSONL format still works after compact format changes"""
    workflow = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "wait", "operation": {"Wait": {"duration": 10}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "wait"}}'

    executor.load_workflow(workflow)
    results = await executor.execute()

    assert "wait" in results
    assert results["wait"] is None


# ---------------------------------------------------------------------------
# DAG / parallel execution tests
# ---------------------------------------------------------------------------

def test_parallel_independent_ops(executor):
    """Two SetData operations with no dependencies should be in the same level."""
    import json

    workflow = json.dumps({
        "operations": [
            {"id": "a", "op": "SetData", "value": 1, "outputPath": "/workflow/a"},
            {"id": "b", "op": "SetData", "value": 2, "outputPath": "/workflow/b"},
        ],
        "execute": "a"
    })

    executor.load_workflow(workflow)

    graph = executor._build_dependency_graph()
    assert graph["a"] == set()
    assert graph["b"] == set()

    levels = executor._topological_levels(graph)
    # Both should be in the first (and only) level
    assert len(levels) == 1
    assert set(levels[0]) == {"a", "b"}


def test_parallel_with_dependency(executor):
    """op_a and op_b are independent; op_c depends on both.
    Levels: [a, b], [c]."""
    import json

    workflow = json.dumps({
        "operations": [
            {"id": "op_a", "op": "SetData", "value": [1, 2], "outputPath": "/workflow/op_a"},
            {"id": "op_b", "op": "SetData", "value": [3, 4], "outputPath": "/workflow/op_b"},
            {
                "id": "op_c", "op": "MergeData",
                "sources": ["/workflow/op_a", "/workflow/op_b"],
                "strategy": "concat",
                "outputPath": "/workflow/op_c"
            }
        ],
        "execute": "op_a"
    })

    executor.load_workflow(workflow)

    graph = executor._build_dependency_graph()
    assert graph["op_a"] == set()
    assert graph["op_b"] == set()
    assert graph["op_c"] == {"op_a", "op_b"}

    levels = executor._topological_levels(graph)
    assert len(levels) == 2
    assert set(levels[0]) == {"op_a", "op_b"}
    assert levels[1] == ["op_c"]


def test_sequential_chain(executor):
    """A -> B -> C should produce 3 levels of 1 each."""
    import json

    workflow = json.dumps({
        "operations": [
            {"id": "A", "op": "SetData", "value": "hello", "outputPath": "/workflow/A"},
            {"id": "B", "op": "FilterData", "input": "A",
             "conditions": [{"field": "name", "operator": "==", "value": "x"}],
             "outputPath": "/workflow/B"},
            {"id": "C", "op": "FilterData", "input": "B",
             "conditions": [{"field": "name", "operator": "==", "value": "y"}],
             "outputPath": "/workflow/C"},
        ],
        "execute": "A"
    })

    executor.load_workflow(workflow)

    graph = executor._build_dependency_graph()
    assert graph["A"] == set()
    assert graph["B"] == {"A"}
    assert graph["C"] == {"B"}

    levels = executor._topological_levels(graph)
    assert len(levels) == 3
    assert levels[0] == ["A"]
    assert levels[1] == ["B"]
    assert levels[2] == ["C"]


@pytest.mark.asyncio
async def test_dag_fallback(executor):
    """Operations with no parseable dependencies should still execute without crashing."""
    import json

    workflow = json.dumps({
        "operations": [
            {"id": "s1", "op": "SetData", "value": 42, "outputPath": "/workflow/s1"},
            {"id": "s2", "op": "SetData", "value": 99, "outputPath": "/workflow/s2"},
        ],
        "execute": "s1"
    })

    executor.load_workflow(workflow)
    results = await executor.execute()

    assert results["s1"] == 42
    assert results["s2"] == 99


@pytest.mark.asyncio
async def test_parallel_execution_produces_correct_results(executor):
    """End-to-end: two independent SetData ops feed into a MergeData."""
    import json

    workflow = json.dumps({
        "operations": [
            {"id": "left", "op": "SetData", "value": [1, 2], "outputPath": "/workflow/left"},
            {"id": "right", "op": "SetData", "value": [3, 4], "outputPath": "/workflow/right"},
            {
                "id": "merged", "op": "MergeData",
                "sources": ["/workflow/left", "/workflow/right"],
                "strategy": "concat",
                "outputPath": "/workflow/merged"
            }
        ],
        "execute": "left"
    })

    executor.load_workflow(workflow)
    results = await executor.execute()

    assert results["left"] == [1, 2]
    assert results["right"] == [3, 4]
    assert results["merged"] == [1, 2, 3, 4]


# ---------------------------------------------------------------------------
# onError fallback tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_on_error_fallback_triggers(executor):
    """When an operation fails and has onError, the fallback executes and
    downstream operations receive the fallback data transparently."""
    import json

    workflow = json.dumps({
        "operations": [
            {
                "id": "fetch",
                "op": "FilterData",
                "inputPath": "/workflow/nonexistent",
                "conditions": [{"field": "x", "operator": "==", "value": 1}],
                "outputPath": "/workflow/fetch",
                "onError": "fallback"
            },
            {
                "id": "fallback",
                "op": "SetData",
                "value": [{"name": "default", "active": True}],
                "outputPath": "/workflow/fallback"
            },
            {
                "id": "process",
                "op": "FilterData",
                "input": "fetch",
                "conditions": [{"field": "active", "operator": "==", "value": True}],
                "outputPath": "/workflow/process"
            }
        ],
        "execute": "fetch"
    })

    executor.load_workflow(workflow)
    results = await executor.execute()

    # fetch should have the fallback result with _fallback flag
    assert results["fetch"]["_fallback"] is True

    # The fallback data should be available at /workflow/fetch for downstream
    fetch_data = executor._get_data("/workflow/fetch")
    assert fetch_data == [{"name": "default", "active": True}]

    # process should succeed using the fallback data
    assert "process" in results
    assert "error" not in results.get("process", {}) if isinstance(results.get("process"), dict) else True
    process_data = executor._get_data("/workflow/process")
    assert process_data == [{"name": "default", "active": True}]


@pytest.mark.asyncio
async def test_on_error_not_triggered_on_success(executor):
    """When an operation succeeds, its onError fallback is NOT executed."""
    import json

    executor.workflow_state = {
        "workflow": {
            "items": [{"name": "Alice", "active": True}]
        }
    }

    workflow = json.dumps({
        "operations": [
            {
                "id": "fetch",
                "op": "FilterData",
                "inputPath": "/workflow/items",
                "conditions": [{"field": "active", "operator": "==", "value": True}],
                "outputPath": "/workflow/fetch",
                "onError": "fallback"
            },
            {
                "id": "fallback",
                "op": "SetData",
                "value": {"source": "fallback"},
                "outputPath": "/workflow/fallback"
            }
        ],
        "execute": "fetch"
    })

    executor.load_workflow(workflow)
    results = await executor.execute()

    # fetch succeeded normally
    assert results["fetch"] == [{"name": "Alice", "active": True}]

    # fallback should not have been executed (not in results at all,
    # since it's excluded from normal flow)
    assert "fallback" not in results


@pytest.mark.asyncio
async def test_on_error_fallback_not_in_normal_execution(executor):
    """Fallback operations should be excluded from normal DAG execution."""
    import json

    workflow = json.dumps({
        "operations": [
            {
                "id": "main",
                "op": "SetData",
                "value": "hello",
                "outputPath": "/workflow/main",
                "onError": "fallback"
            },
            {
                "id": "fallback",
                "op": "SetData",
                "value": "fallback_value",
                "outputPath": "/workflow/fallback"
            },
            {
                "id": "other",
                "op": "SetData",
                "value": "world",
                "outputPath": "/workflow/other"
            }
        ],
        "execute": "main"
    })

    executor.load_workflow(workflow)

    # Check the dependency graph excludes fallback
    graph = executor._build_dependency_graph()
    assert "fallback" not in graph
    assert "main" in graph
    assert "other" in graph

    # Execute and verify fallback didn't run
    results = await executor.execute()
    assert "main" in results
    assert "other" in results
    assert "fallback" not in results


@pytest.mark.asyncio
async def test_on_error_with_compact_format(executor):
    """onError works correctly in compact format — field is passed through."""
    import json

    workflow = json.dumps({
        "operations": [
            {
                "id": "fetch",
                "op": "FilterData",
                "inputPath": "/workflow/does_not_exist",
                "conditions": [{"field": "x", "operator": "==", "value": 1}],
                "outputPath": "/workflow/fetch",
                "onError": "fallback"
            },
            {
                "id": "fallback",
                "op": "SetData",
                "value": {"users": [], "source": "cache"},
                "outputPath": "/workflow/fallback"
            }
        ],
        "execute": "fetch"
    })

    executor.load_workflow(workflow)

    # Verify onError is in the internal config
    fetch_config = executor.operations["fetch"]["operation"]["FilterData"]
    assert fetch_config.get("onError") == "fallback"

    results = await executor.execute()

    # Fallback should have triggered
    assert results["fetch"]["_fallback"] is True

    # Data should be at the original op's outputPath
    fetch_data = executor._get_data("/workflow/fetch")
    assert fetch_data == {"users": [], "source": "cache"}

