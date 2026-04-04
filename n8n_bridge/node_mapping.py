"""
Mapping between A2E operation types and n8n node types.

Each entry defines:
  - n8n_type: The fully qualified n8n node type
  - type_version: n8n node version to target
  - translate: A callable (config) -> n8n_parameters dict
"""

import json
from typing import Any, Dict, Callable


def _translate_api_call(config: Dict[str, Any]) -> Dict[str, Any]:
    """ApiCall → n8n HTTP Request node."""
    params: Dict[str, Any] = {
        "method": config.get("method", "GET"),
        "url": config.get("url", ""),
    }
    headers = config.get("headers", {})
    if headers:
        params["sendHeaders"] = True
        params["headerParameters"] = {
            "parameters": [
                {"name": k, "value": v if isinstance(v, str) else str(v)}
                for k, v in headers.items()
                if not isinstance(v, dict)  # skip credentialRef
            ]
        }
    body = config.get("body")
    if body:
        params["sendBody"] = True
        params["bodyParameters"] = {
            "parameters": [
                {"name": k, "value": v if isinstance(v, str) else str(v)}
                for k, v in (body.items() if isinstance(body, dict) else [])
            ]
        }
    return params


def _translate_filter_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """FilterData → n8n Filter node."""
    conditions = config.get("conditions", [])
    operator_map = {
        "==": "equal", "!=": "notEqual",
        ">": "larger", "<": "smaller",
        ">=": "largerEqual", "<=": "smallerEqual",
        "contains": "contains", "startsWith": "startsWith",
        "endsWith": "endsWith",
    }
    n8n_conditions = []
    for cond in conditions:
        n8n_conditions.append({
            "leftValue": f"={{{{ $json.{cond.get('field', '')} }}}}",
            "rightValue": cond.get("value", ""),
            "operator": {
                "type": "string",
                "operation": operator_map.get(cond.get("operator", "=="), "equal"),
            },
        })
    return {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": ""},
            "conditions": n8n_conditions,
            "combinator": "and",
        },
    }


def _translate_transform_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """TransformData → n8n Code node with JS transform logic."""
    transform_type = config.get("type", "map")
    transform_config = config.get("config", {})

    code_templates = {
        "map": "return items.map(item => {{ {fields} }});",
        "sort": "return items.sort((a, b) => {{ const f = '{field}'; const r = {reverse} ? -1 : 1; return a.json[f] > b.json[f] ? r : -r; }});",
        "pick": "return items.map(item => {{ const picked = {{}}; {picks} return {{ json: picked }}; }});",
        "flatten": "return items.flatMap(item => Array.isArray(item.json) ? item.json.map(v => ({{ json: v }})) : [item]);",
        "unique": "const seen = new Set(); return items.filter(item => {{ const k = JSON.stringify(item.json); if (seen.has(k)) return false; seen.add(k); return true; }});",
        "reverse": "return items.reverse();",
        "group": "const groups = {{}}; items.forEach(item => {{ const k = item.json['{field}']; (groups[k] = groups[k] || []).push(item); }}); return Object.entries(groups).map(([k, v]) => ({{ json: {{ group: k, items: v.map(i => i.json) }} }}));",
        "slice": "return items.slice({start}, {end});",
    }

    if transform_type == "map":
        fields_str = ", ".join(
            f"json: {{ {json.dumps(f)}: item.json[{json.dumps(f)}] }}"
            for f in transform_config.get("fields", [])
        ) or "...item"
        code = f"return items.map(item => ({{ {fields_str} }}));"
    elif transform_type == "sort":
        safe_field = json.dumps(transform_config.get("field", "id"))
        code = f"return items.sort((a, b) => {{ const f = {safe_field}; const r = {'true' if transform_config.get('reverse') else 'false'} ? -1 : 1; return a.json[f] > b.json[f] ? r : -r; }});"
    elif transform_type == "pick":
        picks = " ".join(
            f"picked[{json.dumps(f)}] = item.json[{json.dumps(f)}];"
            for f in transform_config.get("fields", [])
        )
        code = code_templates["pick"].format(picks=picks)
    elif transform_type == "slice":
        start = transform_config.get("start", 0)
        end = transform_config.get("end", "undefined")
        if not isinstance(start, int):
            start = int(start)
        if end != "undefined" and not isinstance(end, int):
            end = int(end)
        code = code_templates["slice"].format(start=start, end=end)
    elif transform_type == "group":
        safe_field = json.dumps(transform_config.get("field", "id"))
        code = f"const groups = {{}}; items.forEach(item => {{ const k = item.json[{safe_field}]; (groups[k] = groups[k] || []).push(item); }}); return Object.entries(groups).map(([k, v]) => ({{ json: {{ group: k, items: v.map(i => i.json) }} }}));"
    else:
        code = code_templates.get(transform_type, "return items;")

    return {
        "jsCode": code,
        "mode": "runOnceForAllItems",
    }


def _translate_wait(config: Dict[str, Any]) -> Dict[str, Any]:
    """Wait → n8n Wait node."""
    duration_ms = config.get("duration", 1000)
    return {
        "amount": max(1, duration_ms / 1000),
        "unit": "seconds",
    }


def _translate_set_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """SetData → n8n Set node."""
    value = config.get("value")
    assignments = []
    if isinstance(value, dict):
        for k, v in value.items():
            assignments.append({"id": k, "name": k, "value": v, "type": "string"})
    else:
        assignments.append({
            "id": "value", "name": "value",
            "value": value if isinstance(value, str) else str(value),
            "type": "string",
        })
    return {
        "mode": "manual",
        "assignments": {"assignments": assignments},
    }


def _translate_conditional(config: Dict[str, Any]) -> Dict[str, Any]:
    """Conditional → n8n IF node."""
    operator_map = {
        "==": "equal", "!=": "notEqual",
        ">": "larger", "<": "smaller",
        "exists": "exists", "isEmpty": "empty",
    }
    return {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": ""},
            "conditions": [{
                "leftValue": f"={{{{ $json.{config.get('path', '')} }}}}",
                "rightValue": config.get("value", ""),
                "operator": {
                    "type": "string",
                    "operation": operator_map.get(config.get("operator", "=="), "equal"),
                },
            }],
            "combinator": "and",
        },
    }


def _translate_datetime(config: Dict[str, Any]) -> Dict[str, Any]:
    """DateTime → n8n Date & Time node."""
    mode = config.get("mode", "now")
    if mode == "now":
        return {
            "action": "format",
            "date": "={{ $now }}",
            "format": config.get("format", "iso8601"),
            "options": {"timezone": config.get("timezone", "UTC")},
        }
    elif mode == "convert":
        return {
            "action": "format",
            "date": f"={{{{ $json.value }}}}",
            "format": config.get("format", "iso8601"),
            "options": {"timezone": config.get("toTimezone", "UTC")},
        }
    else:  # calculate
        return {
            "action": "calculate",
            "date": f"={{{{ $json.value }}}}",
            "duration": config.get("amount", 0),
            "timeUnit": config.get("unit", "days"),
            "operation": "add" if config.get("amount", 0) >= 0 else "subtract",
        }


def _translate_get_current_datetime(config: Dict[str, Any]) -> Dict[str, Any]:
    """GetCurrentDateTime (legacy) → n8n Date & Time node."""
    return {
        "action": "format",
        "date": "={{ $now }}",
        "format": config.get("format", "iso8601"),
        "options": {"timezone": config.get("timezone", "UTC")},
    }


def _translate_convert_timezone(config: Dict[str, Any]) -> Dict[str, Any]:
    """ConvertTimezone (legacy) → n8n Date & Time node."""
    return {
        "action": "format",
        "date": "={{ $json.value }}",
        "format": config.get("format", "iso8601"),
        "options": {"timezone": config.get("toTimezone", "UTC")},
    }


def _translate_date_calculation(config: Dict[str, Any]) -> Dict[str, Any]:
    """DateCalculation (legacy) → n8n Date & Time node."""
    return {
        "action": "calculate",
        "date": "={{ $json.value }}",
        "duration": config.get("amount", config.get("days", config.get("hours", 0))),
        "timeUnit": config.get("unit", "days"),
        "operation": "add",
    }


def _translate_format_text(config: Dict[str, Any]) -> Dict[str, Any]:
    """FormatText → n8n Code node."""
    fmt_type = config.get("type", "template")
    if fmt_type == "template":
        template = config.get("template", "")
        safe_template = json.dumps(template)
        return {
            "jsCode": f"return items.map(item => ({{ json: {{ result: {safe_template} }} }}));",
            "mode": "runOnceForAllItems",
        }
    else:
        method_map = {
            "upper": "toUpperCase()", "lower": "toLowerCase()",
            "title": "split(' ').map(w => w[0].toUpperCase() + w.slice(1)).join(' ')",
            "capitalize": "charAt(0).toUpperCase() + s.slice(1)",
            "trim": "trim()",
        }
        method = method_map.get(fmt_type, "toString()")
        return {
            "jsCode": f"return items.map(item => ({{ json: {{ result: String(item.json.value).{method} }} }}));",
            "mode": "runOnceForAllItems",
        }


def _translate_extract_text(config: Dict[str, Any]) -> Dict[str, Any]:
    """ExtractText → n8n Code node."""
    pattern = config.get("pattern", "")
    safe_pattern = json.dumps(pattern)
    return {
        "jsCode": f"const re = new RegExp({safe_pattern}, 'g'); return items.map(item => ({{ json: {{ matches: String(item.json.value).match(re) || [] }} }}));",
        "mode": "runOnceForAllItems",
    }


def _translate_validate_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """ValidateData → n8n Code node."""
    vtype = config.get("type", "email")
    validators = {
        "email": r"/^[^@]+@[^@]+\.[^@]+$/",
        "url": r"/^https?:\/\/.+/",
        "number": r"/^-?\d+(\.\d+)?$/",
        "phone": r"/^\+?\d[\d\s-]{7,}$/",
    }
    if vtype == "custom":
        custom_pattern = config.get("pattern", ".*")
        safe_pattern = json.dumps(custom_pattern)
        regex_expr = f"new RegExp({safe_pattern})"
    else:
        regex_expr = validators.get(vtype, r"/.*/")
    return {
        "jsCode": f"return items.map(item => ({{ json: {{ valid: {regex_expr}.test(String(item.json.value)), value: item.json.value }} }}));",
        "mode": "runOnceForAllItems",
    }


def _translate_calculate(config: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate → n8n Code node."""
    operation = config.get("operation", "add")
    op_code = {
        "add": "a + b", "subtract": "a - b", "multiply": "a * b",
        "divide": "b !== 0 ? a / b : 0", "power": "Math.pow(a, b)",
        "modulo": "a % b", "round": "Math.round(a)",
        "ceil": "Math.ceil(a)", "floor": "Math.floor(a)",
        "abs": "Math.abs(a)", "max": "Math.max(a, b)",
        "min": "Math.min(a, b)",
    }
    expr = op_code.get(operation, "a + b")
    return {
        "jsCode": f"return items.map(item => {{ const a = Number(item.json.a || item.json.value || 0); const b = Number(item.json.b || 0); return {{ json: {{ result: {expr} }} }}; }});",
        "mode": "runOnceForAllItems",
    }


def _translate_encode_decode(config: Dict[str, Any]) -> Dict[str, Any]:
    """EncodeDecode → n8n Code node."""
    encoding = config.get("encoding", "base64")
    action = config.get("action", "encode")
    if encoding == "base64":
        if action == "encode":
            code = "Buffer.from(String(item.json.value)).toString('base64')"
        else:
            code = "Buffer.from(String(item.json.value), 'base64').toString()"
    elif encoding == "url":
        code = f"{'encodeURIComponent' if action == 'encode' else 'decodeURIComponent'}(String(item.json.value))"
    else:
        code = "String(item.json.value)"
    return {
        "jsCode": f"return items.map(item => ({{ json: {{ result: {code} }} }}));",
        "mode": "runOnceForAllItems",
    }


def _translate_merge_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """MergeData → n8n Merge node."""
    mode_map = {
        "concat": "append", "merge": "combineBySql",
        "intersect": "combineBySql", "union": "append",
    }
    return {
        "mode": mode_map.get(config.get("mode", "concat"), "append"),
    }


def _translate_store_data(config: Dict[str, Any]) -> Dict[str, Any]:
    """StoreData → n8n Set node (stores in workflow state)."""
    return {
        "mode": "manual",
        "assignments": {"assignments": [{
            "id": "stored",
            "name": config.get("key", "data"),
            "value": "={{ $json }}",
            "type": "string",
        }]},
    }


def _translate_loop(config: Dict[str, Any]) -> Dict[str, Any]:
    """Loop → n8n SplitInBatches node."""
    return {
        "batchSize": 1,
        "options": {},
    }


def _translate_execute_n8n_workflow(config: Dict[str, Any]) -> Dict[str, Any]:
    """ExecuteN8nWorkflow → n8n Execute Workflow node."""
    params: Dict[str, Any] = {
        "workflowId": config.get("workflowId", ""),
        "mode": "id",
    }
    payload = config.get("payload")
    if payload and isinstance(payload, dict):
        params["options"] = {
            "waitForSubWorkflow": config.get("waitForCompletion", True),
        }
    return params


# ─── Master mapping table ────────────────────────────────────────────

NodeMapEntry = Dict[str, Any]

NODE_MAPPING: Dict[str, NodeMapEntry] = {
    "ApiCall": {
        "n8n_type": "n8n-nodes-base.httpRequest",
        "type_version": 4.2,
        "translate": _translate_api_call,
    },
    "FilterData": {
        "n8n_type": "n8n-nodes-base.filter",
        "type_version": 2,
        "translate": _translate_filter_data,
    },
    "TransformData": {
        "n8n_type": "n8n-nodes-base.code",
        "type_version": 2,
        "translate": _translate_transform_data,
    },
    "StoreData": {
        "n8n_type": "n8n-nodes-base.set",
        "type_version": 3.4,
        "translate": _translate_store_data,
    },
    "Wait": {
        "n8n_type": "n8n-nodes-base.wait",
        "type_version": 1.1,
        "translate": _translate_wait,
    },
    "DateTime": {
        "n8n_type": "n8n-nodes-base.dateTime",
        "type_version": 2,
        "translate": _translate_datetime,
    },
    "GetCurrentDateTime": {
        "n8n_type": "n8n-nodes-base.dateTime",
        "type_version": 2,
        "translate": _translate_get_current_datetime,
    },
    "ConvertTimezone": {
        "n8n_type": "n8n-nodes-base.dateTime",
        "type_version": 2,
        "translate": _translate_convert_timezone,
    },
    "DateCalculation": {
        "n8n_type": "n8n-nodes-base.dateTime",
        "type_version": 2,
        "translate": _translate_date_calculation,
    },
    "SetData": {
        "n8n_type": "n8n-nodes-base.set",
        "type_version": 3.4,
        "translate": _translate_set_data,
    },
    "Conditional": {
        "n8n_type": "n8n-nodes-base.if",
        "type_version": 2,
        "translate": _translate_conditional,
    },
    "Loop": {
        "n8n_type": "n8n-nodes-base.splitInBatches",
        "type_version": 3,
        "translate": _translate_loop,
    },
    "MergeData": {
        "n8n_type": "n8n-nodes-base.merge",
        "type_version": 3,
        "translate": _translate_merge_data,
    },
    "FormatText": {
        "n8n_type": "n8n-nodes-base.code",
        "type_version": 2,
        "translate": _translate_format_text,
    },
    "ExtractText": {
        "n8n_type": "n8n-nodes-base.code",
        "type_version": 2,
        "translate": _translate_extract_text,
    },
    "ValidateData": {
        "n8n_type": "n8n-nodes-base.code",
        "type_version": 2,
        "translate": _translate_validate_data,
    },
    "Calculate": {
        "n8n_type": "n8n-nodes-base.code",
        "type_version": 2,
        "translate": _translate_calculate,
    },
    "EncodeDecode": {
        "n8n_type": "n8n-nodes-base.code",
        "type_version": 2,
        "translate": _translate_encode_decode,
    },
    "ExecuteN8nWorkflow": {
        "n8n_type": "n8n-nodes-base.executeWorkflow",
        "type_version": 1,
        "translate": _translate_execute_n8n_workflow,
    },
}
