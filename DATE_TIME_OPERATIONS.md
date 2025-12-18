# Operaciones de Fecha y Hora en A2E

Este documento describe las operaciones de fecha y hora disponibles en el catálogo A2E.

## Operaciones Disponibles

### 1. GetCurrentDateTime

Obtiene la fecha y hora actual en el formato especificado.

**Propiedades:**
- `timezone` (opcional): Zona horaria (ej: `"UTC"`, `"America/New_York"`, `"Europe/Madrid"`). Si no se especifica, usa la zona horaria del sistema.
- `format` (opcional): Formato de salida. Valores:
  - `"iso8601"` (default): Formato ISO 8601 (ej: `"2025-12-17T10:30:00+00:00"`)
  - `"timestamp"`: Unix timestamp en segundos (número)
  - `"custom"`: Usa `formatString` para formato personalizado
- `formatString` (opcional): Formato personalizado usando sintaxis strftime de Python (solo si `format="custom"`)
- `outputPath` (requerido): Ruta en el data model donde guardar la fecha/hora

**Ejemplo:**
```json
{
  "GetCurrentDateTime": {
    "timezone": "UTC",
    "format": "iso8601",
    "outputPath": "/workflow/current_time"
  }
}
```

**Ejemplo con formato personalizado:**
```json
{
  "GetCurrentDateTime": {
    "timezone": "Europe/Madrid",
    "format": "custom",
    "formatString": "%Y-%m-%d %H:%M:%S",
    "outputPath": "/workflow/current_time_formatted"
  }
}
```

### 2. ConvertTimezone

Convierte una fecha/hora de una zona horaria a otra.

**Propiedades:**
- `inputPath` (requerido): Ruta a la fecha/hora en el data model. Puede ser:
  - String ISO 8601 (ej: `"2025-12-17T10:30:00+00:00"`)
  - Unix timestamp (número)
  - Objeto con campos `year`, `month`, `day`, `hour`, `minute`, `second`
- `fromTimezone` (opcional): Zona horaria de origen. Si no se especifica, se intenta detectar o usar UTC.
- `toTimezone` (requerido): Zona horaria de destino (ej: `"Europe/Madrid"`, `"America/Los_Angeles"`)
- `format` (opcional): Formato de salida (igual que `GetCurrentDateTime`)
- `formatString` (opcional): Formato personalizado (solo si `format="custom"`)
- `outputPath` (requerido): Ruta donde guardar la fecha/hora convertida

**Ejemplo:**
```json
{
  "ConvertTimezone": {
    "inputPath": "/workflow/utc_time",
    "fromTimezone": "UTC",
    "toTimezone": "Europe/Madrid",
    "format": "iso8601",
    "outputPath": "/workflow/madrid_time"
  }
}
```

**Ejemplo con timestamp:**
```json
{
  "ConvertTimezone": {
    "inputPath": "/workflow/timestamp",
    "toTimezone": "America/New_York",
    "format": "iso8601",
    "outputPath": "/workflow/ny_time"
  }
}
```

### 3. DateCalculation

Realiza cálculos con fechas (sumar días, restar horas, etc.).

**Propiedades:**
- `inputPath` (requerido): Ruta a la fecha base en el data model (mismos formatos que `ConvertTimezone`)
- `operation` (requerido): Operación a realizar:
  - `"add"`: Sumar tiempo
  - `"subtract"`: Restar tiempo
- `years` (opcional): Años a sumar/restar
- `months` (opcional): Meses a sumar/restar (aproximadamente 30 días)
- `days` (opcional): Días a sumar/restar
- `hours` (opcional): Horas a sumar/restar
- `minutes` (opcional): Minutos a sumar/restar
- `seconds` (opcional): Segundos a sumar/restar
- `timezone` (opcional): Zona horaria para la fecha base si no está especificada
- `format` (opcional): Formato de salida (igual que `GetCurrentDateTime`)
- `formatString` (opcional): Formato personalizado (solo si `format="custom"`)
- `outputPath` (requerido): Ruta donde guardar el resultado

**Ejemplo - Sumar 7 días:**
```json
{
  "DateCalculation": {
    "inputPath": "/workflow/current_date",
    "operation": "add",
    "days": 7,
    "format": "iso8601",
    "outputPath": "/workflow/next_week"
  }
}
```

**Ejemplo - Restar 1 mes:**
```json
{
  "DateCalculation": {
    "inputPath": "/workflow/current_date",
    "operation": "subtract",
    "months": 1,
    "format": "iso8601",
    "outputPath": "/workflow/last_month"
  }
}
```

**Ejemplo - Cálculo complejo:**
```json
{
  "DateCalculation": {
    "inputPath": "/workflow/current_date",
    "operation": "add",
    "days": 30,
    "hours": 12,
    "minutes": 30,
    "format": "iso8601",
    "outputPath": "/workflow/future_datetime"
  }
}
```

## Zonas Horarias Soportadas

Las operaciones usan la biblioteca `pytz` que soporta todas las zonas horarias estándar IANA. Ejemplos:

- `"UTC"` - Tiempo Universal Coordinado
- `"America/New_York"` - Hora del Este (EE.UU.)
- `"America/Los_Angeles"` - Hora del Pacífico (EE.UU.)
- `"Europe/Madrid"` - Hora de Madrid
- `"Europe/London"` - Hora de Londres
- `"Asia/Tokyo"` - Hora de Tokio
- `"Australia/Sydney"` - Hora de Sídney

Para ver todas las zonas horarias disponibles, consulta: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

## Formatos de Fecha/Hora

### ISO 8601 (default)
Formato estándar internacional: `"2025-12-17T10:30:00+00:00"`

### Timestamp
Unix timestamp en segundos (número): `1734435000.0`

### Formato Personalizado
Usa la sintaxis de `strftime` de Python. Ejemplos:

- `"%Y-%m-%d"` → `"2025-12-17"`
- `"%Y-%m-%d %H:%M:%S"` → `"2025-12-17 10:30:00"`
- `"%d/%m/%Y"` → `"17/12/2025"`
- `"%A, %B %d, %Y"` → `"Wednesday, December 17, 2025"`

**Códigos de formato comunes:**
- `%Y` - Año con 4 dígitos
- `%m` - Mes (01-12)
- `%d` - Día (01-31)
- `%H` - Hora (00-23)
- `%M` - Minuto (00-59)
- `%S` - Segundo (00-59)
- `%A` - Nombre completo del día de la semana
- `%B` - Nombre completo del mes

## Ejemplos de Workflows Completos

### Ejemplo 1: Obtener hora actual en múltiples zonas

```jsonl
{"operationUpdate": {"workflowId": "multi-timezone", "operations": [
  {"id": "utc", "operation": {
    "GetCurrentDateTime": {
      "timezone": "UTC",
      "format": "iso8601",
      "outputPath": "/workflow/utc_time"
    }
  }},
  {"id": "madrid", "operation": {
    "GetCurrentDateTime": {
      "timezone": "Europe/Madrid",
      "format": "iso8601",
      "outputPath": "/workflow/madrid_time"
    }
  }},
  {"id": "ny", "operation": {
    "GetCurrentDateTime": {
      "timezone": "America/New_York",
      "format": "iso8601",
      "outputPath": "/workflow/ny_time"
    }
  }}
]}}
{"beginExecution": {"workflowId": "multi-timezone", "root": "utc"}}
```

### Ejemplo 2: Convertir y calcular

```jsonl
{"operationUpdate": {"workflowId": "convert-calc", "operations": [
  {"id": "get-now", "operation": {
    "GetCurrentDateTime": {
      "timezone": "UTC",
      "format": "iso8601",
      "outputPath": "/workflow/now"
    }
  }},
  {"id": "convert", "operation": {
    "ConvertTimezone": {
      "inputPath": "/workflow/now",
      "toTimezone": "Europe/Madrid",
      "format": "iso8601",
      "outputPath": "/workflow/madrid_now"
    }
  }},
  {"id": "add-week", "operation": {
    "DateCalculation": {
      "inputPath": "/workflow/madrid_now",
      "operation": "add",
      "days": 7,
      "format": "iso8601",
      "outputPath": "/workflow/next_week"
    }
  }}
]}}
{"beginExecution": {"workflowId": "convert-calc", "root": "get-now"}}
```

## Notas de Implementación

- Las operaciones usan la biblioteca `pytz` para manejo de zonas horarias
- Si `pytz` no está disponible, las operaciones de zona horaria estarán limitadas
- Los cálculos de meses son aproximados (30 días por mes)
- Los años se calculan como 365 días
- Las fechas sin timezone se asumen como UTC por defecto

## Ver También

- [Ejemplos de uso](./examples/date_time_example.py)
- [Catálogo de operaciones](./workflow_catalog.json)
- [Documentación del protocolo A2E](./PROTOCOL_OVERVIEW.md)

