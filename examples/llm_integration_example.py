"""
Ejemplo de cómo un LLM se integraría con A2E
Simula el comportamiento de un LLM usando A2E
"""

import json
from client.a2e_client import A2EClient, WorkflowBuilder


class LLMAgent:
    """
    Simula un agente LLM que usa A2E
    """
    
    def __init__(self, server_url: str, api_key: str):
        self.client = A2EClient(base_url=server_url, api_key=api_key)
        self.capabilities = None
    
    def initialize(self):
        """Inicializa el agente obteniendo capacidades"""
        print("[LLM] Initializing...")
        self.capabilities = self.client.get_capabilities()
        print(f"[LLM] Connected as: {self.capabilities['agent_id']}")
        print(f"[LLM] Available operations: {self.capabilities['capabilities']['supportedOperations']}")
        return self.capabilities
    
    def process_user_query(self, user_query: str):
        """
        Procesa una query del usuario y ejecuta un workflow
        
        En un LLM real, esto sería:
        1. Analizar la query con el modelo
        2. Generar workflow usando las capacidades
        3. Validar y ejecutar
        4. Procesar resultados
        """
        print(f"\n[USER] {user_query}")
        print("\n[LLM] Analyzing query...")
        
        # Simular análisis del LLM
        workflow = self._generate_workflow_from_query(user_query)
        
        print("[LLM] Generated workflow:")
        print(workflow[:200] + "..." if len(workflow) > 200 else workflow)
        
        # Validar
        print("\n[LLM] Validating workflow...")
        validation = self.client.validate_workflow(workflow)
        
        if not validation["valid"]:
            print(f"[LLM] Validation failed: {validation['errors']} errors")
            # En un LLM real, corregiría el workflow
            return {"status": "error", "message": "Workflow validation failed"}
        
        print("[LLM] Workflow is valid")
        
        # Ejecutar
        print("\n[LLM] Executing workflow...")
        result = self.client.execute_workflow(workflow, validate=False)
        
        # Procesar resultados
        print(f"[LLM] Execution status: {result['status']}")
        
        if result["status"] == "success":
            return self._format_success_response(result, user_query)
        else:
            return self._format_error_response(result)
    
    def _generate_workflow_from_query(self, query: str) -> str:
        """
        Genera un workflow desde una query del usuario
        
        En un LLM real, esto usaría el modelo para:
        1. Entender la intención
        2. Mapear a operaciones A2E
        3. Generar JSONL
        """
        query_lower = query.lower()
        
        # Simulación simple de generación de workflow
        # En producción, esto vendría del LLM
        
        if "consulta" in query_lower and "filtra" in query_lower:
            # Query: "Consulta API y filtra datos"
            builder = WorkflowBuilder("user-query-workflow")
            
            # ApiCall
            builder.add_api_call(
                operation_id="fetch",
                method="GET",
                url="https://api.example.com/users",
                headers={
                    "Authorization": {"credentialRef": {"id": "api-token"}}
                },
                output_path="/workflow/users"
            )
            
            # FilterData
            builder.add_filter(
                operation_id="filter",
                input_path="/workflow/users",
                conditions=[
                    {"field": "points", "operator": ">", "value": 100}
                ],
                output_path="/workflow/filtered"
            )
            
            return builder.build()
        
        elif "espera" in query_lower or "wait" in query_lower:
            # Query: "Espera 5 segundos"
            workflow = '{"operationUpdate": {"workflowId": "wait-workflow", "operations": [{"id": "wait", "operation": {"Wait": {"duration": 5000}}}]}}\n{"beginExecution": {"workflowId": "wait-workflow", "root": "wait"}}'
            return workflow
        
        else:
            # Workflow por defecto
            workflow = '{"operationUpdate": {"workflowId": "default", "operations": [{"id": "wait", "operation": {"Wait": {"duration": 100}}}]}}\n{"beginExecution": {"workflowId": "default", "root": "wait"}}'
            return workflow
    
    def _format_success_response(self, result: dict, original_query: str) -> dict:
        """Formatea respuesta exitosa para el usuario"""
        response = {
            "status": "success",
            "message": f"✅ He completado tu solicitud: '{original_query}'",
            "execution_id": result.get("execution_id"),
            "operations_completed": len(result.get("operations", {}))
        }
        
        if "data" in result:
            response["data_summary"] = f"Datos procesados: {len(result['data'])} elementos"
        
        return response
    
    def _format_error_response(self, result: dict) -> dict:
        """Formatea respuesta de error para el usuario"""
        error = result.get("error", {})
        return {
            "status": "error",
            "message": f"❌ Error al ejecutar: {error.get('message', 'Unknown error')}",
            "suggestions": error.get("suggestions", [])
        }


def main():
    """
    Ejemplo de uso: LLM procesando queries del usuario
    """
    print("="*60)
    print("LLM Integration Example - A2E")
    print("="*60)
    
    # Configuración (en producción, esto vendría del sistema)
    SERVER_URL = "http://localhost:8000"
    API_KEY = "your-api-key-here"  # Obtener de agent_auth_cli.py
    
    # Crear agente LLM
    llm = LLMAgent(server_url=SERVER_URL, api_key=API_KEY)
    
    # Inicializar
    capabilities = llm.initialize()
    
    # Procesar queries del usuario
    queries = [
        "Consulta la API de usuarios y filtra los que tienen más de 100 puntos",
        "Espera 2 segundos",
        "Obtén datos y guárdalos"
    ]
    
    print("\n" + "="*60)
    print("Processing User Queries")
    print("="*60)
    
    for query in queries:
        result = llm.process_user_query(query)
        
        print(f"\n[RESULT]")
        print(f"  Status: {result['status']}")
        print(f"  Message: {result['message']}")
        
        if result["status"] == "success":
            print(f"  Execution ID: {result.get('execution_id')}")
            print(f"  Operations: {result.get('operations_completed')}")
    
    print("\n" + "="*60)
    print("Example completed!")
    print("="*60)
    print("\nEn un LLM real:")
    print("1. El LLM recibiría estas queries del usuario")
    print("2. Analizaría la intención usando su modelo")
    print("3. Generaría workflows A2E basados en capacidades")
    print("4. Validaría y ejecutaría los workflows")
    print("5. Procesaría y presentaría los resultados al usuario")


if __name__ == "__main__":
    print("\n⚠️  NOTA: Este es un ejemplo de integración.")
    print("Para ejecutarlo, necesitas:")
    print("1. Tener el servidor A2E corriendo")
    print("2. Registrar un agente y obtener API key")
    print("3. Actualizar SERVER_URL y API_KEY en este archivo\n")
    
    # Descomentar para ejecutar:
    # main()

