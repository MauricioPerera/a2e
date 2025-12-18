# A2E Agent con Google ADK

Agente de Google Agent Development Kit (ADK) que se conecta al servidor A2E para ejecutar workflows declarativos.

## Descripción

Este agente permite a los agentes de Google ADK interactuar con el servidor A2E (Agent-to-Execution), ejecutando workflows declarativos generados por LLMs. El agente proporciona herramientas (tools) que pueden ser usadas por agentes ADK para:

- Configurar la conexión al servidor A2E
- Obtener capacidades disponibles (APIs, credenciales, operaciones)
- Buscar conocimiento usando RAG
- Buscar consultas SQL predefinidas
- Validar workflows
- Ejecutar workflows manualmente o generarlos automáticamente con LLMs
- Consultar historial de ejecuciones

## Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# O instalar directamente
pip install google-adk requests
```

## Configuración

### 1. Variables de Entorno

Configura las variables de entorno:

```bash
export A2E_SERVER_URL="http://localhost:8000"
export A2E_API_KEY="your-api-key-here"
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

### 2. Autenticación con Google Cloud

Para usar modelos de Google (Gemini), necesitas autenticarte:

```bash
# Usando gcloud CLI
gcloud auth application-default login

# O configurar service account
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
```

## Uso Básico

### Crear un Agente

```python
from a2e_agent import create_a2e_agent

# Crear agente con configuración por defecto
agent = create_a2e_agent(
    a2e_server_url="http://localhost:8000",
    api_key="your-api-key-here"
)
```

### Interactuar con el Agente

```python
import asyncio

async def main():
    agent = create_a2e_agent()
    
    # El agente puede responder preguntas y ejecutar workflows
    response = await agent.run("¿Qué capacidades tengo disponibles?")
    print(response.content)

asyncio.run(main())
```

### Ejecutar Workflow Directamente

```python
workflow_jsonl = """{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "wait", "operation": {"Wait": {"duration": 1000}}}
]}}
{"beginExecution": {"workflowId": "test", "root": "wait"}}"""

result = agent.execute_workflow_direct(workflow_jsonl)
print(result)
```

## Herramientas Disponibles

El agente incluye las siguientes herramientas que pueden ser usadas por el LLM:

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

## Ejemplos

Ver `example_usage.py` para ejemplos completos:

- Uso básico del agente
- Ejecutar workflows
- Generar workflows con LLM
- Buscar conocimiento (RAG)
- Buscar consultas SQL
- Validar workflows

## Configuración Avanzada

### Usar un Modelo Diferente

```python
agent = A2EAgent(
    a2e_server_url="http://localhost:8000",
    api_key="your-api-key",
    model_name="gemini-1.5-pro",  # Cambiar modelo
    project_id="your-project-id",
    location="us-central1"
)
```

### Agregar Herramientas Personalizadas

```python
from google.adk import Tool
from google.adk.core import ToolResult

@Tool(
    name="my_custom_tool",
    description="Mi herramienta personalizada"
)
def my_custom_tool(param: str) -> ToolResult:
    return ToolResult(content=f"Resultado: {param}")

# Agregar a las herramientas del agente
agent.agent.config.tools.append(my_custom_tool)
```

## Despliegue

### Desplegar en Vertex AI Agent Engine

```bash
# Usar ADK CLI para desplegar
adk deploy --agent a2e_agent.py
```

### Desplegar en Cloud Run

```bash
# Crear Dockerfile
docker build -t a2e-agent .
docker push gcr.io/your-project/a2e-agent

# Desplegar
gcloud run deploy a2e-agent \
  --image gcr.io/your-project/a2e-agent \
  --platform managed
```

## Referencias

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [A2E Protocol Overview](../PROTOCOL_OVERVIEW.md)
- [A2E Server API](../server/a2e_server.py)
- [A2E Client SDK](../client/a2e_client.py)

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

