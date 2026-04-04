# A2E Protocol - JSON Schemas

This document provides complete JSON Schema definitions for all A2E protocol messages and operations.

## Core Message Schemas

### Operation Update

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "A2E Operation Update",
  "type": "object",
  "required": ["type", "operationId", "operation"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["operationUpdate"],
      "description": "Message type identifier"
    },
    "operationId": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9_-]+$",
      "minLength": 1,
      "maxLength": 100,
      "description": "Unique identifier for this operation"
    },
    "operation": {
      "type": "object",
      "minProperties": 1,
      "maxProperties": 1,
      "description": "Operation definition (must contain exactly one operation type)",
      "oneOf": [
        {"$ref": "#/definitions/ApiCall"},
        {"$ref": "#/definitions/FilterData"},
        {"$ref": "#/definitions/TransformData"},
        {"$ref": "#/definitions/Conditional"},
        {"$ref": "#/definitions/Loop"},
        {"$ref": "#/definitions/StoreData"},
        {"$ref": "#/definitions/Wait"},
        {"$ref": "#/definitions/MergeData"}
      ]
    }
  },
  "additionalProperties": false
}
```

### Begin Execution

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "A2E Begin Execution",
  "type": "object",
  "required": ["type", "executionId", "operationOrder"],
  "properties": {
    "type": {
      "type": "string",
      "enum": ["beginExecution"],
      "description": "Message type identifier"
    },
    "executionId": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9_-]+$",
      "minLength": 1,
      "maxLength": 100,
      "description": "Unique identifier for this execution"
    },
    "operationOrder": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^[a-zA-Z0-9_-]+$"
      },
      "minItems": 1,
      "maxItems": 100,
      "description": "Ordered list of operation IDs to execute"
    }
  },
  "additionalProperties": false
}
```

## Operation Schemas

### ApiCall

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "A2E ApiCall Operation",
  "type": "object",
  "required": ["method", "url", "outputPath"],
  "properties": {
    "method": {
      "type": "string",
      "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
      "description": "HTTP method"
    },
    "url": {
      "type": "string",
      "format": "uri",
      "description": "Endpoint URL. Supports path references: {/workflow/data}"
    },
    "headers": {
      "type": "object",
      "description": "HTTP headers. Values can be strings or credential references",
      "additionalProperties": {
        "oneOf": [
          {"type": "string"},
          {"$ref": "#/definitions/CredentialReference"}
        ]
      }
    },
    "body": {
      "type": ["object", "array", "string", "number", "boolean", "null"],
      "description": "Request body (for POST/PUT). Can reference data model paths"
    },
    "outputPath": {
      "type": "string",
      "pattern": "^/workflow/",
      "description": "Data model path to store response"
    },
    "timeout": {
      "type": "integer",
      "minimum": 1000,
      "maximum": 300000,
      "default": 30000,
      "description": "Timeout in milliseconds"
    }
  },
  "additionalProperties": false
}
```

### FilterData

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "A2E FilterData Operation",
  "type": "object",
  "required": ["inputPath", "conditions", "outputPath"],
  "properties": {
    "inputPath": {
      "type": "string",
      "pattern": "^/workflow/",
      "description": "Path to input array in data model"
    },
    "conditions": {
      "type": "array",
      "items": {"$ref": "#/definitions/FilterCondition"},
      "minItems": 1,
      "description": "Array of filter conditions (AND logic)"
    },
    "outputPath": {
      "type": "string",
      "pattern": "^/workflow/",
      "description": "Path to store filtered results"
    }
  },
  "additionalProperties": false
}
```

### TransformData

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "A2E TransformData Operation",
  "type": "object",
  "required": ["inputPath", "transform", "outputPath"],
  "properties": {
    "inputPath": {
      "type": "string",
      "pattern": "^/workflow/",
      "description": "Path to input data"
    },
    "transform": {
      "type": "string",
      "enum": ["map", "sort", "group", "aggregate", "select"],
      "description": "Transformation type"
    },
    "config": {
      "type": "object",
      "description": "Transformation-specific configuration"
    },
    "outputPath": {
      "type": "string",
      "pattern": "^/workflow/",
      "description": "Path to store transformed data"
    }
  },
  "additionalProperties": false
}
```

### Conditional

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "A2E Conditional Operation",
  "type": "object",
  "required": ["condition", "ifTrue"],
  "properties": {
    "condition": {"$ref": "#/definitions/Condition"},
    "ifTrue": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Operation IDs to execute if condition is true"
    },
    "ifFalse": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Operation IDs to execute if condition is false"
    }
  },
  "additionalProperties": false
}
```

### Loop

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "A2E Loop Operation",
  "type": "object",
  "required": ["inputPath", "operations"],
  "properties": {
    "inputPath": {
      "type": "string",
      "pattern": "^/workflow/",
      "description": "Path to array to iterate over"
    },
    "operations": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 1,
      "description": "Operation IDs to execute for each item"
    },
    "outputPath": {
      "type": "string",
      "pattern": "^/workflow/",
      "description": "Path to store loop results"
    }
  },
  "additionalProperties": false
}
```

### StoreData

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "A2E StoreData Operation",
  "type": "object",
  "required": ["inputPath", "storage", "key"],
  "properties": {
    "inputPath": {
      "type": "string",
      "pattern": "^/workflow/",
      "description": "Path to data to store"
    },
    "storage": {
      "type": "string",
      "enum": ["localStorage", "sessionStorage", "file"],
      "description": "Storage type"
    },
    "key": {
      "type": "string",
      "minLength": 1,
      "description": "Storage key/path"
    }
  },
  "additionalProperties": false
}
```

### Wait

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "A2E Wait Operation",
  "type": "object",
  "required": ["duration"],
  "properties": {
    "duration": {
      "type": "integer",
      "minimum": 0,
      "maximum": 600000,
      "description": "Duration in milliseconds"
    }
  },
  "additionalProperties": false
}
```

### MergeData

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "A2E MergeData Operation",
  "type": "object",
  "required": ["sources", "strategy", "outputPath"],
  "properties": {
    "sources": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^/workflow/"
      },
      "minItems": 2,
      "description": "Array of input paths to merge"
    },
    "strategy": {
      "type": "string",
      "enum": ["concat", "union", "intersect", "deepMerge"],
      "description": "Merge strategy"
    },
    "outputPath": {
      "type": "string",
      "pattern": "^/workflow/",
      "description": "Path to store merged data"
    }
  },
  "additionalProperties": false
}
```

## Common Definitions

### CredentialReference

```json
{
  "type": "object",
  "required": ["credentialRef"],
  "properties": {
    "credentialRef": {
      "type": "object",
      "required": ["id"],
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^[a-zA-Z0-9_-]+$",
          "description": "Credential ID from vault"
        }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

### FilterCondition

```json
{
  "type": "object",
  "required": ["field", "operator", "value"],
  "properties": {
    "field": {
      "type": "string",
      "description": "Field name to filter on"
    },
    "operator": {
      "type": "string",
      "enum": ["==", "!=", ">", "<", ">=", "<=", "in", "contains", "startsWith", "endsWith"],
      "description": "Comparison operator"
    },
    "value": {
      "description": "Value to compare against (any JSON type)"
    }
  },
  "additionalProperties": false
}
```

### Condition

```json
{
  "type": "object",
  "required": ["path", "operator", "value"],
  "properties": {
    "path": {
      "type": "string",
      "pattern": "^/workflow/",
      "description": "Data model path to evaluate"
    },
    "operator": {
      "type": "string",
      "enum": ["==", "!=", ">", "<", ">=", "<=", "exists", "empty"],
      "description": "Comparison operator"
    },
    "value": {
      "description": "Value to compare against (any JSON type, optional for 'exists' and 'empty')"
    }
  },
  "additionalProperties": false
}
```

## Complete Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "A2E Protocol Complete Schema",
  "type": "object",
  "definitions": {
    "ApiCall": { /* ... */ },
    "FilterData": { /* ... */ },
    "TransformData": { /* ... */ },
    "Conditional": { /* ... */ },
    "Loop": { /* ... */ },
    "StoreData": { /* ... */ },
    "Wait": { /* ... */ },
    "MergeData": { /* ... */ },
    "CredentialReference": { /* ... */ },
    "FilterCondition": { /* ... */ },
    "Condition": { /* ... */ }
  },
  "oneOf": [
    {"$ref": "#/definitions/OperationUpdate"},
    {"$ref": "#/definitions/BeginExecution"}
  ]
}
```

---

**Note**: These schemas can be used for validation in any JSON Schema validator.

