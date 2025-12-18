"""
Agente con validación proactiva de workflows
"""

from typing import Dict, Any, Optional, Tuple

from agent_with_auth import AuthenticatedWorkflowAgent
from validation.workflow_validator import WorkflowValidator, ValidationLevel


class ValidatedWorkflowAgent(AuthenticatedWorkflowAgent):
    """
    Agente que valida workflows antes de ejecutarlos
    """
    
    def __init__(
        self,
        agent_id: str,
        api_key: Optional[str] = None,
        token: Optional[str] = None,
        api_kb: Optional[Any] = None,
        vault: Optional[Any] = None,
        auth: Optional[Any] = None,
        rag_system: Optional[Any] = None,
        validation_level: ValidationLevel = ValidationLevel.MODERATE
    ):
        super().__init__(
            agent_id=agent_id,
            api_key=api_key,
            token=token,
            api_kb=api_kb,
            vault=vault,
            auth=auth,
            rag_system=rag_system
        )
        
        self.validator = WorkflowValidator(
            api_kb=api_kb,
            vault=vault,
            auth=auth,
            level=validation_level
        )
    
    def validate_and_suggest(
        self,
        workflow_jsonl: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Valida workflow y retorna sugerencias de mejora
        
        Args:
            workflow_jsonl: Workflow a validar
        
        Returns:
            (es_válido, reporte_de_validación)
        """
        report = self.validator.get_validation_report(
            workflow_jsonl=workflow_jsonl,
            agent_id=self.agent_id
        )
        
        return report["valid"], report
    
    def generate_validated_workflow(
        self,
        user_query: str,
        llm_generate_func
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Genera workflow, lo valida, y retorna versión corregida si es necesario
        
        Args:
            user_query: Query del usuario
            llm_generate_func: Función que genera workflow desde query
        
        Returns:
            (workflow_jsonl, reporte_de_validación)
        """
        # Generar workflow inicial
        workflow_jsonl = llm_generate_func(user_query)
        
        # Validar
        is_valid, report = self.validate_and_suggest(workflow_jsonl)
        
        # Si no es válido, intentar corregir
        if not is_valid:
            # Generar workflow corregido con sugerencias
            suggestions = "\n".join([
                f"- {issue['message']}: {issue.get('suggestion', 'No suggestion')}"
                for issue in report["issues"]
                if issue["severity"] == "error"
            ])
            
            corrected_query = f"{user_query}\n\nPrevious workflow had errors:\n{suggestions}\n\nGenerate a corrected workflow."
            workflow_jsonl = llm_generate_func(corrected_query)
            
            # Validar de nuevo
            is_valid, report = self.validate_and_suggest(workflow_jsonl)
        
        return workflow_jsonl, report

