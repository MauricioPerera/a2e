# A2E Workflow Validation

## Sistema de Validación Proactiva

A diferencia de A2UI que renderiza UI, **A2E necesita validar workflows antes de ejecutarlos** para prevenir errores comunes.

## Concepto

El sistema valida workflows y detecta:
- **Errores críticos**: Combinaciones que definitivamente fallarán
- **Advertencias**: Patrones problemáticos que probablemente fallarán
- **Sugerencias**: Mejoras para evitar problemas

## Tipos de Validación

### 1. Validación de Estructura

- Operaciones sin ID
- IDs duplicados
- Operaciones mal formadas

```json
{
  "severity": "error",
  "message": "Operation missing required 'id' field"
}
```

### 2. Validación de Dependencias

- Referencias a operaciones inexistentes
- Dependencias circulares
- Orden incorrecto de operaciones

```json
{
  "severity": "error",
  "message": "Operation 'filter' references non-existent operation 'fetch' in inputPath",
  "suggestion": "Ensure operation 'fetch' exists before 'filter'"
}
```

### 3. Validación de Tipos de Datos

- Operaciones que requieren arrays pero reciben otros tipos
- Incompatibilidad de tipos entre operaciones

```json
{
  "severity": "error",
  "message": "FilterData operation 'filter' requires array input, but 'transform' produces 'value'",
  "suggestion": "Ensure 'transform' produces an array, or use TransformData to convert it"
}
```

### 4. Validación de Compatibilidad de APIs

- URLs de APIs no registradas
- Endpoints que no existen
- Métodos HTTP incorrectos
- Permisos del agente

```json
{
  "severity": "error",
  "message": "Agent 'agent-123' does not have permission to use API 'user-api'",
  "suggestion": "Request access to 'user-api' or use a different API"
}
```

### 5. Validación de Credenciales

- Credenciales inexistentes
- Credenciales sin permisos
- Referencias inválidas

```json
{
  "severity": "error",
  "message": "Credential 'api-token' referenced in operation 'fetch' does not exist",
  "suggestion": "Register credential 'api-token' in the vault"
}
```

### 6. Validación de Patrones Problemáticos

- Loops infinitos potenciales
- Operaciones que pueden fallar con datos vacíos
- Patrones comúnmente problemáticos

```json
{
  "severity": "warning",
  "message": "FilterData operation 'filter' may fail if API call 'fetch' returns empty array",
  "suggestion": "Consider adding a check for empty data before filtering"
}
```

## Niveles de Validación

### STRICT
Rechaza cualquier posible error, incluyendo advertencias.

### MODERATE (Por defecto)
Rechaza solo errores críticos probables.

### LENIENT
Solo rechaza errores seguros que definitivamente fallarán.

## Uso

### Validación Básica

```python
from validation.workflow_validator import WorkflowValidator, ValidationLevel

validator = WorkflowValidator(
    api_kb=api_kb,
    vault=vault,
    auth=auth,
    level=ValidationLevel.MODERATE
)

is_valid, errors = validator.validate_workflow(workflow_jsonl, agent_id="agent-123")

if not is_valid:
    for error in errors:
        print(f"{error.severity}: {error.message}")
        if error.suggestion:
            print(f"  Suggestion: {error.suggestion}")
```

### Reporte Completo

```python
report = validator.get_validation_report(workflow_jsonl, agent_id="agent-123")

print(f"Valid: {report['valid']}")
print(f"Errors: {report['errors']}")
print(f"Warnings: {report['warnings']}")

for issue in report['issues']:
    print(f"- {issue['severity']}: {issue['message']}")
```

### Agente con Validación

```python
from agent_with_validation import ValidatedWorkflowAgent

agent = ValidatedWorkflowAgent(
    agent_id="agent-123",
    api_key="key",
    api_kb=api_kb,
    vault=vault,
    auth=auth
)

# Validar antes de ejecutar
is_valid, report = agent.validate_and_suggest(workflow_jsonl)

if is_valid:
    # Ejecutar workflow
    result = await executor.execute()
else:
    # Mostrar errores y sugerencias
    print("Workflow has errors:")
    for issue in report['issues']:
        print(f"  {issue['message']}")
        if issue.get('suggestion'):
            print(f"    → {issue['suggestion']}")
```

### Generación con Validación

```python
# Genera workflow, valida, y corrige si es necesario
workflow_jsonl, report = agent.generate_validated_workflow(
    user_query="Consulta API y filtra datos",
    llm_generate_func=llm.generate_workflow
)

if report['valid']:
    # Workflow válido, ejecutar
    result = await executor.execute()
```

## Ejemplos de Errores Detectados

### Error: Dependencia Inexistente

```json
{
  "severity": "error",
  "message": "Operation 'filter' references non-existent operation 'fetch' in inputPath",
  "operation_id": "filter",
  "suggestion": "Ensure operation 'fetch' exists before 'filter'"
}
```

### Error: Tipo Incompatible

```json
{
  "severity": "error",
  "message": "FilterData operation 'filter' requires array input, but 'transform' produces 'value'",
  "operation_id": "filter",
  "suggestion": "Ensure 'transform' produces an array, or use TransformData to convert it"
}
```

### Error: Sin Permisos

```json
{
  "severity": "error",
  "message": "Agent 'agent-123' does not have permission to use API 'user-api'",
  "operation_id": "fetch",
  "suggestion": "Request access to 'user-api' or use a different API"
}
```

### Advertencia: Patrón Problemático

```json
{
  "severity": "warning",
  "message": "FilterData operation 'filter' may fail if API call 'fetch' returns empty array",
  "operation_id": "filter",
  "suggestion": "Consider adding a check for empty data before filtering"
}
```

## Ventajas

1. **Previene errores**: Detecta problemas antes de ejecutar
2. **Ahorra tiempo**: No ejecuta workflows que fallarán
3. **Mejora calidad**: Sugerencias para workflows mejores
4. **Educativo**: Ayuda al agente a aprender patrones correctos

## Comparación con A2UI

| Aspecto | A2UI | A2E |
|---------|------|-----|
| **Validación** | Validación de componentes UI | Validación de workflows completos |
| **Errores** | Errores de renderizado | Errores de ejecución previstos |
| **Prevención** | No aplica | Validación proactiva antes de ejecutar |

## Flujo Completo

1. **Agente genera workflow** desde query del usuario
2. **Sistema valida workflow** antes de ejecutar
3. **Si hay errores**: Retorna errores y sugerencias
4. **Agente corrige workflow** usando sugerencias
5. **Sistema valida de nuevo** hasta que sea válido
6. **Ejecuta workflow** solo cuando es válido

## Integración con Otros Sistemas

- **Autenticación**: Valida permisos del agente
- **API Knowledge Base**: Valida que APIs existen y son accesibles
- **Credentials Vault**: Valida que credenciales existen y son accesibles
- **Monitoring**: Los errores de validación se registran para análisis

