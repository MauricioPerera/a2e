"""
Ejecutor de workflows con gestión robusta de respuestas y errores
"""

import time
import uuid
from typing import Dict, Any, Optional

from workflow_executor_monitored import MonitoredWorkflowExecutor
from responses.response_formatter import ResponseFormatter, ResponseFormat
from responses.error_handler import ErrorHandler, A2EError
from monitoring.audit_logger import AuditLogger, ExecutionStatus


class RobustWorkflowExecutor(MonitoredWorkflowExecutor):
    """
    Ejecutor con gestión robusta de respuestas y errores
    """
    
    def __init__(
        self,
        audit_logger: Optional[AuditLogger] = None,
        response_format: ResponseFormat = ResponseFormat.SUMMARY
    ):
        super().__init__(audit_logger=audit_logger)
        self.response_formatter = ResponseFormatter(format=response_format)
        self.error_handler = ErrorHandler()
    
    async def execute(self) -> Dict[str, Any]:
        """
        Ejecuta workflow con gestión robusta de respuestas
        """
        if not self.current_execution_id:
            self.current_execution_id = str(uuid.uuid4())
        
        start_time = time.time()
        successful_operations = {}
        failed_operations = {}
        
        try:
            for op_id in self.execution_order:
                if op_id not in self.operations:
                    continue
                
                op = self.operations[op_id]
                operation_type = list(op.get("operation", {}).keys())[0]
                operation_config = op["operation"][operation_type]
                
                # Registrar inicio
                self.audit_logger.log_operation_start(
                    execution_id=self.current_execution_id,
                    operation_id=op_id,
                    operation_type=operation_type,
                    operation_config=operation_config
                )
                
                # Ejecutar con manejo de errores
                op_start = time.time()
                try:
                    result = await self._execute_operation(operation_type, operation_config)
                    op_duration = (time.time() - op_start) * 1000
                    
                    # Formatear resultado exitoso
                    formatted_result = self.response_formatter._extract_useful_fields(result)
                    successful_operations[op_id] = formatted_result
                    
                    self.audit_logger.log_operation_result(
                        execution_id=self.current_execution_id,
                        operation_id=op_id,
                        status=ExecutionStatus.SUCCESS,
                        result=formatted_result,
                        duration_ms=op_duration
                    )
                    
                except Exception as e:
                    op_duration = (time.time() - op_start) * 1000
                    
                    # Convertir a error estructurado
                    structured_error = self.error_handler.handle_exception(
                        exception=e,
                        operation_id=op_id,
                        context={
                            "operation_type": operation_type,
                            "operation_config": operation_config
                        }
                    )
                    
                    failed_operations[op_id] = structured_error
                    
                    self.audit_logger.log_operation_result(
                        execution_id=self.current_execution_id,
                        operation_id=op_id,
                        status=ExecutionStatus.FAILED,
                        error=str(structured_error.message),
                        duration_ms=op_duration
                    )
            
            # Formatear respuesta final
            total_duration = (time.time() - start_time) * 1000
            
            if failed_operations and successful_operations:
                # Éxito parcial
                response = self.response_formatter.format_partial_success(
                    execution_id=self.current_execution_id,
                    successful_operations=successful_operations,
                    failed_operations=failed_operations
                )
                status = ExecutionStatus.FAILED
            elif failed_operations:
                # Todo falló
                # Retornar solo el primer error (más relevante)
                first_error = list(failed_operations.values())[0]
                response = self.error_handler.format_error_for_agent(first_error)
                response["execution_id"] = self.current_execution_id
                status = ExecutionStatus.FAILED
            else:
                # Todo exitoso
                response = self.response_formatter.format_success_response(
                    execution_id=self.current_execution_id,
                    results=successful_operations
                )
                status = ExecutionStatus.SUCCESS
            
            # Registrar finalización
            self.audit_logger.log_execution_complete(
                execution_id=self.current_execution_id,
                status=status,
                results=response,
                total_duration_ms=total_duration,
                summary={
                    "successful_operations": len(successful_operations),
                    "failed_operations": len(failed_operations)
                }
            )
            
            return response
            
        except Exception as e:
            # Error crítico en la ejecución
            total_duration = (time.time() - start_time) * 1000
            
            structured_error = self.error_handler.handle_exception(
                exception=e,
                context={"execution_id": self.current_execution_id}
            )
            
            response = self.error_handler.format_error_for_agent(structured_error)
            response["execution_id"] = self.current_execution_id
            
            self.audit_logger.log_execution_complete(
                execution_id=self.current_execution_id,
                status=ExecutionStatus.FAILED,
                results=response,
                total_duration_ms=total_duration,
                summary={"error": str(e)}
            )
            
            return response

