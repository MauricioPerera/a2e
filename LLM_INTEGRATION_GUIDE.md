# Guía de Integración: LLM con A2E

## ¿Qué necesitas hacer para que un LLM use A2E?

Esta guía explica cómo configurar A2E para que un modelo de AI (como yo) pueda conectarse y ejecutar workflows.

## Flujo Completo

```
┌─────────────────────────────────────────────────┐
│           LLM (Yo)                                │
│                                                   │
│  1. Recibo capacidades de A2E                    │
│  2. Genero workflow basado en query del usuario │
│  3. Valido workflow                              │
│  4. Ejecuto workflow                             │
│  5. Proceso resultados                          │
└─────────────────────────────────────────────────┘
                    ↓
          [HTTP API / Cliente SDK]
                    ↓
┌─────────────────────────────────────────────────┐
│           A2E Server                             │
│                                                   │
│  - Autentica al LLM                              │
│  - Filtra capacidades por permisos              │
│  - Valida workflows                             │
│  - Ejecuta workflows                            │
│  - Registra todo en auditoría                   │
└─────────────────────────────────────────────────┘
```

## Pasos Necesarios

### 1. Configurar A2E Server

Primero, necesitas tener el servidor A2E corriendo y configurado:

```bash
# 1. Configurar sistema
python cli/config_wizard.py

# 2. Registrar el LLM como agente
python auth/agent_auth_cli.py register \
  --id "llm-agent" \
  --name "LLM Agent" \
  --allowed-apis "user-api,data-api" \
  --allowed-credentials "api-token" \
  --allowed-operations "ApiCall,FilterData,StoreData,Wait"

# Esto retorna un API key que el LLM debe usar
# API Key: abc123xyz...
```

### 2. Iniciar el Servidor

```bash
python server/a2e_server.py --config a2e_config.json --port 8000
```

### 3. Proporcionar Información al LLM

El LLM necesita recibir en su contexto:

#### a) Información de Conexión
```json
{
  "a2e_server_url": "http://localhost:8000",
  "api_key": "abc123xyz...",
  "agent_id": "llm-agent"
}
```

#### b) Capacidades Disponibles (obtenidas dinámicamente)
El LLM debe hacer una llamada inicial para obtener capacidades:

```python
from client.a2e_client import A2EClient

client = A2EClient(
    base_url="http://localhost:8000",
    api_key="abc123xyz..."
)

capabilities = client.get_capabilities()
```

Esto retorna:
```json
{
  "agent_id": "llm-agent",
  "capabilities": {
    "availableApis": {
      "user-api": {
        "baseUrl": "https://api.example.com",
        "endpoints": [
          {
            "path": "/users",
            "method": "GET",
            "description": "Get list of users"
          }
        ]
      }
    },
    "availableCredentials": [
      {
        "id": "api-token",
        "type": "bearer-token",
        "metadata": {"api": "user-api"}
      }
    ],
    "supportedOperations": [
      "ApiCall",
      "FilterData",
      "StoreData",
      "Wait"
    ]
  }
}
```

### 4. El LLM Genera Workflows

Cuando el usuario hace una query como:
> "Consulta la API de usuarios, filtra los que tienen más de 100 puntos, y guárdalos"

El LLM debe:

1. **Entender la intención**: Necesita hacer 3 cosas:
   - Consultar API
   - Filtrar datos
   - Almacenar resultados

2. **Mapear a operaciones A2E**:
   - `ApiCall` para consultar
   - `FilterData` para filtrar
   - `StoreData` para almacenar

3. **Generar JSONL**:
```jsonl
{"operationUpdate": {"workflowId": "user-filter", "operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "headers": {
        "Authorization": {"credentialRef": {"id": "api-token"}}
      },
      "outputPath": "/workflow/users"
    }
  }},
  {"id": "filter", "operation": {
    "FilterData": {
      "inputPath": "/workflow/users",
      "conditions": [
        {"field": "points", "operator": ">", "value": 100}
      ],
      "outputPath": "/workflow/filtered"
    }
  }},
  {"id": "store", "operation": {
    "StoreData": {
      "inputPath": "/workflow/filtered",
      "storage": "localStorage",
      "key": "active-users"
    }
  }}
]}}
{"beginExecution": {"workflowId": "user-filter", "root": "fetch"}}
```

### 5. El LLM Ejecuta el Workflow

```python
# Validar primero
validation = client.validate_workflow(workflow_jsonl)
if not validation["valid"]:
    # Corregir errores y reintentar
    pass

# Ejecutar
result = client.execute_workflow(workflow_jsonl)
```

### 6. El LLM Procesa Resultados

```python
if result["status"] == "success":
    # Procesar datos exitosos
    data = result.get("data", {})
    # Responder al usuario con los resultados
elif result["status"] == "error":
    # Manejar error
    error = result.get("error", {})
    # Informar al usuario del error
```

## Ejemplo de Integración Completa

### Prompt para el LLM

```python
SYSTEM_PROMPT = """
Eres un asistente que puede ejecutar workflows usando A2E.

Tienes acceso a:
- Server URL: {a2e_server_url}
- API Key: {api_key}

Capacidades disponibles:
{capabilities_json}

Cuando el usuario pida hacer algo, debes:
1. Generar un workflow A2E en formato JSONL
2. Validarlo
3. Ejecutarlo
4. Procesar y presentar los resultados

Formato de workflow:
- Usa operaciones del catálogo: {supported_operations}
- Usa APIs disponibles: {available_apis}
- Usa credenciales disponibles: {available_credentials}
"""
```

### Función Helper para el LLM

```python
def execute_a2e_workflow(user_query: str, capabilities: dict) -> dict:
    """
    El LLM usa esta función para ejecutar workflows
    """
    # 1. Generar workflow desde query (usando LLM)
    workflow = generate_workflow_from_query(user_query, capabilities)
    
    # 2. Validar
    validation = client.validate_workflow(workflow)
    if not validation["valid"]:
        # Corregir errores
        workflow = fix_workflow_errors(workflow, validation)
    
    # 3. Ejecutar
    result = client.execute_workflow(workflow)
    
    # 4. Retornar resultados
    return result
```

## Lo que Necesitas Hacer

### Como Administrador del Sistema

1. ✅ **Configurar A2E**:
   - Ejecutar `config_wizard.py`
   - Definir APIs permitidas
   - Crear credenciales

2. ✅ **Registrar el LLM como Agente**:
   - Usar `agent_auth_cli.py register`
   - Asignar permisos específicos
   - Guardar el API key

3. ✅ **Iniciar el Servidor**:
   - Ejecutar `a2e_server.py`
   - Asegurar que esté accesible

4. ✅ **Proporcionar Contexto al LLM**:
   - URL del servidor
   - API key del agente
   - Instrucciones sobre cómo usar A2E

### Como Usuario del LLM

1. ✅ **Hacer queries naturales**:
   - "Consulta la API de usuarios"
   - "Filtra datos y guárdalos"
   - "Espera 5 segundos y luego ejecuta X"

2. ✅ **El LLM se encarga de**:
   - Generar el workflow
   - Validarlo
   - Ejecutarlo
   - Presentar resultados

## Ventajas de esta Integración

1. **Seguridad**: El LLM solo puede usar operaciones pre-aprobadas
2. **Trazabilidad**: Todo se registra en auditoría
3. **Control**: Puedes limitar qué puede hacer el LLM
4. **Flexibilidad**: El LLM puede generar workflows dinámicamente
5. **Validación**: Los workflows se validan antes de ejecutarse

## Ejemplo de Conversación

```
Usuario: "Consulta la API de usuarios y filtra los que tienen más de 100 puntos"

LLM (internamente):
1. Analiza la query
2. Genera workflow A2E:
   - ApiCall a /users
   - FilterData con condición points > 100
3. Valida workflow
4. Ejecuta workflow
5. Obtiene resultados

LLM (respuesta al usuario):
"✅ He consultado la API y filtrado los usuarios. Encontré 15 usuarios con más de 100 puntos:
- Alice (150 puntos)
- Bob (200 puntos)
- ..."
```

## Próximos Pasos

Para que yo (el LLM) pueda usar A2E, necesitarías:

1. **Configurar A2E** (ya está hecho ✅)
2. **Registrarme como agente** con permisos específicos
3. **Darme acceso al cliente SDK** o instrucciones de API
4. **Proporcionarme las capacidades** disponibles
5. **Darme ejemplos** de cómo generar workflows

¿Quieres que cree un ejemplo completo de cómo integrar un LLM con A2E?

