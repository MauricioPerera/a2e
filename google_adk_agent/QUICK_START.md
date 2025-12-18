# Inicio Rápido - A2E con Google ADK

Guía rápida para empezar a usar el agente A2E con Google ADK en menos de 5 minutos.

## Prerrequisitos

- Python 3.10+ instalado
- Cuenta de Google Cloud con proyecto habilitado
- gcloud CLI instalado y configurado
- Servidor A2E ejecutándose (local o remoto)

## Paso 1: Instalar Dependencias

```bash
cd google_adk_agent
pip install -r requirements.txt
```

O instalar directamente:

```bash
pip install google-adk requests
```

## Paso 2: Autenticarse con Google Cloud

```bash
gcloud auth application-default login
```

Esto abrirá tu navegador para autenticarte.

## Paso 3: Configurar Variables de Entorno

Crea un archivo `.env` o exporta las variables:

```bash
export A2E_SERVER_URL="http://localhost:8000"
export A2E_API_KEY="tu-api-key-aqui"
export GOOGLE_CLOUD_PROJECT="tu-project-id"
```

Para obtener tu API key del servidor A2E:

```bash
# En el directorio del servidor A2E
python auth/agent_auth_cli.py register \
  --id google-adk-agent \
  --name "Google ADK Agent" \
  --allowed-apis "*" \
  --allowed-credentials "*" \
  --allowed-operations "*"
```

## Paso 4: Iniciar el Servidor A2E

En otra terminal:

```bash
# Desde el directorio raíz de A2E
python server/a2e_server.py --port 8000
```

El servidor estará disponible en `http://localhost:8000`

## Paso 5: Crear tu Primer Agente

Crea un archivo `my_agent.py`:

```python
import asyncio
from a2e_agent import create_a2e_agent

async def main():
    # Crear agente
    agent = create_a2e_agent(
        a2e_server_url="http://localhost:8000",
        api_key="tu-api-key-aqui"
    )
    
    # Obtener capacidades
    capabilities = agent.get_capabilities()
    print("Capacidades:", capabilities)
    
    # Interactuar con el agente
    response = await agent.run("¿Qué capacidades tengo disponibles?")
    print("Respuesta:", response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

## Paso 6: Ejecutar el Agente

```bash
python my_agent.py
```

## Paso 7: Ejecutar un Workflow Simple

Modifica `my_agent.py`:

```python
import asyncio
from a2e_agent import create_a2e_agent

async def main():
    agent = create_a2e_agent(
        a2e_server_url="http://localhost:8000",
        api_key="tu-api-key-aqui"
    )
    
    # Workflow simple: esperar 100ms
    workflow_jsonl = """{"operationUpdate": {"workflowId": "test", "operations": [
      {"id": "wait", "operation": {"Wait": {"duration": 100}}}
    ]}}
{"beginExecution": {"workflowId": "test", "root": "wait"}}"""
    
    # Ejecutar directamente
    result = agent.execute_workflow_direct(workflow_jsonl)
    print("Resultado:", result)
    
    # O pedir al agente que lo ejecute
    response = await agent.run(f"Ejecuta este workflow: {workflow_jsonl}")
    print("Respuesta del agente:", response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

## Paso 8: Generar Workflow con LLM

```python
import asyncio
from a2e_agent import create_a2e_agent

async def main():
    agent = create_a2e_agent(
        a2e_server_url="http://localhost:8000",
        api_key="tu-api-key-aqui"
    )
    
    # El agente genera y ejecuta el workflow automáticamente
    response = await agent.run(
        "Genera y ejecuta un workflow que espere 1 segundo y luego haga una llamada GET a https://api.example.com/users"
    )
    print("Respuesta:", response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

## Ejemplos Completos

Ver `example_usage.py` para más ejemplos:

- Obtener capacidades
- Ejecutar workflows manuales
- Generar workflows con LLM
- Buscar conocimiento (RAG)
- Buscar consultas SQL
- Validar workflows

## Troubleshooting

### Error: "A2E client not initialized"
**Solución**: Asegúrate de crear el agente usando `create_a2e_agent()`.

### Error: "Authentication required"
**Solución**: 
- Verifica que la API key sea correcta
- Verifica que el servidor A2E esté ejecutándose

### Error: "Google Cloud authentication failed"
**Solución**: 
- Ejecuta `gcloud auth application-default login`
- Verifica que `GOOGLE_CLOUD_PROJECT` esté configurado

### Error: "Module not found: google.adk"
**Solución**: Instala Google ADK: `pip install google-adk`

## Siguientes Pasos

- Lee la [Guía Completa de Integración](../GOOGLE_ADK_GUIDE.md)
- Revisa los [Ejemplos de Uso](./example_usage.py)
- Consulta la [Documentación de Google ADK](https://google.github.io/adk-docs/)
- Explora la [Documentación del Protocolo A2E](../PROTOCOL_OVERVIEW.md)

## Recursos

- [Google ADK Docs](https://google.github.io/adk-docs/)
- [A2E Server API](../server/a2e_server.py)
- [A2E Client SDK](../client/a2e_client.py)

