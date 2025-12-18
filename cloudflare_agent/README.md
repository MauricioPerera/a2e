# A2E Cloudflare Agent

Agente de Cloudflare Agents que se conecta al servidor A2E para ejecutar workflows declarativos.

## Descripción

Este agente permite a los agentes de Cloudflare interactuar con el servidor A2E (Agent-to-Execution), ejecutando workflows declarativos generados por LLMs. El agente proporciona métodos para:

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
npm install

# O usando yarn
yarn install
```

## Configuración

### 1. Variables de Entorno

Configura las variables de entorno en Cloudflare Dashboard o en `wrangler.toml`:

```toml
[vars]
A2E_SERVER_URL = "http://localhost:8000"
A2E_API_KEY = "your-api-key-here"
```

O puedes configurarlas dinámicamente usando el método `configureA2E()`.

### 2. Inicializar el Agente

```typescript
import { A2EAgent } from './a2e_agent';

const agent = new A2EAgent(env, {
  a2eServerUrl: 'http://localhost:8000',
  apiKey: 'your-api-key-here',
  executions: [],
});

// O configurar después
await agent.configureA2E('http://localhost:8000', 'your-api-key-here');
```

## Uso

### Obtener Capacidades

```typescript
const capabilities = await agent.getCapabilities();
console.log('Available APIs:', Object.keys(capabilities.capabilities?.availableApis || {}));
```

### Ejecutar Workflow Manual

```typescript
const workflowJsonl = `{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "outputPath": "/workflow/users"
    }
  }}
]}}
{"beginExecution": {"workflowId": "test", "root": "fetch"}}`;

const result = await agent.executeWorkflow(workflowJsonl);
```

### Generar y Ejecutar Workflow con LLM

```typescript
const description = 'Obtener usuarios activos y filtrar los que tienen más de 100 puntos';
const result = await agent.generateAndExecuteWorkflow(description, true);
```

### Buscar Conocimiento (RAG)

```typescript
const results = await agent.searchKnowledge('cómo obtener usuarios', undefined, undefined, 5);
```

### Buscar Consultas SQL

```typescript
const results = await agent.searchSQLQueries('obtener usuarios activos', 'users_db', 'analytics', 5);
```

## Métodos Disponibles

### `@callable() configureA2E(serverUrl, apiKey?, token?)`
Configura la conexión al servidor A2E.

### `@callable() getCapabilities()`
Obtiene las capacidades disponibles del servidor A2E.

### `@callable() searchKnowledge(query, kbId?, knowledgeType?, topK?)`
Busca conocimiento relevante usando RAG.

### `@callable() searchSQLQueries(query, database?, category?, topK?)`
Busca consultas SQL predefinidas.

### `@callable() validateWorkflow(workflowJsonl)`
Valida un workflow antes de ejecutarlo.

### `@callable() executeWorkflow(workflowJsonl, validate?)`
Ejecuta un workflow en el servidor A2E.

### `@callable() generateAndExecuteWorkflow(description, useLLM?, llmModel?)`
Genera un workflow usando un LLM y lo ejecuta.

### `@callable() getExecution(executionId)`
Obtiene detalles de una ejecución específica.

### `@callable() listExecutions(limit?, status?)`
Lista ejecuciones del servidor.

### `@callable() getExecutionHistory(limit?)`
Obtiene el historial local de ejecuciones del agente.

## Desarrollo

```bash
# Desarrollo local
npm run dev

# Desplegar a Cloudflare
npm run deploy
```

## Requisitos

- Cloudflare Workers con Agents SDK
- Servidor A2E ejecutándose y accesible
- API Key o Token de autenticación para A2E

## Referencias

- [Cloudflare Agents](https://agents.cloudflare.com/)
- [A2E Protocol Documentation](../README_A2E.md)
- [A2E Server](../server/a2e_server.py)

## Ejemplos

Ver `example_usage.ts` para ejemplos completos de uso.

