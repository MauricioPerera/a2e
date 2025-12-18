"""
Ejecutor de workflows A2UI
Ejecuta operaciones definidas en JSONL en lugar de renderizar UI
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """
    Ejecuta workflows definidos en formato A2UI
    """
    
    def __init__(self):
        self.workflow_state: Dict[str, Any] = {}
        self.operations: Dict[str, Dict[str, Any]] = {}
        self.execution_order: List[str] = []
    
    def load_workflow(self, workflow_jsonl: str):
        """
        Carga un workflow desde JSONL
        """
        lines = workflow_jsonl.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            message = json.loads(line)
            
            if "operationUpdate" in message:
                self._process_operation_update(message["operationUpdate"])
            elif "beginExecution" in message:
                self._process_begin_execution(message["beginExecution"])
    
    def _process_operation_update(self, update: Dict[str, Any]):
        """
        Procesa actualización de operaciones
        """
        workflow_id = update.get("workflowId", "default")
        operations = update.get("operations", [])
        
        for op in operations:
            op_id = op.get("id")
            if op_id:
                self.operations[op_id] = op
                logger.info(f"Loaded operation: {op_id}")
    
    def _process_begin_execution(self, begin: Dict[str, Any]):
        """
        Procesa inicio de ejecución
        """
        root_id = begin.get("root")
        if root_id:
            self.execution_order = self._build_execution_order(root_id)
            logger.info(f"Execution order: {self.execution_order}")
    
    def _build_execution_order(self, root_id: str) -> List[str]:
        """
        Construye el orden de ejecución basándose en dependencias
        """
        # Implementación simple: ejecutar en orden de definición
        # En producción, se analizarían dependencias (inputPath → outputPath)
        order = []
        visited = set()
        
        def traverse(op_id: str):
            if op_id in visited or op_id not in self.operations:
                return
            
            visited.add(op_id)
            op = self.operations[op_id]
            
            # Agregar dependencias primero (simplificado)
            # En producción, analizar inputPath para encontrar dependencias
            order.append(op_id)
        
        traverse(root_id)
        
        # Agregar operaciones restantes
        for op_id in self.operations:
            if op_id not in visited:
                order.append(op_id)
        
        return order
    
    async def execute(self) -> Dict[str, Any]:
        """
        Ejecuta el workflow completo
        """
        results = {}
        
        for op_id in self.execution_order:
            if op_id not in self.operations:
                logger.warning(f"Operation {op_id} not found")
                continue
            
            op = self.operations[op_id]
            operation_type = list(op.get("operation", {}).keys())[0]
            operation_config = op["operation"][operation_type]
            
            logger.info(f"Executing {op_id}: {operation_type}")
            
            try:
                result = await self._execute_operation(operation_type, operation_config)
                results[op_id] = result
            except Exception as e:
                logger.error(f"Error executing {op_id}: {e}")
                results[op_id] = {"error": str(e)}
        
        return results
    
    async def _execute_operation(
        self,
        operation_type: str,
        config: Dict[str, Any]
    ) -> Any:
        """
        Ejecuta una operación específica
        """
        if operation_type == "ApiCall":
            return await self._execute_api_call(config)
        elif operation_type == "FilterData":
            return await self._execute_filter_data(config)
        elif operation_type == "TransformData":
            return await self._execute_transform_data(config)
        elif operation_type == "StoreData":
            return await self._execute_store_data(config)
        elif operation_type == "Wait":
            return await self._execute_wait(config)
        else:
            raise ValueError(f"Unknown operation type: {operation_type}")
    
    async def _execute_api_call(self, config: Dict[str, Any]) -> Any:
        """
        Ejecuta una llamada a API
        """
        import aiohttp
        
        method = config["method"]
        url = self._resolve_path(config["url"])
        headers = self._resolve_object(config.get("headers", {}))
        body = self._resolve_object(config.get("body")) if config.get("body") else None
        
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=body) as response:
                result = await response.json()
                
                # Guardar en data model
                output_path = config["outputPath"]
                self._set_data(output_path, result)
                
                return result
    
    def _execute_filter_data(self, config: Dict[str, Any]) -> List[Any]:
        """
        Filtra datos de un array
        """
        input_path = config["inputPath"]
        data = self._get_data(input_path)
        
        if not isinstance(data, list):
            raise ValueError(f"FilterData requires array, got {type(data)}")
        
        conditions = config.get("conditions", [])
        filtered = data
        
        for condition in conditions:
            field = condition["field"]
            operator = condition["operator"]
            value = self._resolve_value(condition.get("value"))
            
            filtered = [
                item for item in filtered
                if self._evaluate_condition(item.get(field), operator, value)
            ]
        
        output_path = config["outputPath"]
        self._set_data(output_path, filtered)
        
        return filtered
    
    def _execute_transform_data(self, config: Dict[str, Any]) -> Any:
        """
        Transforma datos
        """
        input_path = config["inputPath"]
        transform_type = config["transform"]
        data = self._get_data(input_path)
        
        if transform_type == "map":
            # Implementar map
            pass
        elif transform_type == "sort":
            # Implementar sort
            pass
        # ... más transformaciones
        
        output_path = config["outputPath"]
        self._set_data(output_path, data)
        
        return data
    
    def _execute_store_data(self, config: Dict[str, Any]) -> bool:
        """
        Almacena datos
        """
        input_path = config["inputPath"]
        storage = config["storage"]
        key = config["key"]
        data = self._get_data(input_path)
        
        if storage == "localStorage":
            # En cliente, usar localStorage
            # En servidor, usar base de datos
            pass
        
        return True
    
    async def _execute_wait(self, config: Dict[str, Any]) -> None:
        """
        Espera un tiempo
        """
        import asyncio
        duration = config["duration"]
        await asyncio.sleep(duration / 1000)  # Convertir ms a segundos
    
    def _resolve_path(self, path: str) -> str:
        """
        Resuelve variables en paths usando data model
        """
        # Reemplazar {path} con valores del data model
        import re
        pattern = r'\{([^}]+)\}'
        
        def replace(match):
            var_path = match.group(1)
            value = self._get_data(f"/{var_path}")
            return str(value) if value is not None else match.group(0)
        
        return re.sub(pattern, replace, path)
    
    def _resolve_object(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resuelve paths en objetos
        """
        resolved = {}
        for key, value in obj.items():
            if isinstance(value, dict) and "path" in value:
                resolved[key] = self._get_data(value["path"])
            elif isinstance(value, str) and value.startswith("/"):
                resolved[key] = self._get_data(value)
            else:
                resolved[key] = value
        return resolved
    
    def _resolve_value(self, value: Any) -> Any:
        """
        Resuelve un valor (puede ser literal o path)
        """
        if isinstance(value, dict) and "path" in value:
            return self._get_data(value["path"])
        return value
    
    def _evaluate_condition(self, left: Any, operator: str, right: Any) -> bool:
        """
        Evalúa una condición
        """
        if operator == "==":
            return left == right
        elif operator == "!=":
            return left != right
        elif operator == ">":
            return left > right
        elif operator == "<":
            return left < right
        elif operator == ">=":
            return left >= right
        elif operator == "<=":
            return left <= right
        elif operator == "contains":
            return right in str(left)
        else:
            return False
    
    def _get_data(self, path: str) -> Any:
        """
        Obtiene datos del data model usando JSON Pointer
        """
        if not path.startswith("/"):
            path = "/" + path
        
        parts = path.strip("/").split("/")
        current = self.workflow_state
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    return None
            else:
                return None
            
            if current is None:
                return None
        
        return current
    
    def _set_data(self, path: str, value: Any):
        """
        Establece datos en el data model
        """
        if not path.startswith("/"):
            path = "/" + path
        
        parts = path.strip("/").split("/")
        current = self.workflow_state
        
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value


# Ejemplo de uso
async def main():
    workflow_jsonl = """
{"operationUpdate": {"workflowId": "example", "operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "outputPath": "/workflow/users"
    }
  }},
  {"id": "filter", "operation": {
    "FilterData": {
      "inputPath": "/workflow/users",
      "conditions": [{"field": "points", "operator": ">", "value": 100}],
      "outputPath": "/workflow/filtered"
    }
  }}
]}}
{"beginExecution": {"workflowId": "example", "root": "fetch"}}
"""
    
    executor = WorkflowExecutor()
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("Results:", json.dumps(results, indent=2))

