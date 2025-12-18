"""
Sistema de manejo de errores estructurado para A2E
"""

from typing import Dict, Any, Optional, Type
from enum import Enum
import traceback


class ErrorCategory(Enum):
    """Categorías de errores"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    NETWORK = "network"
    API_ERROR = "api_error"
    DATA_ERROR = "data_error"
    EXECUTION = "execution"
    UNKNOWN = "unknown"


class A2EError(Exception):
    """Error base de A2E con contexto estructurado"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        context: Optional[Dict[str, Any]] = None,
        operation_id: Optional[str] = None,
        recoverable: bool = False
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.context = context or {}
        self.operation_id = operation_id
        self.recoverable = recoverable
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte error a diccionario estructurado"""
        return {
            "type": self.__class__.__name__,
            "category": self.category.value,
            "message": self.message,
            "operation_id": self.operation_id,
            "recoverable": self.recoverable,
            "context": self._sanitize_context()
        }
    
    def _sanitize_context(self) -> Dict[str, Any]:
        """Sanitiza contexto removiendo información sensible"""
        sanitized = {}
        
        for key, value in self.context.items():
            # Remover información sensible
            if any(sensitive in key.lower() for sensitive in ["password", "token", "secret", "key", "auth"]):
                sanitized[key] = "[REDACTED]"
            # Limitar tamaño de strings
            elif isinstance(value, str) and len(value) > 200:
                sanitized[key] = value[:200] + "..."
            else:
                sanitized[key] = value
        
        return sanitized


class AuthenticationError(A2EError):
    """Error de autenticación"""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            category=ErrorCategory.AUTHENTICATION,
            context=context,
            recoverable=False
        )


class AuthorizationError(A2EError):
    """Error de autorización"""
    def __init__(self, message: str, resource: str, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        context["resource"] = resource
        super().__init__(
            message,
            category=ErrorCategory.AUTHORIZATION,
            context=context,
            recoverable=False
        )


class ValidationError(A2EError):
    """Error de validación"""
    def __init__(self, message: str, field: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if field:
            context["field"] = field
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            context=context,
            recoverable=True
        )


class NetworkError(A2EError):
    """Error de red"""
    def __init__(self, message: str, url: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            context["domain"] = parsed.netloc
        super().__init__(
            message,
            category=ErrorCategory.NETWORK,
            context=context,
            recoverable=True
        )


class APIError(A2EError):
    """Error de API"""
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        context = context or {}
        if status_code:
            context["status_code"] = status_code
        if response_body:
            # Solo primeros caracteres
            context["response_preview"] = response_body[:200] if len(response_body) > 200 else response_body
        super().__init__(
            message,
            category=ErrorCategory.API_ERROR,
            context=context,
            recoverable=status_code and status_code < 500  # Errores 4xx son recuperables
        )


class DataError(A2EError):
    """Error de datos"""
    def __init__(self, message: str, data_path: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        context = context or {}
        if data_path:
            context["data_path"] = data_path
        super().__init__(
            message,
            category=ErrorCategory.DATA_ERROR,
            context=context,
            recoverable=True
        )


class ExecutionError(A2EError):
    """Error de ejecución"""
    def __init__(self, message: str, operation_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            category=ErrorCategory.EXECUTION,
            context=context,
            operation_id=operation_id,
            recoverable=False
        )


class ErrorHandler:
    """
    Maneja errores y los convierte a formato estructurado
    """
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        operation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> A2EError:
        """
        Convierte una excepción genérica a A2EError estructurado
        
        Args:
            exception: Excepción a manejar
            operation_id: ID de la operación donde ocurrió
            context: Contexto adicional
        
        Returns:
            A2EError estructurado
        """
        # Si ya es A2EError, retornar directamente
        if isinstance(exception, A2EError):
            if operation_id and not exception.operation_id:
                exception.operation_id = operation_id
            return exception
        
        # Convertir excepciones comunes
        error_type = type(exception).__name__
        error_message = str(exception)
        
        context = context or {}
        
        # Detectar tipo de error
        if "ConnectionError" in error_type or "timeout" in error_message.lower():
            return NetworkError(
                message=f"Network error: {error_message}",
                context=context,
                operation_id=operation_id
            )
        
        elif "HTTPError" in error_type or "status_code" in error_message:
            # Intentar extraer status code
            status_code = None
            if hasattr(exception, "status_code"):
                status_code = exception.status_code
            elif "401" in error_message:
                status_code = 401
            elif "403" in error_message:
                status_code = 403
            elif "404" in error_message:
                status_code = 404
            elif "429" in error_message:
                status_code = 429
            elif "500" in error_message:
                status_code = 500
            
            return APIError(
                message=f"API error: {error_message}",
                status_code=status_code,
                context=context,
                operation_id=operation_id
            )
        
        elif "ValueError" in error_type or "KeyError" in error_type:
            return ValidationError(
                message=f"Validation error: {error_message}",
                context=context,
                operation_id=operation_id
            )
        
        else:
            # Error desconocido
            return A2EError(
                message=error_message,
                category=ErrorCategory.UNKNOWN,
                context=context,
                operation_id=operation_id
            )
    
    @staticmethod
    def format_error_for_agent(error: A2EError) -> Dict[str, Any]:
        """
        Formatea error para enviar al agente
        
        Args:
            error: Error estructurado
        
        Returns:
            Diccionario formateado para el agente
        """
        return {
            "status": "error",
            "error": error.to_dict(),
            "recoverable": error.recoverable,
            "suggestions": ErrorHandler._get_suggestions(error)
        }
    
    @staticmethod
    def _get_suggestions(error: A2EError) -> list[str]:
        """Obtiene sugerencias según el tipo de error"""
        suggestions = []
        
        if error.category == ErrorCategory.AUTHENTICATION:
            suggestions.append("Check API key or token is valid")
            suggestions.append("Verify credentials are correctly configured")
        
        elif error.category == ErrorCategory.AUTHORIZATION:
            suggestions.append("Verify agent has permission to access this resource")
            suggestions.append("Check agent permissions configuration")
        
        elif error.category == ErrorCategory.NETWORK:
            suggestions.append("Check network connectivity")
            suggestions.append("Verify API endpoint is accessible")
            suggestions.append("Consider retrying after a short delay")
        
        elif error.category == ErrorCategory.API_ERROR:
            if error.context.get("status_code") == 401:
                suggestions.append("Authentication failed - check credentials")
            elif error.context.get("status_code") == 403:
                suggestions.append("Access denied - check permissions")
            elif error.context.get("status_code") == 404:
                suggestions.append("Resource not found - verify endpoint URL")
            elif error.context.get("status_code") == 429:
                suggestions.append("Rate limit exceeded - wait before retrying")
            else:
                suggestions.append("API returned an error - check API status")
        
        elif error.category == ErrorCategory.VALIDATION:
            suggestions.append("Check input parameters are valid")
            suggestions.append("Verify data format matches expected schema")
        
        elif error.category == ErrorCategory.DATA_ERROR:
            suggestions.append("Check data format and structure")
            suggestions.append("Verify required fields are present")
        
        return suggestions

