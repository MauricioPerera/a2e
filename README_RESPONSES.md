# A2E Response & Error Management

## Sistema de Gestión de Respuestas

A diferencia de A2UI que renderiza UI, **A2E necesita gestionar respuestas de datos y errores** de forma que:

1. **Respuestas exitosas**: Solo información útil, sin saturar al agente
2. **Errores**: Contexto claro y relevante, sin información inútil
3. **Formato estructurado**: Fácil de procesar por el agente

## Formateo de Respuestas Exitosas

### Formatos Disponibles

1. **MINIMAL**: Solo datos esenciales
2. **SUMMARY**: Resumen con información útil (por defecto)
3. **FULL**: Toda la información (puede ser grande)

### Ejemplo: Respuesta MINIMAL

```json
{
  "status": "success",
  "data": {
    "fetch": {
      "id": "user-123",
      "name": "John Doe"
    },
    "filter": [
      {"id": "user-123", "points": 150}
    ]
  }
}
```

### Ejemplo: Respuesta SUMMARY

```json
{
  "status": "success",
  "execution_id": "abc123",
  "operations": {
    "fetch": {"status": "success", "count": 100},
    "filter": {"status": "success", "count": 25}
  },
  "data": {
    "fetch": {
      "id": "user-123",
      "name": "John Doe",
      "points": 150
    },
    "filter": [
      {"id": "user-123", "points": 150}
    ]
  }
}
```

### Filtrado Automático

El sistema automáticamente:
- **Extrae campos útiles**: id, name, value, result, output, etc.
- **Limita listas grandes**: Máximo 50 items en listas
- **Limita profundidad**: Máximo 3 niveles de anidación
- **Remueve campos grandes**: Strings > 100 caracteres se truncan

## Manejo de Errores Estructurado

### Tipos de Errores

1. **AuthenticationError**: Error de autenticación
2. **AuthorizationError**: Error de autorización
3. **ValidationError**: Error de validación
4. **NetworkError**: Error de red
5. **APIError**: Error de API (con status code)
6. **DataError**: Error de datos
7. **ExecutionError**: Error de ejecución

### Ejemplo: Error Estructurado

```json
{
  "status": "error",
  "error": {
    "type": "APIError",
    "category": "api_error",
    "message": "API returned status 404",
    "operation_id": "fetch",
    "recoverable": true,
    "context": {
      "status_code": 404,
      "domain": "api.example.com",
      "method": "GET"
    }
  },
  "suggestions": [
    "Verify the endpoint URL is correct",
    "Check if the resource exists"
  ]
}
```

### Contexto Relevante

El sistema incluye solo contexto útil:
- **Status codes**: Para errores HTTP
- **Dominios**: Para errores de red (no URLs completas)
- **Campos**: Para errores de validación
- **Paths de datos**: Para errores de datos

### Sugerencias Automáticas

Según el tipo de error, se incluyen sugerencias:

- **NetworkError**: "Check network connectivity", "Verify API endpoint is accessible"
- **APIError 401**: "Authentication failed - check credentials"
- **APIError 404**: "Resource not found - verify endpoint URL"
- **ValidationError**: "Check input parameters are valid"

## Respuestas Parciales

Cuando algunas operaciones fallan:

```json
{
  "status": "partial_success",
  "execution_id": "abc123",
  "successful": {
    "count": 2,
    "operations": {
      "fetch": {...},
      "transform": {...}
    }
  },
  "failed": {
    "count": 1,
    "operations": {
      "filter": {
        "type": "DataError",
        "message": "Invalid filter condition",
        "suggestions": [...]
      }
    }
  }
}
```

## Uso

### Ejecutor con Respuestas

```python
from workflow_executor_with_responses import RobustWorkflowExecutor
from responses.response_formatter import ResponseFormat

executor = RobustWorkflowExecutor(
    response_format=ResponseFormat.SUMMARY
)

executor.load_workflow(workflow_jsonl)
response = await executor.execute()

# response contiene:
# - status: "success", "error", o "partial_success"
# - Datos formateados (solo útiles)
# - Errores estructurados (si hay)
```

### Manejo de Errores

```python
from responses.error_handler import ErrorHandler, NetworkError

try:
    result = await api_call()
except Exception as e:
    # Convertir a error estructurado
    structured = ErrorHandler.handle_exception(
        exception=e,
        operation_id="fetch",
        context={"url": "https://api.example.com/users"}
    )
    
    # Formatear para agente
    response = ErrorHandler.format_error_for_agent(structured)
```

## Ventajas

1. **No satura al agente**: Solo información útil
2. **Errores claros**: Contexto relevante y sugerencias
3. **Estructurado**: Fácil de procesar
4. **Sanitizado**: Sin información sensible o innecesaria

## Comparación con A2UI

| Aspecto | A2UI | A2E |
|---------|------|-----|
| **Respuestas** | UI renderizada | Datos formateados |
| **Errores** | Errores de renderizado | Errores estructurados con contexto |
| **Formato** | Componentes visuales | JSON estructurado |
| **Filtrado** | No aplica | Filtrado automático de datos |

## Ejemplos

### Respuesta Exitosa (Summary)

```json
{
  "status": "success",
  "execution_id": "abc123",
  "operations": {
    "fetch": {"status": "success", "count": 100},
    "filter": {"status": "success", "count": 25}
  },
  "data": {
    "filter": [
      {"id": "user-1", "name": "Alice", "points": 150},
      {"id": "user-2", "name": "Bob", "points": 200}
    ]
  }
}
```

### Error de API

```json
{
  "status": "error",
  "error": {
    "type": "APIError",
    "category": "api_error",
    "message": "API returned status 401",
    "operation_id": "fetch",
    "recoverable": true,
    "context": {
      "status_code": 401,
      "domain": "api.example.com"
    }
  },
  "suggestions": [
    "Authentication failed - check credentials",
    "Verify API key or token is valid"
  ]
}
```

### Éxito Parcial

```json
{
  "status": "partial_success",
  "execution_id": "abc123",
  "successful": {
    "count": 1,
    "operations": {
      "fetch": {"status": "success", "count": 100}
    }
  },
  "failed": {
    "count": 1,
    "operations": {
      "filter": {
        "type": "ValidationError",
        "message": "Invalid filter condition: field 'points' not found",
        "suggestions": [
          "Check input parameters are valid",
          "Verify data format matches expected schema"
        ]
      }
    }
  }
}
```

