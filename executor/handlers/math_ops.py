"""
Math operation handler: Calculate.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MathHandlerMixin:
    """Mixin providing math calculation handler for WorkflowExecutor."""

    def _execute_calculate(self, config: Dict[str, Any]) -> Any:
        """Realiza calculos matematicos"""
        import math

        input_path = config["inputPath"]
        operation = config["operation"]
        operand = config.get("operand")
        precision = config.get("precision", 2)
        output_path = config["outputPath"]

        input_value = self._get_data(input_path)

        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")

        if operand is not None:
            if isinstance(operand, str) and operand.startswith("/"):
                operand = self._get_data(operand)
            if isinstance(operand, str):
                try:
                    operand = float(operand)
                except ValueError:
                    raise ValueError(f"Cannot convert operand '{operand}' to number")

        if operation in ["sum", "average"]:
            if isinstance(input_value, list):
                numbers = []
                for x in input_value:
                    if isinstance(x, (int, float)):
                        numbers.append(float(x))
                    elif isinstance(x, str):
                        try:
                            numbers.append(float(x))
                        except ValueError:
                            pass

                if operation == "sum":
                    result = sum(numbers)
                else:
                    result = sum(numbers) / len(numbers) if numbers else 0

                self._set_data(output_path, result)
                return result
            else:
                if isinstance(input_value, str):
                    try:
                        input_value = float(input_value)
                    except ValueError:
                        raise ValueError(f"Cannot convert '{input_value}' to number")

                result = float(input_value)
                self._set_data(output_path, result)
                return result

        if isinstance(input_value, str):
            try:
                input_value = float(input_value)
            except ValueError:
                raise ValueError(f"Cannot convert '{input_value}' to number")

        if not isinstance(input_value, (int, float)):
            raise ValueError(f"Input must be a number, got {type(input_value)}")

        if operation == "add":
            if operand is None:
                raise ValueError("operand is required for 'add' operation")
            result = input_value + operand
        elif operation == "subtract":
            if operand is None:
                raise ValueError("operand is required for 'subtract' operation")
            result = input_value - operand
        elif operation == "multiply":
            if operand is None:
                raise ValueError("operand is required for 'multiply' operation")
            result = input_value * operand
        elif operation == "divide":
            if operand is None:
                raise ValueError("operand is required for 'divide' operation")
            if operand == 0:
                raise ValueError("Division by zero")
            result = input_value / operand
        elif operation == "power":
            if operand is None:
                raise ValueError("operand is required for 'power' operation")
            result = input_value ** operand
        elif operation == "modulo":
            if operand is None:
                raise ValueError("operand is required for 'modulo' operation")
            result = input_value % operand
        elif operation == "round":
            result = round(input_value, int(precision))
        elif operation == "ceil":
            result = math.ceil(input_value)
        elif operation == "floor":
            result = math.floor(input_value)
        elif operation == "abs":
            result = abs(input_value)
        elif operation == "max":
            if operand is None:
                raise ValueError("operand is required for 'max' operation")
            result = max(input_value, operand)
        elif operation == "min":
            if operand is None:
                raise ValueError("operand is required for 'min' operation")
            result = min(input_value, operand)
        elif operation == "sum":
            if isinstance(input_value, list):
                numbers = [float(x) for x in input_value if isinstance(x, (int, float, str))]
                result = sum(numbers)
            else:
                result = input_value
        elif operation == "average":
            if isinstance(input_value, list):
                numbers = [float(x) for x in input_value if isinstance(x, (int, float, str))]
                result = sum(numbers) / len(numbers) if numbers else 0
            else:
                result = input_value
        else:
            raise ValueError(f"Unknown operation: {operation}")

        self._set_data(output_path, result)

        return result
