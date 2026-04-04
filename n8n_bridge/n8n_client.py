"""
Minimal n8n API client for pushing translated workflows.

Uses the same REST API v1 pattern as agent-shell's N8nApiAdapter,
but in Python. Designed for optional use — the translator works
standalone without this client.

Requires: pip install requests (or use aiohttp for async)
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class N8nClient:
    """
    Simple n8n REST API v1 client.

    Usage:
        client = N8nClient("http://localhost:5678", api_key="your-key")
        wf = client.create_workflow(translated_workflow)
        result = client.execute_workflow(wf["id"])
    """

    def __init__(self, base_url: str, api_key: str):
        if not HAS_REQUESTS:
            raise ImportError(
                "requests library required for N8nClient. "
                "Install with: pip install requests"
            )
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-N8N-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def health_check(self) -> Dict[str, str]:
        """Check n8n instance health."""
        try:
            resp = requests.get(
                f"{self.base_url}/healthz",
                headers={"Accept": "application/json"},
                timeout=5,
            )
            if resp.ok:
                return {"status": "healthy"}
            return {"status": "unhealthy", "code": str(resp.status_code)}
        except requests.RequestException as e:
            return {"status": "unreachable", "error": str(e)}

    def list_workflows(
        self, active: Optional[bool] = None, *, limit: int = 250
    ) -> List[Dict[str, Any]]:
        """List all workflows, handling pagination automatically."""
        params: Dict[str, Any] = {"limit": limit}
        if active is not None:
            params["active"] = str(active).lower()

        all_workflows: List[Dict[str, Any]] = []
        while True:
            resp = requests.get(
                f"{self.base_url}/api/v1/workflows",
                headers=self.headers,
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, dict):
                all_workflows.extend(data.get("data", []))
                next_cursor = data.get("nextCursor")
                if not next_cursor:
                    break
                params["cursor"] = next_cursor
            else:
                all_workflows.extend(data)
                break

        return all_workflows

    def create_workflow(
        self, workflow: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new workflow in n8n.

        Args:
            workflow: n8n workflow dict (as produced by A2EToN8nTranslator).

        Returns:
            Created workflow dict with assigned ID.
        """
        # Strip internal metadata
        payload = {
            k: v for k, v in workflow.items()
            if not k.startswith("_")
        }
        resp = requests.post(
            f"{self.base_url}/api/v1/workflows",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def update_workflow(
        self, workflow_id: str, workflow: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing workflow."""
        payload = {
            k: v for k, v in workflow.items()
            if not k.startswith("_")
        }
        resp = requests.put(
            f"{self.base_url}/api/v1/workflows/{workflow_id}",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def execute_workflow(
        self, workflow_id: str, payload: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a workflow by ID."""
        resp = requests.post(
            f"{self.base_url}/api/v1/workflows/{workflow_id}/run",
            headers=self.headers,
            json=payload or {},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    def activate_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """Activate a workflow."""
        resp = requests.post(
            f"{self.base_url}/api/v1/workflows/{workflow_id}/activate",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        resp = requests.delete(
            f"{self.base_url}/api/v1/workflows/{workflow_id}",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return True


class A2EToN8nPipeline:
    """
    End-to-end pipeline: A2E workflow → translate → push to n8n → execute.

    Usage:
        from n8n_bridge import A2EToN8nTranslator
        from n8n_bridge.n8n_client import A2EToN8nPipeline

        pipeline = A2EToN8nPipeline(
            n8n_url="http://localhost:5678",
            n8n_api_key="your-key",
        )
        result = pipeline.run(a2e_workflow_str, execute=True)
    """

    def __init__(self, n8n_url: str, n8n_api_key: str):
        from .translator import A2EToN8nTranslator
        self.translator = A2EToN8nTranslator()
        self.client = N8nClient(n8n_url, n8n_api_key)

    def run(
        self,
        a2e_workflow: str,
        *,
        name: Optional[str] = None,
        execute: bool = False,
        activate: bool = False,
    ) -> Dict[str, Any]:
        """
        Full pipeline: translate → create → optionally execute.

        Returns:
            Dict with translation_warnings, created_workflow,
            and optionally execution_result.
        """
        # 1. Translate
        n8n_wf = self.translator.translate(a2e_workflow, name=name)
        warnings = n8n_wf.pop("_a2e_translation", {}).get("warnings", [])

        # 2. Create in n8n
        created = self.client.create_workflow(n8n_wf)
        workflow_id = created.get("id")

        result = {
            "translation_warnings": warnings,
            "created_workflow": {
                "id": workflow_id,
                "name": created.get("name"),
                "node_count": len(created.get("nodes", [])),
            },
        }

        # 3. Activate if requested
        if activate and workflow_id:
            self.client.activate_workflow(workflow_id)
            result["activated"] = True

        # 4. Execute if requested
        if execute and workflow_id:
            execution = self.client.execute_workflow(workflow_id)
            result["execution"] = {
                "id": execution.get("id"),
                "status": execution.get("status"),
                "finished": execution.get("finished"),
            }

        return result
