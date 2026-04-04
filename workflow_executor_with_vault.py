"""
Módulo de compatibilidad — SecureWorkflowExecutor ahora es WorkflowExecutor + VaultMiddleware.
Este shim mantiene la interfaz anterior para código que aún importe desde aquí.
"""

from executor.workflow_executor import WorkflowExecutor, VaultMiddleware
from credentials_vault import CredentialsVault

from typing import Optional


class SecureWorkflowExecutor(WorkflowExecutor):
    """
    Compatibilidad: WorkflowExecutor con VaultMiddleware preconfigurado.
    Prefiera usar WorkflowExecutor(middlewares=[VaultMiddleware(...)]) directamente.
    """

    def __init__(self, vault: Optional[CredentialsVault] = None):
        _vault = vault or CredentialsVault()
        super().__init__(middlewares=[VaultMiddleware(vault=_vault)])
        self.vault = _vault


__all__ = ['SecureWorkflowExecutor']
