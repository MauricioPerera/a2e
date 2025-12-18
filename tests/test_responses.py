"""
Tests para Gestión de Respuestas y Errores
"""

import pytest
from responses.response_formatter import ResponseFormatter, ResponseFormat
from responses.error_handler import (
    ErrorHandler, A2EError, NetworkError, APIError,
    ValidationError, ErrorCategory
)


@pytest.fixture
def formatter():
    """Fixture para crear formateador"""
    return ResponseFormatter(format=ResponseFormat.SUMMARY)


def test_format_minimal_response(formatter):
    """Test formateo de respuesta mínima"""
    results = {
        "fetch": {"data": {"id": "1", "name": "Alice"}},
        "filter": {"items": [{"id": "1"}]}
    }
    
    response = formatter.format_success_response(
        execution_id="test",
        results=results,
        format=ResponseFormat.MINIMAL
    )
    
    assert response["status"] == "success"
    assert "data" in response
    assert "fetch" in response["data"]


def test_format_summary_response(formatter):
    """Test formateo de respuesta resumen"""
    results = {
        "fetch": {"data": {"id": "1", "name": "Alice"}, "count": 100},
        "filter": {"items": [{"id": "1"}], "count": 25}
    }
    
    response = formatter.format_success_response(
        execution_id="test",
        results=results
    )
    
    assert response["status"] == "success"
    assert "operations" in response
    assert "data" in response
    assert response["operations"]["fetch"]["status"] == "success"


def test_format_error_response(formatter):
    """Test formateo de respuesta de error"""
    error = Exception("API returned status 404")
    context = {"url": "https://api.example.com/users", "status_code": 404}
    
    response = formatter.format_error_response(
        execution_id="test",
        error=error,
        context=context,
        operation_id="fetch"
    )
    
    assert response["status"] == "error"
    assert "error" in response
    assert response["error"]["operation_id"] == "fetch"
    assert "suggestions" in response["error"]


def test_format_partial_success(formatter):
    """Test formateo de éxito parcial"""
    successful = {"fetch": {"data": [1, 2, 3]}}
    failed = {"filter": Exception("Filter failed")}
    
    response = formatter.format_partial_success(
        execution_id="test",
        successful_operations=successful,
        failed_operations=failed
    )
    
    assert response["status"] == "partial_success"
    assert response["successful"]["count"] == 1
    assert response["failed"]["count"] == 1


def test_extract_useful_fields(formatter):
    """Test extracción de campos útiles"""
    data = {
        "id": "1",
        "name": "Alice",
        "large_field": "x" * 200,  # Campo grande
        "nested": {
            "deep": {
                "very_deep": {
                    "value": "too deep"  # Muy profundo
                }
            }
        }
    }
    
    useful = formatter._extract_useful_fields(data, max_depth=2)
    
    assert "id" in useful
    assert "name" in useful
    # Campo grande puede estar truncado o no incluido
    # Profundidad limitada


def test_error_handler_network_error():
    """Test manejo de error de red"""
    error = ConnectionError("Connection timeout")
    
    structured = ErrorHandler.handle_exception(
        exception=error,
        operation_id="fetch",
        context={"url": "https://api.example.com"}
    )
    
    assert isinstance(structured, NetworkError)
    assert structured.category == ErrorCategory.NETWORK
    assert structured.operation_id == "fetch"


def test_error_handler_api_error():
    """Test manejo de error de API"""
    class HTTPError(Exception):
        status_code = 404
    
    error = HTTPError("Not found")
    
    structured = ErrorHandler.handle_exception(
        exception=error,
        operation_id="fetch",
        context={"url": "https://api.example.com/users"}
    )
    
    assert isinstance(structured, APIError)
    assert structured.category == ErrorCategory.API_ERROR
    assert structured.context.get("status_code") == 404


def test_error_handler_format_for_agent():
    """Test formateo de error para agente"""
    error = APIError(
        message="API returned status 401",
        status_code=401,
        operation_id="fetch"
    )
    
    formatted = ErrorHandler.format_error_for_agent(error)
    
    assert formatted["status"] == "error"
    assert formatted["error"]["type"] == "APIError"
    assert formatted["error"]["category"] == "api_error"
    assert "suggestions" in formatted
    assert len(formatted["suggestions"]) > 0

