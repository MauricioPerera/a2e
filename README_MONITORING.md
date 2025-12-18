# A2E Monitoring & Auditing

## Sistema de Monitoreo

A diferencia de A2UI que principalmente renderiza UI, **A2E requiere monitoreo robusto** porque:

1. **Ejecuta código**: Necesita rastrear qué se ejecutó
2. **Usa credenciales**: Necesita auditoría de acceso a credenciales
3. **Hace llamadas externas**: Necesita rastrear APIs llamadas
4. **Procesa datos**: Necesita rastrear resultados

## Componentes del Sistema

### 1. Audit Logger

Registra todas las ejecuciones con detalles completos:

- **Inicio de ejecución**: Agente, workflow, timestamp
- **Operaciones**: Tipo, configuración, duración
- **Credenciales usadas**: Qué credencial se usó, en qué operación
- **Resultados**: Éxito/fallo, resultados, errores
- **Finalización**: Resumen completo de la ejecución

### 2. Monitored Executor

Ejecutor que integra monitoreo automático:

```python
from workflow_executor_monitored import MonitoredWorkflowExecutor
from monitoring.audit_logger import AuditLogger

logger = AuditLogger(log_dir="logs")
executor = MonitoredWorkflowExecutor(audit_logger=logger)
executor.set_agent_context("agent-123")
executor.load_workflow(workflow_jsonl, agent_id="agent-123")
results = await executor.execute()
```

### 3. Monitoring CLI

Herramienta CLI para consultar y analizar logs:

```bash
# Listar ejecuciones
python monitoring/monitor_cli.py list --limit 10

# Ver detalles de ejecución
python monitoring/monitor_cli.py show --execution-id abc123

# Estadísticas
python monitoring/monitor_cli.py stats

# Exportar logs
python monitoring/monitor_cli.py export --output logs.json
```

## Qué se Registra

### Por Ejecución

- **Execution ID**: ID único de la ejecución
- **Agent ID**: Qué agente inició la ejecución
- **Workflow ID**: Qué workflow se ejecutó
- **Workflow JSONL**: El workflow completo (para auditoría)
- **Status**: pending → running → success/failed
- **Duration**: Duración total en milisegundos
- **Results**: Resultados de todas las operaciones

### Por Operación

- **Operation ID**: ID de la operación
- **Operation Type**: ApiCall, FilterData, etc.
- **Config**: Configuración (sanitizada, sin credenciales)
- **Status**: success/failed
- **Duration**: Duración en milisegundos
- **Result**: Resultado de la operación
- **Error**: Mensaje de error si falló

### Por Credencial

- **Credential ID**: ID de la credencial usada
- **Credential Type**: bearer-token, api-key, etc.
- **Operation ID**: En qué operación se usó
- **Usage Context**: Cómo se usó (ej: "Authorization header")
- **Timestamp**: Cuándo se usó

## Archivos de Log

### audit_YYYYMMDD.log
Log estándar con formato de texto:

```
2025-01-15 10:30:45 - INFO - Execution started: abc123 by agent agent-123
2025-01-15 10:30:46 - INFO - Operation started: fetch (ApiCall) in execution abc123
2025-01-15 10:30:46 - INFO - Credential used: api-token (bearer-token) in operation fetch
2025-01-15 10:30:47 - INFO - Operation completed: fetch in 1200ms
2025-01-15 10:30:47 - INFO - Execution completed: abc123 in 1500ms
```

### executions_YYYYMMDD.jsonl
Log estructurado en JSONL (una línea por evento):

```jsonl
{"timestamp": "2025-01-15T10:30:45", "execution_id": "abc123", "agent_id": "agent-123", "workflow_id": "user-filter", "status": "pending"}
{"timestamp": "2025-01-15T10:30:46", "execution_id": "abc123", "operation_id": "fetch", "operation_type": "ApiCall", "status": "running"}
{"timestamp": "2025-01-15T10:30:46", "execution_id": "abc123", "operation_id": "fetch", "credential_id": "api-token", "event_type": "credential_usage"}
{"timestamp": "2025-01-15T10:30:47", "execution_id": "abc123", "operation_id": "fetch", "status": "success", "duration_ms": 1200}
{"timestamp": "2025-01-15T10:30:47", "execution_id": "abc123", "status": "success", "total_duration_ms": 1500}
```

## Consultas Comunes

### ¿Qué ejecutó un agente?

```bash
python monitoring/monitor_cli.py list --agent-id agent-123
```

### ¿Qué workflows fallaron?

```bash
python monitoring/monitor_cli.py list --status failed
```

### ¿Qué credenciales se usaron en una ejecución?

```bash
python monitoring/monitor_cli.py show --execution-id abc123
# Muestra sección "Credentials Used"
```

### ¿Cuánto tiempo toma cada operación?

```bash
python monitoring/monitor_cli.py show --execution-id abc123
# Muestra duración por operación
```

### Estadísticas generales

```bash
python monitoring/monitor_cli.py stats
```

Output:
```
Execution Statistics
============================================================
Total Executions: 150
By Status:
  success: 142 (94.7%)
  failed: 8 (5.3%)
By Agent:
  agent-123: 100 (66.7%)
  agent-456: 50 (33.3%)
Average Duration: 1250.50ms
Average Success Duration: 1200.00ms
```

## Seguridad y Sanitización

### Datos Sanitizados

El sistema automáticamente sanitiza datos sensibles:

- **Credenciales**: Valores nunca se registran, solo IDs
- **Headers**: Tokens en headers se reemplazan con `[REDACTED]`
- **Resultados**: Campos con "token", "password", "secret" se sanitizan

### Ejemplo de Sanitización

**Configuración original:**
```json
{
  "headers": {
    "Authorization": "Bearer secret-token-12345"
  }
}
```

**Configuración registrada:**
```json
{
  "headers": {
    "Authorization": "[REDACTED]"
  }
}
```

## Integración

### En el Ejecutor

```python
from workflow_executor_monitored import MonitoredWorkflowExecutor
from monitoring.audit_logger import AuditLogger

# Crear logger
logger = AuditLogger(log_dir="logs")

# Crear ejecutor con monitoreo
executor = MonitoredWorkflowExecutor(audit_logger=logger)
executor.set_agent_context("my-agent-id")
executor.load_workflow(workflow_jsonl, agent_id="my-agent-id")
results = await executor.execute()
```

### En el Agente

El agente debe proporcionar su ID:

```python
executor.set_agent_context(agent_id="my-agent-123")
```

## Retención de Logs

Por defecto, los logs se guardan por día. Para gestionar retención:

```python
# Configurar retención
logger = AuditLogger(
    log_dir="logs",
    max_log_files=30  # Mantener últimos 30 días
)
```

## Comparación con A2UI

| Aspecto | A2UI | A2E |
|---------|------|-----|
| **Monitoreo** | Logs básicos de renderizado | Auditoría completa de ejecuciones |
| **Credenciales** | No aplica | Rastreo de uso de credenciales |
| **Resultados** | UI renderizada | Resultados de operaciones |
| **Auditoría** | Limitada | Completa y detallada |

## Próximos Pasos

1. ✅ Sistema de logging básico
2. ✅ Auditoría de credenciales
3. ✅ CLI de monitoreo
4. Dashboard web (futuro)
5. Alertas de seguridad (futuro)
6. Análisis de patrones (futuro)

