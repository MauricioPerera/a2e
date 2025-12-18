"""
Sistema de validación proactiva de workflows
Detecta y previene errores antes de ejecutar
"""

import json
from typing import Dict, Any, List, Optional, Tuple, Set
from enum import Enum
from urllib.parse import urlparse


class ValidationLevel(Enum):
    """Nivel de validación"""
    STRICT = "strict"  # Rechaza cualquier posible error
    MODERATE = "moderate"  # Rechaza errores probables (por defecto)
    LENIENT = "lenient"  # Solo errores seguros


class ValidationError:
    """Error de validación"""
    def __init__(
        self,
        severity: str,
        message: str,
        operation_id: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        self.severity = severity  # "error", "warning"
        self.message = message
        self.operation_id = operation_id
        self.suggestion = suggestion
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "message": self.message,
            "operation_id": self.operation_id,
            "suggestion": self.suggestion
        }


class WorkflowValidator:
    """
    Valida workflows antes de ejecutar para prevenir errores
    """
    
    def __init__(
        self,
        api_kb: Optional[Any] = None,
        vault: Optional[Any] = None,
        auth: Optional[Any] = None,
        level: ValidationLevel = ValidationLevel.MODERATE
    ):
        """
        Inicializa el validador
        
        Args:
            api_kb: Base de conocimiento de APIs
            vault: Vault de credenciales
            auth: Sistema de autenticación
            level: Nivel de validación
        """
        self.api_kb = api_kb
        self.vault = vault
        self.auth = auth
        self.level = level
    
    def validate_workflow(
        self,
        workflow_jsonl: str,
        agent_id: Optional[str] = None
    ) -> Tuple[bool, List[ValidationError]]:
        """
        Valida un workflow completo
        
        Args:
            workflow_jsonl: Workflow a validar
            agent_id: ID del agente (para validar permisos)
        
        Returns:
            (es_válido, lista_de_errores)
        """
        errors = []
        
        try:
            # Parsear workflow
            operations = self._parse_workflow(workflow_jsonl)
            
            if not operations:
                errors.append(ValidationError(
                    severity="error",
                    message="Workflow contains no operations"
                ))
                return False, errors
            
            # Validar estructura básica
            structure_errors = self._validate_structure(operations)
            errors.extend(structure_errors)
            
            # Validar dependencias
            dependency_errors = self._validate_dependencies(operations)
            errors.extend(dependency_errors)
            
            # Validar tipos de datos
            type_errors = self._validate_data_types(operations)
            errors.extend(type_errors)
            
            # Validar compatibilidad de APIs
            if self.api_kb:
                api_errors = self._validate_api_compatibility(operations, agent_id)
                errors.extend(api_errors)
            
            # Validar credenciales
            if self.vault and self.auth and agent_id:
                credential_errors = self._validate_credentials(operations, agent_id)
                errors.extend(credential_errors)
            
            # Validar patrones problemáticos
            pattern_errors = self._validate_patterns(operations)
            errors.extend(pattern_errors)
            
            # Filtrar por nivel de validación
            if self.level == ValidationLevel.STRICT:
                # Incluir warnings como errores
                pass
            elif self.level == ValidationLevel.MODERATE:
                # Solo errores críticos
                errors = [e for e in errors if e.severity == "error"]
            elif self.level == ValidationLevel.LENIENT:
                # Solo errores seguros
                errors = [e for e in errors if e.severity == "error" and "will fail" in e.message.lower()]
            
            is_valid = len([e for e in errors if e.severity == "error"]) == 0
            
            return is_valid, errors
            
        except Exception as e:
            errors.append(ValidationError(
                severity="error",
                message=f"Failed to validate workflow: {str(e)}"
            ))
            return False, errors
    
    def _parse_workflow(self, workflow_jsonl: str) -> List[Dict[str, Any]]:
        """Parsea workflow y extrae operaciones"""
        operations = []
        lines = workflow_jsonl.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                if "operationUpdate" in message:
                    ops = message["operationUpdate"].get("operations", [])
                    operations.extend(ops)
            except json.JSONDecodeError:
                continue
        
        return operations
    
    def _validate_structure(self, operations: List[Dict[str, Any]]) -> List[ValidationError]:
        """Valida estructura básica del workflow"""
        errors = []
        operation_ids = set()
        
        for op in operations:
            op_id = op.get("id")
            if not op_id:
                errors.append(ValidationError(
                    severity="error",
                    message="Operation missing required 'id' field"
                ))
                continue
            
            if op_id in operation_ids:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Duplicate operation ID: {op_id}",
                    operation_id=op_id
                ))
            
            operation_ids.add(op_id)
            
            # Validar que tiene operation
            if "operation" not in op:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Operation '{op_id}' missing 'operation' field",
                    operation_id=op_id
                ))
                continue
            
            # Validar que tiene un tipo de operación
            operation = op["operation"]
            if not isinstance(operation, dict) or len(operation) != 1:
                errors.append(ValidationError(
                    severity="error",
                    message=f"Operation '{op_id}' must have exactly one operation type",
                    operation_id=op_id
                ))
        
        return errors
    
    def _validate_dependencies(self, operations: List[Dict[str, Any]]) -> List[ValidationError]:
        """Valida dependencias entre operaciones"""
        errors = []
        operation_ids = {op.get("id") for op in operations if op.get("id")}
        
        for op in operations:
            op_id = op.get("id")
            operation = op.get("operation", {})
            op_type = list(operation.keys())[0] if operation else None
            op_config = operation.get(op_type, {}) if op_type else {}
            
            # Validar inputPath apunta a operación existente
            if "inputPath" in op_config:
                input_path = op_config["inputPath"]
                # Extraer ID de operación del path (ej: /workflow/op-id)
                if input_path.startswith("/workflow/"):
                    referenced_id = input_path.split("/")[-1]
                    if referenced_id not in operation_ids:
                        errors.append(ValidationError(
                            severity="error",
                            message=f"Operation '{op_id}' references non-existent operation '{referenced_id}' in inputPath",
                            operation_id=op_id,
                            suggestion=f"Ensure operation '{referenced_id}' exists before '{op_id}'"
                        ))
            
            # Validar referencias en condiciones
            if op_type == "Conditional":
                if_true = op_config.get("ifTrue")
                if_false = op_config.get("ifFalse")
                
                if if_true and if_true not in operation_ids:
                    errors.append(ValidationError(
                        severity="error",
                        message=f"Conditional operation '{op_id}' references non-existent operation '{if_true}'",
                        operation_id=op_id
                    ))
                
                if if_false and if_false not in operation_ids:
                    errors.append(ValidationError(
                        severity="error",
                        message=f"Conditional operation '{op_id}' references non-existent operation '{if_false}'",
                        operation_id=op_id
                    ))
        
        return errors
    
    def _validate_data_types(self, operations: List[Dict[str, Any]]) -> List[ValidationError]:
        """Valida tipos de datos entre operaciones"""
        errors = []
        
        # Mapear qué tipo de dato produce cada operación
        output_types = {}
        
        for op in operations:
            op_id = op.get("id")
            operation = op.get("operation", {})
            op_type = list(operation.keys())[0] if operation else None
            op_config = operation.get(op_type, {}) if op_type else {}
            
            # Determinar tipo de salida
            if op_type == "ApiCall":
                output_types[op_id] = "api_response"  # Generalmente objeto o array
            elif op_type == "FilterData":
                output_types[op_id] = "array"
            elif op_type == "TransformData":
                transform = op_config.get("transform")
                if transform == "map":
                    output_types[op_id] = "array"
                elif transform == "reduce":
                    output_types[op_id] = "value"
                else:
                    output_types[op_id] = "unknown"
            else:
                output_types[op_id] = "unknown"
        
        # Validar que operaciones que requieren arrays reciben arrays
        for op in operations:
            op_id = op.get("id")
            operation = op.get("operation", {})
            op_type = list(operation.keys())[0] if operation else None
            op_config = operation.get(op_type, {}) if op_type else {}
            
            if op_type == "FilterData":
                input_path = op_config.get("inputPath", "")
                if input_path.startswith("/workflow/"):
                    source_id = input_path.split("/")[-1]
                    source_type = output_types.get(source_id)
                    
                    if source_type and source_type != "array" and source_type != "api_response":
                        errors.append(ValidationError(
                            severity="error",
                            message=f"FilterData operation '{op_id}' requires array input, but '{source_id}' produces '{source_type}'",
                            operation_id=op_id,
                            suggestion=f"Ensure '{source_id}' produces an array, or use TransformData to convert it"
                        ))
        
        return errors
    
    def _validate_api_compatibility(
        self,
        operations: List[Dict[str, Any]],
        agent_id: Optional[str] = None
    ) -> List[ValidationError]:
        """Valida compatibilidad de APIs"""
        errors = []
        
        for op in operations:
            op_id = op.get("id")
            operation = op.get("operation", {})
            op_type = list(operation.keys())[0] if operation else None
            op_config = operation.get(op_type, {}) if op_type else {}
            
            if op_type == "ApiCall":
                url = op_config.get("url", "")
                method = op_config.get("method", "GET")
                
                if not url:
                    errors.append(ValidationError(
                        severity="error",
                        message=f"ApiCall operation '{op_id}' missing required 'url'",
                        operation_id=op_id
                    ))
                    continue
                
                # Validar que la URL es de una API permitida
                if self.api_kb:
                    parsed = urlparse(url)
                    domain = parsed.netloc
                    
                    # Buscar API que coincida con este dominio
                    matching_api = None
                    for api_id, api_info in self.api_kb.apis.items():
                        api_domain = urlparse(api_info.get("baseUrl", "")).netloc
                        if domain == api_domain:
                            matching_api = api_id
                            break
                    
                    if not matching_api:
                        errors.append(ValidationError(
                            severity="warning",
                            message=f"ApiCall operation '{op_id}' uses URL from unknown API domain: {domain}",
                            operation_id=op_id,
                            suggestion="Verify the API is registered in the knowledge base"
                        ))
                    else:
                        # Validar que el agente tiene acceso
                        if agent_id and self.auth:
                            if not self.auth.is_api_allowed(agent_id, matching_api):
                                errors.append(ValidationError(
                                    severity="error",
                                    message=f"Agent '{agent_id}' does not have permission to use API '{matching_api}'",
                                    operation_id=op_id,
                                    suggestion=f"Request access to '{matching_api}' or use a different API"
                                ))
                        
                        # Validar que el endpoint existe
                        api_info = self.api_kb.get_api_info(matching_api)
                        if api_info:
                            endpoint_path = parsed.path
                            endpoints = api_info.get("endpoints", [])
                            
                            # Buscar endpoint que coincida
                            matching_endpoint = None
                            for ep in endpoints:
                                if ep.get("path") == endpoint_path and ep.get("method") == method:
                                    matching_endpoint = ep
                                    break
                            
                            if not matching_endpoint:
                                errors.append(ValidationError(
                                    severity="warning",
                                    message=f"Endpoint {method} {endpoint_path} not found in API '{matching_api}' definition",
                                    operation_id=op_id,
                                    suggestion="Verify the endpoint exists or add it to the API definition"
                                ))
        
        return errors
    
    def _validate_credentials(
        self,
        operations: List[Dict[str, Any]],
        agent_id: str
    ) -> List[ValidationError]:
        """Valida uso de credenciales"""
        errors = []
        
        for op in operations:
            op_id = op.get("id")
            operation = op.get("operation", {})
            op_type = list(operation.keys())[0] if operation else None
            op_config = operation.get(op_type, {}) if op_type else {}
            
            if op_type == "ApiCall":
                headers = op_config.get("headers", {})
                
                for header_key, header_value in headers.items():
                    if isinstance(header_value, dict) and "credentialRef" in header_value:
                        cred_id = header_value["credentialRef"].get("id")
                        
                        if not cred_id:
                            errors.append(ValidationError(
                                severity="error",
                                message=f"ApiCall operation '{op_id}' has invalid credential reference in header '{header_key}'",
                                operation_id=op_id
                            ))
                            continue
                        
                        # Validar que la credencial existe
                        if self.vault:
                            cred_metadata = self.vault.get_credential_metadata(cred_id)
                            if not cred_metadata:
                                errors.append(ValidationError(
                                    severity="error",
                                    message=f"Credential '{cred_id}' referenced in operation '{op_id}' does not exist",
                                    operation_id=op_id,
                                    suggestion=f"Register credential '{cred_id}' in the vault"
                                ))
                                continue
                        
                        # Validar que el agente tiene acceso
                        if self.auth:
                            if not self.auth.is_credential_allowed(agent_id, cred_id):
                                errors.append(ValidationError(
                                    severity="error",
                                    message=f"Agent '{agent_id}' does not have permission to use credential '{cred_id}'",
                                    operation_id=op_id,
                                    suggestion=f"Request access to credential '{cred_id}'"
                                ))
        
        return errors
    
    def _validate_patterns(self, operations: List[Dict[str, Any]]) -> List[ValidationError]:
        """Valida patrones problemáticos comunes"""
        errors = []
        operation_ids = {op.get("id") for op in operations if op.get("id")}
        
        # Detectar loops infinitos potenciales
        for op in operations:
            op_id = op.get("id")
            operation = op.get("operation", {})
            op_type = list(operation.keys())[0] if operation else None
            op_config = operation.get(op_type, {}) if op_type else {}
            
            if op_type == "Loop":
                loop_ops = op_config.get("operations", [])
                # Verificar que las operaciones del loop existen
                for loop_op_id in loop_ops:
                    if loop_op_id not in operation_ids:
                        errors.append(ValidationError(
                            severity="error",
                            message=f"Loop operation '{op_id}' references non-existent operation '{loop_op_id}'",
                            operation_id=op_id
                        ))
                
                # Advertencia si el loop no tiene condición de salida clara
                errors.append(ValidationError(
                    severity="warning",
                    message=f"Loop operation '{op_id}' may run indefinitely if input array is large",
                    operation_id=op_id,
                    suggestion="Consider adding a limit or condition to prevent infinite loops"
                ))
            
            # Detectar operaciones que pueden fallar por datos vacíos
            if op_type == "FilterData":
                input_path = op_config.get("inputPath", "")
                if input_path.startswith("/workflow/"):
                    source_id = input_path.split("/")[-1]
                    # Verificar si la fuente puede estar vacía
                    source_op = next((o for o in operations if o.get("id") == source_id), None)
                    if source_op:
                        source_type = list(source_op.get("operation", {}).keys())[0] if source_op.get("operation") else None
                        if source_type == "ApiCall":
                            errors.append(ValidationError(
                                severity="warning",
                                message=f"FilterData operation '{op_id}' may fail if API call '{source_id}' returns empty array",
                                operation_id=op_id,
                                suggestion="Consider adding a check for empty data before filtering"
                            ))
        
        return errors
    
    def get_validation_report(
        self,
        workflow_jsonl: str,
        agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Genera reporte completo de validación
        
        Args:
            workflow_jsonl: Workflow a validar
            agent_id: ID del agente
        
        Returns:
            Reporte de validación
        """
        is_valid, errors = self.validate_workflow(workflow_jsonl, agent_id)
        
        error_count = len([e for e in errors if e.severity == "error"])
        warning_count = len([e for e in errors if e.severity == "warning"])
        
        return {
            "valid": is_valid,
            "errors": error_count,
            "warnings": warning_count,
            "issues": [e.to_dict() for e in errors],
            "summary": self._generate_summary(errors)
        }
    
    def _generate_summary(self, errors: List[ValidationError]) -> Dict[str, Any]:
        """Genera resumen de errores"""
        by_type = {}
        by_operation = {}
        
        for error in errors:
            # Por tipo
            error_type = error.message.split(":")[0] if ":" in error.message else "Other"
            by_type[error_type] = by_type.get(error_type, 0) + 1
            
            # Por operación
            if error.operation_id:
                by_operation[error.operation_id] = by_operation.get(error.operation_id, 0) + 1
        
        return {
            "by_type": by_type,
            "by_operation": by_operation
        }

