"""
Example: A2E -> n8n Translation

Shows how to translate A2E workflows into n8n-compatible JSON
that can be imported directly into n8n or pushed via API.

This is a standalone example — does NOT require a running n8n instance
for the translation step.

Usage:
    python examples/a2e_to_n8n_example.py
"""

import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from n8n_bridge import A2EToN8nTranslator


def example_1_simple_wait():
    """Minimal example: single Wait operation."""
    print("=" * 60)
    print("Example 1: Simple Wait")
    print("=" * 60)

    a2e = json.dumps({
        "operations": [
            {"id": "pause", "op": "Wait", "duration": 3000},
        ],
    })

    translator = A2EToN8nTranslator()
    n8n_wf = translator.translate(a2e, name="Simple Wait")

    print(f"  A2E operations: 1")
    print(f"  n8n nodes:      {len(n8n_wf['nodes'])}")
    print(f"  Node types:     {[n['type'].split('.')[-1] for n in n8n_wf['nodes']]}")
    print()


def example_2_api_filter_pipeline():
    """Realistic pipeline: API call -> filter -> transform."""
    print("=" * 60)
    print("Example 2: API -> Filter -> Transform Pipeline")
    print("=" * 60)

    # Compact format
    a2e = json.dumps({
        "operations": [
            {
                "id": "fetch-users",
                "op": "ApiCall",
                "method": "GET",
                "url": "https://jsonplaceholder.typicode.com/users",
                "headers": {"Accept": "application/json"},
            },
            {
                "id": "active-only",
                "op": "FilterData",
                "input": "fetch-users",
                "conditions": [
                    {"field": "active", "operator": "==", "value": True}
                ],
            },
            {
                "id": "pick-fields",
                "op": "TransformData",
                "input": "active-only",
                "type": "pick",
                "config": {"fields": ["name", "email", "company"]},
            },
        ],
        "execute": "fetch-users",
    })

    translator = A2EToN8nTranslator()
    n8n_wf = translator.translate(a2e, name="User Pipeline")

    print(f"  A2E operations: 3")
    print(f"  n8n nodes:      {len(n8n_wf['nodes'])}")
    print(f"  Connections:    {list(n8n_wf['connections'].keys())}")
    print(f"  Warnings:       {n8n_wf['_a2e_translation']['warnings'] or 'None'}")
    print()

    # Show the translated JSON (importable into n8n)
    print("  n8n workflow JSON (first 20 lines):")
    json_str = json.dumps(
        {k: v for k, v in n8n_wf.items() if not k.startswith("_")},
        indent=2,
    )
    for i, line in enumerate(json_str.split("\n")[:20]):
        print(f"    {line}")
    print("    ...")
    print()


def example_3_jsonl_datetime():
    """JSONL format with DateTime operations."""
    print("=" * 60)
    print("Example 3: JSONL DateTime Workflow")
    print("=" * 60)

    a2e = (
        '{"operationUpdate": {"workflowId": "datetime-demo", "operations": ['
        '{"id": "get-utc", "operation": {"GetCurrentDateTime": {"timezone": "UTC", "format": "iso8601", "outputPath": "/workflow/utc_time"}}},'
        '{"id": "to-madrid", "operation": {"ConvertTimezone": {"inputPath": "/workflow/utc_time", "fromTimezone": "UTC", "toTimezone": "Europe/Madrid", "format": "iso8601", "outputPath": "/workflow/madrid_time"}}}'
        ']}}\n'
        '{"beginExecution": {"workflowId": "datetime-demo", "root": "get-utc"}}'
    )

    translator = A2EToN8nTranslator()
    n8n_wf = translator.translate(a2e, name="DateTime Demo")

    print(f"  Source format:  JSONL")
    print(f"  n8n nodes:      {len(n8n_wf['nodes'])}")
    for node in n8n_wf["nodes"]:
        print(f"    - {node['name']} ({node['type'].split('.')[-1]})")
    print()


def example_4_conditional_workflow():
    """Workflow with conditional branching."""
    print("=" * 60)
    print("Example 4: Conditional Branching")
    print("=" * 60)

    a2e = json.dumps({
        "operations": [
            {
                "id": "set-status",
                "op": "SetData",
                "value": {"status": "active", "score": "85"},
            },
            {
                "id": "check-status",
                "op": "Conditional",
                "input": "set-status",
                "path": "status",
                "operator": "==",
                "value": "active",
            },
            {
                "id": "calc-bonus",
                "op": "Calculate",
                "input": "set-status",
                "operation": "multiply",
            },
        ],
        "execute": "set-status",
    })

    translator = A2EToN8nTranslator()
    n8n_wf = translator.translate(a2e, name="Conditional Demo")

    print(f"  n8n nodes: {len(n8n_wf['nodes'])}")
    for node in n8n_wf["nodes"]:
        print(f"    - {node['name']} -> {node['type'].split('.')[-1]}")
    print()


def example_5_full_pipeline_output():
    """Export a complete n8n workflow to file."""
    print("=" * 60)
    print("Example 5: Full JSON Export")
    print("=" * 60)

    a2e = json.dumps({
        "operations": [
            {
                "id": "fetch",
                "op": "ApiCall",
                "method": "GET",
                "url": "https://api.example.com/orders",
                "headers": {"Authorization": "Bearer {{token}}"},
            },
            {
                "id": "filter-pending",
                "op": "FilterData",
                "input": "fetch",
                "conditions": [
                    {"field": "status", "operator": "==", "value": "pending"}
                ],
            },
            {
                "id": "sort-by-date",
                "op": "TransformData",
                "input": "filter-pending",
                "type": "sort",
                "config": {"field": "created_at", "reverse": True},
            },
            {
                "id": "add-timestamp",
                "op": "DateTime",
                "mode": "now",
                "timezone": "Europe/Madrid",
                "format": "iso8601",
            },
        ],
        "execute": "fetch",
    })

    translator = A2EToN8nTranslator()
    n8n_json = translator.translate_to_json(a2e, name="Order Processing")

    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "output_n8n_workflow.json",
    )
    with open(output_path, "w") as f:
        # Strip internal metadata for clean export
        wf = json.loads(n8n_json)
        clean = {k: v for k, v in wf.items() if not k.startswith("_")}
        json.dump(clean, f, indent=2)

    print(f"  Exported to: {output_path}")
    print(f"  Import this file into n8n via: Settings -> Import Workflow")
    print()


def example_6_supported_operations():
    """Show all supported A2E -> n8n operation mappings."""
    print("=" * 60)
    print("Supported A2E -> n8n Mappings")
    print("=" * 60)

    from n8n_bridge.node_mapping import NODE_MAPPING

    for op_name in sorted(NODE_MAPPING.keys()):
        entry = NODE_MAPPING[op_name]
        n8n_type = entry["n8n_type"].replace("n8n-nodes-base.", "")
        print(f"  {op_name:25s} -> {n8n_type}")
    print()


if __name__ == "__main__":
    print("\nA2E -> n8n Bridge Examples\n")

    example_1_simple_wait()
    example_2_api_filter_pipeline()
    example_3_jsonl_datetime()
    example_4_conditional_workflow()
    example_5_full_pipeline_output()
    example_6_supported_operations()

    print("Done. All examples completed successfully.")
