"""
Flow control operation handlers: Wait, Loop, Conditional.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FlowHandlerMixin:
    """Mixin providing flow control handlers for WorkflowExecutor."""

    async def _execute_wait(self, config: Dict[str, Any]) -> None:
        """Espera un tiempo"""
        import asyncio
        duration = config["duration"]
        await asyncio.sleep(duration / 1000)

    async def _execute_loop(self, config: Dict[str, Any]) -> Any:
        """Itera sobre un array y ejecuta sub-operaciones por cada item"""
        input_path = config["inputPath"]
        operation_ids = config["operations"]
        output_path = config.get("outputPath")
        data = self._get_data(input_path)

        if not isinstance(data, list):
            raise ValueError(f"Loop input at {input_path} is not an array")

        results = []
        for index, item in enumerate(data):
            self._set_data("/loop/current", item)
            self._set_data("/loop/index", index)

            item_results = {}
            for op_id in operation_ids:
                if op_id not in self.operations:
                    logger.warning(f"Loop sub-operation {op_id} not found, skipping")
                    continue
                op = self.operations[op_id]
                operation_type = list(op.get("operation", {}).keys())[0]
                operation_config = op["operation"][operation_type]
                try:
                    result = await self._execute_operation(operation_type, operation_config)
                    item_results[op_id] = result
                except Exception as e:
                    logger.error(f"Error in loop iteration {index}, operation {op_id}: {e}")
                    item_results[op_id] = {"error": str(e)}

            results.append(item_results)

        if output_path:
            self._set_data(output_path, results)

        return results

    def _execute_conditional(self, config: Dict[str, Any]) -> Any:
        """Ejecuta operaciones condicionalmente basandose en una condicion"""
        condition = config["condition"]
        path = condition.get("path", "")
        operator = condition.get("operator", "==")
        expected_value = condition.get("value")

        actual_value = self._get_data(path)

        if operator == "exists":
            result = actual_value is not None
        elif operator == "isEmpty":
            result = actual_value is None or actual_value == "" or actual_value == [] or actual_value == {}
        else:
            result = self._evaluate_condition(actual_value, operator, expected_value)

        if result:
            target_op_id = config.get("ifTrue")
        else:
            target_op_id = config.get("ifFalse")

        if not target_op_id:
            return {"conditionResult": result, "executed": None}

        return {"conditionResult": result, "executeOperationId": target_op_id}
