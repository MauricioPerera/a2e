"""
Text operation handlers: FormatText, ExtractText.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class TextHandlerMixin:
    """Mixin providing text manipulation handlers for WorkflowExecutor."""

    def _execute_format_text(self, config: Dict[str, Any]) -> str:
        """Formatea texto usando plantillas o transformaciones"""
        input_path = config["inputPath"]
        format_type = config["format"]
        output_path = config["outputPath"]

        input_value = self._get_data(input_path)

        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")

        if not isinstance(input_value, str):
            if isinstance(input_value, dict):
                if format_type == "template":
                    template = config.get("template", str(input_value))
                    result = template.format(**input_value)
                else:
                    result = str(input_value)
            else:
                result = str(input_value)
        else:
            result = input_value

        if format_type == "upper":
            result = result.upper()
        elif format_type == "lower":
            result = result.lower()
        elif format_type == "title":
            result = result.title()
        elif format_type == "capitalize":
            result = result.capitalize()
        elif format_type == "trim":
            result = result.strip()
        elif format_type == "template":
            template = config.get("template", result)
            if isinstance(input_value, dict):
                result = template.format(**input_value)
            else:
                result = template.replace("{value}", str(input_value))
        elif format_type == "replace":
            replacements = config.get("replacements", {})
            for old, new in replacements.items():
                result = result.replace(old, new)

        self._set_data(output_path, result)

        return result

    def _execute_extract_text(self, config: Dict[str, Any]) -> Any:
        """Extrae informacion de texto usando expresiones regulares"""
        import re

        input_path = config["inputPath"]
        pattern = config["pattern"]
        extract_all = config.get("extractAll", False)
        output_path = config["outputPath"]

        input_value = self._get_data(input_path)

        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")

        text = str(input_value)

        try:
            regex = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {pattern} - {e}")

        if extract_all:
            matches = regex.findall(text)
            result = matches if matches else []
        else:
            match = regex.search(text)
            result = match.group(0) if match else None

        self._set_data(output_path, result)

        return result
