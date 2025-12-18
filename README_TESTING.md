# Guía de Testing - A2E

## Tests Disponibles

### 1. Test Básico (`run_agent_test.py`)

Test simple que verifica el flujo básico:
- Conexión del agente
- Obtención de capacidades
- Generación y ejecución de workflow simple
- Consulta de resultados

**Ejecutar**:
```bash
python run_agent_test.py
```

**Resultado esperado**: ✅ Todos los pasos completados exitosamente

### 2. Tests Complejos (`run_complex_tests.py`)

Suite completa de tests que cubre:
- Workflows con múltiples operaciones
- Flujo de datos entre operaciones
- Validación de workflows
- Ejecución concurrente
- Filtrado de capacidades
- Historial de ejecuciones
- Manejo de errores
- Workflows condicionales
- Workflows grandes (10+ operaciones)

**Ejecutar**:
```bash
python run_complex_tests.py
```

**Resultado esperado**: ✅ 9/9 tests pasados (100%)

## Estructura de Tests

### Test Runner

La clase `ComplexTestRunner` proporciona:
- Método `run_test()` para ejecutar tests individuales
- Registro automático de resultados
- Manejo de errores
- Resumen final

### Tests Incluidos

1. **Multiple Operations**: Workflow con 3 operaciones secuenciales
2. **Data Flow**: Workflow con flujo de datos entre operaciones
3. **Validation Errors**: Verificar que el validador funciona
4. **Concurrent Workflows**: 3 workflows ejecutados concurrentemente
5. **Capabilities Filtering**: Verificar filtrado por permisos
6. **Execution History**: Consultar historial de ejecuciones
7. **Error Handling**: Manejo de workflows inválidos
8. **Conditional Workflow**: Workflow con operaciones condicionales
9. **Large Workflow**: Workflow con 10 operaciones

## Interpretación de Resultados

### ✅ Test Pasado
- El test completó todas sus verificaciones
- El sistema funcionó como se esperaba

### ❌ Test Fallido
- El test encontró un problema
- Revisar el error en la salida
- Verificar logs del servidor

### ⚠️ Test con Advertencias
- El test pasó pero con advertencias
- Puede indicar comportamiento inesperado pero aceptable

## Debugging

### Ver Logs del Servidor

Los logs del servidor se muestran en la consola cuando se ejecutan los tests.

### Ver Detalles de Ejecución

Cada test que ejecuta un workflow genera un `execution_id` que se puede consultar:

```python
details = client.get_execution(execution_id)
print(json.dumps(details, indent=2))
```

### Verificar Estado del Servidor

```bash
curl http://localhost:8005/health
```

## Próximos Tests

Para expandir la cobertura de tests:

1. **Tests de Operaciones Reales**:
   - ApiCall con APIs reales
   - FilterData con datos reales
   - TransformData con transformaciones complejas

2. **Tests de Seguridad**:
   - Intentar usar credenciales no autorizadas
   - Intentar usar APIs no permitidas
   - Intentar ejecutar operaciones no permitidas

3. **Tests de Rendimiento**:
   - Workflows con 100+ operaciones
   - Múltiples workflows concurrentes (10+)
   - Workflows con operaciones que tardan mucho

4. **Tests de Resiliencia**:
   - Simular fallos de red
   - Simular timeouts
   - Simular errores en operaciones

## Contribuir Tests

Para agregar nuevos tests:

1. Crear método en `ComplexTestRunner`:
```python
def test_nuevo_caso(self):
    """Test: Descripción del caso"""
    print("\n[1/N] Paso 1...")
    # Código del test
    assert condicion, "Mensaje de error"
    return {"resultado": "datos"}
```

2. Agregar a la lista de tests:
```python
tests = [
    # ... tests existentes
    ("Nuevo Caso", runner.test_nuevo_caso),
]
```

3. Ejecutar y verificar que pasa

