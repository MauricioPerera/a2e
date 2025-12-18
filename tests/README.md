# A2E Test Suite

## Batería de Tests Completa

Suite de tests para validar cada componente del sistema A2E.

## Estructura de Tests

### 1. `test_workflow_executor.py`
Tests para el ejecutor de workflows:
- ✅ Ejecución de workflows simples
- ✅ Flujo de datos entre operaciones
- ✅ Orden de ejecución
- ✅ Manejo de errores
- ✅ Operaciones de data model

### 2. `test_api_knowledge_base.py`
Tests para la base de conocimiento de APIs:
- ✅ Agregar APIs
- ✅ Agregar endpoints
- ✅ Búsqueda de endpoints
- ✅ Construcción de catálogo
- ✅ Listado de APIs disponibles

### 3. `test_credentials_vault.py`
Tests para el vault de credenciales:
- ✅ Almacenar y obtener credenciales
- ✅ Encriptación de credenciales
- ✅ Listado de credenciales (solo metadatos)
- ✅ Inyección de credenciales
- ✅ Eliminación de credenciales

### 4. `test_agent_auth.py`
Tests para autenticación y autorización:
- ✅ Registro de agentes
- ✅ Autenticación con API key
- ✅ Generación y verificación de tokens JWT
- ✅ Permisos de agentes
- ✅ Filtrado de capacidades
- ✅ Middleware de autenticación

### 5. `test_validation.py`
Tests para validación de workflows:
- ✅ Validación de estructura
- ✅ Validación de dependencias
- ✅ Validación de tipos de datos
- ✅ Validación de referencias condicionales
- ✅ Niveles de validación
- ✅ Reportes de validación

### 6. `test_responses.py`
Tests para gestión de respuestas y errores:
- ✅ Formateo de respuestas exitosas (minimal, summary, full)
- ✅ Formateo de errores
- ✅ Éxito parcial
- ✅ Extracción de campos útiles
- ✅ Manejo de diferentes tipos de errores
- ✅ Formateo de errores para agente

### 7. `test_monitoring.py`
Tests para monitoreo y auditoría:
- ✅ Registro de inicio de ejecución
- ✅ Registro de operaciones
- ✅ Registro de uso de credenciales
- ✅ Registro de resultados
- ✅ Consultas por agente/estado
- ✅ Obtención de detalles completos

### 8. `test_integration.py`
Tests de integración completa:
- ✅ Ejecución completa de workflow
- ✅ Workflow con validación previa
- ✅ Flujo de autenticación completo
- ✅ Filtrado de capacidades
- ✅ Manejo de errores en ejecución
- ✅ Integración con monitoreo

## Ejecutar Tests

### Todos los tests

```bash
pytest tests/
```

### Tests específicos

```bash
# Solo tests de ejecutor
pytest tests/test_workflow_executor.py

# Solo tests de validación
pytest tests/test_validation.py

# Test específico
pytest tests/test_workflow_executor.py::test_simple_workflow
```

### Con cobertura

```bash
pytest tests/ --cov=. --cov-report=html
```

### Con verbose

```bash
pytest tests/ -v
```

## Cobertura

Los tests cubren:
- ✅ Todos los componentes principales
- ✅ Flujos de éxito y error
- ✅ Casos límite
- ✅ Integración entre componentes
- ✅ Validación de seguridad

## Fixtures

Los tests usan fixtures para:
- Crear instancias limpias de componentes
- Configurar directorios temporales
- Limpiar después de cada test

## Ejemplos de Uso

### Test de Ejecutor

```python
@pytest.mark.asyncio
async def test_simple_workflow(executor):
    workflow = '{"operationUpdate": {...}}'
    executor.load_workflow(workflow)
    results = await executor.execute()
    assert "op1" in results
```

### Test de Validación

```python
def test_validate_structure(validator):
    is_valid, errors = validator.validate_workflow(workflow)
    assert is_valid is False
    assert any("missing required 'id'" in e.message for e in errors)
```

### Test de Integración

```python
@pytest.mark.asyncio
async def test_full_workflow_execution(full_system):
    executor = full_system["executor"]
    executor.load_workflow(workflow, agent_id="agent-123")
    response = await executor.execute()
    assert response["status"] == "success"
```

## Próximos Tests

- [ ] Tests de rendimiento
- [ ] Tests de carga
- [ ] Tests de seguridad (penetration)
- [ ] Tests de regresión
- [ ] Tests de compatibilidad

