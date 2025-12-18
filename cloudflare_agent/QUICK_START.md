# Inicio Rápido - A2E Cloudflare Agent

Guía rápida para empezar a usar el agente A2E en Cloudflare en menos de 5 minutos.

## Prerrequisitos

- Node.js 18+ instalado
- Cuenta de Cloudflare con Workers habilitado
- Wrangler CLI instalado: `npm install -g wrangler`
- Servidor A2E ejecutándose (local o remoto)

## Paso 1: Instalar Dependencias

```bash
cd cloudflare_agent
npm install
```

## Paso 2: Configurar Variables de Entorno

Crea un archivo `.dev.vars` (NO se commitea, está en `.gitignore`):

```bash
# .dev.vars
A2E_SERVER_URL = "http://localhost:8000"
A2E_API_KEY = "tu-api-key-aqui"
```

Para obtener tu API key del servidor A2E:

```bash
# En el directorio del servidor A2E
python auth/agent_auth_cli.py register \
  --id cloudflare-agent \
  --name "Cloudflare Agent" \
  --allowed-apis "*" \
  --allowed-credentials "*" \
  --allowed-operations "*"
```

## Paso 3: Iniciar el Servidor A2E

En otra terminal:

```bash
# Desde el directorio raíz de A2E
python server/a2e_server.py --port 8000
```

El servidor estará disponible en `http://localhost:8000`

## Paso 4: Crear tu Primer Agente

Crea un archivo `my_agent.ts`:

```typescript
import { A2EAgent } from './a2e_agent';

export default {
  async fetch(request: Request, env: any): Promise<Response> {
    // Crear instancia del agente
    const agent = new A2EAgent(env, {
      a2eServerUrl: env.A2E_SERVER_URL || 'http://localhost:8000',
      apiKey: env.A2E_API_KEY,
      executions: [],
    });

    // Configurar conexión
    await agent.configureA2E(
      env.A2E_SERVER_URL || 'http://localhost:8000',
      env.A2E_API_KEY
    );

    // Obtener capacidades
    const capabilities = await agent.getCapabilities();

    return new Response(JSON.stringify({
      message: 'A2E Agent está funcionando!',
      capabilities: {
        apis: Object.keys(capabilities.capabilities?.availableApis || {}),
        operations: capabilities.capabilities?.supportedOperations || [],
      },
    }), {
      headers: { 'Content-Type': 'application/json' },
    });
  },
};
```

## Paso 5: Probar Localmente

```bash
npm run dev
```

O con Wrangler directamente:

```bash
wrangler dev
```

Visita `http://localhost:8787` para ver la respuesta del agente.

## Paso 6: Ejecutar un Workflow Simple

Modifica `my_agent.ts` para ejecutar un workflow:

```typescript
import { A2EAgent } from './a2e_agent';

export default {
  async fetch(request: Request, env: any): Promise<Response> {
    const agent = new A2EAgent(env, {
      a2eServerUrl: env.A2E_SERVER_URL || 'http://localhost:8000',
      apiKey: env.A2E_API_KEY,
      executions: [],
    });

    await agent.configureA2E(
      env.A2E_SERVER_URL || 'http://localhost:8000',
      env.A2E_API_KEY
    );

    // Workflow simple: esperar 100ms
    const workflowJsonl = `{"operationUpdate": {"workflowId": "test", "operations": [
      {"id": "wait", "operation": {"Wait": {"duration": 100}}}
    ]}}
{"beginExecution": {"workflowId": "test", "root": "wait"}}`;

    try {
      const result = await agent.executeWorkflow(workflowJsonl);
      return new Response(JSON.stringify({
        success: true,
        result: result,
      }), {
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (error: any) {
      return new Response(JSON.stringify({
        success: false,
        error: error.message,
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  },
};
```

## Paso 7: Generar Workflow con LLM

Para generar workflows automáticamente usando un LLM:

```typescript
// Generar workflow desde descripción en lenguaje natural
const description = 'Esperar 1 segundo y luego hacer una llamada GET a https://api.example.com/users';

const result = await agent.generateAndExecuteWorkflow(
  description,
  true, // usar LLM
  '@cf/meta/llama-3.3-70b-instruct-fp8-fast' // modelo opcional
);
```

## Paso 8: Desplegar a Cloudflare

1. Autentícate con Wrangler:
   ```bash
   wrangler login
   ```

2. Configura los secrets en Cloudflare:
   ```bash
   wrangler secret put A2E_SERVER_URL
   wrangler secret put A2E_API_KEY
   ```

3. Despliega:
   ```bash
   npm run deploy
   ```

   O:
   ```bash
   wrangler deploy
   ```

## Ejemplos Completos

Ver `example_usage.ts` para más ejemplos:

- Obtener capacidades
- Ejecutar workflows manuales
- Generar workflows con LLM
- Buscar conocimiento (RAG)
- Buscar consultas SQL
- Gestionar historial de ejecuciones

## Troubleshooting

### Error: "A2E client not initialized"
**Solución**: Asegúrate de llamar `configureA2E()` antes de usar otros métodos.

### Error: "Failed to get capabilities"
**Solución**: 
- Verifica que el servidor A2E esté ejecutándose
- Verifica la URL en `A2E_SERVER_URL`
- Verifica que la API key sea correcta

### Error: "Workflow validation failed"
**Solución**: Revisa el reporte de validación para ver qué operaciones son inválidas.

### Error: "Module not found: agents"
**Solución**: Ejecuta `npm install` en el directorio `cloudflare_agent`.

## Siguientes Pasos

- Lee la [Guía Completa de Integración](../CLOUDFLARE_AGENT_GUIDE.md)
- Revisa los [Ejemplos de Uso](./example_usage.ts)
- Consulta la [Documentación de Seguridad](./SECURITY.md)
- Explora la [Documentación del Protocolo A2E](../PROTOCOL_OVERVIEW.md)

## Recursos

- [Cloudflare Agents Docs](https://agents.cloudflare.com/)
- [A2E Server API](../server/a2e_server.py)
- [A2E Client SDK](../client/a2e_client.py)

