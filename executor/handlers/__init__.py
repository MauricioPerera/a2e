"""
Operation handlers for the A2E workflow executor.
Each module provides a mixin class with handler methods.
"""

from .api import ApiHandlerMixin
from .data import DataHandlerMixin
from .datetime_ops import DateTimeHandlerMixin
from .text import TextHandlerMixin
from .validation import ValidationHandlerMixin
from .math_ops import MathHandlerMixin
from .encoding import EncodingHandlerMixin
from .flow import FlowHandlerMixin

__all__ = [
    "ApiHandlerMixin",
    "DataHandlerMixin",
    "DateTimeHandlerMixin",
    "TextHandlerMixin",
    "ValidationHandlerMixin",
    "MathHandlerMixin",
    "EncodingHandlerMixin",
    "FlowHandlerMixin",
]

# Registry mapping operation types to handler method names
OPERATION_HANDLERS = {
    "ApiCall": "_execute_api_call",
    "FilterData": "_execute_filter_data",
    "TransformData": "_execute_transform_data",
    "StoreData": "_execute_store_data",
    "Wait": "_execute_wait",
    "GetCurrentDateTime": "_execute_get_current_datetime",
    "ConvertTimezone": "_execute_convert_timezone",
    "DateCalculation": "_execute_date_calculation",
    "FormatText": "_execute_format_text",
    "ExtractText": "_execute_extract_text",
    "ValidateData": "_execute_validate_data",
    "Calculate": "_execute_calculate",
    "EncodeDecode": "_execute_encode_decode",
    "DateTime": "_execute_date_time",
    "SetData": "_execute_set_data",
    "MergeData": "_execute_merge_data",
    "Loop": "_execute_loop",
    "Conditional": "_execute_conditional",
    "ExecuteN8nWorkflow": "_execute_n8n_workflow",
}
