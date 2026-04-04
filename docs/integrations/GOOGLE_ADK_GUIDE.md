# Guía de Integración: Google ADK con A2E

Esta guía explica cómo integrar un agente de Google Agent Development Kit (ADK) con el servidor A2E para ejecutar workflows declarativos.

## Visión General

El agente de Google ADK permite:
- Conectarse al servidor A2E mediante HTTP
- Ejecutar workflows declarativos generados por LLMs (Gemini)
- Buscar conocimiento usando RAG
- Buscar consultas SQL predefinidas
- Gestionar ejecuciones y su historial

## Arquitectura

```
┌─────────────────────────────────────┐
│   Google ADK Agent (Python)         │
│                                     │
│  - LlmAgent con herramientas A2E   │
│  - Integración con Gemini           │
│  - Cliente HTTP para A2E            │
└──────────────┬──────────────────────┘
               │ HTTP/REST
               │
┌──────────────▼──────────────────────┐
│      Servidor A2E (Python)          │
│                                     │
│  - Flask REST API                   │
│  - Workflow Executor                │
│  - RAG System                       │
│  - SQL Query Manager                │
│  - Dashboard Metrics                │
└─────────────────────────────────────┘
```

## Instalación

### 1. Instalar Google ADK

```bash
pip install google-adk
```

O desde el directorio del proyecto:

```bash
cd google_adk_agent
pip install -r requirements.txt
```

### 2. Configurar Autenticación de Google Cloud

Para usar modelos de Gemini, necesitas autenticarte:

```bash
# Opción 1: Application Default Credentials
gcloud auth application-default login

# Opción 2: Service Account
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

### 3. Configurar Variables de Entorno

```bash
export A2E_SERVER_URL="http://localhost:8000"
export A2E_API_KEY="your-api-key-here"
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

### 4. Iniciar Servidor A2E

```bash
# En otro terminal
cd a2ui/samples/agent/adk/workflow_executor
python server/a2e_server.py --config a2e_config.json --port 8000
```

## Uso Básico

### 1. Crear y Configurar el Agente

```python
from a2e_agent import create_a2e_agent

# Crear agente con configuración por defecto
agent = create_a2e_agent(
    a2e_server_url="http://localhost:8000",
    api_key="your-api-key-here"
)
```

### 2. Obtener Capacidades

```python
capabilities = agent.get_capabilities()
print("APIs disponibles:", list(capabilities['capabilities']['availableApis'].keys()))
print("Operaciones:", capabilities['capabilities']['supportedOperations'])
```

### 3. Interactuar con el Agente

```python
import asyncio

async def main():
    agent = create_a2e_agent()
    
    # El agente puede responder preguntas y ejecutar workflows
    response = await agent.run("¿Qué capacidades tengo disponibles en el servidor A2E?")
    print(response.content)

asyncio.run(main())
```

### 4. Ejecutar Workflow Manual

```python
workflow_jsonl = """{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "headers": {
        "Authorization": {
          "credentialRef": {"id": "api-token"}
        }
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
  }}
]}}
{"beginExecution": {"workflowId": "test", "root": "fetch"}}"""

# Validar primero
response = await agent.run(f"Valida este workflow: {workflow_jsonl}")

# Ejecutar
result = agent.execute_workflow_direct(workflow_jsonl, validate=True)
print("Resultado:", result)
```

### 5. Generar y Ejecutar con LLM

```python
# El agente usa Gemini para generar el workflow automáticamente
response = await agent.run(
    "Genera y ejecuta un workflow que obtenga usuarios activos de la API y filtre los que tienen más de 100 puntos"
)
print(response.content)
```

## Funcionalidades Avanzadas

### Búsqueda de Conocimiento (RAG)

```python
response = await agent.run("Busca información sobre cómo obtener usuarios de una API")
print(response.content)
```

### Búsqueda de Consultas SQL

```python
response = await agent.run("Busca consultas SQL para obtener usuarios activos de la base de datos")
print(response.content)
```

### Gestión de Ejecuciones

```python
# Listar ejecuciones
response = await agent.run("Lista las últimas 10 ejecuciones")

# Obtener detalles de una ejecución
response = await agent.run("Obtén detalles de la ejecución exec-123")
```

## Flujo Completo de Ejemplo

```python
import asyncio
from a2e_agent import create_a2e_agent

async def complete_example():
    # 1. Crear agente
    agent = create_a2e_agent(
        a2e_server_url="http://localhost:8000",
        api_key="your-api-key-here"
    )
    
    # 2. Obtener capacidades
    capabilities = agent.get_capabilities()
    print("Sistema configurado:", capabilities)
    
    # 3. Buscar conocimiento relevante
    response = await agent.run("Busca información sobre cómo obtener datos de usuarios")
    print("Conocimiento encontrado:", response.content)
    
    # 4. Generar y ejecutar workflow con LLM
    response = await agent.run(
        "Genera y ejecuta un workflow que obtenga usuarios activos y guarde los resultados"
    )
    print("Workflow ejecutado:", response.content)
    
    # 5. Consultar historial
    response = await agent.run("Lista las últimas 5 ejecuciones")
    print("Historial:", response.content)

asyncio.run(complete_example())
```

## Herramientas Disponibles

El agente incluye las siguientes herramientas que pueden ser usadas automáticamente por el LLM:

### `a2e_get_capabilities`
Obtiene las capacidades disponibles del servidor A2E.

### `a2e_search_knowledge`
Busca conocimiento relevante usando RAG (Retrieval Augmented Generation).

### `a2e_search_sql_queries`
Busca consultas SQL predefinidas relevantes.

### `a2e_validate_workflow`
Valida un workflow A2E antes de ejecutarlo.

### `a2e_execute_workflow`
Ejecuta un workflow A2E en formato JSONL.

### `a2e_get_execution`
Obtiene detalles de una ejecución específica.

### `a2e_list_executions`
Lista las ejecuciones del agente.

## Configuración de Modelos

### Usar Diferentes Modelos de Gemini

```python
agent = A2EAgent(
    a2e_server_url="http://localhost:8000",
    api_key="your-api-key",
    model_name="gemini-1.5-pro",  # Modelo más potente
    project_id="your-project-id",
    location="us-central1"
)
```

Modelos disponibles:
- `gemini-2.0-flash-exp` (default) - Rápido y eficiente
- `gemini-1.5-pro` - Más potente para tareas complejas
- `gemini-1.5-flash` - Balance entre velocidad y capacidad

## Despliegue

### Desplegar en Vertex AI Agent Engine

```bash
# Usar ADK CLI para desplegar
adk deploy --agent google_adk_agent/a2e_agent.py
```

### Desplegar en Cloud Run

```bash
# Crear Dockerfile
cat > Dockerfile << EOF
FROM python:3.11-slim

WORKDIR /app
COPY google_adk_agent/requirements.txt .
RUN pip install -r requirements.txt

COPY google_adk_agent/ .
CMD ["python", "a2e_agent.py"]
EOF

# Construir y desplegar
docker build -t a2e-adk-agent .
docker push gcr.io/your-project/a2e-adk-agent

gcloud run deploy a2e-adk-agent \
  --image gcr.io/your-project/a2e-adk-agent \
  --platform managed \
  --set-env-vars A2E_SERVER_URL=https://your-a2e-server.com
```

## Troubleshooting

### Error: "A2E client not initialized"
**Solución**: Asegúrate de crear el agente usando `create_a2e_agent()` o `A2EAgent()`.

### Error: "Authentication required"
**Solución**: Verifica que la API key o token sean correctos y estén configurados.

### Error: "Failed to get capabilities"
**Solución**: 
- Verifica que el servidor A2E esté ejecutándose
- Verifica la URL en `A2E_SERVER_URL`
- Verifica que la API key sea correcta

### Error: "Google Cloud authentication failed"
**Solución**: 
- Ejecuta `gcloud auth application-default login`
- O configura `GOOGLE_APPLICATION_CREDENTIALS`

### Error: "Module not found: google.adk"
**Solución**: Instala Google ADK: `pip install google-adk`

## Referencias

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [A2E Protocol Overview](../PROTOCOL_OVERVIEW.md)
- [A2E Server API](../server/a2e_server.py)
- [A2E Client SDK](../client/a2e_client.py)

## Ejemplos Completos

Ver `google_adk_agent/example_usage.py` para más ejemplos.

