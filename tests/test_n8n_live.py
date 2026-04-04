"""
Live integration tests against a running n8n instance.

These tests require:
  - n8n running at localhost:5678
  - API key configured in ~/.n8n-cli/config.json

Note: n8n Community Edition does not expose a workflow execution endpoint
via REST API v1. Tests cover CRUD operations, translation, catalog
enrichment, and CLI catalog reading. Execution tests are skipped.

Run with:
  pytest tests/test_n8n_live.py -v
"""

import json
import os
import pytest
import requests

# ─── Load n8n credentials from n8n-cli config ────────────────────────

N8N_CLI_CONFIG = os.path.expanduser("~/.n8n-cli/config.json")
N8N_URL = "http://localhost:5678"
N8N_API_KEY = ""

if os.path.exists(N8N_CLI_CONFIG):
    with open(N8N_CLI_CONFIG) as f:
        cli_config = json.load(f)
    default_profile = cli_config.get("default", "local")
    profile = cli_config.get("profiles", {}).get(default_profile, {})
    N8N_URL = profile.get("baseUrl", N8N_URL)
    N8N_API_KEY = profile.get("apiKey", "")


def n8n_is_reachable():
    try:
        r = requests.get(f"{N8N_URL}/healthz", timeout=3)
        return r.ok
    except Exception:
        return False


skip_if_no_n8n = pytest.mark.skipif(
    not n8n_is_reachable() or not N8N_API_KEY,
    reason="n8n not available or API key not configured",
)

HEADERS = {
    "X-N8N-API-KEY": N8N_API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def n8n_test_workflow():
    """Create a simple test workflow in n8n, yield its ID, then delete it."""
    workflow_payload = {
        "name": "A2E Live Test Workflow",
        "nodes": [
            {
                "parameters": {},
                "name": "When clicking 'Test workflow'",
                "type": "n8n-nodes-base.manualTrigger",
                "typeVersion": 1,
                "position": [250, 300],
            },
            {
                "parameters": {
                    "mode": "manual",
                    "assignments": {
                        "assignments": [
                            {
                                "id": "msg",
                                "name": "message",
                                "value": "Hello from A2E live test",
                                "type": "string",
                            },
                        ]
                    },
                },
                "name": "Set Test Data",
                "type": "n8n-nodes-base.set",
                "typeVersion": 3.4,
                "position": [500, 300],
            },
        ],
        "connections": {
            "When clicking 'Test workflow'": {
                "main": [
                    [{"node": "Set Test Data", "type": "main", "index": 0}]
                ]
            }
        },
        "settings": {"executionOrder": "v1"},
    }

    resp = requests.post(
        f"{N8N_URL}/api/v1/workflows",
        headers=HEADERS,
        json=workflow_payload,
        timeout=10,
    )
    resp.raise_for_status()
    created = resp.json()
    wf_id = created["id"]

    yield {"id": wf_id, "name": created["name"], "data": created}

    try:
        requests.delete(
            f"{N8N_URL}/api/v1/workflows/{wf_id}",
            headers=HEADERS,
            timeout=10,
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════
# 1. Direct n8n API tests (CRUD)
# ═══════════════════════════════════════════════════════════════════════


@skip_if_no_n8n
class TestN8nDirectAPI:
    """Verify n8n API is working correctly."""

    def test_health(self):
        r = requests.get(f"{N8N_URL}/healthz", timeout=5)
        assert r.ok
        assert r.json()["status"] == "ok"

    def test_list_workflows(self):
        r = requests.get(
            f"{N8N_URL}/api/v1/workflows", headers=HEADERS, timeout=10
        )
        assert r.ok
        data = r.json()
        workflows = data.get("data", data)
        assert isinstance(workflows, list)
        assert len(workflows) > 0

    def test_create_read_delete_workflow(self, n8n_test_workflow):
        """Full CRUD cycle: create, read, fixture handles delete."""
        wf_id = n8n_test_workflow["id"]

        # Read
        r = requests.get(
            f"{N8N_URL}/api/v1/workflows/{wf_id}",
            headers=HEADERS,
            timeout=10,
        )
        assert r.ok
        detail = r.json()
        assert detail["name"] == "A2E Live Test Workflow"
        assert len(detail["nodes"]) == 2

        # Verify node types
        node_types = [n["type"] for n in detail["nodes"]]
        assert "n8n-nodes-base.manualTrigger" in node_types
        assert "n8n-nodes-base.set" in node_types

        # Verify connections
        assert "When clicking 'Test workflow'" in detail["connections"]

    def test_list_executions(self):
        """Verify executions endpoint works (read-only)."""
        r = requests.get(
            f"{N8N_URL}/api/v1/executions?limit=5",
            headers=HEADERS,
            timeout=10,
        )
        assert r.ok
        data = r.json()
        assert "data" in data


# ═══════════════════════════════════════════════════════════════════════
# 2. N8nClient against real n8n
# ═══════════════════════════════════════════════════════════════════════


@skip_if_no_n8n
class TestN8nClientLive:
    """Test n8n_bridge.N8nClient against real n8n."""

    def test_health_check(self):
        from n8n_bridge.n8n_client import N8nClient

        client = N8nClient(N8N_URL, N8N_API_KEY)
        result = client.health_check()
        assert result["status"] == "healthy"

    def test_list_workflows(self):
        from n8n_bridge.n8n_client import N8nClient

        client = N8nClient(N8N_URL, N8N_API_KEY)
        workflows = client.list_workflows()
        assert isinstance(workflows, list)
        assert len(workflows) > 0

    def test_create_and_delete(self):
        from n8n_bridge.n8n_client import N8nClient

        client = N8nClient(N8N_URL, N8N_API_KEY)

        workflow = {
            "name": "N8nClient Live Test",
            "nodes": [
                {
                    "parameters": {},
                    "name": "Manual Trigger",
                    "type": "n8n-nodes-base.manualTrigger",
                    "typeVersion": 1,
                    "position": [250, 300],
                },
                {
                    "parameters": {
                        "mode": "manual",
                        "assignments": {
                            "assignments": [
                                {
                                    "id": "v",
                                    "name": "value",
                                    "value": "test-ok",
                                    "type": "string",
                                }
                            ]
                        },
                    },
                    "name": "Set",
                    "type": "n8n-nodes-base.set",
                    "typeVersion": 3.4,
                    "position": [500, 300],
                },
            ],
            "connections": {
                "Manual Trigger": {
                    "main": [
                        [{"node": "Set", "type": "main", "index": 0}]
                    ]
                }
            },
            "settings": {"executionOrder": "v1"},
        }

        created = client.create_workflow(workflow)
        wf_id = created["id"]
        assert wf_id

        # Verify it exists in list
        all_wfs = client.list_workflows()
        ids = [w["id"] for w in all_wfs]
        assert wf_id in ids

        # Cleanup
        assert client.delete_workflow(wf_id)


# ═══════════════════════════════════════════════════════════════════════
# 3. A2E -> n8n Translator against real n8n
# ═══════════════════════════════════════════════════════════════════════


@skip_if_no_n8n
class TestA2eToN8nTranslatorLive:
    """Translate A2E workflows and push them to real n8n."""

    def test_translate_and_create_simple(self):
        """A2E SetData + Wait -> translate -> create in n8n -> verify -> delete."""
        from n8n_bridge.translator import A2EToN8nTranslator
        from n8n_bridge.n8n_client import N8nClient

        a2e_workflow = json.dumps({
            "operations": [
                {
                    "id": "set-data",
                    "op": "SetData",
                    "value": {"source": "a2e", "test": "true"},
                },
                {
                    "id": "wait-brief",
                    "op": "Wait",
                    "duration": 100,
                },
            ],
            "execute": "set-data",
        })

        translator = A2EToN8nTranslator()
        n8n_wf = translator.translate(
            a2e_workflow, name="A2E Translated Live Test"
        )

        assert len(n8n_wf["nodes"]) == 3  # trigger + set + wait
        assert n8n_wf["_a2e_translation"]["warnings"] == []

        # Push to n8n (strip internal fields)
        client = N8nClient(N8N_URL, N8N_API_KEY)
        clean_wf = {k: v for k, v in n8n_wf.items() if not k.startswith("_")}
        created = client.create_workflow(clean_wf)
        wf_id = created["id"]
        assert wf_id

        try:
            # Verify in n8n
            workflows = client.list_workflows()
            wf_names = [w["name"] for w in workflows]
            assert "A2E Translated Live Test" in wf_names

            # Verify node structure
            detail_resp = requests.get(
                f"{N8N_URL}/api/v1/workflows/{wf_id}",
                headers=HEADERS,
                timeout=10,
            )
            detail = detail_resp.json()
            node_types = [n["type"] for n in detail["nodes"]]
            assert "n8n-nodes-base.manualTrigger" in node_types
            assert "n8n-nodes-base.set" in node_types
            assert "n8n-nodes-base.wait" in node_types

            # Verify connections chain: trigger -> set -> wait
            assert len(detail["connections"]) >= 2

        finally:
            client.delete_workflow(wf_id)

    def test_translate_complex_pipeline(self):
        """Multi-op pipeline: API call + filter + DateTime."""
        from n8n_bridge.translator import A2EToN8nTranslator
        from n8n_bridge.n8n_client import N8nClient

        a2e_workflow = json.dumps({
            "operations": [
                {
                    "id": "fetch",
                    "op": "ApiCall",
                    "method": "GET",
                    "url": "https://jsonplaceholder.typicode.com/users",
                },
                {
                    "id": "filter",
                    "op": "FilterData",
                    "input": "fetch",
                    "conditions": [
                        {"field": "id", "operator": "<", "value": 5}
                    ],
                },
                {
                    "id": "timestamp",
                    "op": "DateTime",
                    "mode": "now",
                    "timezone": "Europe/Madrid",
                },
            ],
            "execute": "fetch",
        })

        translator = A2EToN8nTranslator()
        n8n_wf = translator.translate(
            a2e_workflow, name="A2E Complex Pipeline Live Test"
        )

        assert len(n8n_wf["nodes"]) == 4  # trigger + http + filter + datetime

        client = N8nClient(N8N_URL, N8N_API_KEY)
        clean_wf = {k: v for k, v in n8n_wf.items() if not k.startswith("_")}
        created = client.create_workflow(clean_wf)
        wf_id = created["id"]

        try:
            detail_resp = requests.get(
                f"{N8N_URL}/api/v1/workflows/{wf_id}",
                headers=HEADERS,
                timeout=10,
            )
            detail = detail_resp.json()
            node_types = sorted(
                n["type"].replace("n8n-nodes-base.", "")
                for n in detail["nodes"]
            )
            assert "dateTime" in node_types
            assert "filter" in node_types
            assert "httpRequest" in node_types
            assert "manualTrigger" in node_types

            # Verify connections: 3 links (trigger->http, http->filter, filter->dt)
            assert len(detail["connections"]) >= 3

        finally:
            client.delete_workflow(wf_id)

    def test_translate_jsonl_datetime_workflow(self):
        """Translate JSONL format with legacy DateTime operations."""
        from n8n_bridge.translator import A2EToN8nTranslator
        from n8n_bridge.n8n_client import N8nClient

        a2e = (
            '{"operationUpdate": {"workflowId": "dt", "operations": ['
            '{"id": "utc", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/utc"}}},'
            '{"id": "madrid", "operation": {"ConvertTimezone": {"inputPath": "/workflow/utc", "fromTimezone": "UTC", "toTimezone": "Europe/Madrid", "format": "iso8601", "outputPath": "/workflow/madrid"}}}'
            ']}}\n'
            '{"beginExecution": {"workflowId": "dt", "root": "utc"}}'
        )

        translator = A2EToN8nTranslator()
        n8n_wf = translator.translate(a2e, name="A2E JSONL DateTime Live")

        # 3 nodes: trigger + 2 dateTime
        assert len(n8n_wf["nodes"]) == 3
        dt_nodes = [
            n for n in n8n_wf["nodes"]
            if n["type"] == "n8n-nodes-base.dateTime"
        ]
        assert len(dt_nodes) == 2

        client = N8nClient(N8N_URL, N8N_API_KEY)
        clean_wf = {k: v for k, v in n8n_wf.items() if not k.startswith("_")}
        created = client.create_workflow(clean_wf)
        wf_id = created["id"]

        try:
            detail_resp = requests.get(
                f"{N8N_URL}/api/v1/workflows/{wf_id}",
                headers=HEADERS,
                timeout=10,
            )
            assert detail_resp.ok
            detail = detail_resp.json()
            assert detail["name"] == "A2E JSONL DateTime Live"
        finally:
            client.delete_workflow(wf_id)


# ═══════════════════════════════════════════════════════════════════════
# 4. Catalog Enricher against real n8n
# ═══════════════════════════════════════════════════════════════════════


@skip_if_no_n8n
class TestCatalogEnricherLive:
    """Test N8nCatalogEnricher against real n8n instance."""

    def test_from_api_real(self):
        from n8n_bridge.catalog_enricher import N8nCatalogEnricher

        enricher = N8nCatalogEnricher(n8n_url=N8N_URL, api_key=N8N_API_KEY)
        entries = enricher.from_api()

        assert len(entries) > 0
        for entry in entries:
            assert "workflowId" in entry
            assert "name" in entry
            assert "description" in entry
            assert "nodeTypes" in entry
            assert entry["source"] == "n8n-api"

    def test_from_api_active_only(self):
        from n8n_bridge.catalog_enricher import N8nCatalogEnricher

        enricher = N8nCatalogEnricher(n8n_url=N8N_URL, api_key=N8N_API_KEY)
        active_entries = enricher.from_api(active_only=True)

        all_enricher = N8nCatalogEnricher(n8n_url=N8N_URL, api_key=N8N_API_KEY)
        all_entries = all_enricher.from_api()

        assert len(active_entries) <= len(all_entries)
        for entry in active_entries:
            assert entry["active"] is True

    def test_standalone_catalog_from_real_n8n(self):
        from n8n_bridge.catalog_enricher import N8nCatalogEnricher

        enricher = N8nCatalogEnricher(n8n_url=N8N_URL, api_key=N8N_API_KEY)
        enricher.from_api()

        catalog = enricher.to_standalone_catalog()
        assert catalog["catalogId"] == "n8n-workflows-enriched"
        assert len(catalog["operations"]) > 0

        for key, op in catalog["operations"].items():
            assert key.startswith("n8n:")
            assert "workflowId" in op["properties"]
            assert "outputPath" in op["properties"]

    def test_search_real_workflows(self):
        from n8n_bridge.catalog_enricher import N8nCatalogEnricher

        enricher = N8nCatalogEnricher(n8n_url=N8N_URL, api_key=N8N_API_KEY)
        enricher.from_api()

        results = enricher.search("webhook")
        assert len(results) >= 1

    def test_merge_into_temp_catalog(self):
        """Merge real n8n workflows into a temp catalog file."""
        import tempfile
        from n8n_bridge.catalog_enricher import N8nCatalogEnricher

        enricher = N8nCatalogEnricher(n8n_url=N8N_URL, api_key=N8N_API_KEY)
        enricher.from_api(active_only=True)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({
                "catalogId": "test",
                "operations": {"Wait": {"type": "object", "description": "Wait"}},
            }, f)
            path = f.name

        try:
            result = enricher.merge_into_catalog(path)
            assert "Wait" in result["operations"]
            # Active n8n workflows should be present
            n8n_keys = [k for k in result["operations"] if k.startswith("n8n:")]
            assert len(n8n_keys) >= 1
        finally:
            os.unlink(path)


# ═══════════════════════════════════════════════════════════════════════
# 5. n8n-cli catalog file
# ═══════════════════════════════════════════════════════════════════════


@skip_if_no_n8n
class TestCliCatalogLive:
    """Test reading the actual n8n-cli catalog file."""

    def test_read_local_catalog(self):
        from n8n_bridge.catalog_enricher import N8nCatalogEnricher

        catalog_dir = os.path.expanduser("~/.n8n-cli/catalog")
        if not os.path.exists(os.path.join(catalog_dir, "local.json")):
            pytest.skip("n8n-cli catalog not found")

        enricher = N8nCatalogEnricher()
        entries = enricher.from_cli_catalog(
            profile="local", catalog_dir=catalog_dir
        )

        assert len(entries) > 0
        for entry in entries:
            assert "nodeType" in entry
            assert "displayName" in entry
            assert entry["source"] == "n8n-cli-catalog"
