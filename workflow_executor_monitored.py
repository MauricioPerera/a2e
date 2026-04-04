"""
Módulo de compatibilidad — MonitoredWorkflowExecutor ahora es WorkflowExecutor + AuditMiddleware.
Este shim mantiene la interfaz anterior para código que aún importe desde aquí.
"""

from executor.workflow_executor import WorkflowExecutor, AuditMiddleware
from monitoring.audit_logger import AuditLogger


class MonitoredWorkflowExecutor(WorkflowExecutor):
    """
    Compatibilidad: WorkflowExecutor con AuditMiddleware preconfigurado.
    Prefiera usar WorkflowExecutor(middlewares=[AuditMiddleware(...)]) directamente.
    """

    def __init__(self, audit_logger=None):
        _logger = audit_logger or AuditLogger()
        super().__init__(middlewares=[AuditMiddleware(audit_logger=_logger)])
        self.audit_logger = _logger


__all__ = ['MonitoredWorkflowExecutor']
