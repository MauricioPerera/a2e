"""
Middleware classes for the A2E workflow executor.
Extracted from workflow_executor.py for modularity.
"""

import json
import logging

logger = logging.getLogger(__name__)


class ExecutorMiddleware:
    """Clase base para middlewares del ejecutor"""

    def on_execution_start(self, execution_id, workflow_jsonl, agent_id=None):
        """Llamado al iniciar la ejecucion"""
        pass

    def on_operation_start(self, execution_id, op_id, op_type, config):
        """Llamado antes de cada operacion"""
        pass

    def on_operation_complete(self, execution_id, op_id, op_type, result, duration_ms):
        """Llamado despues de una operacion exitosa"""
        pass

    def on_operation_error(self, execution_id, op_id, op_type, error, duration_ms):
        """Llamado despues de una operacion fallida"""
        pass

    def on_execution_complete(self, execution_id, results, duration_ms):
        """Llamado al finalizar la ejecucion"""
        pass

    def process_config(self, op_type, config):
        """Pre-procesa la configuracion de operacion. Retorna config modificado."""
        return config

    def process_result(self, op_type, config, result):
        """Post-procesa el resultado de operacion. Retorna resultado modificado."""
        return result


class AuditMiddleware(ExecutorMiddleware):
    """
    Middleware de auditoria — registra inicio/fin de ejecucion,
    operaciones, uso de credenciales y timing.
    """

    def __init__(self, audit_logger, response_formatter=None, error_handler=None):
        self.audit_logger = audit_logger
        self.response_formatter = response_formatter
        self.error_handler = error_handler

    def on_execution_start(self, execution_id, workflow_jsonl, agent_id=None):
        workflow_id = "default"
        for line in workflow_jsonl.strip().split('\n'):
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                if "operationUpdate" in message:
                    workflow_id = message["operationUpdate"].get("workflowId", "default")
                    break
            except Exception:
                pass

        if agent_id:
            self.audit_logger.log_execution_start(
                execution_id=execution_id,
                agent_id=agent_id,
                workflow_id=workflow_id,
                workflow_jsonl=workflow_jsonl,
            )

    def on_operation_start(self, execution_id, op_id, op_type, config):
        self.audit_logger.log_operation_start(
            execution_id=execution_id,
            operation_id=op_id,
            operation_type=op_type,
            operation_config=config,
        )

        if op_type == "ApiCall" and "headers" in config:
            headers = config["headers"]
            for key, value in headers.items():
                if isinstance(value, dict) and "credentialRef" in value:
                    cred_id = value["credentialRef"].get("id")
                    if cred_id:
                        self.audit_logger.log_credential_usage(
                            execution_id=execution_id,
                            operation_id=op_id,
                            credential_id=cred_id,
                            credential_type="unknown",
                            usage_context=f"{key} header",
                        )

    def on_operation_complete(self, execution_id, op_id, op_type, result, duration_ms):
        from monitoring.audit_logger import ExecutionStatus

        formatted = result
        if self.response_formatter is not None:
            try:
                formatted = self.response_formatter._extract_useful_fields(result)
            except Exception:
                formatted = result

        self.audit_logger.log_operation_result(
            execution_id=execution_id,
            operation_id=op_id,
            status=ExecutionStatus.SUCCESS,
            result=formatted,
            duration_ms=duration_ms,
        )

    def on_operation_error(self, execution_id, op_id, op_type, error, duration_ms):
        from monitoring.audit_logger import ExecutionStatus

        error_msg = str(error)
        if self.error_handler is not None:
            try:
                structured = self.error_handler.handle_exception(
                    exception=error if isinstance(error, Exception) else Exception(error),
                    operation_id=op_id,
                    context={"operation_type": op_type},
                )
                error_msg = str(structured.message)
            except Exception:
                pass

        self.audit_logger.log_operation_result(
            execution_id=execution_id,
            operation_id=op_id,
            status=ExecutionStatus.FAILED,
            error=error_msg,
            duration_ms=duration_ms,
        )

    def on_execution_complete(self, execution_id, results, duration_ms):
        from monitoring.audit_logger import ExecutionStatus

        successful = sum(1 for r in results.values() if not (isinstance(r, dict) and "error" in r))
        failed = sum(1 for r in results.values() if isinstance(r, dict) and "error" in r)
        status = ExecutionStatus.SUCCESS if failed == 0 else ExecutionStatus.FAILED

        self.audit_logger.log_execution_complete(
            execution_id=execution_id,
            status=status,
            results=results,
            total_duration_ms=duration_ms,
            summary={
                "successful_operations": successful,
                "failed_operations": failed,
            },
        )


class CacheMiddleware(ExecutorMiddleware):
    """Middleware de cache — almacena y recupera resultados de operaciones."""

    def __init__(self, cache):
        self.cache = cache

    def process_config(self, op_type, config):
        cached = self.cache.get(op_type, config)
        if cached is not None:
            logger.info(f"Cache hit for {op_type}")
            config = dict(config)
            config["_cached_result"] = cached
        return config

    def process_result(self, op_type, config, result):
        self.cache.set(op_type, config, result)
        return result


class VaultMiddleware(ExecutorMiddleware):
    """Middleware de vault — inyecta credenciales en operaciones ApiCall."""

    def __init__(self, vault):
        from credentials_vault import CredentialInjector
        self.vault = vault
        self.injector = CredentialInjector(vault)

    def process_config(self, op_type, config):
        if op_type == "ApiCall":
            return self.injector.inject_into_operation(config, op_type)
        return config
