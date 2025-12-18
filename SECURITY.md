# Seguridad en A2UI Workflow Executor

## Principio Fundamental de Seguridad

**La AI NO ejecuta código directamente. Solo indica QUÉ operaciones del catálogo ejecutar y en QUÉ orden.**

## Modelo de Seguridad

```
┌─────────────────────────────────────────────────┐
│           AGENTE (LLM)                         │
│                                                 │
│  Solo puede:                                    │
│  ✅ Indicar nombres de operaciones              │
│  ✅ Especificar parámetros                      │
│  ✅ Definir orden de ejecución                  │
│                                                 │
│  NO puede:                                      │
│  ❌ Ejecutar código arbitrario                  │
│  ❌ Crear nuevas operaciones                    │
│  ❌ Acceder a APIs no permitidas                │
│  ❌ Modificar código del cliente                │
└─────────────────────────────────────────────────┘
                    ↓
          [JSONL con operaciones]
                    ↓
┌─────────────────────────────────────────────────┐
│           CLIENTE (Executor)                    │
│                                                 │
│  Tiene control total:                           │
│  ✅ Código de operaciones pre-definido          │
│  ✅ Validación de operaciones                   │
│  ✅ Whitelist de APIs                          │
│  ✅ Sandboxing                                  │
│                                                 │
│  Ejecuta SOLO operaciones del catálogo         │
└─────────────────────────────────────────────────┘
```

## Cómo Funciona la Seguridad

### 1. Catálogo Pre-definido en el Cliente

```typescript
// Cliente define QUÉ operaciones existen
const OPERATION_CATALOG = {
  "ApiCall": {
    execute: async (config) => {
      // Código SEGURO pre-definido
      // Solo permite URLs de whitelist
      if (!isAllowedUrl(config.url)) {
        throw new Error("URL not allowed");
      }
      return await fetch(config.url);
    }
  },
  "FilterData": {
    execute: (config) => {
      // Código SEGURO pre-definido
      return filterData(config);
    }
  }
  // NO hay "ExecuteArbitraryCode" en el catálogo
};
```

### 2. Agente Solo Puede Referenciar Operaciones del Catálogo

```jsonl
// ✅ VÁLIDO: Operación del catálogo
{"operation": {"ApiCall": {"url": "...", "outputPath": "..."}}}

// ❌ INVÁLIDO: Operación no existe
{"operation": {"ExecuteArbitraryCode": {"code": "malicious()"}}}
// → El cliente rechaza: "Unknown operation type"
```

### 3. Validación Estricta

```python
# En workflow_executor.py - línea 118-137
async def _execute_operation(self, operation_type: str, config: Dict[str, Any]):
    # Solo ejecuta si está en el catálogo
    if operation_type == "ApiCall":
        return await self._execute_api_call(config)
    elif operation_type == "FilterData":
        return await self._execute_filter_data(config)
    # ...
    else:
        # ❌ Rechaza operaciones desconocidas
        raise ValueError(f"Unknown operation type: {operation_type}")
```

### 4. El Código Ejecutado es del Cliente

```python
# workflow_executor.py - línea 139-158
async def _execute_api_call(self, config: Dict[str, Any]):
    # Este código está en el CLIENTE, no en el agente
    url = self._resolve_path(config["url"])
    
    # Validación de seguridad
    if not self._is_url_allowed(url):
        raise SecurityError("URL not in whitelist")
    
    # Ejecución controlada
    async with aiohttp.ClientSession() as session:
        async with session.request(...) as response:
            return await response.json()
```

## Comparación: Seguro vs Inseguro

### ❌ INSEGURO (No usar)
```python
# Si el agente pudiera ejecutar código arbitrario:
agent_message = {"execute": "eval('malicious_code()')"}
exec(agent_message["execute"])  # ⚠️ PELIGROSO
```

### ✅ SEGURO (A2UI Workflow)
```python
# Agente solo puede referenciar operaciones del catálogo:
agent_message = {"operation": {"ApiCall": {"url": "..."}}}

# Cliente valida y ejecuta código pre-definido:
if operation_type in OPERATION_CATALOG:
    result = OPERATION_CATALOG[operation_type].execute(config)
else:
    raise SecurityError("Operation not allowed")
```

## Capas de Seguridad

### Capa 1: Validación de Operación
```python
# Solo operaciones del catálogo
allowed_operations = ["ApiCall", "FilterData", "StoreData"]
if operation_type not in allowed_operations:
    raise ValueError("Operation not in catalog")
```

### Capa 2: Validación de Parámetros
```python
# Validar que los parámetros son válidos
if operation_type == "ApiCall":
    url = config.get("url")
    if not self._is_url_allowed(url):
        raise SecurityError("URL not in whitelist")
```

### Capa 3: Sandboxing
```python
# Ejecutar en entorno aislado
with sandbox():
    result = await execute_operation(config)
```

### Capa 4: Rate Limiting
```python
# Limitar ejecuciones
if execution_count > MAX_EXECUTIONS_PER_MINUTE:
    raise RateLimitError("Too many executions")
```

## Ejemplo de Ataque Bloqueado

### Intento del Agente:
```jsonl
{"operationUpdate": {"operations": [
  {"id": "malicious", "operation": {
    "ExecuteCode": {
      "code": "import os; os.system('rm -rf /')"
    }
  }}
]}}
```

### Cliente Rechaza:
```python
# workflow_executor.py línea 136
else:
    raise ValueError(f"Unknown operation type: {operation_type}")
# Error: "Unknown operation type: ExecuteCode"
```

**Resultado**: El ataque es bloqueado porque `ExecuteCode` no está en el catálogo.

## Ventajas de Seguridad

1. **Whitelist de Operaciones**: Solo operaciones pre-aprobadas
2. **Código del Cliente**: Todo el código ejecutado está en el cliente
3. **Validación de Parámetros**: Cada operación valida sus parámetros
4. **Sin Ejecución Arbitraria**: Imposible ejecutar código no definido
5. **Auditable**: Todas las operaciones están en el catálogo

## Analogía

Es como un menú de restaurante:
- **Agente**: Puede pedir platos del menú (operaciones del catálogo)
- **Cliente**: Solo prepara platos del menú (ejecuta código pre-definido)
- **Agente NO puede**: Pedir ingredientes tóxicos o crear nuevos platos

## Conclusión

✅ **Correcto**: El código ejecutado es código pre-definido en el cliente
✅ **Correcto**: La AI solo indica qué operaciones ejecutar y en qué orden
✅ **Correcto**: No hay capacidad de ejecutar código arbitrario
✅ **Seguro**: Solo operaciones del catálogo pueden ejecutarse

