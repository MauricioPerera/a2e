"""
A2E Catalog Enricher from n8n

Reads n8n workflows (via API or n8n-cli catalog files) and generates
A2E-compatible ExecuteN8nWorkflow operation entries. This allows A2E agents
to discover and invoke existing n8n workflows as native operations.

Two data sources:
  1. n8n REST API v1 — queries live instance for workflow list + details
  2. n8n-cli catalog files — reads local ~/.n8n-cli/catalog/{profile}.json

The enriched catalog can be merged into workflow_catalog.json or used
as a standalone discovery layer.
"""

import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _atomic_write_json(filepath: str, data: Any, indent: int = 2) -> None:
    """Write JSON atomically using temp file + rename."""
    dir_name = os.path.dirname(os.path.abspath(filepath))
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".tmp", dir=dir_name,
        delete=False, encoding="utf-8"
    ) as tmp_f:
        json.dump(data, tmp_f, indent=indent, ensure_ascii=False)
        tmp_path = tmp_f.name
    os.replace(tmp_path, filepath)


class N8nCatalogEnricher:
    """
    Enriches the A2E operation catalog with n8n workflow entries.

    Each n8n workflow becomes an ExecuteN8nWorkflow operation with
    pre-filled workflowId and descriptive metadata from n8n.

    Usage:
        enricher = N8nCatalogEnricher(n8n_url="http://localhost:5678", api_key="key")
        entries = enricher.from_api()
        enricher.merge_into_catalog("workflow_catalog.json")
    """

    def __init__(
        self,
        n8n_url: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.n8n_url = (n8n_url or os.environ.get("N8N_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("N8N_API_KEY", "")
        self._entries: List[Dict[str, Any]] = []

    # ─── Source 1: n8n REST API ───────────────────────────────────────

    def from_api(
        self,
        *,
        active_only: bool = False,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch workflows from n8n API and generate A2E catalog entries.

        Args:
            active_only: Only include active workflows.
            tags: Filter by tag names (if supported by instance).

        Returns:
            List of enriched catalog entries.
        """
        if not self.n8n_url or not self.api_key:
            raise ValueError(
                "n8n URL and API key required. Set via constructor or "
                "N8N_URL / N8N_API_KEY environment variables."
            )

        import requests

        headers = {
            "X-N8N-API-KEY": self.api_key,
            "Accept": "application/json",
        }

        # Fetch workflow list
        params = {}
        if active_only:
            params["active"] = "true"

        resp = requests.get(
            f"{self.n8n_url}/api/v1/workflows",
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        workflows = data.get("data", data) if isinstance(data, dict) else data

        # Fetch details for each workflow
        entries = []
        for wf in workflows:
            wf_id = wf.get("id", "")
            wf_name = wf.get("name", f"workflow-{wf_id}")
            wf_tags = [t["name"] for t in wf.get("tags", []) if isinstance(t, dict)]

            # Filter by tags if specified
            if tags and not any(t in wf_tags for t in tags):
                continue

            # Try to get workflow details for richer metadata
            nodes_info = []
            try:
                detail_resp = requests.get(
                    f"{self.n8n_url}/api/v1/workflows/{wf_id}",
                    headers=headers,
                    timeout=10,
                )
                if detail_resp.ok:
                    detail = detail_resp.json()
                    nodes_info = [
                        {"type": n.get("type", ""), "name": n.get("name", "")}
                        for n in detail.get("nodes", [])
                    ]
            except Exception:
                pass

            entry = self._build_entry(wf_id, wf_name, wf_tags, nodes_info, wf)
            entries.append(entry)

        self._entries = entries
        logger.info(f"Enriched catalog with {len(entries)} n8n workflows from API")
        return entries

    # ─── Source 2: n8n-cli catalog files ──────────────────────────────

    def from_cli_catalog(
        self,
        profile: str = "default",
        catalog_dir: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read n8n-cli local catalog and generate A2E entries.

        n8n-cli stores node catalogs at ~/.n8n-cli/catalog/{profile}.json
        These contain the full node type registry for the n8n instance.

        Args:
            profile: n8n-cli profile name (default: "default").
            catalog_dir: Override catalog directory path.

        Returns:
            List of node type entries (for discovery, not direct execution).
        """
        if catalog_dir:
            catalog_path = Path(catalog_dir) / f"{profile}.json"
        else:
            catalog_path = Path.home() / ".n8n-cli" / "catalog" / f"{profile}.json"

        if not catalog_path.exists():
            logger.warning(f"n8n-cli catalog not found at {catalog_path}")
            return []

        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog_data = json.load(f)

        # n8n-cli catalog structure: array of node type objects
        # Each has: name, displayName, description, group, version, defaults, etc.
        nodes = catalog_data if isinstance(catalog_data, list) else catalog_data.get("nodes", [])

        entries = []
        for node in nodes:
            node_type = node.get("name", "")
            display_name = node.get("displayName", node_type)
            description = node.get("description", "")
            group = node.get("group", [])

            entry = {
                "source": "n8n-cli-catalog",
                "profile": profile,
                "nodeType": node_type,
                "displayName": display_name,
                "description": description,
                "group": group if isinstance(group, list) else [group],
                "n8nType": node_type,
            }
            entries.append(entry)

        self._entries = entries
        logger.info(
            f"Loaded {len(entries)} n8n node types from cli catalog ({profile})"
        )
        return entries

    # ─── Source 3: From workflow list (no API needed) ─────────────────

    def from_workflow_list(
        self, workflows: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate entries from a pre-fetched workflow list.
        Useful when you already have workflows from n8n-cli or another source.

        Args:
            workflows: List of workflow dicts with at least 'id' and 'name'.
        """
        entries = []
        for wf in workflows:
            entry = self._build_entry(
                wf_id=wf.get("id", ""),
                wf_name=wf.get("name", ""),
                wf_tags=[t["name"] for t in wf.get("tags", []) if isinstance(t, dict)],
                nodes_info=[
                    {"type": n.get("type", ""), "name": n.get("name", "")}
                    for n in wf.get("nodes", [])
                ],
                raw=wf,
            )
            entries.append(entry)

        self._entries = entries
        return entries

    # ─── Catalog operations ───────────────────────────────────────────

    def merge_into_catalog(
        self,
        catalog_path: str,
        *,
        namespace: str = "n8n",
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Merge enriched entries into an A2E workflow_catalog.json.

        Each n8n workflow becomes an ExecuteN8nWorkflow operation
        with a namespaced key like "n8n:send-email" or "n8n:12345".

        Args:
            catalog_path: Path to workflow_catalog.json.
            namespace: Prefix for operation keys (default: "n8n").
            output_path: Write to different file (default: overwrite catalog_path).

        Returns:
            The updated catalog dict.
        """
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        operations = catalog.get("operations", {})

        for entry in self._entries:
            op_key = self._make_operation_key(entry, namespace)
            operations[op_key] = self._entry_to_catalog_operation(entry)

        catalog["operations"] = operations

        target = output_path or catalog_path
        _atomic_write_json(target, catalog)

        logger.info(
            f"Merged {len(self._entries)} n8n entries into {target}"
        )
        return catalog

    def to_standalone_catalog(self, namespace: str = "n8n") -> Dict[str, Any]:
        """
        Generate a standalone catalog dict (without merging).

        Returns:
            A2E-format catalog with only n8n workflow entries.
        """
        operations = {}
        for entry in self._entries:
            op_key = self._make_operation_key(entry, namespace)
            operations[op_key] = self._entry_to_catalog_operation(entry)

        return {
            "catalogId": "n8n-workflows-enriched",
            "description": (
                "Auto-generated A2E catalog from n8n workflows. "
                "Each entry maps to an ExecuteN8nWorkflow operation."
            ),
            "source": {
                "n8n_url": self.n8n_url or None,
                "workflow_count": len(self._entries),
            },
            "operations": operations,
        }

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search enriched entries by name, tags, or description.

        Args:
            query: Search term (case-insensitive substring match).

        Returns:
            Matching entries.
        """
        q = query.lower()
        results = []
        for entry in self._entries:
            searchable = " ".join([
                entry.get("name", ""),
                entry.get("description", ""),
                " ".join(entry.get("tags", [])),
                " ".join(entry.get("nodeTypes", [])),
            ]).lower()
            if q in searchable:
                results.append(entry)
        return results

    @property
    def entries(self) -> List[Dict[str, Any]]:
        """Current enriched entries."""
        return self._entries

    # ─── Internal helpers ─────────────────────────────────────────────

    def _build_entry(
        self,
        wf_id: str,
        wf_name: str,
        wf_tags: List[str],
        nodes_info: List[Dict],
        raw: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a normalized entry from workflow data."""
        # Extract node types for description
        node_types = list(set(
            n.get("type", "").replace("n8n-nodes-base.", "")
            for n in nodes_info
            if n.get("type")
        ))

        # Build human-readable description
        desc_parts = [f"n8n workflow: {wf_name}"]
        if node_types:
            desc_parts.append(f"Nodes: {', '.join(sorted(node_types))}")
        if wf_tags:
            desc_parts.append(f"Tags: {', '.join(wf_tags)}")

        return {
            "source": "n8n-api",
            "workflowId": str(wf_id),
            "name": wf_name,
            "description": ". ".join(desc_parts),
            "tags": wf_tags,
            "nodeTypes": node_types,
            "nodeCount": len(nodes_info),
            "active": raw.get("active", False),
            "createdAt": raw.get("createdAt"),
            "updatedAt": raw.get("updatedAt"),
        }

    def _make_operation_key(self, entry: Dict, namespace: str) -> str:
        """Generate catalog operation key."""
        wf_id = entry.get("workflowId", "")
        name = entry.get("name", wf_id)
        # Sanitize name for use as key
        safe_name = (
            name.lower()
            .replace(" ", "-")
            .replace("_", "-")
        )
        # Remove non-alphanumeric except hyphens
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "-")
        safe_name = safe_name.strip("-") or wf_id
        # Append short hash of workflowId to prevent collisions
        suffix = hashlib.sha256(str(wf_id).encode()).hexdigest()[:6]
        return f"{namespace}:{safe_name}-{suffix}"

    def _entry_to_catalog_operation(self, entry: Dict) -> Dict[str, Any]:
        """Convert an enriched entry to A2E catalog operation format."""
        return {
            "type": "object",
            "description": entry.get("description", ""),
            "_n8n_source": {
                "workflowId": entry.get("workflowId"),
                "nodeTypes": entry.get("nodeTypes", []),
                "tags": entry.get("tags", []),
            },
            "properties": {
                "workflowId": {
                    "type": "string",
                    "const": entry.get("workflowId"),
                    "description": f"n8n workflow ID (pre-filled: {entry.get('workflowId')})"
                },
                "payload": {
                    "type": ["object", "string"],
                    "description": "Input data for the workflow. Object literal or path to data model."
                },
                "outputPath": {
                    "type": "string",
                    "description": "Path to store execution result"
                },
            },
            "required": ["workflowId", "outputPath"],
            "_usage_example": {
                "id": f"run-{entry.get('workflowId', 'xxx')}",
                "operation": {
                    "ExecuteN8nWorkflow": {
                        "workflowId": entry.get("workflowId"),
                        "payload": {},
                        "outputPath": f"/workflow/n8n_result"
                    }
                }
            },
        }
