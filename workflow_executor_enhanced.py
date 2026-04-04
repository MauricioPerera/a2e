"""
Módulo de compatibilidad — EnhancedWorkflowExecutor ahora es WorkflowExecutor + middlewares.
Este shim mantiene la interfaz anterior para código que aún importe desde aquí.
"""

from executor.workflow_executor import WorkflowExecutor, AuditMiddleware, CacheMiddleware
from monitoring.audit_logger import AuditLogger
from responses.response_formatter import ResponseFormatter, ResponseFormat
from responses.error_handler import ErrorHandler
from retry import RetryHandler, RetryConfig
from cache import ResultCache, CacheConfig

from typing import Optional

import asyncio  # Para asyncio.TimeoutError


class EnhancedWorkflowExecutor(WorkflowExecutor):
    """
    Compatibilidad: WorkflowExecutor con Audit + Cache + Retry.
    Prefiera usar WorkflowExecutor(middlewares=[...]) directamente.
    """

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        cache_config: Optional[CacheConfig] = None,
        **kwargs,
    ):
        _logger = kwargs.get("audit_logger") or AuditLogger()
        _formatter = ResponseFormatter(format=kwargs.get("response_format", ResponseFormat.SUMMARY))
        _error_handler = ErrorHandler()
        _cache = ResultCache(config=cache_config) if cache_config else ResultCache()

        middlewares = [
            AuditMiddleware(
                audit_logger=_logger,
                response_formatter=_formatter,
                error_handler=_error_handler,
            ),
            CacheMiddleware(cache=_cache),
        ]

        super().__init__(middlewares=middlewares)

        self.retry_handler = RetryHandler(config=retry_config) if retry_config else RetryHandler()
        self.cache = _cache
        self.audit_logger = _logger

    def get_cache_stats(self):
        return self.cache.get_stats()

    def clear_cache(self):
        self.cache.clear()

    def invalidate_cache(self, operation_type=None):
        self.cache.invalidate(operation_type=operation_type)


__all__ = ['EnhancedWorkflowExecutor']
