# A2E Authentication & Authorization

## Sistema de Autenticación

A diferencia de A2UI, **A2E requiere autenticación de agentes** para:

1. **Identificar agentes**: Saber qué agente ejecuta qué workflow
2. **Control de acceso**: Cada agente solo recibe recursos asignados
3. **Evitar sobrecarga**: No enviar información innecesaria al agente
4. **Auditoría**: Rastrear qué agente hizo qué

## Concepto

Cada agente tiene:
- **ID único**: Identificador del agente
- **API Key**: Para autenticación directa
- **JWT Token**: Para autenticación con expiración
- **Permisos asignados**: APIs, credenciales, operaciones permitidas

## Registro de Agentes

### Registrar un Agente

```bash
python auth/agent_auth_cli.py register \
  --id agent-123 \
  --name "User Data Agent" \
  --allowed-apis "user-api" \
  --allowed-credentials "user-api-token" \
  --allowed-operations "ApiCall,FilterData"
```

Esto retorna un **API key** que el agente debe usar para autenticarse.

### Permisos

- **Lista vacía = Todo permitido**: Si no se especifican permisos, el agente puede usar todo
- **Lista con elementos = Solo esos**: Si se especifican, solo puede usar esos recursos

Ejemplos:

```bash
# Agente con acceso completo
python auth/agent_auth_cli.py register --id agent-full --name "Full Access"

# Agente con acceso restringido
python auth/agent_auth_cli.py register \
  --id agent-limited \
  --name "Limited Access" \
  --allowed-apis "user-api" \
  --allowed-credentials "user-api-token"
```

## Autenticación

### Método 1: API Key

```python
from agent_with_auth import AuthenticatedWorkflowAgent

agent = AuthenticatedWorkflowAgent(
    agent_id="agent-123",
    api_key="generated-api-key-here"
)
```

En HTTP requests:
```
X-API-Key: generated-api-key-here
```

### Método 2: JWT Token

```bash
# Generar token
python auth/agent_auth_cli.py generate-token --id agent-123 --expires-in 24
```

```python
agent = AuthenticatedWorkflowAgent(
    agent_id="agent-123",
    token="jwt-token-here"
)
```

En HTTP requests:
```
Authorization: Bearer jwt-token-here
```

## Capacidades Filtradas

Cuando un agente autenticado solicita capacidades, **solo recibe lo que tiene asignado**:

```python
capabilities = agent.get_capabilities_for_llm()
```

**Agente con acceso completo:**
```json
{
  "availableApis": {
    "user-api": {...},
    "product-api": {...}
  },
  "availableCredentials": [
    {"id": "user-api-token", ...},
    {"id": "product-api-token", ...}
  ],
  "supportedOperations": ["ApiCall", "FilterData", "StoreData"]
}
```

**Agente con acceso limitado:**
```json
{
  "availableApis": {
    "user-api": {...}  // Solo user-api
  },
  "availableCredentials": [
    {"id": "user-api-token", ...}  // Solo este token
  ],
  "supportedOperations": ["ApiCall", "FilterData"]  // Solo estas operaciones
}
```

## Validación de Workflows

El sistema valida que el workflow solo use recursos permitidos:

```python
is_valid, error = agent.validate_workflow(workflow_jsonl)
```

Valida:
- ✅ Operaciones permitidas
- ✅ APIs permitidas (por dominio)
- ✅ Credenciales permitidas

## Gestión de Agentes

### Listar Agentes

```bash
python auth/agent_auth_cli.py list
```

### Ver Detalles

```bash
python auth/agent_auth_cli.py show --id agent-123
```

### Actualizar Permisos

```bash
python auth/agent_auth_cli.py update-permissions \
  --id agent-123 \
  --allowed-apis "user-api,product-api"
```

### Probar Autenticación

```bash
python auth/agent_auth_cli.py test --api-key <api-key>
python auth/agent_auth_cli.py test --token <jwt-token>
```

## Flujo Completo

### 1. Administrador Registra Agente

```bash
python auth/agent_auth_cli.py register \
  --id agent-123 \
  --name "User Agent" \
  --allowed-apis "user-api" \
  --allowed-credentials "user-api-token"
```

### 2. Agente se Autentica

```python
agent = AuthenticatedWorkflowAgent(
    agent_id="agent-123",
    api_key="received-api-key"
)
```

### 3. Agente Obtiene Capacidades (Filtradas)

```python
capabilities = agent.get_capabilities_for_llm()
# Solo recibe user-api y user-api-token
```

### 4. Agente Genera Workflow

```jsonl
{"operationUpdate": {"operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "url": "https://api.example.com/users",  // user-api
      "headers": {
        "Authorization": {"credentialRef": {"id": "user-api-token"}}
      }
    }
  }}
]}}
```

### 5. Sistema Valida Workflow

```python
is_valid, error = agent.validate_workflow(workflow_jsonl)
# Valida que solo usa recursos permitidos
```

## Ventajas

1. **Seguridad**: Cada agente solo accede a lo asignado
2. **Optimización**: Agente no recibe información innecesaria
3. **Auditoría**: Se sabe qué agente hizo qué
4. **Escalabilidad**: Fácil agregar/quitar permisos

## Comparación con A2UI

| Aspecto | A2UI | A2E |
|---------|------|-----|
| **Autenticación** | No requerida | Requerida |
| **Autorización** | Catálogo de componentes | Permisos por agente |
| **Capacidades** | Todas disponibles | Filtradas por agente |
| **Auditoría** | Limitada | Completa por agente |

## Archivo de Configuración

`agent_auth.json`:

```json
{
  "agents": {
    "agent-123": {
      "id": "agent-123",
      "name": "User Data Agent",
      "api_key_hash": "...",
      "allowed_apis": ["user-api"],
      "allowed_credentials": ["user-api-token"],
      "allowed_operations": ["ApiCall", "FilterData"],
      "created_at": "2025-01-15T10:00:00",
      "last_used": "2025-01-15T12:00:00"
    }
  }
}
```

**Nota**: Las API keys nunca se almacenan, solo sus hashes.

