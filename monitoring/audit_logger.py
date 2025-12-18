"""
Sistema de auditoría y logging para A2E
Registra todas las ejecuciones, credenciales usadas, y resultados
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum
import hashlib


class ExecutionStatus(Enum):
    """Estado de ejecución"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AuditLogger:
    """
    Logger de auditoría para A2E
    Registra todas las ejecuciones con detalles completos
    """
    
    def __init__(self, log_dir: str = "logs", max_log_files: int = 100):
        """
        Inicializa el logger de auditoría
        
        Args:
            log_dir: Directorio donde guardar logs
            max_log_files: Número máximo de archivos de log a mantener
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_log_files = max_log_files
        
        # Configurar logging estándar
        self.logger = logging.getLogger("a2e.audit")
        self.logger.setLevel(logging.INFO)
        
        # Handler para archivo de log diario
        log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(file_handler)
    
    def log_execution_start(
        self,
        execution_id: str,
        agent_id: str,
        workflow_id: str,
        workflow_jsonl: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Registra inicio de ejecución
        
        Args:
            execution_id: ID único de la ejecución
            agent_id: ID del agente que inició la ejecución
            workflow_id: ID del workflow
            workflow_jsonl: JSONL del workflow (para auditoría)
            metadata: Metadatos adicionales
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "execution_id": execution_id,
            "agent_id": agent_id,
            "workflow_id": workflow_id,
            "status": ExecutionStatus.PENDING.value,
            "workflow": workflow_jsonl,
            "metadata": metadata or {}
        }
        
        self._write_log_entry(log_entry)
        self.logger.info(f"Execution started: {execution_id} by agent {agent_id}")
    
    def log_operation_start(
        self,
        execution_id: str,
        operation_id: str,
        operation_type: str,
        operation_config: Dict[str, Any]
    ):
        """
        Registra inicio de una operación
        
        Args:
            execution_id: ID de la ejecución
            operation_id: ID de la operación
            operation_type: Tipo de operación (ApiCall, FilterData, etc.)
            operation_config: Configuración de la operación (sin credenciales)
        """
        # Sanitizar configuración (remover valores de credenciales)
        sanitized_config = self._sanitize_config(operation_config)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "execution_id": execution_id,
            "operation_id": operation_id,
            "operation_type": operation_type,
            "status": ExecutionStatus.RUNNING.value,
            "config": sanitized_config
        }
        
        self._write_log_entry(log_entry)
        self.logger.info(f"Operation started: {operation_id} ({operation_type}) in execution {execution_id}")
    
    def log_credential_usage(
        self,
        execution_id: str,
        operation_id: str,
        credential_id: str,
        credential_type: str,
        usage_context: str
    ):
        """
        Registra uso de credencial
        
        Args:
            execution_id: ID de la ejecución
            operation_id: ID de la operación que usó la credencial
            credential_id: ID de la credencial usada
            credential_type: Tipo de credencial
            usage_context: Contexto de uso (ej: "Authorization header")
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "execution_id": execution_id,
            "operation_id": operation_id,
            "credential_id": credential_id,
            "credential_type": credential_type,
            "usage_context": usage_context,
            "event_type": "credential_usage"
        }
        
        self._write_log_entry(log_entry)
        self.logger.info(
            f"Credential used: {credential_id} ({credential_type}) in operation {operation_id}"
        )
    
    def log_operation_result(
        self,
        execution_id: str,
        operation_id: str,
        status: ExecutionStatus,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        """
        Registra resultado de una operación
        
        Args:
            execution_id: ID de la ejecución
            operation_id: ID de la operación
            status: Estado de la operación
            result: Resultado (puede ser sanitizado)
            error: Mensaje de error si falló
            duration_ms: Duración en milisegundos
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "execution_id": execution_id,
            "operation_id": operation_id,
            "status": status.value,
            "duration_ms": duration_ms,
            "error": error
        }
        
        # Sanitizar resultado si es necesario
        if result is not None:
            sanitized_result = self._sanitize_result(result)
            log_entry["result"] = sanitized_result
        
        self._write_log_entry(log_entry)
        
        if status == ExecutionStatus.SUCCESS:
            self.logger.info(f"Operation completed: {operation_id} in {duration_ms}ms")
        else:
            self.logger.warning(f"Operation failed: {operation_id} - {error}")
    
    def log_execution_complete(
        self,
        execution_id: str,
        status: ExecutionStatus,
        results: Optional[Dict[str, Any]] = None,
        total_duration_ms: Optional[float] = None,
        summary: Optional[Dict[str, Any]] = None
    ):
        """
        Registra finalización de ejecución completa
        
        Args:
            execution_id: ID de la ejecución
            status: Estado final
            results: Resultados de todas las operaciones
            total_duration_ms: Duración total en milisegundos
            summary: Resumen de la ejecución
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "execution_id": execution_id,
            "status": status.value,
            "total_duration_ms": total_duration_ms,
            "summary": summary or {}
        }
        
        # Sanitizar resultados
        if results is not None:
            sanitized_results = self._sanitize_result(results)
            log_entry["results"] = sanitized_results
        
        self._write_log_entry(log_entry)
        
        if status == ExecutionStatus.SUCCESS:
            self.logger.info(f"Execution completed: {execution_id} in {total_duration_ms}ms")
        else:
            self.logger.error(f"Execution failed: {execution_id}")
    
    def _sanitize_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitiza configuración removiendo valores sensibles
        """
        sanitized = config.copy()
        
        # Remover valores de credenciales pero mantener referencia
        if "headers" in sanitized:
            headers = sanitized["headers"].copy()
            for key, value in headers.items():
                if isinstance(value, str) and ("Bearer" in value or "token" in key.lower()):
                    headers[key] = "[REDACTED]"
            sanitized["headers"] = headers
        
        return sanitized
    
    def _sanitize_result(self, result: Any) -> Any:
        """
        Sanitiza resultados removiendo datos sensibles
        """
        if isinstance(result, dict):
            sanitized = {}
            for key, value in result.items():
                if any(sensitive in key.lower() for sensitive in ["token", "password", "secret", "key"]):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize_result(value)
            return sanitized
        elif isinstance(result, list):
            return [self._sanitize_result(item) for item in result]
        else:
            return result
    
    def _write_log_entry(self, entry: Dict[str, Any]):
        """
        Escribe entrada de log en archivo JSONL
        """
        log_file = self.log_dir / f"executions_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    
    def query_executions(
        self,
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Consulta ejecuciones con filtros
        
        Args:
            agent_id: Filtrar por agente
            workflow_id: Filtrar por workflow
            status: Filtrar por estado
            start_date: Fecha de inicio
            end_date: Fecha de fin
            limit: Límite de resultados
        
        Returns:
            Lista de ejecuciones que coinciden con los filtros
        """
        results = []
        
        # Buscar en archivos de log
        for log_file in sorted(self.log_dir.glob("executions_*.jsonl"), reverse=True):
            if len(results) >= limit:
                break
            
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if len(results) >= limit:
                        break
                    
                    try:
                        entry = json.loads(line)
                        
                        # Aplicar filtros
                        if agent_id and entry.get("agent_id") != agent_id:
                            continue
                        if workflow_id and entry.get("workflow_id") != workflow_id:
                            continue
                        if status and entry.get("status") != status.value:
                            continue
                        
                        # Filtrar por fecha
                        entry_date = datetime.fromisoformat(entry["timestamp"])
                        if start_date and entry_date < start_date:
                            continue
                        if end_date and entry_date > end_date:
                            continue
                        
                        results.append(entry)
                    except json.JSONDecodeError:
                        continue
        
        return results[:limit]
    
    def get_execution_details(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene detalles completos de una ejecución
        """
        details = {
            "execution_id": execution_id,
            "operations": [],
            "credentials_used": [],
            "timeline": []
        }
        
        # Buscar en todos los archivos de log
        for log_file in self.log_dir.glob("executions_*.jsonl"):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("execution_id") == execution_id:
                            # Agregar a timeline
                            details["timeline"].append(entry)
                            
                            # Extraer operaciones
                            if "operation_id" in entry:
                                details["operations"].append(entry)
                            
                            # Extraer credenciales usadas
                            if entry.get("event_type") == "credential_usage":
                                details["credentials_used"].append(entry)
                    except json.JSONDecodeError:
                        continue
        
        if not details["timeline"]:
            return None
        
        # Ordenar timeline
        details["timeline"].sort(key=lambda x: x["timestamp"])
        
        return details

