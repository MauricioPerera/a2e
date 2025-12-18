"""
Agente que usa base de conocimiento de APIs para generar workflows
"""

import json
import logging
from typing import Dict, Any, Optional

from api_knowledge_base import APIKnowledgeBase, ClientCapabilitiesAnnouncer
from rag_catalog import ComponentRAG, ComponentIndexer

logger = logging.getLogger(__name__)


class WorkflowAgent:
    """
    Agente que genera workflows usando base de conocimiento de APIs
    """
    
    def __init__(
        self,
        api_kb: APIKnowledgeBase,
        rag_system: Optional[ComponentRAG] = None
    ):
        self.api_kb = api_kb
        self.rag = rag_system
        self.capabilities_announcer = ClientCapabilitiesAnnouncer(api_kb)
    
    def get_capabilities_for_llm(self) -> Dict[str, Any]:
        """
        Construye el contexto de capacidades para el LLM
        Similar a cómo se envía el catálogo de componentes
        """
        capabilities = self.capabilities_announcer.build_capabilities_message()
        
        # Formatear para el LLM
        context = {
            "availableOperations": capabilities["workflowCapabilities"]["supportedOperations"],
            "availableApis": capabilities["workflowCapabilities"]["availableApis"],
            "securityConstraints": capabilities["workflowCapabilities"]["securityConstraints"]
        }
        
        return context
    
    def generate_workflow_prompt(
        self,
        user_query: str,
        include_api_info: bool = True
    ) -> str:
        """
        Genera el prompt para el LLM con información de APIs disponibles
        """
        capabilities = self.get_capabilities_for_llm()
        
        prompt_parts = [
            "You are a workflow generation agent. Generate a workflow to fulfill the user's request.",
            "",
            "Available Operations:",
            json.dumps(capabilities["availableOperations"], indent=2),
        ]
        
        if include_api_info:
            prompt_parts.extend([
                "",
                "Available APIs:",
                json.dumps(capabilities["availableApis"], indent=2),
                "",
                "Security Constraints:",
                f"- Only APIs from these domains: {capabilities['securityConstraints']['allowedDomains']}",
                f"- Maximum execution time: {capabilities['securityConstraints']['maxExecutionTime']}ms",
                f"- Maximum operations: {capabilities['securityConstraints']['maxOperations']}",
            ])
        
        prompt_parts.extend([
            "",
            "User Request:",
            user_query,
            "",
            "Generate a workflow JSONL that:",
            "1. Uses only operations from the available operations list",
            "2. Uses only APIs from the available APIs list",
            "3. Respects security constraints",
            "4. Defines the execution order correctly",
        ])
        
        return "\n".join(prompt_parts)
    
    def search_relevant_apis(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Busca APIs relevantes para una query usando RAG o búsqueda simple
        """
        return self.api_kb.search_endpoints(query, top_k=top_k)
    
    def validate_workflow(self, workflow_jsonl: str) -> tuple[bool, Optional[str]]:
        """
        Valida que el workflow solo use operaciones y APIs permitidas
        """
        lines = workflow_jsonl.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                return False, f"Invalid JSON: {line}"
            
            if "operationUpdate" in message:
                operations = message["operationUpdate"].get("operations", [])
                
                for op in operations:
                    op_type = list(op.get("operation", {}).keys())[0]
                    
                    # Validar que la operación está permitida
                    if op_type not in self.api_kb.operations:
                        return False, f"Operation '{op_type}' not in allowed operations"
                    
                    # Si es ApiCall, validar URL
                    if op_type == "ApiCall":
                        config = op["operation"]["ApiCall"]
                        url = config.get("url", "")
                        
                        # Validar dominio
                        allowed_domains = self.capabilities_announcer._get_allowed_domains()
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        
                        if parsed.netloc and parsed.netloc not in allowed_domains:
                            return False, f"URL domain '{parsed.netloc}' not in allowed domains"
        
        return True, None


# Ejemplo de uso
def main():
    from api_knowledge_base import create_example_knowledge_base
    
    # Crear base de conocimiento
    api_kb = create_example_knowledge_base()
    
    # Crear agente
    agent = WorkflowAgent(api_kb)
    
    # Query del usuario
    user_query = "Consulta la API de usuarios, filtra los que tienen más de 100 puntos"
    
    # Buscar APIs relevantes
    relevant_apis = agent.search_relevant_apis(user_query)
    print("APIs relevantes encontradas:")
    for api in relevant_apis:
        print(f"  - {api['method']} {api['baseUrl']}{api['path']}")
    
    # Generar prompt para LLM
    prompt = agent.generate_workflow_prompt(user_query)
    print("\n" + "="*60)
    print("Prompt para LLM:")
    print("="*60)
    print(prompt)


if __name__ == "__main__":
    main()

