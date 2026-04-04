"""
Validation operation handler: ValidateData.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ValidationHandlerMixin:
    """Mixin providing data validation handler for WorkflowExecutor."""

    def _execute_validate_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos usando reglas predefinidas"""
        import re
        from datetime import datetime
        from urllib.parse import urlparse

        input_path = config["inputPath"]
        validation_type = config["validationType"]
        pattern = config.get("pattern")
        output_path = config["outputPath"]

        input_value = self._get_data(input_path)

        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")

        value_str = str(input_value)
        is_valid = False
        error_message = None

        if validation_type == "email":
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            is_valid = bool(re.match(email_pattern, value_str))
            if not is_valid:
                error_message = "Invalid email format"

        elif validation_type == "url":
            try:
                parsed = urlparse(value_str)
                is_valid = all([parsed.scheme, parsed.netloc])
                if not is_valid:
                    error_message = "Invalid URL format"
            except Exception:
                is_valid = False
                error_message = "Invalid URL format"

        elif validation_type == "number":
            try:
                float(value_str)
                is_valid = True
            except ValueError:
                is_valid = False
                error_message = "Not a valid number"

        elif validation_type == "integer":
            try:
                int(value_str)
                is_valid = True
            except ValueError:
                is_valid = False
                error_message = "Not a valid integer"

        elif validation_type == "phone":
            phone_pattern = r'^[\d\s\-\+\(\)]+$'
            is_valid = bool(re.match(phone_pattern, value_str)) and len(re.sub(r'[\s\-\+\(\)]', '', value_str)) >= 10
            if not is_valid:
                error_message = "Invalid phone number format"

        elif validation_type == "date":
            try:
                datetime.fromisoformat(value_str.replace('Z', '+00:00'))
                is_valid = True
            except Exception:
                try:
                    datetime.strptime(value_str, "%Y-%m-%d")
                    is_valid = True
                except Exception:
                    is_valid = False
                    error_message = "Invalid date format"

        elif validation_type == "custom":
            if not pattern:
                raise ValueError("pattern is required for custom validation")
            try:
                regex = re.compile(pattern)
                is_valid = bool(regex.match(value_str))
                if not is_valid:
                    error_message = f"Value does not match pattern: {pattern}"
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {pattern} - {e}")

        result = {
            "valid": is_valid,
            "value": input_value,
        }

        if error_message:
            result["error"] = error_message

        self._set_data(output_path, result)

        return result
