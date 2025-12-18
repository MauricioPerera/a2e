"""
Ejecutor de workflows A2UI
Ejecuta operaciones definidas en JSONL en lugar de renderizar UI
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Intentar importar pytz, pero no fallar si no está disponible
try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    logger.warning("pytz not available. Timezone operations will be limited.")


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
        elif operation_type == "GetCurrentDateTime":
            return self._execute_get_current_datetime(config)
        elif operation_type == "ConvertTimezone":
            return self._execute_convert_timezone(config)
        elif operation_type == "DateCalculation":
            return self._execute_date_calculation(config)
        elif operation_type == "FormatText":
            return self._execute_format_text(config)
        elif operation_type == "ExtractText":
            return self._execute_extract_text(config)
        elif operation_type == "ValidateData":
            return self._execute_validate_data(config)
        elif operation_type == "Calculate":
            return self._execute_calculate(config)
        elif operation_type == "EncodeDecode":
            return self._execute_encode_decode(config)
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
    
    def _execute_get_current_datetime(self, config: Dict[str, Any]) -> str:
        """
        Obtiene la fecha y hora actual
        """
        from datetime import datetime
        import pytz
        
        timezone_str = config.get("timezone")
        format_type = config.get("format", "iso8601")
        format_string = config.get("formatString")
        output_path = config["outputPath"]
        
        # Obtener fecha/hora actual
        if timezone_str:
            try:
                tz = pytz.timezone(timezone_str)
                now = datetime.now(tz)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone: {timezone_str}, using system timezone")
                now = datetime.now()
        else:
            now = datetime.now()
        
        # Formatear según el tipo solicitado
        if format_type == "timestamp":
            result = now.timestamp()
        elif format_type == "custom" and format_string:
            result = now.strftime(format_string)
        else:  # iso8601 (default)
            result = now.isoformat()
        
        # Guardar en data model
        self._set_data(output_path, result)
        
        return result
    
    def _execute_convert_timezone(self, config: Dict[str, Any]) -> str:
        """
        Convierte una fecha/hora de una zona horaria a otra
        """
        from datetime import datetime
        import pytz
        
        input_path = config["inputPath"]
        from_timezone_str = config.get("fromTimezone")
        to_timezone_str = config["toTimezone"]
        format_type = config.get("format", "iso8601")
        format_string = config.get("formatString")
        output_path = config["outputPath"]
        
        # Obtener fecha/hora de entrada
        input_value = self._get_data(input_path)
        
        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")
        
        # Parsear fecha/hora
        dt = None
        
        if isinstance(input_value, (int, float)):
            # Unix timestamp
            dt = datetime.fromtimestamp(input_value, tz=pytz.UTC)
        elif isinstance(input_value, str):
            # Intentar parsear ISO 8601
            try:
                dt = datetime.fromisoformat(input_value.replace('Z', '+00:00'))
            except ValueError:
                # Intentar otros formatos comunes
                try:
                    dt = datetime.strptime(input_value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    raise ValueError(f"Unable to parse date string: {input_value}")
        elif isinstance(input_value, dict):
            # Objeto con campos date/time
            year = input_value.get("year", datetime.now().year)
            month = input_value.get("month", datetime.now().month)
            day = input_value.get("day", datetime.now().day)
            hour = input_value.get("hour", 0)
            minute = input_value.get("minute", 0)
            second = input_value.get("second", 0)
            dt = datetime(year, month, day, hour, minute, second)
        else:
            raise ValueError(f"Unsupported date format: {type(input_value)}")
        
        # Si no tiene timezone y se especificó fromTimezone, aplicarla
        if dt.tzinfo is None and from_timezone_str:
            try:
                from_tz = pytz.timezone(from_timezone_str)
                dt = from_tz.localize(dt)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Unknown from_timezone: {from_timezone_str}, assuming UTC")
                dt = pytz.UTC.localize(dt)
        elif dt.tzinfo is None:
            # Si no tiene timezone, asumir UTC
            dt = pytz.UTC.localize(dt)
        
        # Convertir a zona horaria destino
        try:
            to_tz = pytz.timezone(to_timezone_str)
            converted_dt = dt.astimezone(to_tz)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f"Unknown timezone: {to_timezone_str}")
        
        # Formatear según el tipo solicitado
        if format_type == "timestamp":
            result = converted_dt.timestamp()
        elif format_type == "custom" and format_string:
            result = converted_dt.strftime(format_string)
        else:  # iso8601 (default)
            result = converted_dt.isoformat()
        
        # Guardar en data model
        self._set_data(output_path, result)
        
        return result
    
    def _execute_date_calculation(self, config: Dict[str, Any]) -> str:
        """
        Realiza cálculos con fechas (sumar días, restar horas, etc.)
        """
        from datetime import datetime, timedelta
        import pytz
        
        input_path = config["inputPath"]
        operation = config["operation"]
        timezone_str = config.get("timezone")
        format_type = config.get("format", "iso8601")
        format_string = config.get("formatString")
        output_path = config["outputPath"]
        
        # Obtener fecha base
        input_value = self._get_data(input_path)
        
        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")
        
        # Parsear fecha/hora
        dt = None
        
        if isinstance(input_value, (int, float)):
            # Unix timestamp
            dt = datetime.fromtimestamp(input_value, tz=pytz.UTC)
        elif isinstance(input_value, str):
            # Intentar parsear ISO 8601
            try:
                dt = datetime.fromisoformat(input_value.replace('Z', '+00:00'))
            except ValueError:
                try:
                    dt = datetime.strptime(input_value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    raise ValueError(f"Unable to parse date string: {input_value}")
        elif isinstance(input_value, dict):
            # Objeto con campos date/time
            year = input_value.get("year", datetime.now().year)
            month = input_value.get("month", datetime.now().month)
            day = input_value.get("day", datetime.now().day)
            hour = input_value.get("hour", 0)
            minute = input_value.get("minute", 0)
            second = input_value.get("second", 0)
            dt = datetime(year, month, day, hour, minute, second)
        else:
            raise ValueError(f"Unsupported date format: {type(input_value)}")
        
        # Aplicar timezone si se especificó y la fecha no tiene timezone
        if dt.tzinfo is None and timezone_str:
            try:
                tz = pytz.timezone(timezone_str)
                dt = tz.localize(dt)
            except pytz.exceptions.UnknownTimeZoneError:
                logger.warning(f"Unknown timezone: {timezone_str}, using UTC")
                dt = pytz.UTC.localize(dt)
        elif dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        # Calcular delta
        delta_kwargs = {}
        if "years" in config:
            delta_kwargs["days"] = delta_kwargs.get("days", 0) + (config["years"] * 365)
        if "months" in config:
            delta_kwargs["days"] = delta_kwargs.get("days", 0) + (config["months"] * 30)
        if "days" in config:
            delta_kwargs["days"] = delta_kwargs.get("days", 0) + config["days"]
        if "hours" in config:
            delta_kwargs["hours"] = config["hours"]
        if "minutes" in config:
            delta_kwargs["minutes"] = config["minutes"]
        if "seconds" in config:
            delta_kwargs["seconds"] = config["seconds"]
        
        delta = timedelta(**delta_kwargs)
        
        # Aplicar operación
        if operation == "add":
            result_dt = dt + delta
        elif operation == "subtract":
            result_dt = dt - delta
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Formatear según el tipo solicitado
        if format_type == "timestamp":
            result = result_dt.timestamp()
        elif format_type == "custom" and format_string:
            result = result_dt.strftime(format_string)
        else:  # iso8601 (default)
            result = result_dt.isoformat()
        
        # Guardar en data model
        self._set_data(output_path, result)
        
        return result
    
    def _execute_format_text(self, config: Dict[str, Any]) -> str:
        """
        Formatea texto usando plantillas o transformaciones
        """
        import re
        
        input_path = config["inputPath"]
        format_type = config["format"]
        output_path = config["outputPath"]
        
        # Obtener texto de entrada
        input_value = self._get_data(input_path)
        
        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")
        
        # Convertir a string si no lo es
        if not isinstance(input_value, str):
            if isinstance(input_value, dict):
                # Si es un objeto, usar template
                if format_type == "template":
                    template = config.get("template", str(input_value))
                    result = template.format(**input_value)
                else:
                    result = str(input_value)
            else:
                result = str(input_value)
        else:
            result = input_value
        
        # Aplicar formato
        if format_type == "upper":
            result = result.upper()
        elif format_type == "lower":
            result = result.lower()
        elif format_type == "title":
            result = result.title()
        elif format_type == "capitalize":
            result = result.capitalize()
        elif format_type == "trim":
            result = result.strip()
        elif format_type == "template":
            template = config.get("template", result)
            # Si input_value es dict, usar format
            if isinstance(input_value, dict):
                result = template.format(**input_value)
            else:
                # Reemplazar {value} con el valor
                result = template.replace("{value}", str(input_value))
        elif format_type == "replace":
            replacements = config.get("replacements", {})
            for old, new in replacements.items():
                result = result.replace(old, new)
        
        # Guardar en data model
        self._set_data(output_path, result)
        
        return result
    
    def _execute_extract_text(self, config: Dict[str, Any]) -> Any:
        """
        Extrae información de texto usando expresiones regulares
        """
        import re
        
        input_path = config["inputPath"]
        pattern = config["pattern"]
        extract_all = config.get("extractAll", False)
        output_path = config["outputPath"]
        
        # Obtener texto
        input_value = self._get_data(input_path)
        
        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")
        
        text = str(input_value)
        
        # Compilar regex
        try:
            regex = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {pattern} - {e}")
        
        # Extraer
        if extract_all:
            matches = regex.findall(text)
            result = matches if matches else []
        else:
            match = regex.search(text)
            result = match.group(0) if match else None
        
        # Guardar en data model
        self._set_data(output_path, result)
        
        return result
    
    def _execute_validate_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida datos usando reglas predefinidas
        """
        import re
        from urllib.parse import urlparse
        
        input_path = config["inputPath"]
        validation_type = config["validationType"]
        pattern = config.get("pattern")
        output_path = config["outputPath"]
        
        # Obtener datos
        input_value = self._get_data(input_path)
        
        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")
        
        value_str = str(input_value)
        is_valid = False
        error_message = None
        
        # Validar según tipo
        if validation_type == "email":
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            is_valid = bool(re.match(email_pattern, value_str))
            if not is_valid:
                error_message = "Invalid email format"
        
        elif validation_type == "url":
            try:
                parsed = urlparse(value_str)
                is_valid = all([parsed.scheme, parsed.netloc])
                if not is_valid:
                    error_message = "Invalid URL format"
            except:
                is_valid = False
                error_message = "Invalid URL format"
        
        elif validation_type == "number":
            try:
                float(value_str)
                is_valid = True
            except ValueError:
                is_valid = False
                error_message = "Not a valid number"
        
        elif validation_type == "integer":
            try:
                int(value_str)
                is_valid = True
            except ValueError:
                is_valid = False
                error_message = "Not a valid integer"
        
        elif validation_type == "phone":
            # Patrón básico para números de teléfono
            phone_pattern = r'^[\d\s\-\+\(\)]+$'
            is_valid = bool(re.match(phone_pattern, value_str)) and len(re.sub(r'[\s\-\+\(\)]', '', value_str)) >= 10
            if not is_valid:
                error_message = "Invalid phone number format"
        
        elif validation_type == "date":
            try:
                datetime.fromisoformat(value_str.replace('Z', '+00:00'))
                is_valid = True
            except:
                try:
                    datetime.strptime(value_str, "%Y-%m-%d")
                    is_valid = True
                except:
                    is_valid = False
                    error_message = "Invalid date format"
        
        elif validation_type == "custom":
            if not pattern:
                raise ValueError("pattern is required for custom validation")
            try:
                regex = re.compile(pattern)
                is_valid = bool(regex.match(value_str))
                if not is_valid:
                    error_message = f"Value does not match pattern: {pattern}"
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {pattern} - {e}")
        
        # Crear resultado
        result = {
            "valid": is_valid,
            "value": input_value
        }
        
        if error_message:
            result["error"] = error_message
        
        # Guardar en data model
        self._set_data(output_path, result)
        
        return result
    
    def _execute_calculate(self, config: Dict[str, Any]) -> Any:
        """
        Realiza cálculos matemáticos
        """
        import math
        
        input_path = config["inputPath"]
        operation = config["operation"]
        operand = config.get("operand")
        precision = config.get("precision", 2)
        output_path = config["outputPath"]
        
        # Obtener valor de entrada
        input_value = self._get_data(input_path)
        
        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")
        
        # Resolver operando si es necesario
        if operand is not None:
            if isinstance(operand, str) and operand.startswith("/"):
                # Es un path
                operand = self._get_data(operand)
            if isinstance(operand, str):
                try:
                    operand = float(operand)
                except ValueError:
                    raise ValueError(f"Cannot convert operand '{operand}' to number")
        
        # Operaciones que trabajan con listas
        if operation in ["sum", "average"]:
            if isinstance(input_value, list):
                numbers = []
                for x in input_value:
                    if isinstance(x, (int, float)):
                        numbers.append(float(x))
                    elif isinstance(x, str):
                        try:
                            numbers.append(float(x))
                        except ValueError:
                            pass  # Ignorar valores no numéricos
                
                if operation == "sum":
                    result = sum(numbers)
                else:  # average
                    result = sum(numbers) / len(numbers) if numbers else 0
                
                self._set_data(output_path, result)
                return result
            else:
                # Si no es lista, tratar como número único
                if isinstance(input_value, str):
                    try:
                        input_value = float(input_value)
                    except ValueError:
                        raise ValueError(f"Cannot convert '{input_value}' to number")
                
                if operation == "sum":
                    result = float(input_value)
                else:  # average
                    result = float(input_value)
                
                self._set_data(output_path, result)
                return result
        
        # Para otras operaciones, convertir a número
        if isinstance(input_value, str):
            try:
                input_value = float(input_value)
            except ValueError:
                raise ValueError(f"Cannot convert '{input_value}' to number")
        
        if not isinstance(input_value, (int, float)):
            raise ValueError(f"Input must be a number, got {type(input_value)}")
        
        # Realizar cálculo
        if operation == "add":
            if operand is None:
                raise ValueError("operand is required for 'add' operation")
            result = input_value + operand
        
        elif operation == "subtract":
            if operand is None:
                raise ValueError("operand is required for 'subtract' operation")
            result = input_value - operand
        
        elif operation == "multiply":
            if operand is None:
                raise ValueError("operand is required for 'multiply' operation")
            result = input_value * operand
        
        elif operation == "divide":
            if operand is None:
                raise ValueError("operand is required for 'divide' operation")
            if operand == 0:
                raise ValueError("Division by zero")
            result = input_value / operand
        
        elif operation == "power":
            if operand is None:
                raise ValueError("operand is required for 'power' operation")
            result = input_value ** operand
        
        elif operation == "modulo":
            if operand is None:
                raise ValueError("operand is required for 'modulo' operation")
            result = input_value % operand
        
        elif operation == "round":
            result = round(input_value, int(precision))
        
        elif operation == "ceil":
            result = math.ceil(input_value)
        
        elif operation == "floor":
            result = math.floor(input_value)
        
        elif operation == "abs":
            result = abs(input_value)
        
        elif operation == "max":
            if operand is None:
                raise ValueError("operand is required for 'max' operation")
            result = max(input_value, operand)
        
        elif operation == "min":
            if operand is None:
                raise ValueError("operand is required for 'min' operation")
            result = min(input_value, operand)
        
        elif operation == "sum":
            # Si input_value es una lista, sumar todos los elementos
            if isinstance(input_value, list):
                numbers = [float(x) for x in input_value if isinstance(x, (int, float, str))]
                result = sum(numbers)
            else:
                result = input_value
        
        elif operation == "average":
            # Si input_value es una lista, calcular promedio
            if isinstance(input_value, list):
                numbers = [float(x) for x in input_value if isinstance(x, (int, float, str))]
                result = sum(numbers) / len(numbers) if numbers else 0
            else:
                result = input_value
        
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        # Guardar en data model
        self._set_data(output_path, result)
        
        return result
    
    def _execute_encode_decode(self, config: Dict[str, Any]) -> str:
        """
        Codifica o decodifica datos
        """
        import base64
        from urllib.parse import quote, unquote, quote_plus, unquote_plus
        import html
        
        input_path = config["inputPath"]
        operation = config["operation"]
        encoding = config["encoding"]
        output_path = config["outputPath"]
        
        # Obtener datos
        input_value = self._get_data(input_path)
        
        if input_value is None:
            raise ValueError(f"No data found at path: {input_path}")
        
        # Convertir a bytes si es necesario
        if isinstance(input_value, str):
            input_bytes = input_value.encode('utf-8')
        elif isinstance(input_value, bytes):
            input_bytes = input_value
        else:
            input_bytes = str(input_value).encode('utf-8')
        
        # Realizar codificación/decodificación
        if encoding == "base64":
            if operation == "encode":
                result = base64.b64encode(input_bytes).decode('utf-8')
            else:  # decode
                try:
                    result = base64.b64decode(input_bytes).decode('utf-8')
                except Exception as e:
                    raise ValueError(f"Invalid base64 data: {e}")
        
        elif encoding == "url":
            if isinstance(input_value, str):
                input_str = input_value
            else:
                input_str = input_bytes.decode('utf-8')
            
            if operation == "encode":
                result = quote(input_str)
            else:  # decode
                result = unquote(input_str)
        
        elif encoding == "html":
            if isinstance(input_value, str):
                input_str = input_value
            else:
                input_str = input_bytes.decode('utf-8')
            
            if operation == "encode":
                result = html.escape(input_str)
            else:  # decode
                result = html.unescape(input_str)
        
        else:
            raise ValueError(f"Unknown encoding: {encoding}")
        
        # Guardar en data model
        self._set_data(output_path, result)
        
        return result


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

