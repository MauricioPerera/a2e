"""
Ejemplos de uso del agente A2E con Google ADK
"""

import asyncio
from a2e_agent import create_a2e_agent, A2EAgent


async def example1_basic_usage():
    """Ejemplo 1: Uso básico del agente"""
    print("=" * 60)
    print("Ejemplo 1: Uso Básico")
    print("=" * 60)
    
    # Crear agente
    agent = create_a2e_agent(
        a2e_server_url="http://localhost:8000",
        api_key="your-api-key-here"
    )
    
    # Obtener capacidades
    print("\n1. Obteniendo capacidades...")
    capabilities = agent.get_capabilities()
    print(f"   APIs disponibles: {list(capabilities.get('capabilities', {}).get('availableApis', {}).keys())}")
    print(f"   Operaciones: {capabilities.get('capabilities', {}).get('supportedOperations', [])}")
    
    # Interactuar con el agente
    print("\n2. Consultando al agente...")
    response = await agent.run("¿Qué capacidades tengo disponibles en el servidor A2E?")
    print(f"   Respuesta: {response.content}")


async def example2_execute_workflow():
    """Ejemplo 2: Ejecutar un workflow"""
    print("\n" + "=" * 60)
    print("Ejemplo 2: Ejecutar Workflow")
    print("=" * 60)
    
    agent = create_a2e_agent(
        a2e_server_url="http://localhost:8000",
        api_key="your-api-key-here"
    )
    
    # Workflow simple: esperar 100ms
    workflow_jsonl = """{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "wait", "operation": {"Wait": {"duration": 100}}}
]}}
{"beginExecution": {"workflowId": "test", "root": "wait"}}"""
    
    print("\n1. Ejecutando workflow...")
    result = agent.execute_workflow_direct(workflow_jsonl, validate=True)
    print(f"   Estado: {result.get('status')}")
    print(f"   Execution ID: {result.get('execution_id')}")


async def example3_generate_workflow_with_llm():
    """Ejemplo 3: Generar workflow usando LLM"""
    print("\n" + "=" * 60)
    print("Ejemplo 3: Generar Workflow con LLM")
    print("=" * 60)
    
    agent = create_a2e_agent(
        a2e_server_url="http://localhost:8000",
        api_key="your-api-key-here"
    )
    
    # Pedir al agente que genere y ejecute un workflow
    print("\n1. Pidiendo al agente que genere un workflow...")
    response = await agent.run(
        "Genera y ejecuta un workflow que espere 1 segundo y luego haga una llamada GET a https://api.example.com/users"
    )
    print(f"   Respuesta: {response.content}")


async def example4_search_knowledge():
    """Ejemplo 4: Buscar conocimiento usando RAG"""
    print("\n" + "=" * 60)
    print("Ejemplo 4: Buscar Conocimiento (RAG)")
    print("=" * 60)
    
    agent = create_a2e_agent(
        a2e_server_url="http://localhost:8000",
        api_key="your-api-key-here"
    )
    
    print("\n1. Buscando conocimiento...")
    response = await agent.run("Busca información sobre cómo obtener usuarios de una API")
    print(f"   Respuesta: {response.content}")


async def example5_search_sql_queries():
    """Ejemplo 5: Buscar consultas SQL"""
    print("\n" + "=" * 60)
    print("Ejemplo 5: Buscar Consultas SQL")
    print("=" * 60)
    
    agent = create_a2e_agent(
        a2e_server_url="http://localhost:8000",
        api_key="your-api-key-here"
    )
    
    print("\n1. Buscando consultas SQL...")
    response = await agent.run("Busca consultas SQL para obtener usuarios activos")
    print(f"   Respuesta: {response.content}")


async def example6_workflow_validation():
    """Ejemplo 6: Validar workflow"""
    print("\n" + "=" * 60)
    print("Ejemplo 6: Validar Workflow")
    print("=" * 60)
    
    agent = create_a2e_agent(
        a2e_server_url="http://localhost:8000",
        api_key="your-api-key-here"
    )
    
    # Workflow con error potencial
    workflow_jsonl = """{"operationUpdate": {"workflowId": "test", "operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "outputPath": "/workflow/users"
    }
  }}
]}}
{"beginExecution": {"workflowId": "test", "root": "fetch"}}"""
    
    print("\n1. Validando workflow...")
    response = await agent.run(f"Valida este workflow: {workflow_jsonl}")
    print(f"   Respuesta: {response.content}")


async def main():
    """Ejecuta todos los ejemplos"""
    print("\n" + "=" * 60)
    print("Ejemplos de Uso: A2E Agent con Google ADK")
    print("=" * 60)
    
    try:
        await example1_basic_usage()
        await example2_execute_workflow()
        await example3_generate_workflow_with_llm()
        await example4_search_knowledge()
        await example5_search_sql_queries()
        await example6_workflow_validation()
        
        print("\n" + "=" * 60)
        print("Todos los ejemplos completados")
        print("=" * 60)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

