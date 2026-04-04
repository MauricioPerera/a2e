"""
Tests for n8n_bridge — A2E → n8n workflow translator.
"""

import json
import pytest
from n8n_bridge.translator import A2EToN8nTranslator
from n8n_bridge.node_mapping import NODE_MAPPING


class TestTranslatorParsing:
    """Test parsing of different A2E workflow formats."""

    def test_parse_jsonl_format(self):
        """Parse standard JSONL workflow."""
        workflow = '{"operationUpdate": {"workflowId": "test", "operations": [{"id": "wait1", "operation": {"Wait": {"duration": 500}}}]}}\n{"beginExecution": {"workflowId": "test", "root": "wait1"}}'

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow)

        assert result["name"] == "A2E Translated Workflow"
        assert len(result["nodes"]) == 2  # trigger + wait
        assert result["nodes"][1]["type"] == "n8n-nodes-base.wait"

    def test_parse_compact_format(self):
        """Parse compact format workflow."""
        workflow = json.dumps({
            "operations": [
                {"id": "w1", "op": "Wait", "duration": 200},
                {"id": "w2", "op": "Wait", "duration": 300},
            ],
            "execute": "w1",
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow)

        assert len(result["nodes"]) == 3  # trigger + 2 waits

    def test_parse_no_trigger(self):
        """Translate without manual trigger."""
        workflow = '{"operationUpdate": {"workflowId": "t", "operations": [{"id": "w", "operation": {"Wait": {"duration": 100}}}]}}\n{"beginExecution": {"workflowId": "t", "root": "w"}}'

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["type"] == "n8n-nodes-base.wait"

    def test_empty_workflow_raises(self):
        """Empty workflow raises ValueError."""
        translator = A2EToN8nTranslator()
        with pytest.raises(ValueError, match="No operations found"):
            translator.translate("")


class TestApiCallTranslation:
    """Test ApiCall → HTTP Request translation."""

    def test_basic_get(self):
        workflow = '{"operationUpdate": {"workflowId": "t", "operations": [{"id": "fetch", "operation": {"ApiCall": {"method": "GET", "url": "https://api.example.com/users", "outputPath": "/workflow/users"}}}]}}\n{"beginExecution": {"workflowId": "t", "root": "fetch"}}'

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        node = result["nodes"][0]
        assert node["type"] == "n8n-nodes-base.httpRequest"
        assert node["parameters"]["method"] == "GET"
        assert node["parameters"]["url"] == "https://api.example.com/users"

    def test_post_with_headers(self):
        workflow = json.dumps({
            "operations": [{
                "id": "post",
                "op": "ApiCall",
                "method": "POST",
                "url": "https://api.example.com/data",
                "headers": {"Authorization": "Bearer token123", "X-Custom": "val"},
            }],
            "execute": "post",
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        node = result["nodes"][0]
        assert node["parameters"]["method"] == "POST"
        assert node["parameters"]["sendHeaders"] is True
        header_params = node["parameters"]["headerParameters"]["parameters"]
        header_names = [h["name"] for h in header_params]
        assert "Authorization" in header_names
        assert "X-Custom" in header_names


class TestFilterDataTranslation:
    """Test FilterData → Filter node translation."""

    def test_basic_filter(self):
        workflow = json.dumps({
            "operations": [{
                "id": "f1",
                "op": "FilterData",
                "inputPath": "/workflow/data",
                "conditions": [{"field": "age", "operator": ">", "value": 18}],
            }],
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        node = result["nodes"][0]
        assert node["type"] == "n8n-nodes-base.filter"
        conds = node["parameters"]["conditions"]["conditions"]
        assert len(conds) == 1
        assert "age" in conds[0]["leftValue"]


class TestTransformDataTranslation:
    """Test TransformData → Code node translation."""

    def test_sort_transform(self):
        workflow = json.dumps({
            "operations": [{
                "id": "sort1",
                "op": "TransformData",
                "type": "sort",
                "config": {"field": "name", "reverse": True},
            }],
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        node = result["nodes"][0]
        assert node["type"] == "n8n-nodes-base.code"
        assert "sort" in node["parameters"]["jsCode"]
        assert "name" in node["parameters"]["jsCode"]

    def test_unique_transform(self):
        workflow = json.dumps({
            "operations": [{"id": "u1", "op": "TransformData", "type": "unique"}],
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        node = result["nodes"][0]
        assert "seen" in node["parameters"]["jsCode"]


class TestWaitTranslation:
    """Test Wait → Wait node translation."""

    def test_wait_duration(self):
        workflow = json.dumps({
            "operations": [{"id": "w", "op": "Wait", "duration": 5000}],
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        node = result["nodes"][0]
        assert node["type"] == "n8n-nodes-base.wait"
        assert node["parameters"]["amount"] == 5.0
        assert node["parameters"]["unit"] == "seconds"


class TestDateTimeTranslation:
    """Test DateTime operations translation."""

    def test_datetime_now(self):
        workflow = json.dumps({
            "operations": [{
                "id": "dt",
                "op": "DateTime",
                "mode": "now",
                "timezone": "Europe/Madrid",
                "format": "iso8601",
            }],
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        node = result["nodes"][0]
        assert node["type"] == "n8n-nodes-base.dateTime"
        assert node["parameters"]["options"]["timezone"] == "Europe/Madrid"

    def test_legacy_get_current_datetime(self):
        workflow = '{"operationUpdate": {"workflowId": "t", "operations": [{"id": "dt", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/time"}}}]}}\n{"beginExecution": {"workflowId": "t", "root": "dt"}}'

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        node = result["nodes"][0]
        assert node["type"] == "n8n-nodes-base.dateTime"


class TestSetDataTranslation:
    """Test SetData → Set node translation."""

    def test_set_object(self):
        workflow = json.dumps({
            "operations": [{
                "id": "s1",
                "op": "SetData",
                "value": {"name": "test", "count": "42"},
            }],
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        node = result["nodes"][0]
        assert node["type"] == "n8n-nodes-base.set"
        assignments = node["parameters"]["assignments"]["assignments"]
        assert len(assignments) == 2

    def test_set_scalar(self):
        workflow = json.dumps({
            "operations": [{"id": "s2", "op": "SetData", "value": "hello"}],
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        node = result["nodes"][0]
        assert node["parameters"]["assignments"]["assignments"][0]["value"] == "hello"


class TestConditionalTranslation:
    """Test Conditional → IF node translation."""

    def test_basic_conditional(self):
        workflow = json.dumps({
            "operations": [{
                "id": "c1",
                "op": "Conditional",
                "path": "status",
                "operator": "==",
                "value": "active",
            }],
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        node = result["nodes"][0]
        assert node["type"] == "n8n-nodes-base.if"


class TestConnectionBuilding:
    """Test n8n connection wiring."""

    def test_linear_chain(self):
        workflow = json.dumps({
            "operations": [
                {"id": "a", "op": "Wait", "duration": 100},
                {"id": "b", "op": "Wait", "duration": 200},
                {"id": "c", "op": "Wait", "duration": 300},
            ],
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow)

        conns = result["connections"]
        # trigger → a → b → c
        assert "Manual Trigger" in conns
        assert len(conns) == 3  # trigger→a, a→b, b→c

    def test_dependency_order(self):
        """Operations with inputPath deps are ordered correctly."""
        workflow = '{"operationUpdate": {"workflowId": "t", "operations": [{"id": "fetch", "operation": {"ApiCall": {"method": "GET", "url": "https://api.example.com", "outputPath": "/workflow/data"}}}, {"id": "filter", "operation": {"FilterData": {"inputPath": "/workflow/data", "conditions": [{"field": "x", "operator": ">", "value": 0}], "outputPath": "/workflow/filtered"}}}]}}\n{"beginExecution": {"workflowId": "t", "root": "fetch"}}'

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, add_manual_trigger=False)

        # fetch should come before filter
        node_names = [n["name"] for n in result["nodes"]]
        fetch_idx = next(i for i, n in enumerate(node_names) if "fetch" in n)
        filter_idx = next(i for i, n in enumerate(node_names) if "filter" in n)
        assert fetch_idx < filter_idx


class TestComplexWorkflows:
    """Test realistic multi-operation workflows."""

    def test_api_filter_transform_chain(self):
        """Full pipeline: fetch → filter → transform."""
        workflow = json.dumps({
            "operations": [
                {
                    "id": "fetch",
                    "op": "ApiCall",
                    "method": "GET",
                    "url": "https://api.example.com/users",
                },
                {
                    "id": "filter",
                    "op": "FilterData",
                    "input": "fetch",
                    "conditions": [{"field": "active", "operator": "==", "value": True}],
                },
                {
                    "id": "transform",
                    "op": "TransformData",
                    "input": "filter",
                    "type": "pick",
                    "config": {"fields": ["name", "email"]},
                },
            ],
            "execute": "fetch",
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow, name="User Pipeline")

        assert result["name"] == "User Pipeline"
        assert len(result["nodes"]) == 4  # trigger + 3 ops
        assert result["_a2e_meta"]["a2e_source"] is True

        # Check node types in order
        types = [n["type"] for n in result["nodes"]]
        assert types[0] == "n8n-nodes-base.manualTrigger"
        assert types[1] == "n8n-nodes-base.httpRequest"
        assert types[2] == "n8n-nodes-base.filter"
        assert types[3] == "n8n-nodes-base.code"

    def test_datetime_workflow(self):
        """DateTime + SetData workflow."""
        workflow = '{"operationUpdate": {"workflowId": "dt-test", "operations": [{"id": "now", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/utc"}}}, {"id": "convert", "operation": {"ConvertTimezone": {"inputPath": "/workflow/utc", "fromTimezone": "UTC", "toTimezone": "Europe/Madrid", "format": "iso8601", "outputPath": "/workflow/madrid"}}}]}}\n{"beginExecution": {"workflowId": "dt-test", "root": "now"}}'

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow)

        assert len(result["nodes"]) == 3  # trigger + 2 datetime nodes
        for node in result["nodes"][1:]:
            assert node["type"] == "n8n-nodes-base.dateTime"


class TestOutputFormat:
    """Test output format and metadata."""

    def test_json_output(self):
        """translate_to_json returns valid JSON."""
        workflow = json.dumps({
            "operations": [{"id": "w", "op": "Wait", "duration": 100}],
        })

        translator = A2EToN8nTranslator()
        json_str = translator.translate_to_json(workflow)

        parsed = json.loads(json_str)
        assert "nodes" in parsed
        assert "connections" in parsed

    def test_metadata_present(self):
        """Translation metadata is included."""
        workflow = json.dumps({
            "operations": [{"id": "w", "op": "Wait", "duration": 100}],
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow)

        assert "_a2e_translation" in result
        assert result["_a2e_translation"]["operation_count"] == 1
        assert result["_a2e_translation"]["node_count"] == 2  # trigger + wait

    def test_warnings_on_unknown_op(self):
        """Unknown operations generate warnings."""
        workflow = json.dumps({
            "operations": [{"id": "x", "op": "UnknownOp", "foo": "bar"}],
        })

        translator = A2EToN8nTranslator()
        result = translator.translate(workflow)

        assert len(result["_a2e_translation"]["warnings"]) > 0
        assert "UnknownOp" in result["_a2e_translation"]["warnings"][0]
        # Should still produce a fallback Code node
        code_nodes = [n for n in result["nodes"] if n["type"] == "n8n-nodes-base.code"]
        assert len(code_nodes) == 1


class TestNodeMapping:
    """Test that all A2E operations have mappings."""

    def test_all_operations_mapped(self):
        """All 19 A2E operations should have n8n mappings."""
        expected_ops = [
            "ApiCall", "FilterData", "TransformData", "StoreData", "Wait",
            "DateTime", "GetCurrentDateTime", "ConvertTimezone", "DateCalculation",
            "SetData", "Conditional", "Loop", "MergeData",
            "FormatText", "ExtractText", "ValidateData", "Calculate", "EncodeDecode",
            "ExecuteN8nWorkflow",
        ]
        for op in expected_ops:
            assert op in NODE_MAPPING, f"Missing mapping for {op}"
            assert "n8n_type" in NODE_MAPPING[op]
            assert "translate" in NODE_MAPPING[op]
            assert callable(NODE_MAPPING[op]["translate"])

    def test_supported_operations_list(self):
        """supported_operations() returns sorted list."""
        ops = A2EToN8nTranslator.supported_operations()
        assert ops == sorted(ops)
        assert len(ops) == 19
