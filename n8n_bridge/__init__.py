"""
A2E <-> n8n Bridge

Three capabilities:
  1. Translator: A2E workflow -> n8n workflow JSON (Option 1)
  2. ExecuteN8nWorkflow: invoke n8n workflows from within A2E (Option 2)
  3. Catalog Enricher: n8n workflows -> A2E catalog entries (Option 3)

This is a standalone module that does NOT modify the original A2E executor
(except for registering ExecuteN8nWorkflow in OPERATION_HANDLERS).
"""

from .translator import A2EToN8nTranslator
from .node_mapping import NODE_MAPPING
from .catalog_enricher import N8nCatalogEnricher

__all__ = ["A2EToN8nTranslator", "NODE_MAPPING", "N8nCatalogEnricher"]
