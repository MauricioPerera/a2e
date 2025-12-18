/**
 * A2E Cloudflare Agent
 * 
 * Este agente se conecta al servidor A2E para ejecutar workflows declarativos.
 * Basado en Cloudflare Agents SDK: https://agents.cloudflare.com/
 */

import { Agent, callable } from 'agents';

/**
 * Estado del agente A2E
 */
export type A2EAgentState = {
	// Configuración del servidor A2E
	a2eServerUrl: string;
	apiKey?: string;
	token?: string;
	
	// Historial de ejecuciones
	executions: Array<{
		executionId: string;
		workflowId: string;
		status: string;
		timestamp: number;
		result?: any;
	}>;
	
	// Capacidades disponibles del servidor A2E
	capabilities?: {
		availableApis: Record<string, any>;
		availableCredentials: Array<any>;
		supportedOperations: Array<string>;
	};
	
	// Última ejecución
	lastExecution?: {
		executionId: string;
		workflowId: string;
		status: string;
		result?: any;
	};
};

/**
 * Variables de entorno del agente
 */
export interface A2EAgentEnv {
	// Cloudflare AI
	AI: any;
	
	// Variables de configuración A2E (opcionales, pueden venir del estado)
	A2E_SERVER_URL?: string;
	A2E_API_KEY?: string;
	A2E_TOKEN?: string;
}

/**
 * Cliente HTTP para comunicarse con el servidor A2E
 */
class A2EClient {
	private baseUrl: string;
	private apiKey?: string;
	private token?: string;

	constructor(baseUrl: string, apiKey?: string, token?: string) {
		this.baseUrl = baseUrl.replace(/\/$/, '');
		this.apiKey = apiKey;
		this.token = token;
	}

	private getHeaders(): HeadersInit {
		const headers: HeadersInit = {
			'Content-Type': 'application/json',
		};

		if (this.apiKey) {
			headers['X-API-Key'] = this.apiKey;
		} else if (this.token) {
			headers['Authorization'] = `Bearer ${this.token}`;
		}

		return headers;
	}

	/**
	 * Obtiene las capacidades disponibles del servidor A2E
	 */
	async getCapabilities(): Promise<any> {
		const response = await fetch(`${this.baseUrl}/api/v1/capabilities`, {
			method: 'GET',
			headers: this.getHeaders(),
		});

		if (!response.ok) {
			throw new Error(`Failed to get capabilities: ${response.statusText}`);
		}

		return await response.json();
	}

	/**
	 * Valida un workflow antes de ejecutarlo
	 */
	async validateWorkflow(workflowJsonl: string): Promise<any> {
		const response = await fetch(`${this.baseUrl}/api/v1/workflows/validate`, {
			method: 'POST',
			headers: this.getHeaders(),
			body: JSON.stringify({ workflow: workflowJsonl }),
		});

		if (!response.ok) {
			throw new Error(`Failed to validate workflow: ${response.statusText}`);
		}

		return await response.json();
	}

	/**
	 * Ejecuta un workflow en el servidor A2E
	 */
	async executeWorkflow(workflowJsonl: string, validate: boolean = true): Promise<any> {
		const response = await fetch(`${this.baseUrl}/api/v1/workflows/execute`, {
			method: 'POST',
			headers: this.getHeaders(),
			body: JSON.stringify({
				workflow: workflowJsonl,
				validate: validate,
			}),
		});

		if (!response.ok) {
			const error = await response.text();
			throw new Error(`Failed to execute workflow: ${response.statusText} - ${error}`);
		}

		return await response.json();
	}

	/**
	 * Obtiene detalles de una ejecución
	 */
	async getExecution(executionId: string): Promise<any> {
		const response = await fetch(`${this.baseUrl}/api/v1/executions/${executionId}`, {
			method: 'GET',
			headers: this.getHeaders(),
		});

		if (!response.ok) {
			throw new Error(`Failed to get execution: ${response.statusText}`);
		}

		return await response.json();
	}

	/**
	 * Lista ejecuciones del agente
	 */
	async listExecutions(limit: number = 100, status?: string): Promise<any[]> {
		const params = new URLSearchParams({ limit: limit.toString() });
		if (status) {
			params.append('status', status);
		}

		const response = await fetch(`${this.baseUrl}/api/v1/executions?${params}`, {
			method: 'GET',
			headers: this.getHeaders(),
		});

		if (!response.ok) {
			throw new Error(`Failed to list executions: ${response.statusText}`);
		}

		const data = await response.json();
		return data.executions || [];
	}

	/**
	 * Busca conocimiento relevante usando RAG
	 */
	async searchKnowledge(
		query: string,
		kbId?: string,
		knowledgeType?: string,
		topK: number = 5
	): Promise<any[]> {
		const response = await fetch(`${this.baseUrl}/api/v1/knowledge/search`, {
			method: 'POST',
			headers: this.getHeaders(),
			body: JSON.stringify({
				query: query,
				kb_id: kbId,
				type: knowledgeType,
				top_k: topK,
			}),
		});

		if (!response.ok) {
			throw new Error(`Failed to search knowledge: ${response.statusText}`);
		}

		const data = await response.json();
		return data.results || [];
	}

	/**
	 * Busca consultas SQL relevantes
	 */
	async searchSQLQueries(
		query: string,
		database?: string,
		category?: string,
		topK: number = 5
	): Promise<any[]> {
		const response = await fetch(`${this.baseUrl}/api/v1/sql-queries/search`, {
			method: 'POST',
			headers: this.getHeaders(),
			body: JSON.stringify({
				query: query,
				database: database,
				category: category,
				top_k: topK,
			}),
		});

		if (!response.ok) {
			throw new Error(`Failed to search SQL queries: ${response.statusText}`);
		}

		const data = await response.json();
		return data.results || [];
	}
}

/**
 * Agente A2E para Cloudflare
 * 
 * Este agente permite ejecutar workflows declarativos en el servidor A2E,
 * utilizando LLMs para generar workflows basados en descripciones en lenguaje natural.
 */
export class A2EAgent extends Agent<A2EAgentEnv, A2EAgentState> {
	private a2eClient: A2EClient | null = null;

	onStart() {
		// Inicializar cliente A2E
		const serverUrl = this.state.a2eServerUrl || this.env.A2E_SERVER_URL || 'http://localhost:8000';
		const apiKey = this.state.apiKey || this.env.A2E_API_KEY;
		const token = this.state.token || this.env.A2E_TOKEN;

		if (!apiKey && !token) {
			console.warn('A2E Agent: No API key or token provided. Some operations may fail.');
		}

		this.a2eClient = new A2EClient(serverUrl, apiKey, token);

		// Cargar capacidades al iniciar
		this.loadCapabilities();
	}

	/**
	 * Carga las capacidades disponibles del servidor A2E
	 */
	private async loadCapabilities() {
		if (!this.a2eClient) return;

		try {
			const capabilities = await this.a2eClient.getCapabilities();
			this.setState({
				...this.state,
				capabilities: capabilities.capabilities || capabilities,
			});
		} catch (error) {
			console.error('Failed to load A2E capabilities:', error);
		}
	}

	/**
	 * Configura la conexión al servidor A2E
	 */
	@callable()
	async configureA2E(serverUrl: string, apiKey?: string, token?: string) {
		this.setState({
			...this.state,
			a2eServerUrl: serverUrl,
			apiKey: apiKey,
			token: token,
		});

		// Recrear cliente con nueva configuración
		this.a2eClient = new A2EClient(serverUrl, apiKey, token);
		await this.loadCapabilities();

		return {
			success: true,
			message: 'A2E server configured successfully',
			serverUrl: serverUrl,
		};
	}

	/**
	 * Obtiene las capacidades disponibles del servidor A2E
	 */
	@callable()
	async getCapabilities() {
		if (!this.a2eClient) {
			throw new Error('A2E client not initialized. Call configureA2E first.');
		}

		const capabilities = await this.a2eClient.getCapabilities();
		
		// Actualizar estado
		this.setState({
			...this.state,
			capabilities: capabilities.capabilities || capabilities,
		});

		return capabilities;
	}

	/**
	 * Busca conocimiento relevante usando RAG
	 */
	@callable()
	async searchKnowledge(
		query: string,
		kbId?: string,
		knowledgeType?: string,
		topK: number = 5
	) {
		if (!this.a2eClient) {
			throw new Error('A2E client not initialized. Call configureA2E first.');
		}

		const results = await this.a2eClient.searchKnowledge(query, kbId, knowledgeType, topK);
		return {
			query: query,
			results: results,
			count: results.length,
		};
	}

	/**
	 * Busca consultas SQL relevantes
	 */
	@callable()
	async searchSQLQueries(
		query: string,
		database?: string,
		category?: string,
		topK: number = 5
	) {
		if (!this.a2eClient) {
			throw new Error('A2E client not initialized. Call configureA2E first.');
		}

		const results = await this.a2eClient.searchSQLQueries(query, database, category, topK);
		return {
			query: query,
			results: results,
			count: results.length,
		};
	}

	/**
	 * Valida un workflow antes de ejecutarlo
	 */
	@callable()
	async validateWorkflow(workflowJsonl: string) {
		if (!this.a2eClient) {
			throw new Error('A2E client not initialized. Call configureA2E first.');
		}

		const validation = await this.a2eClient.validateWorkflow(workflowJsonl);
		return validation;
	}

	/**
	 * Ejecuta un workflow en el servidor A2E
	 */
	@callable()
	async executeWorkflow(workflowJsonl: string, validate: boolean = true) {
		if (!this.a2eClient) {
			throw new Error('A2E client not initialized. Call configureA2E first.');
		}

		// Validar si se solicita
		if (validate) {
			const validation = await this.a2eClient.validateWorkflow(workflowJsonl);
			if (!validation.valid) {
				return {
					success: false,
					error: 'Workflow validation failed',
					validation: validation,
				};
			}
		}

		// Ejecutar workflow
		const result = await this.a2eClient.executeWorkflow(workflowJsonl, false);

		// Guardar en historial
		const execution = {
			executionId: result.execution_id || result.executionId || `exec-${Date.now()}`,
			workflowId: result.workflow_id || result.workflowId || 'unknown',
			status: result.status || 'unknown',
			timestamp: Date.now(),
			result: result,
		};

		const executions = [...(this.state.executions || []), execution];
		if (executions.length > 100) {
			executions.shift(); // Mantener solo las últimas 100
		}

		this.setState({
			...this.state,
			executions: executions,
			lastExecution: execution,
		});

		return result;
	}

	/**
	 * Genera y ejecuta un workflow basado en una descripción en lenguaje natural
	 * Utiliza un LLM para generar el workflow automáticamente
	 */
	@callable()
	async generateAndExecuteWorkflow(
		description: string,
		useLLM: boolean = true,
		llmModel: string = '@cf/meta/llama-3.3-70b-instruct-fp8-fast'
	) {
		if (!this.a2eClient) {
			throw new Error('A2E client not initialized. Call configureA2E first.');
		}

		let workflowJsonl: string;

		if (useLLM && this.env.AI) {
			// Obtener capacidades para el prompt
			const capabilities = this.state.capabilities || await this.a2eClient.getCapabilities();
			const capabilitiesStr = JSON.stringify(capabilities, null, 2);

			// Generar workflow usando LLM
			const { response } = await this.env.AI.run(llmModel, {
				messages: [
					{
						role: 'system',
						content: `You are an expert at generating A2E workflows. 
A2E workflows are in JSONL format (JSON Lines), where each line is a JSON object.

Available capabilities:
${capabilitiesStr}

Workflow format:
1. First line: {"operationUpdate": {"workflowId": "workflow-id", "operations": [...]}}
2. Second line: {"beginExecution": {"workflowId": "workflow-id", "root": "operation-id"}}

Operations can be:
- ApiCall: {"ApiCall": {"method": "GET|POST|PUT|DELETE", "url": "...", "headers": {...}, "body": {...}, "outputPath": "/workflow/result"}}
- FilterData: {"FilterData": {"inputPath": "/workflow/data", "conditions": [...], "outputPath": "/workflow/filtered"}}
- TransformData: {"TransformData": {"inputPath": "/workflow/data", "transformations": [...], "outputPath": "/workflow/transformed"}}
- StoreData: {"StoreData": {"inputPath": "/workflow/data", "storage": "localStorage", "key": "key"}}
- Wait: {"Wait": {"duration": 1000}}
- Conditional: {"Conditional": {"condition": {...}, "ifTrue": "operation-id", "ifFalse": "operation-id"}}

Generate ONLY the JSONL workflow, no explanations.`,
					},
					{
						role: 'user',
						content: `Generate an A2E workflow for: ${description}`,
					},
				],
			});

			// Extraer JSONL de la respuesta del LLM
			workflowJsonl = response.message?.content || response.content || response;
			
			// Limpiar la respuesta si tiene markdown code blocks
			workflowJsonl = workflowJsonl.replace(/```jsonl?\n?/g, '').replace(/```\n?/g, '').trim();
		} else {
			throw new Error('LLM generation requires AI environment. Set useLLM=false and provide workflowJsonl manually.');
		}

		// Ejecutar el workflow generado
		return await this.executeWorkflow(workflowJsonl, true);
	}

	/**
	 * Obtiene detalles de una ejecución
	 */
	@callable()
	async getExecution(executionId: string) {
		if (!this.a2eClient) {
			throw new Error('A2E client not initialized. Call configureA2E first.');
		}

		const execution = await this.a2eClient.getExecution(executionId);
		return execution;
	}

	/**
	 * Lista ejecuciones del agente
	 */
	@callable()
	async listExecutions(limit: number = 100, status?: string) {
		if (!this.a2eClient) {
			throw new Error('A2E client not initialized. Call configureA2E first.');
		}

		const executions = await this.a2eClient.listExecutions(limit, status);
		return {
			executions: executions,
			count: executions.length,
		};
	}

	/**
	 * Obtiene el historial de ejecuciones del agente
	 */
	@callable()
	async getExecutionHistory(limit: number = 10) {
		const executions = (this.state.executions || []).slice(-limit);
		return {
			executions: executions,
			count: executions.length,
		};
	}
}

