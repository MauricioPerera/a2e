# Operaciones de Utilidad en A2E

Este documento describe las operaciones de utilidad disponibles en el catálogo A2E para manipulación de texto, validación, cálculos matemáticos y codificación.

## Operaciones Disponibles

### 1. FormatText

Formatea texto usando plantillas o transformaciones.

**Propiedades:**
- `inputPath` (requerido): Ruta al texto o datos en el data model
- `format` (requerido): Tipo de formateo. Valores:
  - `"template"`: Usa una plantilla con variables
  - `"upper"`: Convierte a mayúsculas
  - `"lower"`: Convierte a minúsculas
  - `"title"`: Convierte a título (primera letra de cada palabra en mayúscula)
  - `"capitalize"`: Primera letra en mayúscula
  - `"trim"`: Elimina espacios al inicio y final
  - `"replace"`: Reemplaza texto
- `template` (opcional): Plantilla de formato (solo si `format="template"`). Usa `{field}` para variables
- `replacements` (opcional): Objeto con reemplazos (solo si `format="replace"`). Clave: texto a buscar, Valor: texto de reemplazo
- `outputPath` (requerido): Ruta donde guardar el texto formateado

**Ejemplo - Mayúsculas:**
```json
{
  "FormatText": {
    "inputPath": "/workflow/text",
    "format": "upper",
    "outputPath": "/workflow/formatted"
  }
}
```

**Ejemplo - Plantilla:**
```json
{
  "FormatText": {
    "inputPath": "/workflow/user",
    "format": "template",
    "template": "Hello {name}, you have {points} points",
    "outputPath": "/workflow/message"
  }
}
```

**Ejemplo - Reemplazar:**
```json
{
  "FormatText": {
    "inputPath": "/workflow/text",
    "format": "replace",
    "replacements": {
      "old": "new",
      "test": "example"
    },
    "outputPath": "/workflow/formatted"
  }
}
```

### 2. ExtractText

Extrae información de texto usando expresiones regulares.

**Propiedades:**
- `inputPath` (requerido): Ruta al texto en el data model
- `pattern` (requerido): Expresión regular para extraer
- `extractAll` (opcional): Si extraer todas las coincidencias (`true`) o solo la primera (`false`, default)
- `outputPath` (requerido): Ruta donde guardar los resultados extraídos

**Ejemplo - Extraer primera coincidencia:**
```json
{
  "ExtractText": {
    "inputPath": "/workflow/text",
    "pattern": "[0-9]+",
    "extractAll": false,
    "outputPath": "/workflow/number"
  }
}
```

**Ejemplo - Extraer todas las coincidencias:**
```json
{
  "ExtractText": {
    "inputPath": "/workflow/text",
    "pattern": "[0-9]+",
    "extractAll": true,
    "outputPath": "/workflow/numbers"
  }
}
```

### 3. ValidateData

Valida datos usando reglas predefinidas.

**Propiedades:**
- `inputPath` (requerido): Ruta a los datos a validar
- `validationType` (requerido): Tipo de validación. Valores:
  - `"email"`: Valida formato de email
  - `"url"`: Valida formato de URL
  - `"number"`: Valida que sea un número
  - `"integer"`: Valida que sea un entero
  - `"phone"`: Valida formato de teléfono
  - `"date"`: Valida formato de fecha
  - `"custom"`: Validación con expresión regular personalizada
- `pattern` (opcional): Expresión regular para validación custom (solo si `validationType="custom"`)
- `outputPath` (requerido): Ruta donde guardar el resultado de validación

**Ejemplo - Validar email:**
```json
{
  "ValidateData": {
    "inputPath": "/workflow/email",
    "validationType": "email",
    "outputPath": "/workflow/validation_result"
  }
}
```

**Ejemplo - Validación custom:**
```json
{
  "ValidateData": {
    "inputPath": "/workflow/code",
    "validationType": "custom",
    "pattern": "^[A-Z]{2}[0-9]{4}$",
    "outputPath": "/workflow/validation_result"
  }
}
```

**Resultado de validación:**
```json
{
  "valid": true,
  "value": "user@example.com"
}
```

O si es inválido:
```json
{
  "valid": false,
  "value": "invalid-email",
  "error": "Invalid email format"
}
```

### 4. Calculate

Realiza cálculos matemáticos.

**Propiedades:**
- `inputPath` (requerido): Ruta a los números o expresión en el data model
- `operation` (requerido): Operación matemática. Valores:
  - `"add"`: Sumar
  - `"subtract"`: Restar
  - `"multiply"`: Multiplicar
  - `"divide"`: Dividir
  - `"power"`: Potencia
  - `"modulo"`: Módulo
  - `"round"`: Redondear
  - `"ceil"`: Redondear hacia arriba
  - `"floor"`: Redondear hacia abajo
  - `"abs"`: Valor absoluto
  - `"max"`: Máximo entre dos números
  - `"min"`: Mínimo entre dos números
  - `"sum"`: Sumar lista de números
  - `"average"`: Promedio de lista de números
- `operand` (opcional): Segundo operando (para operaciones binarias) o path al segundo operando
- `precision` (opcional): Precisión decimal para redondeo (solo si `operation="round"`, default: 2)
- `outputPath` (requerido): Ruta donde guardar el resultado

**Ejemplo - Sumar:**
```json
{
  "Calculate": {
    "inputPath": "/workflow/number",
    "operation": "add",
    "operand": 10,
    "outputPath": "/workflow/result"
  }
}
```

**Ejemplo - Redondear:**
```json
{
  "Calculate": {
    "inputPath": "/workflow/number",
    "operation": "round",
    "precision": 2,
    "outputPath": "/workflow/rounded"
  }
}
```

**Ejemplo - Sumar lista:**
```json
{
  "Calculate": {
    "inputPath": "/workflow/numbers",
    "operation": "sum",
    "outputPath": "/workflow/total"
  }
}
```

**Ejemplo - Promedio:**
```json
{
  "Calculate": {
    "inputPath": "/workflow/scores",
    "operation": "average",
    "outputPath": "/workflow/average_score"
  }
}
```

### 5. EncodeDecode

Codifica o decodifica datos.

**Propiedades:**
- `inputPath` (requerido): Ruta a los datos en el data model
- `operation` (requerido): `"encode"` o `"decode"`
- `encoding` (requerido): Tipo de codificación. Valores:
  - `"base64"`: Codificación Base64
  - `"url"`: URL encoding
  - `"html"`: HTML entity encoding
- `outputPath` (requerido): Ruta donde guardar el resultado

**Ejemplo - Codificar Base64:**
```json
{
  "EncodeDecode": {
    "inputPath": "/workflow/text",
    "operation": "encode",
    "encoding": "base64",
    "outputPath": "/workflow/encoded"
  }
}
```

**Ejemplo - Decodificar Base64:**
```json
{
  "EncodeDecode": {
    "inputPath": "/workflow/encoded",
    "operation": "decode",
    "encoding": "base64",
    "outputPath": "/workflow/decoded"
  }
}
```

**Ejemplo - Codificar URL:**
```json
{
  "EncodeDecode": {
    "inputPath": "/workflow/text",
    "operation": "encode",
    "encoding": "url",
    "outputPath": "/workflow/url_encoded"
  }
}
```

## Ejemplos de Workflows Completos

### Ejemplo 1: Validar y Formatear Email

```jsonl
{"operationUpdate": {"workflowId": "email-example", "operations": [
  {"id": "validate", "operation": {
    "ValidateData": {
      "inputPath": "/workflow/email",
      "validationType": "email",
      "outputPath": "/workflow/validated"
    }
  }},
  {"id": "format", "operation": {
    "FormatText": {
      "inputPath": "/workflow/email",
      "format": "lower",
      "outputPath": "/workflow/email_lowercase"
    }
  }},
  {"id": "extract-domain", "operation": {
    "ExtractText": {
      "inputPath": "/workflow/email",
      "pattern": "@([a-zA-Z0-9.]+)",
      "extractAll": false,
      "outputPath": "/workflow/domain"
    }
  }}
]}}
{"beginExecution": {"workflowId": "email-example", "root": "validate"}}
```

### Ejemplo 2: Procesar y Calcular Datos

```jsonl
{"operationUpdate": {"workflowId": "calc-example", "operations": [
  {"id": "extract-numbers", "operation": {
    "ExtractText": {
      "inputPath": "/workflow/text",
      "pattern": "[0-9]+",
      "extractAll": true,
      "outputPath": "/workflow/numbers"
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
      "outputPath": "/workflow/average"
    }
  }}
]}}
{"beginExecution": {"workflowId": "calc-example", "root": "extract-numbers"}}
```

### Ejemplo 3: Codificar y Validar

```jsonl
{"operationUpdate": {"workflowId": "encode-example", "operations": [
  {"id": "encode", "operation": {
    "EncodeDecode": {
      "inputPath": "/workflow/data",
      "operation": "encode",
      "encoding": "base64",
      "outputPath": "/workflow/encoded"
    }
  }},
  {"id": "validate-url", "operation": {
    "ValidateData": {
      "inputPath": "/workflow/url",
      "validationType": "url",
      "outputPath": "/workflow/url_validated"
    }
  }}
]}}
{"beginExecution": {"workflowId": "encode-example", "root": "encode"}}
```

## Casos de Uso Comunes

### Validar Formulario

```jsonl
{"operationUpdate": {"workflowId": "form-validation", "operations": [
  {"id": "validate-email", "operation": {
    "ValidateData": {
      "inputPath": "/workflow/form/email",
      "validationType": "email",
      "outputPath": "/workflow/validation/email"
    }
  }},
  {"id": "validate-phone", "operation": {
    "ValidateData": {
      "inputPath": "/workflow/form/phone",
      "validationType": "phone",
      "outputPath": "/workflow/validation/phone"
    }
  }},
  {"id": "format-name", "operation": {
    "FormatText": {
      "inputPath": "/workflow/form/name",
      "format": "title",
      "outputPath": "/workflow/form/name_formatted"
    }
  }}
]}}
{"beginExecution": {"workflowId": "form-validation", "root": "validate-email"}}
```

### Procesar Texto de API

```jsonl
{"operationUpdate": {"workflowId": "text-processing", "operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/data",
      "outputPath": "/workflow/raw_data"
    }
  }},
  {"id": "extract-ids", "operation": {
    "ExtractText": {
      "inputPath": "/workflow/raw_data",
      "pattern": "ID: ([0-9]+)",
      "extractAll": true,
      "outputPath": "/workflow/ids"
    }
  }},
  {"id": "format-message", "operation": {
    "FormatText": {
      "inputPath": "/workflow/raw_data",
      "format": "template",
      "template": "Found {count} items",
      "outputPath": "/workflow/message"
    }
  }}
]}}
{"beginExecution": {"workflowId": "text-processing", "root": "fetch"}}
```

### Calcular Estadísticas

```jsonl
{"operationUpdate": {"workflowId": "stats", "operations": [
  {"id": "get-scores", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/scores",
      "outputPath": "/workflow/scores"
    }
  }},
  {"id": "sum", "operation": {
    "Calculate": {
      "inputPath": "/workflow/scores",
      "operation": "sum",
      "outputPath": "/workflow/total"
    }
  }},
  {"id": "average", "operation": {
    "Calculate": {
      "inputPath": "/workflow/scores",
      "operation": "average",
      "outputPath": "/workflow/average"
    }
  }},
  {"id": "round-avg", "operation": {
    "Calculate": {
      "inputPath": "/workflow/average",
      "operation": "round",
      "precision": 2,
      "outputPath": "/workflow/average_rounded"
    }
  }}
]}}
{"beginExecution": {"workflowId": "stats", "root": "get-scores"}}
```

## Notas de Implementación

- **FormatText**: Soporta objetos como entrada para plantillas con múltiples variables
- **ExtractText**: Usa expresiones regulares de Python (re module)
- **ValidateData**: Retorna objeto con `valid`, `value`, y opcionalmente `error`
- **Calculate**: Soporta listas para operaciones `sum` y `average`
- **EncodeDecode**: Codifica/decodifica strings y bytes

## Ver También

- [Ejemplos de uso](./examples/date_time_example.py)
- [Catálogo de operaciones](./workflow_catalog.json)
- [Documentación del protocolo A2E](./PROTOCOL_OVERVIEW.md)

