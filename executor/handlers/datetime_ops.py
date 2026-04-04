"""
DateTime operation handlers: GetCurrentDateTime, ConvertTimezone, DateCalculation, DateTime.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DateTimeHandlerMixin:
    """Mixin providing date/time handlers for WorkflowExecutor."""

    def _parse_datetime(self, input_value, timezone_str=None):
        """Parsea un valor de entrada a datetime."""
        from datetime import datetime
        import pytz

        dt = None

        if isinstance(input_value, (int, float)):
            dt = datetime.fromtimestamp(input_value, tz=pytz.UTC)
        elif isinstance(input_value, str):
            try:
                dt = datetime.fromisoformat(input_value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    dt = datetime.strptime(input_value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    raise ValueError(f"Unable to parse date string: {input_value}")
        elif isinstance(input_value, dict):
            year = input_value.get("year", datetime.now().year)
            month = input_value.get("month", datetime.now().month)
            day = input_value.get("day", datetime.now().day)
            hour = input_value.get("hour", 0)
            minute = input_value.get("minute", 0)
            second = input_value.get("second", 0)
            dt = datetime(year, month, day, hour, minute, second)
        else:
            raise ValueError(f"Unsupported date format: {type(input_value)}")

        if dt.tzinfo is None and timezone_str:
            try:
                tz = pytz.timezone(timezone_str)
                dt = tz.localize(dt)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone: {timezone_str}, assuming UTC")
                dt = pytz.UTC.localize(dt)
        elif dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)

        return dt

    def _format_datetime(self, dt, format_type, format_string=None):
        """Formatea un datetime segun el tipo solicitado."""
        if format_type == "timestamp":
            return dt.timestamp()
        elif format_type == "custom" and format_string:
            return dt.strftime(format_string)
        else:
            return dt.isoformat()

    def _execute_get_current_datetime(self, config: Dict[str, Any]) -> str:
        """Obtiene la fecha y hora actual"""
        from datetime import datetime
        import pytz

        timezone_str = config.get("timezone")
        format_type = config.get("format", "iso8601")
        format_string = config.get("formatString")
        output_path = config["outputPath"]

        if timezone_str:
            try:
                tz = pytz.timezone(timezone_str)
                now = datetime.now(tz)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone: {timezone_str}, using system timezone")
                now = datetime.now()
        else:
            now = datetime.now()

        result = self._format_datetime(now, format_type, format_string)
        self._set_data(output_path, result)

        return result

    def _execute_convert_timezone(self, config: Dict[str, Any]) -> str:
        """Convierte una fecha/hora de una zona horaria a otra"""
        import pytz

        input_path = config["inputPath"]
        from_timezone_str = config.get("fromTimezone")
        to_timezone_str = config["toTimezone"]
        format_type = config.get("format", "iso8601")
        format_string = config.get("formatString")
        output_path = config["outputPath"]

        input_value = self._get_data(input_path)

        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")

        dt = self._parse_datetime(input_value, timezone_str=from_timezone_str)

        try:
            to_tz = pytz.timezone(to_timezone_str)
            converted_dt = dt.astimezone(to_tz)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Unknown timezone: {to_timezone_str}")

        result = self._format_datetime(converted_dt, format_type, format_string)
        self._set_data(output_path, result)

        return result

    def _execute_date_calculation(self, config: Dict[str, Any]) -> str:
        """Realiza calculos con fechas (sumar dias, restar horas, etc.)"""
        from datetime import timedelta

        input_path = config["inputPath"]
        operation = config["operation"]
        timezone_str = config.get("timezone")
        format_type = config.get("format", "iso8601")
        format_string = config.get("formatString")
        output_path = config["outputPath"]

        input_value = self._get_data(input_path)

        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")

        dt = self._parse_datetime(input_value, timezone_str=timezone_str)

        delta_kwargs = {}
        if "years" in config:
            delta_kwargs["days"] = delta_kwargs.get("days", 0) + (config["years"] * 365)
        if "months" in config:
            delta_kwargs["days"] = delta_kwargs.get("days", 0) + (config["months"] * 30)
        if "days" in config:
            delta_kwargs["days"] = delta_kwargs.get("days", 0) + config["days"]
        if "hours" in config:
            delta_kwargs["hours"] = config["hours"]
        if "minutes" in config:
            delta_kwargs["minutes"] = config["minutes"]
        if "seconds" in config:
            delta_kwargs["seconds"] = config["seconds"]

        delta = timedelta(**delta_kwargs)

        if operation == "add":
            result_dt = dt + delta
        elif operation == "subtract":
            result_dt = dt - delta
        else:
            raise ValueError(f"Unknown operation: {operation}")

        result = self._format_datetime(result_dt, format_type, format_string)
        self._set_data(output_path, result)

        return result

    def _execute_date_time(self, config: Dict[str, Any]) -> str:
        """Unified DateTime operation that delegates based on mode."""
        mode = config.get("mode")
        if not mode:
            raise ValueError("DateTime operation requires a 'mode' parameter (now, convert, calculate)")

        if mode == "now":
            now_config = {
                "outputPath": config["outputPath"],
            }
            if "timezone" in config:
                now_config["timezone"] = config["timezone"]
            if "format" in config:
                now_config["format"] = config["format"]
            if "formatString" in config:
                now_config["formatString"] = config["formatString"]
            return self._execute_get_current_datetime(now_config)

        elif mode == "convert":
            convert_config = {
                "inputPath": config.get("input", ""),
                "toTimezone": config.get("timezone", "UTC"),
                "outputPath": config["outputPath"],
            }
            if "format" in config:
                convert_config["format"] = config["format"]
            if "formatString" in config:
                convert_config["formatString"] = config["formatString"]
            return self._execute_convert_timezone(convert_config)

        elif mode == "calculate":
            calc_config = {
                "inputPath": config.get("input", ""),
                "operation": config.get("operation", "add"),
                "outputPath": config["outputPath"],
            }
            if "timezone" in config:
                calc_config["timezone"] = config["timezone"]
            if "format" in config:
                calc_config["format"] = config["format"]
            if "formatString" in config:
                calc_config["formatString"] = config["formatString"]
            amount = config.get("amount", 0)
            unit = config.get("unit", "days")
            calc_config[unit] = amount
            return self._execute_date_calculation(calc_config)

        else:
            raise ValueError(f"Unknown DateTime mode: {mode}. Expected 'now', 'convert', or 'calculate'")
