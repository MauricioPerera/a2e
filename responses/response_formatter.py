"""
Sistema de formateo de respuestas para A2E
Filtra y formatea respuestas para entregar solo información útil al agente
"""

import json
from typing import Dict, Any, Optional, List, Union
from enum import Enum


class ResponseFormat(Enum):
    """Formato de respuesta"""
    FULL = "full"  # Respuesta completa
    SUMMARY = "summary"  # Solo resumen
    MINIMAL = "minimal"  # Mínimo necesario


class ResponseFormatter:
    """
    Formatea respuestas para entregar solo información útil al agente
    """
    
    def __init__(self, format: ResponseFormat = ResponseFormat.SUMMARY):
        """
        Inicializa el formateador
        
        Args:
            format: Formato de respuesta por defecto
        """
        self.format = format
    
    def format_success_response(
        self,
        execution_id: str,
        results: Dict[str, Any],
        format: Optional[ResponseFormat] = None
    ) -> Dict[str, Any]:
        """
        Formatea respuesta exitosa
        
        Args:
            execution_id: ID de la ejecución
            results: Resultados de todas las operaciones
            format: Formato a usar (si None, usa el por defecto)
        
        Returns:
            Respuesta formateada
        """
        format_type = format or self.format
        
        if format_type == ResponseFormat.MINIMAL:
            return self._format_minimal(results)
        elif format_type == ResponseFormat.SUMMARY:
            return self._format_summary(execution_id, results)
        else:
            return self._format_full(execution_id, results)
    
    def _format_minimal(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formato mínimo: solo datos esenciales
        """
        minimal = {
            "status": "success",
            "data": {}
        }
        
        # Extraer solo datos de outputPath
        for op_id, result in results.items():
            if isinstance(result, dict):
                # Si tiene estructura conocida, extraer datos útiles
                if "data" in result:
                    minimal["data"][op_id] = result["data"]
                elif "items" in result:
                    minimal["data"][op_id] = result["items"]
                else:
                    # Intentar extraer datos relevantes
                    relevant_keys = ["id", "name", "value", "result", "output"]
                    relevant_data = {
                        k: v for k, v in result.items()
                        if k in relevant_keys and v is not None
                    }
                    if relevant_data:
                        minimal["data"][op_id] = relevant_data
        
        return minimal
    
    def _format_summary(self, execution_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formato resumen: información útil sin saturar
        """
        summary = {
            "status": "success",
            "execution_id": execution_id,
            "operations": {},
            "data": {}
        }
        
        for op_id, result in results.items():
            # Información de la operación
            op_info = {
                "status": "success" if "error" not in str(result) else "failed"
            }
            
            # Extraer datos útiles
            if isinstance(result, dict):
                # Filtrar campos útiles
                useful_fields = self._extract_useful_fields(result)
                if useful_fields:
                    summary["data"][op_id] = useful_fields
                
                # Información adicional útil
                if "count" in result:
                    op_info["count"] = result["count"]
                if "duration_ms" in result:
                    op_info["duration_ms"] = result["duration_ms"]
            
            summary["operations"][op_id] = op_info
        
        return summary
    
    def _format_full(self, execution_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formato completo: toda la información (puede ser grande)
        """
        return {
            "status": "success",
            "execution_id": execution_id,
            "results": results
        }
    
    def _extract_useful_fields(self, data: Any, max_depth: int = 3, current_depth: int = 0) -> Any:
        """
        Extrae solo campos útiles de los datos
        
        Args:
            data: Datos a filtrar
            max_depth: Profundidad máxima a procesar
            current_depth: Profundidad actual
        """
        if current_depth >= max_depth:
            return None
        
        if isinstance(data, dict):
            # Campos útiles comunes
            useful_keys = [
                "id", "name", "title", "value", "result", "output",
                "data", "items", "results", "count", "total",
                "status", "message", "url", "path"
            ]
            
            filtered = {}
            for key, value in data.items():
                # Incluir si es una clave útil
                if key.lower() in [k.lower() for k in useful_keys]:
                    filtered[key] = self._extract_useful_fields(value, max_depth, current_depth + 1)
                # O si es un campo pequeño (probablemente útil)
                elif isinstance(value, (str, int, float, bool)) and len(str(value)) < 100:
                    filtered[key] = value
                # O si es una lista pequeña
                elif isinstance(value, list) and len(value) <= 10:
                    filtered[key] = [
                        self._extract_useful_fields(item, max_depth, current_depth + 1)
                        for item in value[:10]
                    ]
            
            return filtered if filtered else None
        
        elif isinstance(data, list):
            # Limitar tamaño de listas
            limited = data[:50]  # Máximo 50 items
            return [
                self._extract_useful_fields(item, max_depth, current_depth + 1)
                for item in limited
            ]
        
        else:
            return data
    
    def format_error_response(
        self,
        execution_id: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Formatea respuesta de error con contexto útil
        
        Args:
            execution_id: ID de la ejecución
            error: Excepción ocurrida
            context: Contexto adicional
            operation_id: ID de la operación que falló
        
        Returns:
            Respuesta de error formateada
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # Construir respuesta estructurada
        response = {
            "status": "error",
            "execution_id": execution_id,
            "error": {
                "type": error_type,
                "message": self._sanitize_error_message(error_message),
                "operation_id": operation_id
            }
        }
        
        # Agregar contexto relevante
        if context:
            relevant_context = self._extract_relevant_context(context, error)
            if relevant_context:
                response["error"]["context"] = relevant_context
        
        # Agregar sugerencias según tipo de error
        suggestions = self._get_error_suggestions(error_type, error_message)
        if suggestions:
            response["error"]["suggestions"] = suggestions
        
        return response
    
    def _sanitize_error_message(self, message: str) -> str:
        """
        Sanitiza mensaje de error removiendo información sensible o innecesaria
        """
        # Remover paths completos (pueden ser largos)
        import re
        message = re.sub(r'/[^\s]+', '[path]', message)
        
        # Remover stack traces largos
        if '\n' in message:
            lines = message.split('\n')
            # Mantener solo primeras líneas relevantes
            message = '\n'.join(lines[:3])
        
        # Limitar longitud
        if len(message) > 500:
            message = message[:500] + "..."
        
        return message
    
    def _extract_relevant_context(
        self,
        context: Dict[str, Any],
        error: Exception
    ) -> Dict[str, Any]:
        """
        Extrae solo contexto relevante para el error
        """
        relevant = {}
        
        # Contexto siempre útil
        if "operation_type" in context:
            relevant["operation_type"] = context["operation_type"]
        if "url" in context:
            # Solo dominio, no URL completa
            from urllib.parse import urlparse
            parsed = urlparse(context["url"])
            relevant["domain"] = parsed.netloc
        if "status_code" in context:
            relevant["status_code"] = context["status_code"]
        if "method" in context:
            relevant["method"] = context["method"]
        
        # Contexto específico por tipo de error
        error_type = type(error).__name__
        if "ConnectionError" in error_type or "Timeout" in error_type:
            if "timeout" in context:
                relevant["timeout"] = context["timeout"]
            if "retries" in context:
                relevant["retries"] = context["retries"]
        elif "HTTPError" in error_type or "status_code" in str(error):
            if "status_code" in context:
                relevant["status_code"] = context["status_code"]
            if "response_body" in context:
                # Solo primeros caracteres del body
                body = str(context["response_body"])
                relevant["response_preview"] = body[:200] if len(body) > 200 else body
        
        return relevant
    
    def _get_error_suggestions(self, error_type: str, error_message: str) -> List[str]:
        """
        Retorna sugerencias útiles según el tipo de error
        """
        suggestions = []
        
        if "ConnectionError" in error_type or "timeout" in error_message.lower():
            suggestions.append("Verify network connectivity")
            suggestions.append("Check if the API endpoint is accessible")
            suggestions.append("Consider increasing timeout if operation is slow")
        
        elif "HTTPError" in error_type or "status_code" in error_message:
            if "401" in error_message or "403" in error_message:
                suggestions.append("Check authentication credentials")
                suggestions.append("Verify API key or token is valid")
            elif "404" in error_message:
                suggestions.append("Verify the endpoint URL is correct")
            elif "429" in error_message:
                suggestions.append("Rate limit exceeded, wait before retrying")
            elif "500" in error_message or "502" in error_message or "503" in error_message:
                suggestions.append("Server error, try again later")
        
        elif "ValueError" in error_type or "invalid" in error_message.lower():
            suggestions.append("Check input parameters are valid")
            suggestions.append("Verify data format matches expected schema")
        
        elif "KeyError" in error_type or "not found" in error_message.lower():
            suggestions.append("Verify the requested resource exists")
            suggestions.append("Check field names are correct")
        
        return suggestions
    
    def format_partial_success(
        self,
        execution_id: str,
        successful_operations: Dict[str, Any],
        failed_operations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Formatea respuesta cuando algunas operaciones fallaron
        
        Args:
            execution_id: ID de la ejecución
            successful_operations: Operaciones exitosas
            failed_operations: Operaciones fallidas con errores
        """
        return {
            "status": "partial_success",
            "execution_id": execution_id,
            "successful": {
                "count": len(successful_operations),
                "operations": successful_operations
            },
            "failed": {
                "count": len(failed_operations),
                "operations": {
                    op_id: self.format_error_response(
                        execution_id=execution_id,
                        error=error if isinstance(error, Exception) else Exception(str(error)),
                        operation_id=op_id
                    )["error"]
                    for op_id, error in failed_operations.items()
                }
            }
        }

