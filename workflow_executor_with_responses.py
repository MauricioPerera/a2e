"""
Módulo de compatibilidad — RobustWorkflowExecutor ahora es WorkflowExecutor + AuditMiddleware.
Este shim mantiene la interfaz anterior para código que aún importe desde aquí.
"""

from executor.workflow_executor import WorkflowExecutor, AuditMiddleware
from monitoring.audit_logger import AuditLogger
from responses.response_formatter import ResponseFormatter, ResponseFormat
from responses.error_handler import ErrorHandler


class RobustWorkflowExecutor(WorkflowExecutor):
    """
    Compatibilidad: WorkflowExecutor con AuditMiddleware + ResponseFormatter + ErrorHandler.
    Prefiera usar WorkflowExecutor(middlewares=[...]) directamente.
    """

    def __init__(self, audit_logger=None, response_format=ResponseFormat.SUMMARY, **kwargs):
        _logger = audit_logger or AuditLogger()
        _formatter = ResponseFormatter(format=response_format)
        _error_handler = ErrorHandler()

        middleware = AuditMiddleware(
            audit_logger=_logger,
            response_formatter=_formatter,
            error_handler=_error_handler,
        )

        super().__init__(middlewares=[middleware])
        self.audit_logger = _logger
        self.response_formatter = _formatter
        self.error_handler = _error_handler

    async def execute(self):
        """Execute workflow and wrap results with ResponseFormatter."""
        try:
            raw_results = await super().execute()
            return self.response_formatter.format_success_response(
                execution_id=self.current_execution_id or "unknown",
                results=raw_results,
            )
        except Exception as e:
            return self.response_formatter.format_error_response(
                execution_id=self.current_execution_id or "unknown",
                error=e,
            )


__all__ = ['RobustWorkflowExecutor']
