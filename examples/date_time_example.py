"""
Ejemplo de uso de operaciones de fecha y hora en A2E
"""

import asyncio
import json
from workflow_executor import WorkflowExecutor


async def example1_get_current_datetime():
    """Ejemplo 1: Obtener fecha y hora actual"""
    print("=" * 60)
    print("Ejemplo 1: Obtener Fecha y Hora Actual")
    print("=" * 60)
    
    workflow_jsonl = """{"operationUpdate": {"workflowId": "datetime-example", "operations": [
  {"id": "get-now", "operation": {
    "GetCurrentDateTime": {
      "timezone": "UTC",
      "format": "iso8601",
      "outputPath": "/workflow/current_time"
    }
  }},
  {"id": "get-now-madrid", "operation": {
    "GetCurrentDateTime": {
      "timezone": "Europe/Madrid",
      "format": "iso8601",
      "outputPath": "/workflow/current_time_madrid"
    }
  }},
  {"id": "get-now-timestamp", "operation": {
    "GetCurrentDateTime": {
      "format": "timestamp",
      "outputPath": "/workflow/current_timestamp"
    }
  }},
  {"id": "get-now-custom", "operation": {
    "GetCurrentDateTime": {
      "format": "custom",
      "formatString": "%Y-%m-%d %H:%M:%S",
      "outputPath": "/workflow/current_time_formatted"
    }
  }}
]}}
{"beginExecution": {"workflowId": "datetime-example", "root": "get-now"}}"""
    
    executor = WorkflowExecutor()
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("\nResultados:")
    print(f"  Hora UTC: {executor._get_data('/workflow/current_time')}")
    print(f"  Hora Madrid: {executor._get_data('/workflow/current_time_madrid')}")
    print(f"  Timestamp: {executor._get_data('/workflow/current_timestamp')}")
    print(f"  Formato personalizado: {executor._get_data('/workflow/current_time_formatted')}")


async def example2_convert_timezone():
    """Ejemplo 2: Convertir zona horaria"""
    print("\n" + "=" * 60)
    print("Ejemplo 2: Convertir Zona Horaria")
    print("=" * 60)
    
    workflow_jsonl = """{"operationUpdate": {"workflowId": "timezone-example", "operations": [
  {"id": "get-utc", "operation": {
    "GetCurrentDateTime": {
      "timezone": "UTC",
      "format": "iso8601",
      "outputPath": "/workflow/utc_time"
    }
  }},
  {"id": "convert-to-ny", "operation": {
    "ConvertTimezone": {
      "inputPath": "/workflow/utc_time",
      "fromTimezone": "UTC",
      "toTimezone": "America/New_York",
      "format": "iso8601",
      "outputPath": "/workflow/ny_time"
    }
  }},
  {"id": "convert-to-tokyo", "operation": {
    "ConvertTimezone": {
      "inputPath": "/workflow/utc_time",
      "toTimezone": "Asia/Tokyo",
      "format": "iso8601",
      "outputPath": "/workflow/tokyo_time"
    }
  }},
  {"id": "convert-custom-format", "operation": {
    "ConvertTimezone": {
      "inputPath": "/workflow/utc_time",
      "toTimezone": "Europe/Madrid",
      "format": "custom",
      "formatString": "%Y-%m-%d %H:%M:%S %Z",
      "outputPath": "/workflow/madrid_time_formatted"
    }
  }}
]}}
{"beginExecution": {"workflowId": "timezone-example", "root": "get-utc"}}"""
    
    executor = WorkflowExecutor()
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("\nResultados:")
    print(f"  UTC: {executor._get_data('/workflow/utc_time')}")
    print(f"  New York: {executor._get_data('/workflow/ny_time')}")
    print(f"  Tokyo: {executor._get_data('/workflow/tokyo_time')}")
    print(f"  Madrid (formato personalizado): {executor._get_data('/workflow/madrid_time_formatted')}")


async def example3_date_calculation():
    """Ejemplo 3: Cálculos con fechas"""
    print("\n" + "=" * 60)
    print("Ejemplo 3: Cálculos con Fechas")
    print("=" * 60)
    
    workflow_jsonl = """{"operationUpdate": {"workflowId": "datecalc-example", "operations": [
  {"id": "get-now", "operation": {
    "GetCurrentDateTime": {
      "timezone": "UTC",
      "format": "iso8601",
      "outputPath": "/workflow/now"
    }
  }},
  {"id": "add-7-days", "operation": {
    "DateCalculation": {
      "inputPath": "/workflow/now",
      "operation": "add",
      "days": 7,
      "format": "iso8601",
      "outputPath": "/workflow/next_week"
    }
  }},
  {"id": "subtract-1-month", "operation": {
    "DateCalculation": {
      "inputPath": "/workflow/now",
      "operation": "subtract",
      "months": 1,
      "format": "iso8601",
      "outputPath": "/workflow/last_month"
    }
  }},
  {"id": "add-complex", "operation": {
    "DateCalculation": {
      "inputPath": "/workflow/now",
      "operation": "add",
      "days": 30,
      "hours": 12,
      "minutes": 30,
      "format": "iso8601",
      "outputPath": "/workflow/future_datetime"
    }
  }},
  {"id": "subtract-hours", "operation": {
    "DateCalculation": {
      "inputPath": "/workflow/now",
      "operation": "subtract",
      "hours": 24,
      "format": "custom",
      "formatString": "%Y-%m-%d %H:%M:%S",
      "outputPath": "/workflow/yesterday"
    }
  }}
]}}
{"beginExecution": {"workflowId": "datecalc-example", "root": "get-now"}}"""
    
    executor = WorkflowExecutor()
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("\nResultados:")
    print(f"  Ahora: {executor._get_data('/workflow/now')}")
    print(f"  +7 días: {executor._get_data('/workflow/next_week')}")
    print(f"  -1 mes: {executor._get_data('/workflow/last_month')}")
    print(f"  +30 días, 12 horas, 30 minutos: {executor._get_data('/workflow/future_datetime')}")
    print(f"  -24 horas (ayer): {executor._get_data('/workflow/yesterday')}")


async def example4_combined_workflow():
    """Ejemplo 4: Workflow combinado"""
    print("\n" + "=" * 60)
    print("Ejemplo 4: Workflow Combinado")
    print("=" * 60)
    
    # Workflow que obtiene la hora actual en UTC, la convierte a Madrid,
    # calcula la fecha de hace 7 días, y la convierte también a Madrid
    workflow_jsonl = """{"operationUpdate": {"workflowId": "combined-example", "operations": [
  {"id": "get-utc", "operation": {
    "GetCurrentDateTime": {
      "timezone": "UTC",
      "format": "iso8601",
      "outputPath": "/workflow/utc_now"
    }
  }},
  {"id": "to-madrid", "operation": {
    "ConvertTimezone": {
      "inputPath": "/workflow/utc_now",
      "toTimezone": "Europe/Madrid",
      "format": "iso8601",
      "outputPath": "/workflow/madrid_now"
    }
  }},
  {"id": "calc-7-days-ago", "operation": {
    "DateCalculation": {
      "inputPath": "/workflow/utc_now",
      "operation": "subtract",
      "days": 7,
      "format": "iso8601",
      "outputPath": "/workflow/utc_7_days_ago"
    }
  }},
  {"id": "convert-7-days-ago", "operation": {
    "ConvertTimezone": {
      "inputPath": "/workflow/utc_7_days_ago",
      "toTimezone": "Europe/Madrid",
      "format": "custom",
      "formatString": "%Y-%m-%d %H:%M:%S",
      "outputPath": "/workflow/madrid_7_days_ago"
    }
  }}
]}}
{"beginExecution": {"workflowId": "combined-example", "root": "get-utc"}}"""
    
    executor = WorkflowExecutor()
    executor.load_workflow(workflow_jsonl)
    results = await executor.execute()
    
    print("\nResultados:")
    print(f"  UTC ahora: {executor._get_data('/workflow/utc_now')}")
    print(f"  Madrid ahora: {executor._get_data('/workflow/madrid_now')}")
    print(f"  UTC hace 7 días: {executor._get_data('/workflow/utc_7_days_ago')}")
    print(f"  Madrid hace 7 días: {executor._get_data('/workflow/madrid_7_days_ago')}")


async def main():
    """Ejecuta todos los ejemplos"""
    print("\n" + "=" * 60)
    print("Ejemplos de Operaciones de Fecha y Hora en A2E")
    print("=" * 60)
    
    try:
        await example1_get_current_datetime()
        await example2_convert_timezone()
        await example3_date_calculation()
        await example4_combined_workflow()
        
        print("\n" + "=" * 60)
        print("Todos los ejemplos completados")
        print("=" * 60)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

