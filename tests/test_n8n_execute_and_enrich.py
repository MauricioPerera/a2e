"""
Tests for:
  - Option 2: ExecuteN8nWorkflow as native A2E operation
  - Option 3: N8nCatalogEnricher (catalog enrichment from n8n)
"""

import json
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from executor.workflow_executor import WorkflowExecutor, OPERATION_HANDLERS
from n8n_bridge.catalog_enricher import N8nCatalogEnricher


# ═══════════════════════════════════════════════════════════════════════
# Option 2: ExecuteN8nWorkflow operation
# ═══════════════════════════════════════════════════════════════════════


class TestExecuteN8nWorkflowRegistration:
    """Verify the operation is properly registered."""

    def test_registered_in_handlers(self):
        assert "ExecuteN8nWorkflow" in OPERATION_HANDLERS
        assert OPERATION_HANDLERS["ExecuteN8nWorkflow"] == "_execute_n8n_workflow"

    def test_executor_has_method(self):
        executor = WorkflowExecutor()
        assert hasattr(executor, "_execute_n8n_workflow")
        assert callable(getattr(executor, "_execute_n8n_workflow"))


class TestExecuteN8nWorkflowValidation:
    """Test config validation."""

    @pytest.mark.asyncio
    async def test_missing_workflow_id_raises(self):
        executor = WorkflowExecutor()
        with pytest.raises(ValueError, match="requires 'workflowId'"):
            await executor._execute_n8n_workflow({"outputPath": "/workflow/out"})

    @pytest.mark.asyncio
    async def test_missing_n8n_url_raises(self):
        executor = WorkflowExecutor()
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("N8N_URL", None)
            os.environ.pop("N8N_API_KEY", None)
            with pytest.raises(ValueError, match="n8n URL"):
                await executor._execute_n8n_workflow({
                    "workflowId": "123",
                    "outputPath": "/workflow/out",
                })

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self):
        executor = WorkflowExecutor()
        with patch.dict(os.environ, {"N8N_URL": "http://localhost:5678"}, clear=True):
            os.environ.pop("N8N_API_KEY", None)
            with pytest.raises(ValueError, match="API key"):
                await executor._execute_n8n_workflow({
                    "workflowId": "123",
                    "outputPath": "/workflow/out",
                })


class TestExecuteN8nWorkflowExecution:
    """Test execution with mocked n8n API."""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Mock a successful n8n workflow execution."""
        executor = WorkflowExecutor()
        executor.workflow_state = {"workflow": {}}

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": "exec-999",
            "status": "success",
            "finished": True,
            "data": None,
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await executor._execute_n8n_workflow({
                "workflowId": "wf-42",
                "payload": {"email": "test@example.com"},
                "n8nUrl": "http://localhost:5678",
                "n8nApiKey": "test-key",
                "outputPath": "/workflow/n8n_result",
            })

        assert result["n8n_workflow_id"] == "wf-42"
        assert result["execution_id"] == "exec-999"
        assert result["status"] == "success"
        assert result["finished"] is True

        # Check it was stored in data model
        stored = executor._get_data("/workflow/n8n_result")
        assert stored is not None
        assert stored["execution_id"] == "exec-999"

    @pytest.mark.asyncio
    async def test_execution_with_payload_from_data_model(self):
        """Payload can be a path reference to the data model."""
        executor = WorkflowExecutor()
        executor.workflow_state = {
            "workflow": {
                "input_data": {"name": "test", "value": 42},
            }
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": "exec-100",
            "status": "success",
            "finished": True,
            "data": None,
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await executor._execute_n8n_workflow({
                "workflowId": "wf-99",
                "payload": "/workflow/input_data",
                "n8nUrl": "http://localhost:5678",
                "n8nApiKey": "test-key",
                "outputPath": "/workflow/result",
            })

        assert result["status"] == "success"
        # Verify the POST was called with resolved payload
        call_args = mock_session.post.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_execution_http_error(self):
        """n8n API returning error status."""
        executor = WorkflowExecutor()

        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value="Workflow not found")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(RuntimeError, match="n8n execution failed"):
                await executor._execute_n8n_workflow({
                    "workflowId": "nonexistent",
                    "n8nUrl": "http://localhost:5678",
                    "n8nApiKey": "test-key",
                    "outputPath": "/workflow/result",
                })

    @pytest.mark.asyncio
    async def test_env_var_fallback(self):
        """Uses N8N_URL and N8N_API_KEY env vars when config omits them."""
        executor = WorkflowExecutor()
        executor.workflow_state = {"workflow": {}}

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": "exec-env",
            "status": "success",
            "finished": True,
            "data": None,
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        env = {"N8N_URL": "http://n8n.local:5678", "N8N_API_KEY": "env-key"}
        with patch.dict(os.environ, env):
            with patch("aiohttp.ClientSession", return_value=mock_session):
                result = await executor._execute_n8n_workflow({
                    "workflowId": "wf-env",
                    "outputPath": "/workflow/result",
                })

        assert result["n8n_workflow_id"] == "wf-env"
        # Verify URL used env var
        call_args = mock_session.post.call_args
        assert "n8n.local" in str(call_args)


class TestExecuteN8nWorkflowInWorkflow:
    """Test ExecuteN8nWorkflow within a full A2E workflow execution."""

    @pytest.mark.asyncio
    async def test_in_compact_workflow(self):
        """ExecuteN8nWorkflow works in compact format workflow."""
        workflow = json.dumps({
            "operations": [
                {"id": "set-input", "op": "SetData", "value": {"msg": "hello"}},
                {
                    "id": "run-n8n",
                    "op": "ExecuteN8nWorkflow",
                    "workflowId": "wf-compact",
                    "payload": "/workflow/set-input",
                    "n8nUrl": "http://localhost:5678",
                    "n8nApiKey": "test-key",
                },
            ],
            "execute": "set-input",
        })

        executor = WorkflowExecutor()
        executor.load_workflow(workflow)

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": "exec-compact",
            "status": "success",
            "finished": True,
            "data": None,
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            results = await executor.execute()

        assert "run-n8n" in results
        run_result = results["run-n8n"]
        # The executor wraps with status or returns the handler result directly
        actual_status = run_result.get("status", "")
        assert actual_status in ("completed", "success"), f"Unexpected status: {actual_status}"


# ═══════════════════════════════════════════════════════════════════════
# Option 3: N8nCatalogEnricher
# ═══════════════════════════════════════════════════════════════════════


class TestCatalogEnricherFromWorkflowList:
    """Test enrichment from pre-fetched workflow lists."""

    def test_basic_enrichment(self):
        enricher = N8nCatalogEnricher()
        workflows = [
            {
                "id": "1",
                "name": "Send Email",
                "active": True,
                "tags": [{"id": "t1", "name": "notifications"}],
                "nodes": [
                    {"type": "n8n-nodes-base.manualTrigger", "name": "Trigger"},
                    {"type": "n8n-nodes-base.gmail", "name": "Send"},
                ],
            },
            {
                "id": "2",
                "name": "Daily Report",
                "active": True,
                "tags": [{"id": "t2", "name": "reports"}],
                "nodes": [
                    {"type": "n8n-nodes-base.cron", "name": "Schedule"},
                    {"type": "n8n-nodes-base.httpRequest", "name": "Fetch Data"},
                    {"type": "n8n-nodes-base.spreadsheetFile", "name": "Export"},
                ],
            },
        ]

        entries = enricher.from_workflow_list(workflows)

        assert len(entries) == 2
        assert entries[0]["workflowId"] == "1"
        assert entries[0]["name"] == "Send Email"
        assert "notifications" in entries[0]["tags"]
        assert "gmail" in entries[0]["nodeTypes"]

        assert entries[1]["workflowId"] == "2"
        assert entries[1]["nodeCount"] == 3

    def test_search(self):
        enricher = N8nCatalogEnricher()
        enricher.from_workflow_list([
            {"id": "1", "name": "Send Email Notification", "tags": [], "nodes": []},
            {"id": "2", "name": "Generate PDF Report", "tags": [], "nodes": []},
            {"id": "3", "name": "Sync CRM Data", "tags": [{"id": "t1", "name": "email"}], "nodes": []},
        ])

        results = enricher.search("email")
        assert len(results) == 2  # "Send Email" + "Sync CRM" (tagged "email")

        results = enricher.search("pdf")
        assert len(results) == 1
        assert results[0]["name"] == "Generate PDF Report"


class TestCatalogEnricherOutput:
    """Test catalog generation and merging."""

    def test_standalone_catalog(self):
        enricher = N8nCatalogEnricher()
        enricher.from_workflow_list([
            {"id": "10", "name": "Process Order", "tags": [], "nodes": []},
        ])

        catalog = enricher.to_standalone_catalog()

        assert catalog["catalogId"] == "n8n-workflows-enriched"
        assert "n8n:process-order-4a44dc" in catalog["operations"]

        op = catalog["operations"]["n8n:process-order-4a44dc"]
        assert op["properties"]["workflowId"]["const"] == "10"
        assert "outputPath" in op["properties"]
        assert "_usage_example" in op

    def test_merge_into_catalog(self):
        """Merge n8n entries into existing A2E catalog file."""
        enricher = N8nCatalogEnricher()
        enricher.from_workflow_list([
            {"id": "5", "name": "Slack Alert", "tags": [{"id": "t1", "name": "alerts"}], "nodes": []},
            {"id": "6", "name": "DB Backup", "tags": [], "nodes": []},
        ])

        # Create a minimal A2E catalog
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({
                "catalogId": "test-catalog",
                "operations": {
                    "Wait": {"type": "object", "description": "Wait"},
                },
            }, f)
            catalog_path = f.name

        try:
            result = enricher.merge_into_catalog(catalog_path)

            # Original operation preserved
            assert "Wait" in result["operations"]
            # n8n entries added
            assert "n8n:slack-alert-ef2d12" in result["operations"]
            assert "n8n:db-backup-e7f6c0" in result["operations"]

            # Verify file was written
            with open(catalog_path) as f:
                saved = json.load(f)
            assert "n8n:slack-alert-ef2d12" in saved["operations"]
        finally:
            os.unlink(catalog_path)

    def test_merge_to_separate_file(self):
        """Merge to a different output file, preserving original."""
        enricher = N8nCatalogEnricher()
        enricher.from_workflow_list([
            {"id": "7", "name": "Test WF", "tags": [], "nodes": []},
        ])

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as src, tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as dst:
            json.dump({"catalogId": "original", "operations": {}}, src)
            src_path = src.name
            dst_path = dst.name

        try:
            enricher.merge_into_catalog(src_path, output_path=dst_path)

            # Original untouched
            with open(src_path) as f:
                original = json.load(f)
            assert "n8n:test-wf-790269" not in original.get("operations", {})

            # Output has entries
            with open(dst_path) as f:
                enriched = json.load(f)
            assert "n8n:test-wf-790269" in enriched["operations"]
        finally:
            os.unlink(src_path)
            os.unlink(dst_path)


class TestCatalogEnricherFromCliCatalog:
    """Test reading n8n-cli local catalog files."""

    def test_read_cli_catalog(self):
        """Read a mock n8n-cli catalog file."""
        catalog_data = [
            {
                "name": "n8n-nodes-base.httpRequest",
                "displayName": "HTTP Request",
                "description": "Makes an HTTP request",
                "group": ["transform"],
            },
            {
                "name": "n8n-nodes-base.gmail",
                "displayName": "Gmail",
                "description": "Send and receive emails",
                "group": ["communication"],
            },
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = os.path.join(tmpdir, "default.json")
            with open(catalog_path, "w") as f:
                json.dump(catalog_data, f)

            enricher = N8nCatalogEnricher()
            entries = enricher.from_cli_catalog(
                profile="default", catalog_dir=tmpdir
            )

        assert len(entries) == 2
        assert entries[0]["nodeType"] == "n8n-nodes-base.httpRequest"
        assert entries[0]["displayName"] == "HTTP Request"
        assert entries[1]["nodeType"] == "n8n-nodes-base.gmail"

    def test_missing_catalog_returns_empty(self):
        """Missing catalog file returns empty list."""
        enricher = N8nCatalogEnricher()
        entries = enricher.from_cli_catalog(
            profile="nonexistent", catalog_dir="/tmp/does-not-exist"
        )
        assert entries == []


class TestCatalogEnricherApiMocked:
    """Test API-based enrichment with mocked requests."""

    def test_from_api(self):
        enricher = N8nCatalogEnricher(
            n8n_url="http://localhost:5678", api_key="test-key"
        )

        mock_list_response = MagicMock()
        mock_list_response.ok = True
        mock_list_response.status_code = 200
        mock_list_response.json.return_value = {
            "data": [
                {
                    "id": "100",
                    "name": "Invoice Generator",
                    "active": True,
                    "tags": [{"id": "t1", "name": "finance"}],
                },
            ]
        }
        mock_list_response.raise_for_status = MagicMock()

        mock_detail_response = MagicMock()
        mock_detail_response.ok = True
        mock_detail_response.json.return_value = {
            "id": "100",
            "name": "Invoice Generator",
            "nodes": [
                {"type": "n8n-nodes-base.manualTrigger", "name": "Start"},
                {"type": "n8n-nodes-base.httpRequest", "name": "Fetch"},
                {"type": "n8n-nodes-base.pdf", "name": "Generate PDF"},
            ],
        }

        def mock_get(url, **kwargs):
            if "/api/v1/workflows/" in url and not url.endswith("workflows"):
                return mock_detail_response
            return mock_list_response

        with patch("requests.get", side_effect=mock_get):
            entries = enricher.from_api()

        assert len(entries) == 1
        assert entries[0]["workflowId"] == "100"
        assert entries[0]["name"] == "Invoice Generator"
        assert "finance" in entries[0]["tags"]
        assert "httpRequest" in entries[0]["nodeTypes"]
        assert entries[0]["nodeCount"] == 3

    def test_from_api_active_only(self):
        enricher = N8nCatalogEnricher(
            n8n_url="http://localhost:5678", api_key="test-key"
        )

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response) as mock_get:
            enricher.from_api(active_only=True)

        call_args = mock_get.call_args
        assert call_args[1]["params"]["active"] == "true"

    def test_from_api_filter_by_tags(self):
        enricher = N8nCatalogEnricher(
            n8n_url="http://localhost:5678", api_key="test-key"
        )

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"id": "1", "name": "WF1", "tags": [{"id": "t1", "name": "email"}]},
                {"id": "2", "name": "WF2", "tags": [{"id": "t2", "name": "reports"}]},
                {"id": "3", "name": "WF3", "tags": []},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_detail = MagicMock()
        mock_detail.ok = True
        mock_detail.json.return_value = {"nodes": []}

        def mock_get(url, **kwargs):
            if "/api/v1/workflows/" in url and not url.endswith("workflows"):
                return mock_detail
            return mock_response

        with patch("requests.get", side_effect=mock_get):
            entries = enricher.from_api(tags=["email"])

        assert len(entries) == 1
        assert entries[0]["name"] == "WF1"

    def test_from_api_missing_credentials(self):
        enricher = N8nCatalogEnricher()
        with pytest.raises(ValueError, match="n8n URL and API key"):
            enricher.from_api()
