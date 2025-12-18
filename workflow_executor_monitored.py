"""
Ejecutor de workflows con monitoreo integrado
"""

import time
import uuid
from typing import Dict, Any, Optional

from workflow_executor import WorkflowExecutor
from monitoring.audit_logger import AuditLogger, ExecutionStatus


class MonitoredWorkflowExecutor(WorkflowExecutor):
    """
    Ejecutor de workflows con monitoreo y auditoría
    """
    
    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        super().__init__()
        self.audit_logger = audit_logger or AuditLogger()
        self.current_execution_id: Optional[str] = None
        self.current_agent_id: Optional[str] = None
    
    def set_agent_context(self, agent_id: str):
        """
        Establece el contexto del agente para logging
        """
        self.current_agent_id = agent_id
    
    def load_workflow(self, workflow_jsonl: str, agent_id: Optional[str] = None):
        """
        Carga workflow y registra inicio de ejecución
        """
        super().load_workflow(workflow_jsonl)
        
        # Generar ID de ejecución
        self.current_execution_id = str(uuid.uuid4())
        if agent_id:
            self.current_agent_id = agent_id
        
        # Obtener workflow_id del JSONL
        workflow_id = "default"
        for line in workflow_jsonl.strip().split('\n'):
            if not line.strip():
                continue
            try:
                import json
                message = json.loads(line)
                if "operationUpdate" in message:
                    workflow_id = message["operationUpdate"].get("workflowId", "default")
                    break
            except:
                pass
        
        # Registrar inicio
        if self.current_agent_id:
            self.audit_logger.log_execution_start(
                execution_id=self.current_execution_id,
                agent_id=self.current_agent_id,
                workflow_id=workflow_id,
                workflow_jsonl=workflow_jsonl
            )
    
    async def execute(self) -> Dict[str, Any]:
        """
        Ejecuta workflow con monitoreo
        """
        if not self.current_execution_id:
            self.current_execution_id = str(uuid.uuid4())
        
        start_time = time.time()
        results = {}
        operation_times = {}
        
        try:
            for op_id in self.execution_order:
                if op_id not in self.operations:
                    continue
                
                op = self.operations[op_id]
                operation_type = list(op.get("operation", {}).keys())[0]
                operation_config = op["operation"][operation_type]
                
                # Registrar inicio de operación
                self.audit_logger.log_operation_start(
                    execution_id=self.current_execution_id,
                    operation_id=op_id,
                    operation_type=operation_type,
                    operation_config=operation_config
                )
                
                # Registrar uso de credenciales si aplica
                if operation_type == "ApiCall" and "headers" in operation_config:
                    headers = operation_config["headers"]
                    for key, value in headers.items():
                        if isinstance(value, dict) and "credentialRef" in value:
                            cred_id = value["credentialRef"].get("id")
                            if cred_id:
                                self.audit_logger.log_credential_usage(
                                    execution_id=self.current_execution_id,
                                    operation_id=op_id,
                                    credential_id=cred_id,
                                    credential_type="unknown",  # Se podría obtener del vault
                                    usage_context=f"{key} header"
                                )
                
                # Ejecutar operación
                op_start = time.time()
                try:
                    result = await self._execute_operation(operation_type, operation_config)
                    op_duration = (time.time() - op_start) * 1000
                    operation_times[op_id] = op_duration
                    
                    self.audit_logger.log_operation_result(
                        execution_id=self.current_execution_id,
                        operation_id=op_id,
                        status=ExecutionStatus.SUCCESS,
                        result=result,
                        duration_ms=op_duration
                    )
                    
                    results[op_id] = result
                except Exception as e:
                    op_duration = (time.time() - op_start) * 1000
                    operation_times[op_id] = op_duration
                    
                    self.audit_logger.log_operation_result(
                        execution_id=self.current_execution_id,
                        operation_id=op_id,
                        status=ExecutionStatus.FAILED,
                        error=str(e),
                        duration_ms=op_duration
                    )
                    
                    results[op_id] = {"error": str(e)}
            
            # Registrar finalización
            total_duration = (time.time() - start_time) * 1000
            summary = {
                "total_operations": len(self.execution_order),
                "successful_operations": sum(1 for r in results.values() if "error" not in r),
                "failed_operations": sum(1 for r in results.values() if "error" in r),
                "operation_times": operation_times
            }
            
            self.audit_logger.log_execution_complete(
                execution_id=self.current_execution_id,
                status=ExecutionStatus.SUCCESS,
                results=results,
                total_duration_ms=total_duration,
                summary=summary
            )
            
            return results
            
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            
            self.audit_logger.log_execution_complete(
                execution_id=self.current_execution_id,
                status=ExecutionStatus.FAILED,
                results=results,
                total_duration_ms=total_duration,
                summary={"error": str(e)}
            )
            
            raise

