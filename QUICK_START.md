# A2E Quick Start Guide

## Inicio Rápido en 5 Pasos

### 1. Instalar Dependencias

```bash
pip install -e .
```

### 2. Configurar Sistema

```bash
python cli/config_wizard.py
```

Esto crea:
- `credentials.vault.json` - Vault de credenciales
- `api_definitions.json` - Definiciones de APIs
- `a2e_config.json` - Configuración principal

### 3. Registrar Agente

```bash
python auth/agent_auth_cli.py register \
  --id my-agent \
  --name "My Agent" \
  --allowed-apis "user-api"
```

Guarda el API key que se muestra.

### 4. Iniciar Servidor

```bash
python server/a2e_server.py --config a2e_config.json --port 8000
```

### 5. Usar Cliente

```python
from client.a2e_client import A2EClient, WorkflowBuilder

# Conectar
client = A2EClient(
    base_url="http://localhost:8000",
    api_key="your-api-key-here"
)

# Obtener capacidades
capabilities = client.get_capabilities()
print("Available operations:", capabilities["capabilities"]["supportedOperations"])

# Construir y ejecutar workflow
builder = WorkflowBuilder("my-workflow")
builder.add_api_call("fetch", "GET", "https://api.example.com/users")

workflow = builder.build()
result = client.execute_workflow(workflow)
print("Result:", result)
```

## Ejemplo Completo

Ver `examples/complete_example.py` para un ejemplo completo end-to-end.

## Próximos Pasos

1. Agregar más APIs a `api_definitions.json`
2. Agregar más credenciales con `cli/vault_cli.py`
3. Registrar más agentes con `auth/agent_auth_cli.py`
4. Monitorear ejecuciones con `monitoring/monitor_cli.py`

