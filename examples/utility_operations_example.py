"""
Ejemplos de uso de operaciones de utilidad en A2E
"""

import asyncio
import json
from workflow_executor import WorkflowExecutor


async def example1_format_text():
    """Ejemplo 1: Formatear texto"""
    print("=" * 60)
    print("Ejemplo 1: Formatear Texto")
    print("=" * 60)
    
    workflow_jsonl = """{"operationUpdate": {"workflowId": "format-example", "operations": [
  {"id": "upper", "operation": {
    "FormatText": {
      "inputPath": "/workflow/text",
      "format": "upper",
      "outputPath": "/workflow/upper"
    }
  }},
  {"id": "lower", "operation": {
    "FormatText": {
      "inputPath": "/workflow/text",
      "format": "lower",
      "outputPath": "/workflow/lower"
    }
  }},
  {"id": "template", "operation": {
    "FormatText": {
      "inputPath": "/workflow/user",
      "format": "template",
      "template": "Hello {name}, you have {points} points",
      "outputPath": "/workflow/message"
    }
  }}
]}}
{"beginExecution": {"workflowId": "format-example", "root": "upper"}}"""
    
    executor = WorkflowExecutor()
    executor._set_data("/workflow/text", "Hello World")
    executor._set_data("/workflow/user", {"name": "Alice", "points": 100})
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("\nResultados:")
    print(f"  Upper: {executor._get_data('/workflow/upper')}")
    print(f"  Lower: {executor._get_data('/workflow/lower')}")
    print(f"  Message: {executor._get_data('/workflow/message')}")


async def example2_extract_text():
    """Ejemplo 2: Extraer información de texto"""
    print("\n" + "=" * 60)
    print("Ejemplo 2: Extraer Texto")
    print("=" * 60)
    
    workflow_jsonl = """{"operationUpdate": {"workflowId": "extract-example", "operations": [
  {"id": "extract-single", "operation": {
    "ExtractText": {
      "inputPath": "/workflow/text",
      "pattern": "[0-9]+",
      "extractAll": false,
      "outputPath": "/workflow/first_number"
    }
  }},
  {"id": "extract-all", "operation": {
    "ExtractText": {
      "inputPath": "/workflow/text",
      "pattern": "[0-9]+",
      "extractAll": true,
      "outputPath": "/workflow/all_numbers"
    }
  }},
  {"id": "extract-email", "operation": {
    "ExtractText": {
      "inputPath": "/workflow/text",
      "pattern": "[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}",
      "extractAll": true,
      "outputPath": "/workflow/emails"
    }
  }}
]}}
{"beginExecution": {"workflowId": "extract-example", "root": "extract-single"}}"""
    
    executor = WorkflowExecutor()
    executor._set_data("/workflow/text", "Contact us at user@example.com or admin@test.com. Prices: 100, 200, 300")
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("\nResultados:")
    print(f"  Primer número: {executor._get_data('/workflow/first_number')}")
    print(f"  Todos los números: {executor._get_data('/workflow/all_numbers')}")
    print(f"  Emails: {executor._get_data('/workflow/emails')}")


async def example3_validate_data():
    """Ejemplo 3: Validar datos"""
    print("\n" + "=" * 60)
    print("Ejemplo 3: Validar Datos")
    print("=" * 60)
    
    workflow_jsonl = """{"operationUpdate": {"workflowId": "validate-example", "operations": [
  {"id": "validate-email", "operation": {
    "ValidateData": {
      "inputPath": "/workflow/email",
      "validationType": "email",
      "outputPath": "/workflow/email_valid"
    }
  }},
  {"id": "validate-url", "operation": {
    "ValidateData": {
      "inputPath": "/workflow/url",
      "validationType": "url",
      "outputPath": "/workflow/url_valid"
    }
  }},
  {"id": "validate-number", "operation": {
    "ValidateData": {
      "inputPath": "/workflow/number",
      "validationType": "number",
      "outputPath": "/workflow/number_valid"
    }
  }}
]}}
{"beginExecution": {"workflowId": "validate-example", "root": "validate-email"}}"""
    
    executor = WorkflowExecutor()
    executor._set_data("/workflow/email", "user@example.com")
    executor._set_data("/workflow/url", "https://example.com")
    executor._set_data("/workflow/number", "123.45")
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("\nResultados:")
    print(f"  Email válido: {executor._get_data('/workflow/email_valid')['valid']}")
    print(f"  URL válida: {executor._get_data('/workflow/url_valid')['valid']}")
    print(f"  Número válido: {executor._get_data('/workflow/number_valid')['valid']}")


async def example4_calculate():
    """Ejemplo 4: Cálculos matemáticos"""
    print("\n" + "=" * 60)
    print("Ejemplo 4: Cálculos Matemáticos")
    print("=" * 60)
    
    workflow_jsonl = """{"operationUpdate": {"workflowId": "calc-example", "operations": [
  {"id": "add", "operation": {
    "Calculate": {
      "inputPath": "/workflow/number",
      "operation": "add",
      "operand": 10,
      "outputPath": "/workflow/added"
    }
  }},
  {"id": "multiply", "operation": {
    "Calculate": {
      "inputPath": "/workflow/number",
      "operation": "multiply",
      "operand": 3,
      "outputPath": "/workflow/multiplied"
    }
  }},
  {"id": "round", "operation": {
    "Calculate": {
      "inputPath": "/workflow/pi",
      "operation": "round",
      "precision": 2,
      "outputPath": "/workflow/rounded"
    }
  }},
  {"id": "sum", "operation": {
    "Calculate": {
      "inputPath": "/workflow/numbers",
      "operation": "sum",
      "outputPath": "/workflow/total"
    }
  }},
  {"id": "average", "operation": {
    "Calculate": {
      "inputPath": "/workflow/numbers",
      "operation": "average",
      "outputPath": "/workflow/avg"
    }
  }}
]}}
{"beginExecution": {"workflowId": "calc-example", "root": "add"}}"""
    
    executor = WorkflowExecutor()
    executor._set_data("/workflow/number", 5)
    executor._set_data("/workflow/pi", 3.14159)
    executor._set_data("/workflow/numbers", [10, 20, 30, 40, 50])
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("\nResultados:")
    print(f"  5 + 10 = {executor._get_data('/workflow/added')}")
    print(f"  5 * 3 = {executor._get_data('/workflow/multiplied')}")
    print(f"  π redondeado (2 decimales) = {executor._get_data('/workflow/rounded')}")
    print(f"  Suma de [10, 20, 30, 40, 50] = {executor._get_data('/workflow/total')}")
    print(f"  Promedio de [10, 20, 30, 40, 50] = {executor._get_data('/workflow/avg')}")


async def example5_encode_decode():
    """Ejemplo 5: Codificar y decodificar"""
    print("\n" + "=" * 60)
    print("Ejemplo 5: Codificar/Decodificar")
    print("=" * 60)
    
    workflow_jsonl = """{"operationUpdate": {"workflowId": "encode-example", "operations": [
  {"id": "encode-base64", "operation": {
    "EncodeDecode": {
      "inputPath": "/workflow/text",
      "operation": "encode",
      "encoding": "base64",
      "outputPath": "/workflow/encoded"
    }
  }},
  {"id": "decode-base64", "operation": {
    "EncodeDecode": {
      "inputPath": "/workflow/encoded",
      "operation": "decode",
      "encoding": "base64",
      "outputPath": "/workflow/decoded"
    }
  }},
  {"id": "encode-url", "operation": {
    "EncodeDecode": {
      "inputPath": "/workflow/text",
      "operation": "encode",
      "encoding": "url",
      "outputPath": "/workflow/url_encoded"
    }
  }},
  {"id": "encode-html", "operation": {
    "EncodeDecode": {
      "inputPath": "/workflow/html",
      "operation": "encode",
      "encoding": "html",
      "outputPath": "/workflow/html_encoded"
    }
  }}
]}}
{"beginExecution": {"workflowId": "encode-example", "root": "encode-base64"}}"""
    
    executor = WorkflowExecutor()
    executor._set_data("/workflow/text", "Hello World")
    executor._set_data("/workflow/html", "<script>alert('test')</script>")
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("\nResultados:")
    print(f"  Texto original: Hello World")
    print(f"  Base64 codificado: {executor._get_data('/workflow/encoded')}")
    print(f"  Base64 decodificado: {executor._get_data('/workflow/decoded')}")
    print(f"  URL codificado: {executor._get_data('/workflow/url_encoded')}")
    print(f"  HTML codificado: {executor._get_data('/workflow/html_encoded')}")


async def example6_combined_workflow():
    """Ejemplo 6: Workflow combinado"""
    print("\n" + "=" * 60)
    print("Ejemplo 6: Workflow Combinado")
    print("=" * 60)
    
    # Workflow que valida email, extrae dominio, formatea mensaje y calcula estadísticas
    workflow_jsonl = """{"operationUpdate": {"workflowId": "combined-example", "operations": [
  {"id": "validate-email", "operation": {
    "ValidateData": {
      "inputPath": "/workflow/email",
      "validationType": "email",
      "outputPath": "/workflow/email_valid"
    }
  }},
  {"id": "extract-domain", "operation": {
    "ExtractText": {
      "inputPath": "/workflow/email",
      "pattern": "@([a-zA-Z0-9.]+)",
      "extractAll": false,
      "outputPath": "/workflow/domain"
    }
  }},
  {"id": "format-email", "operation": {
    "FormatText": {
      "inputPath": "/workflow/email",
      "format": "lower",
      "outputPath": "/workflow/email_lower"
    }
  }},
  {"id": "format-message", "operation": {
    "FormatText": {
      "inputPath": "/workflow/data",
      "format": "template",
      "template": "Email {email} from {domain} is valid",
      "outputPath": "/workflow/message"
    }
  }},
  {"id": "calculate-stats", "operation": {
    "Calculate": {
      "inputPath": "/workflow/scores",
      "operation": "average",
      "outputPath": "/workflow/avg_score"
    }
  }}
]}}
{"beginExecution": {"workflowId": "combined-example", "root": "validate-email"}}"""
    
    executor = WorkflowExecutor()
    executor._set_data("/workflow/email", "User@Example.COM")
    executor._set_data("/workflow/data", {"email": "user@example.com", "domain": "example.com"})
    executor._set_data("/workflow/scores", [85, 90, 95, 88, 92])
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("\nResultados:")
    print(f"  Email válido: {executor._get_data('/workflow/email_valid')['valid']}")
    print(f"  Dominio extraído: {executor._get_data('/workflow/domain')}")
    print(f"  Email en minúsculas: {executor._get_data('/workflow/email_lower')}")
    print(f"  Mensaje: {executor._get_data('/workflow/message')}")
    print(f"  Promedio de scores: {executor._get_data('/workflow/avg_score')}")


async def main():
    """Ejecuta todos los ejemplos"""
    print("\n" + "=" * 60)
    print("Ejemplos de Operaciones de Utilidad en A2E")
    print("=" * 60)
    
    try:
        await example1_format_text()
        await example2_extract_text()
        await example3_validate_data()
        await example4_calculate()
        await example5_encode_decode()
        await example6_combined_workflow()
        
        print("\n" + "=" * 60)
        print("Todos los ejemplos completados")
        print("=" * 60)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

