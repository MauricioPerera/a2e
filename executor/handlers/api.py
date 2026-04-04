"""
API-related operation handlers: ApiCall, ExecuteN8nWorkflow.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ApiHandlerMixin:
    """Mixin providing API call handlers for WorkflowExecutor."""

    async def _execute_api_call(self, config: Dict[str, Any]) -> Any:
        """Ejecuta una llamada a API"""
        import aiohttp

        method = config["method"]
        url = self._resolve_path(config["url"])
        headers = self._resolve_object(config.get("headers", {}))
        body = self._resolve_object(config.get("body")) if config.get("body") else None

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=body) as response:
                result = await response.json()

                output_path = config["outputPath"]
                self._set_data(output_path, result)

                return result

    async def _execute_n8n_workflow(self, config: Dict[str, Any]) -> Any:
        """
        Executes an existing n8n workflow by ID.

        Config:
            workflowId: str - n8n workflow ID to execute
            payload: dict (optional) - Input data to pass to the workflow
            n8nUrl: str (optional) - n8n instance URL (falls back to env N8N_URL)
            n8nApiKey: str (optional) - n8n API key (falls back to env N8N_API_KEY)
            outputPath: str - Where to store the execution result
            waitForCompletion: bool (optional, default True)
            timeoutMs: int (optional, default 30000)
        """
        import os
        import aiohttp

        workflow_id = config.get("workflowId")
        if not workflow_id:
            raise ValueError("ExecuteN8nWorkflow requires 'workflowId'")

        n8n_url = config.get("n8nUrl") or os.environ.get("N8N_URL", "")
        n8n_api_key = config.get("n8nApiKey") or os.environ.get("N8N_API_KEY", "")

        if not n8n_url:
            raise ValueError(
                "ExecuteN8nWorkflow requires n8n URL. "
                "Set 'n8nUrl' in config or N8N_URL environment variable."
            )
        if not n8n_api_key:
            raise ValueError(
                "ExecuteN8nWorkflow requires n8n API key. "
                "Set 'n8nApiKey' in config or N8N_API_KEY environment variable."
            )

        payload = config.get("payload", {})
        if isinstance(payload, str) and payload.startswith("/"):
            payload = self._get_data(payload) or {}

        timeout_ms = config.get("timeoutMs", 30000)
        output_path = config.get("outputPath")

        headers = {
            "X-N8N-API-KEY": n8n_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        base_url = n8n_url.rstrip("/")
        timeout = aiohttp.ClientTimeout(total=timeout_ms / 1000)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{base_url}/api/v1/workflows/{workflow_id}/run",
                headers=headers,
                json=payload,
            ) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise RuntimeError(
                        f"n8n execution failed (HTTP {response.status}): {error_text}"
                    )
                execution_data = await response.json()

            result = {
                "n8n_workflow_id": workflow_id,
                "execution_id": execution_data.get("id"),
                "status": execution_data.get("status", "unknown"),
                "finished": execution_data.get("finished", False),
                "data": execution_data.get("data"),
            }

            if execution_data.get("data") and isinstance(execution_data["data"], dict):
                result_data = execution_data["data"].get("resultData", {})
                run_data = result_data.get("runData", {})
                if run_data:
                    last_node = list(run_data.keys())[-1] if run_data else None
                    if last_node and run_data[last_node]:
                        last_output = run_data[last_node][-1]
                        if isinstance(last_output, dict) and "data" in last_output:
                            main_data = last_output["data"].get("main", [[]])
                            if main_data and main_data[0]:
                                result["output"] = [
                                    item.get("json", item)
                                    for item in main_data[0]
                                    if isinstance(item, dict)
                                ]

        if output_path:
            self._set_data(output_path, result)

        logger.info(
            f"ExecuteN8nWorkflow: workflow={workflow_id}, "
            f"execution={result.get('execution_id')}, "
            f"status={result.get('status')}"
        )

        return result
