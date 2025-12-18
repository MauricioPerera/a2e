/**
 * Ejemplo de uso del agente A2E en Cloudflare
 * 
 * Este archivo muestra cómo usar el agente A2E para ejecutar workflows
 */

import { A2EAgent, A2EAgentState, A2EAgentEnv } from './a2e_agent';

/**
 * Ejemplo 1: Configurar y obtener capacidades
 */
export async function example1_GetCapabilities(env: A2EAgentEnv) {
	const agent = new A2EAgent(env, {
		a2eServerUrl: 'http://localhost:8000',
		apiKey: 'your-api-key-here',
		executions: [],
	});

	// Configurar servidor A2E
	await agent.configureA2E('http://localhost:8000', 'your-api-key-here');

	// Obtener capacidades
	const capabilities = await agent.getCapabilities();
	console.log('Available APIs:', Object.keys(capabilities.capabilities?.availableApis || {}));
	console.log('Supported Operations:', capabilities.capabilities?.supportedOperations || []);
}

/**
 * Ejemplo 2: Ejecutar un workflow manual
 */
export async function example2_ExecuteManualWorkflow(env: A2EAgentEnv) {
	const agent = new A2EAgent(env, {
		a2eServerUrl: 'http://localhost:8000',
		apiKey: 'your-api-key-here',
		executions: [],
	});

	await agent.configureA2E('http://localhost:8000', 'your-api-key-here');

	// Workflow simple: hacer una llamada API
	const workflowJsonl = `{"operationUpdate": {"workflowId": "test-workflow", "operations": [
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
		}}
	]}}
{"beginExecution": {"workflowId": "test-workflow", "root": "fetch"}}`;

	// Validar
	const validation = await agent.validateWorkflow(workflowJsonl);
	console.log('Validation:', validation);

	if (validation.valid) {
		// Ejecutar
		const result = await agent.executeWorkflow(workflowJsonl);
		console.log('Execution result:', result);
	}
}

/**
 * Ejemplo 3: Generar y ejecutar workflow usando LLM
 */
export async function example3_GenerateAndExecute(env: A2EAgentEnv) {
	const agent = new A2EAgent(env, {
		a2eServerUrl: 'http://localhost:8000',
		apiKey: 'your-api-key-here',
		executions: [],
	});

	await agent.configureA2E('http://localhost:8000', 'your-api-key-here');

	// Generar y ejecutar workflow usando LLM
	const description = 'Obtener usuarios activos de la API y filtrar los que tienen más de 100 puntos';
	
	const result = await agent.generateAndExecuteWorkflow(description, true);
	console.log('Generated and executed workflow:', result);
}

/**
 * Ejemplo 4: Buscar conocimiento usando RAG
 */
export async function example4_SearchKnowledge(env: A2EAgentEnv) {
	const agent = new A2EAgent(env, {
		a2eServerUrl: 'http://localhost:8000',
		apiKey: 'your-api-key-here',
		executions: [],
	});

	await agent.configureA2E('http://localhost:8000', 'your-api-key-here');

	// Buscar conocimiento relevante
	const results = await agent.searchKnowledge('cómo obtener usuarios', undefined, undefined, 5);
	console.log('Knowledge search results:', results);
}

/**
 * Ejemplo 5: Buscar consultas SQL
 */
export async function example5_SearchSQLQueries(env: A2EAgentEnv) {
	const agent = new A2EAgent(env, {
		a2eServerUrl: 'http://localhost:8000',
		apiKey: 'your-api-key-here',
		executions: [],
	});

	await agent.configureA2E('http://localhost:8000', 'your-api-key-here');

	// Buscar consultas SQL relevantes
	const results = await agent.searchSQLQueries('obtener usuarios activos', 'users_db', 'analytics', 5);
	console.log('SQL queries found:', results);
}

/**
 * Ejemplo 6: Obtener historial de ejecuciones
 */
export async function example6_GetHistory(env: A2EAgentEnv) {
	const agent = new A2EAgent(env, {
		a2eServerUrl: 'http://localhost:8000',
		apiKey: 'your-api-key-here',
		executions: [],
	});

	await agent.configureA2E('http://localhost:8000', 'your-api-key-here');

	// Obtener historial local
	const localHistory = await agent.getExecutionHistory(10);
	console.log('Local execution history:', localHistory);

	// Obtener historial del servidor
	const serverHistory = await agent.listExecutions(100);
	console.log('Server execution history:', serverHistory);
}

