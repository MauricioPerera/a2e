"""
Encoding operation handler: EncodeDecode.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class EncodingHandlerMixin:
    """Mixin providing encode/decode handler for WorkflowExecutor."""

    def _execute_encode_decode(self, config: Dict[str, Any]) -> str:
        """Codifica o decodifica datos"""
        import base64
        from urllib.parse import quote, unquote
        import html

        input_path = config["inputPath"]
        operation = config["operation"]
        encoding = config["encoding"]
        output_path = config["outputPath"]

        input_value = self._get_data(input_path)

        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")

        if isinstance(input_value, str):
            input_bytes = input_value.encode('utf-8')
        elif isinstance(input_value, bytes):
            input_bytes = input_value
        else:
            input_bytes = str(input_value).encode('utf-8')

        if encoding == "base64":
            if operation == "encode":
                result = base64.b64encode(input_bytes).decode('utf-8')
            else:
                try:
                    result = base64.b64decode(input_bytes).decode('utf-8')
                except Exception as e:
                    raise ValueError(f"Invalid base64 data: {e}")

        elif encoding == "url":
            input_str = input_value if isinstance(input_value, str) else input_bytes.decode('utf-8')
            if operation == "encode":
                result = quote(input_str)
            else:
                result = unquote(input_str)

        elif encoding == "html":
            input_str = input_value if isinstance(input_value, str) else input_bytes.decode('utf-8')
            if operation == "encode":
                result = html.escape(input_str)
            else:
                result = html.unescape(input_str)

        else:
            raise ValueError(f"Unknown encoding: {encoding}")

        self._set_data(output_path, result)

        return result
