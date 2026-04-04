"""
Data operation handlers: FilterData, TransformData, MergeData, StoreData, SetData.
"""

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class DataHandlerMixin:
    """Mixin providing data manipulation handlers for WorkflowExecutor."""

    def _execute_filter_data(self, config: Dict[str, Any]) -> List[Any]:
        """Filtra datos de un array"""
        input_path = config["inputPath"]
        data = self._get_data(input_path)

        if not isinstance(data, list):
            raise ValueError(f"FilterData requires array, got {type(data)}")

        conditions = config.get("conditions", [])
        filtered = data

        for condition in conditions:
            field = condition["field"]
            operator = condition["operator"]
            value = self._resolve_value(condition.get("value"))

            filtered = [
                item for item in filtered
                if self._evaluate_condition(item.get(field), operator, value)
            ]

        output_path = config["outputPath"]
        self._set_data(output_path, filtered)

        return filtered

    def _execute_transform_data(self, config: Dict[str, Any]) -> Any:
        """Transforma datos (map, sort, pick, flatten, group, unique, reverse, slice)"""
        input_path = config["inputPath"]
        transform_type = config["transform"]
        data = self._get_data(input_path)
        output_path = config["outputPath"]

        if transform_type == "map" and isinstance(data, list):
            fields = config.get("fields", [])
            if fields:
                data = [
                    {f: item.get(f) for f in fields if isinstance(item, dict)}
                    for item in data
                ]

        elif transform_type == "sort" and isinstance(data, list):
            sort_field = config.get("field")
            reverse = config.get("reverse", False)
            if sort_field:
                data = sorted(
                    data,
                    key=lambda x: x.get(sort_field, "") if isinstance(x, dict) else x,
                    reverse=reverse,
                )
            else:
                data = sorted(data, reverse=reverse)

        elif transform_type == "pick" and isinstance(data, dict):
            fields = config.get("fields", [])
            data = {k: v for k, v in data.items() if k in fields}

        elif transform_type == "flatten" and isinstance(data, list):
            flat = []
            for item in data:
                if isinstance(item, list):
                    flat.extend(item)
                else:
                    flat.append(item)
            data = flat

        elif transform_type == "group" and isinstance(data, list):
            group_field = config.get("field")
            if group_field:
                groups: Dict[str, list] = {}
                for item in data:
                    key = str(item.get(group_field, "other")) if isinstance(item, dict) else "other"
                    groups.setdefault(key, []).append(item)
                data = groups

        elif transform_type == "unique" and isinstance(data, list):
            seen = []
            unique = []
            for item in data:
                serialized = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item
                if serialized not in seen:
                    seen.append(serialized)
                    unique.append(item)
            data = unique

        elif transform_type == "reverse" and isinstance(data, list):
            data = list(reversed(data))

        elif transform_type == "slice" and isinstance(data, list):
            start = config.get("start", 0)
            end = config.get("end")
            data = data[start:end]

        self._set_data(output_path, data)
        return data

    def _execute_merge_data(self, config: Dict[str, Any]) -> Any:
        """Combina datos de multiples fuentes usando la estrategia indicada"""
        sources = config["sources"]
        strategy = config["strategy"]
        output_path = config["outputPath"]

        datasets = [self._get_data(src) for src in sources]

        if strategy == "concat":
            result = []
            for ds in datasets:
                if isinstance(ds, list):
                    result.extend(ds)
                elif ds is not None:
                    result.append(ds)

        elif strategy == "merge":
            result = {}
            for ds in datasets:
                if isinstance(ds, dict):
                    result.update(ds)
                elif isinstance(ds, list):
                    for i, item in enumerate(ds):
                        result[str(i)] = item

        elif strategy == "intersect":
            if all(isinstance(ds, list) for ds in datasets) and datasets:
                sets = []
                for ds in datasets:
                    s = set()
                    for item in ds:
                        s.add(json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item)
                    sets.append(s)
                common = sets[0]
                for s in sets[1:]:
                    common = common & s
                result = []
                for item in datasets[0]:
                    serialized = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item
                    if serialized in common:
                        result.append(item)
                        common.discard(serialized)
            else:
                result = {}

        elif strategy == "union":
            seen = set()
            result = []
            for ds in datasets:
                if isinstance(ds, list):
                    for item in ds:
                        serialized = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item
                        if serialized not in seen:
                            seen.add(serialized)
                            result.append(item)
                elif ds is not None:
                    serialized = json.dumps(ds, sort_keys=True) if isinstance(ds, (dict, list)) else ds
                    if serialized not in seen:
                        seen.add(serialized)
                        result.append(ds)
        else:
            raise ValueError(f"Unknown merge strategy: {strategy}")

        self._set_data(output_path, result)
        return result

    def _execute_store_data(self, config: Dict[str, Any]) -> bool:
        """Almacena datos en el workflow_state"""
        input_path = config["inputPath"]
        key = config["key"]
        data = self._get_data(input_path)

        self._set_data(f"/store/{key}", data)

        return True

    async def _execute_set_data(self, config):
        """Stores a literal value in the workflow data model."""
        value = config.get("value")
        output_path = config.get("outputPath")
        if output_path:
            self._set_data(output_path, value)
        return value
