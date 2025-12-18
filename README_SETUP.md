# A2E Setup Guide

## Configuración Humana Requerida

A diferencia de A2UI que principalmente requiere componentes UI pre-definidos, **A2E requiere configuración humana activa** para:

1. **Credenciales**: Configurar tokens, API keys, passwords
2. **Base de Conocimiento de APIs**: Definir qué APIs están disponibles
3. **Seguridad**: Configurar whitelists, rate limits, etc.
4. **Catálogo de Operaciones**: Definir qué operaciones están permitidas

## Herramientas de Configuración

### 1. Configuration Wizard (Recomendado para Inicio)

Wizard interactivo que guía a través de toda la configuración:

```bash
python cli/config_wizard.py
```

El wizard:
- Crea el vault de credenciales
- Configura APIs disponibles
- Genera archivo de configuración
- Guía paso a paso

### 2. Vault CLI

Gestión del vault de credenciales:

```bash
# Crear vault
python cli/vault_cli.py create --vault-path my-vault.json

# Agregar credencial
python cli/vault_cli.py add \
  --id api-token \
  --type bearer-token \
  --api user-api \
  --description "Token for user API"

# Listar credenciales (solo metadatos)
python cli/vault_cli.py list

# Exportar metadatos para agente
python cli/vault_cli.py export-metadata --output capabilities.json
```

### 3. API Knowledge Base CLI

Gestión de la base de conocimiento de APIs:

```bash
# Crear API
python cli/api_cli.py create \
  --id user-api \
  --base-url https://api.example.com \
  --auth-type bearer \
  --output apis.json

# Agregar endpoint
python cli/api_cli.py add-endpoint \
  --api-file apis.json \
  --api-id user-api \
  --path /users \
  --method GET \
  --description "Get list of users"

# Listar APIs
python cli/api_cli.py list --api-file apis.json

# Exportar capacidades para agente
python cli/api_cli.py export-capabilities \
  --api-file apis.json \
  --output capabilities.json
```

## Flujo de Configuración Típico

### Paso 1: Configuración Inicial

```bash
# Ejecutar wizard
python cli/config_wizard.py
```

Esto crea:
- `credentials.vault.json` - Vault de credenciales
- `api_definitions.json` - Definiciones de APIs
- `a2e_config.json` - Configuración principal

### Paso 2: Agregar Credenciales

```bash
# Agregar token de API
python cli/vault_cli.py add \
  --id user-api-token \
  --type bearer-token \
  --api user-api
# (solicitará el valor de forma segura)
```

### Paso 3: Definir APIs

```bash
# Crear API
python cli/api_cli.py create \
  --id user-api \
  --base-url https://api.example.com \
  --auth-type bearer \
  --token-path /config/user-api-token

# Agregar endpoints
python cli/api_cli.py add-endpoint \
  --api-file api_definitions.json \
  --api-id user-api \
  --path /users \
  --method GET \
  --description "Get users with optional filters"
```

### Paso 4: Exportar Capacidades

```bash
# Exportar todo para el agente
python cli/vault_cli.py export-metadata --output creds.json
python cli/api_cli.py export-capabilities --api-file api_definitions.json --output apis.json

# Combinar en un solo archivo de capacidades
# (el agente leerá este archivo)
```

## Archivos de Configuración

### credentials.vault.json
Vault encriptado con credenciales. **NUNCA** compartir este archivo.

```json
{
  "credentials": {
    "api-token": {
      "id": "api-token",
      "type": "bearer-token",
      "encryptedValue": "...",
      "metadata": {"api": "user-api"}
    }
  }
}
```

### api_definitions.json
Definiciones de APIs disponibles (sin credenciales).

```json
{
  "apis": {
    "user-api": {
      "id": "user-api",
      "baseUrl": "https://api.example.com",
      "authentication": {
        "type": "bearer",
        "tokenPath": "/config/api-token"
      },
      "endpoints": [
        {
          "path": "/users",
          "method": "GET",
          "description": "Get users"
        }
      ]
    }
  }
}
```

### a2e_config.json
Configuración principal del sistema.

```json
{
  "vault": {
    "path": "credentials.vault.json"
  },
  "apiKnowledgeBase": {
    "path": "api_definitions.json"
  },
  "security": {
    "maxExecutionTime": 30000,
    "maxOperations": 20,
    "allowedDomains": ["api.example.com"]
  }
}
```

## Seguridad

### Credenciales

- ✅ **NUNCA** compartir `credentials.vault.json`
- ✅ Usar `vault_cli.py` para gestionar credenciales
- ✅ Rotar credenciales periódicamente
- ✅ Usar variables de entorno para master key en producción

### APIs

- ✅ Validar que solo APIs permitidas están en `api_definitions.json`
- ✅ Revisar endpoints antes de agregarlos
- ✅ Configurar whitelist de dominios en `a2e_config.json`

## Integración con Agente

Una vez configurado, el agente necesita:

1. **Capacidades de Credenciales**: Metadatos (sin valores)
2. **Capacidades de APIs**: Definiciones de APIs disponibles
3. **Configuración de Seguridad**: Restricciones y límites

El agente lee estos archivos al iniciar y los usa para generar workflows válidos.

## Mantenimiento

### Actualizar Credenciales

```bash
# Ver credenciales
python cli/vault_cli.py list

# Actualizar (eliminar y agregar nueva)
python cli/vault_cli.py delete --id old-token
python cli/vault_cli.py add --id new-token --type bearer-token
```

### Agregar Nueva API

```bash
python cli/api_cli.py create --id new-api --base-url https://new-api.com
python cli/api_cli.py add-endpoint --api-file api_definitions.json --api-id new-api --path /endpoint
```

### Exportar para Agente

Después de cambios, re-exportar capacidades:

```bash
python cli/vault_cli.py export-metadata --output creds.json
python cli/api_cli.py export-capabilities --api-file api_definitions.json --output apis.json
```

## Comparación con A2UI

| Aspecto | A2UI | A2E |
|---------|------|-----|
| **Configuración** | Componentes UI pre-definidos | Requiere configuración humana activa |
| **Credenciales** | No aplica | Vault de credenciales requerido |
| **APIs** | No aplica | Base de conocimiento de APIs requerida |
| **Seguridad** | Catálogo de componentes | Catálogo + APIs + Credenciales |

## Próximos Pasos

1. Ejecutar `config_wizard.py` para configuración inicial
2. Agregar credenciales necesarias
3. Definir APIs disponibles
4. Exportar capacidades para el agente
5. Iniciar el executor de A2E

