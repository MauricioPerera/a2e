# Guía de Integración: Cloudflare Agents con A2E

Esta guía explica cómo integrar un agente de Cloudflare Agents con el servidor A2E para ejecutar workflows declarativos.

## Visión General

El agente de Cloudflare Agents permite:
- Conectarse al servidor A2E mediante HTTP
- Ejecutar workflows declarativos generados por LLMs
- Buscar conocimiento usando RAG
- Buscar consultas SQL predefinidas
- Gestionar ejecuciones y su historial

## Arquitectura

```
┌─────────────────────────────────────┐
│   Cloudflare Agent (TypeScript)     │
│                                     │
│  - A2EAgent extends Agent           │
│  - Métodos @callable()              │
│  - Cliente HTTP para A2E            │
│  - Integración con LLM              │
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

### 1. Instalar Cloudflare Agents SDK

```bash
cd cloudflare_agent
npm install agents
```

### 2. Configurar Variables de Entorno

Edita `wrangler.toml` o configura en Cloudflare Dashboard:

```toml
[vars]
A2E_SERVER_URL = "http://localhost:8000"
A2E_API_KEY = "your-api-key-here"
```

### 3. Iniciar Servidor A2E

```bash
# En otro terminal
cd a2ui/samples/agent/adk/workflow_executor
python server/a2e_server.py --config a2e_config.json --port 8000
```

## Uso Básico

### 1. Crear y Configurar el Agente

```typescript
import { A2EAgent } from './a2e_agent';

const agent = new A2EAgent(env, {
  a2eServerUrl: 'http://localhost:8000',
  apiKey: 'your-api-key-here',
  executions: [],
});

// Configurar conexión
await agent.configureA2E('http://localhost:8000', 'your-api-key-here');
```

### 2. Obtener Capacidades

```typescript
const capabilities = await agent.getCapabilities();
console.log('APIs disponibles:', Object.keys(capabilities.capabilities?.availableApis || {}));
console.log('Operaciones:', capabilities.capabilities?.supportedOperations || []);
```

### 3. Ejecutar Workflow Manual

```typescript
const workflowJsonl = `{"operationUpdate": {"workflowId": "test", "operations": [
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
{"beginExecution": {"workflowId": "test", "root": "fetch"}}`;

// Validar primero
const validation = await agent.validateWorkflow(workflowJsonl);
if (validation.valid) {
  const result = await agent.executeWorkflow(workflowJsonl);
  console.log('Resultado:', result);
}
```

### 4. Generar y Ejecutar con LLM

```typescript
// El agente usa el LLM para generar el workflow automáticamente
const description = 'Obtener usuarios activos de la API y filtrar los que tienen más de 100 puntos';

const result = await agent.generateAndExecuteWorkflow(
  description,
  true, // usar LLM
  '@cf/meta/llama-3.3-70b-instruct-fp8-fast' // modelo opcional
);

console.log('Workflow generado y ejecutado:', result);
```

## Funcionalidades Avanzadas

### Búsqueda de Conocimiento (RAG)

```typescript
// Buscar conocimiento relevante
const knowledge = await agent.searchKnowledge(
  'cómo obtener usuarios activos',
  undefined, // kb_id opcional
  undefined, // knowledge_type opcional
  5 // top_k
);

console.log('Conocimiento encontrado:', knowledge.results);
```

### Búsqueda de Consultas SQL

```typescript
// Buscar consultas SQL predefinidas
const sqlQueries = await agent.searchSQLQueries(
  'obtener usuarios activos',
  'users_db', // database opcional
  'analytics', // category opcional
  5 // top_k
);

console.log('Consultas SQL encontradas:', sqlQueries.results);
```

### Gestión de Ejecuciones

```typescript
// Obtener historial local
const localHistory = await agent.getExecutionHistory(10);

// Listar ejecuciones del servidor
const serverExecutions = await agent.listExecutions(100, 'success');

// Obtener detalles de una ejecución específica
const execution = await agent.getExecution('exec-123');
```

## Flujo Completo de Ejemplo

```typescript
import { A2EAgent } from './a2e_agent';

export async function completeExample(env: A2EAgentEnv) {
  // 1. Crear agente
  const agent = new A2EAgent(env, {
    a2eServerUrl: 'http://localhost:8000',
    apiKey: 'your-api-key-here',
    executions: [],
  });

  // 2. Configurar conexión
  await agent.configureA2E('http://localhost:8000', 'your-api-key-here');

  // 3. Obtener capacidades
  const capabilities = await agent.getCapabilities();
  console.log('Sistema configurado:', capabilities);

  // 4. Buscar conocimiento relevante
  const knowledge = await agent.searchKnowledge('obtener datos de usuarios');
  console.log('Conocimiento encontrado:', knowledge);

  // 5. Generar y ejecutar workflow con LLM
  const result = await agent.generateAndExecuteWorkflow(
    'Obtener usuarios activos y guardar los resultados'
  );
  console.log('Workflow ejecutado:', result);

  // 6. Consultar historial
  const history = await agent.getExecutionHistory(5);
  console.log('Últimas ejecuciones:', history);
}
```

## Métodos Disponibles

### Configuración

- `configureA2E(serverUrl, apiKey?, token?)`: Configura la conexión al servidor A2E

### Información

- `getCapabilities()`: Obtiene capacidades disponibles (APIs, credenciales, operaciones)
- `searchKnowledge(query, kbId?, knowledgeType?, topK?)`: Busca conocimiento usando RAG
- `searchSQLQueries(query, database?, category?, topK?)`: Busca consultas SQL

### Workflows

- `validateWorkflow(workflowJsonl)`: Valida un workflow antes de ejecutarlo
- `executeWorkflow(workflowJsonl, validate?)`: Ejecuta un workflow
- `generateAndExecuteWorkflow(description, useLLM?, llmModel?)`: Genera y ejecuta workflow con LLM

### Ejecuciones

- `getExecution(executionId)`: Obtiene detalles de una ejecución
- `listExecutions(limit?, status?)`: Lista ejecuciones del servidor
- `getExecutionHistory(limit?)`: Obtiene historial local del agente

## Despliegue

### Desarrollo Local

```bash
npm run dev
```

### Despliegue a Cloudflare

```bash
npm run deploy
```

O usando Wrangler directamente:

```bash
wrangler deploy
```

## Configuración de Producción

### Variables de Entorno en Cloudflare

1. Ve a Cloudflare Dashboard
2. Selecciona tu Worker
3. Configura las variables de entorno:
   - `A2E_SERVER_URL`: URL del servidor A2E
   - `A2E_API_KEY`: API Key para autenticación

### Seguridad

- **Nunca** expongas tu API Key en el código
- Usa variables de entorno o Cloudflare Secrets
- Configura CORS apropiadamente en el servidor A2E
- Usa HTTPS en producción

## Troubleshooting

### Error: "A2E client not initialized"

Solución: Llama a `configureA2E()` antes de usar otros métodos.

### Error: "Failed to get capabilities"

Solución: Verifica que:
- El servidor A2E esté ejecutándose
- La URL sea correcta
- La API Key sea válida

### Error: "Workflow validation failed"

Solución: Revisa el reporte de validación para ver qué operaciones o parámetros son inválidos.

## Referencias

- [Cloudflare Agents Documentation](https://agents.cloudflare.com/)
- [A2E Protocol Overview](../PROTOCOL_OVERVIEW.md)
- [A2E Server API](../server/a2e_server.py)
- [A2E Client SDK](../client/a2e_client.py)

## Ejemplos Completos

Ver `cloudflare_agent/example_usage.ts` para más ejemplos.

