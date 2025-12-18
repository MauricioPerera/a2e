# Vault de Credenciales Seguro

## Concepto

El agente necesita usar credenciales (tokens, API keys, passwords) pero **NUNCA debe ver los valores reales**.

## Modelo de Seguridad

```
┌─────────────────────────────────────────────────┐
│           CLIENTE                               │
│                                                 │
│  1. Almacena credenciales encriptadas           │
│  2. Anuncia IDs disponibles (sin valores)        │
│  3. Inyecta credenciales al ejecutar            │
└─────────────────────────────────────────────────┘
                    ↓
          [availableCredentials]
                    ↓
┌─────────────────────────────────────────────────┐
│           AGENTE                                │
│                                                 │
│  1. Ve IDs de credenciales disponibles          │
│  2. Referencia por ID en workflow                │
│  3. NUNCA ve valores reales                     │
└─────────────────────────────────────────────────┘
```

## Flujo de Uso

### 1. Cliente Almacena Credencial

```python
vault = CredentialsVault()
vault.store_credential(
    credential_id="api-token",
    credential_type="bearer-token",
    value="secret-token-12345",  # Se encripta
    metadata={"api": "user-api"}
)
```

### 2. Cliente Anuncia al Agente (Solo Metadatos)

```json
{
  "availableCredentials": [
    {
      "id": "api-token",
      "type": "bearer-token",
      "metadata": {"api": "user-api"},
      "usage": "Use in Authorization header: {'credentialRef': {'id': 'api-token'}}"
    }
  ]
}
```

**Nota**: El agente NO ve el valor `"secret-token-12345"`, solo el ID.

### 3. Agente Genera Workflow con Referencia

```jsonl
{"operationUpdate": {"operations": [
  {"id": "fetch", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "headers": {
        "Authorization": {
          "credentialRef": {"id": "api-token"}
        }
      }
    }
  }}
]}}
```

El agente solo referencia `{"credentialRef": {"id": "api-token"}}`, nunca el valor real.

### 4. Cliente Inyecta Credencial Real

```python
injector = CredentialInjector(vault)
config = injector.inject_into_operation(operation_config, "ApiCall")

# Resultado:
# {
#   "headers": {
#     "Authorization": "Bearer secret-token-12345"
#   }
# }
```

El cliente reemplaza la referencia con el valor real (desencriptado) antes de ejecutar.

## Seguridad

### Encriptación

```python
# Credenciales se almacenan encriptadas
encrypted_value = cipher.encrypt(value.encode())
# Se guarda: base64(encrypted_value)
```

### Separación de Responsabilidades

- **Cliente**: Almacena, encripta, desencripta, inyecta
- **Agente**: Solo referencia por ID, nunca ve valores

### Validación

```python
# El cliente valida que la credencial existe antes de inyectar
if credential_id not in vault.credentials:
    raise SecurityError("Credential not found")
```

## Tipos de Credenciales Soportadas

1. **bearer-token**: Para APIs con autenticación Bearer
   - Se inyecta como: `"Bearer {token}"`

2. **api-key**: Para APIs con API keys
   - Se inyecta como: `"{key}"`

3. **password**: Para contraseñas
   - Se inyecta como valor directo

4. **username**: Para usernames (usar con password)
   - Se inyecta como valor directo

## Ejemplo Completo

### Setup del Cliente

```python
# 1. Crear vault
vault = CredentialsVault(vault_path="credentials.vault.json")

# 2. Almacenar credenciales
vault.store_credential(
    credential_id="user-api-token",
    credential_type="bearer-token",
    value=os.getenv("USER_API_TOKEN"),
    metadata={"api": "user-api"}
)

# 3. Anunciar al agente
announcer = CredentialCapabilitiesAnnouncer(vault)
capabilities = announcer.build_capabilities_message()
# Enviar al agente en metadata
```

### Agente Genera Workflow

```jsonl
{"operationUpdate": {"operations": [
  {"id": "api-call", "operation": {
    "ApiCall": {
      "method": "GET",
      "url": "https://api.example.com/users",
      "headers": {
        "Authorization": {
          "credentialRef": {"id": "user-api-token"}
        }
      },
      "outputPath": "/workflow/users"
    }
  }}
]}}
```

### Cliente Ejecuta

```python
executor = SecureWorkflowExecutor(vault)
executor.load_workflow(workflow_jsonl)
results = await executor.execute()

# Durante ejecución:
# 1. Cliente ve: {"credentialRef": {"id": "user-api-token"}}
# 2. Cliente resuelve: "Bearer secret-token-12345"
# 3. Cliente ejecuta: GET con Authorization header
# 4. Agente nunca vio el token real
```

## Ventajas

1. **Seguridad**: Credenciales nunca salen del cliente
2. **Flexibilidad**: Agente puede referenciar sin conocer valores
3. **Auditoría**: Todas las referencias son rastreables
4. **Rotación**: Cliente puede rotar credenciales sin afectar workflows

## Consideraciones

### Almacenamiento

- **Encriptación**: Todas las credenciales encriptadas
- **Persistencia**: Opcional (memoria o archivo encriptado)
- **Master Key**: Debe venir de variable de entorno o sistema de secretos

### Rotación de Credenciales

```python
# Rotar credencial sin afectar workflows
vault.store_credential(
    credential_id="api-token",  # Mismo ID
    credential_type="bearer-token",
    value="new-token-67890"  # Nuevo valor
)
# Workflows existentes siguen funcionando (usan mismo ID)
```

### Validación

- Cliente valida que credencial existe antes de inyectar
- Cliente valida tipo de credencial para formateo correcto
- Cliente puede tener whitelist de credenciales por operación

