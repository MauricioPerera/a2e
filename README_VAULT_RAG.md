# Vault de Credenciales con RAG

## Estado: ✅ COMPLETAMENTE INTEGRADO

El vault de credenciales ahora incluye **soporte opcional para RAG con LokiJS y embeddings locales** para búsqueda semántica.

## Características

### Seguridad (Sin Cambios)

- ✅ **Encriptación**: Todas las credenciales encriptadas con Fernet
- ✅ **Separación**: Agente nunca ve valores, solo IDs
- ✅ **Inyección**: Cliente inyecta valores reales al ejecutar

### Nuevas Características con RAG

- ✅ **Búsqueda Semántica**: Busca credenciales por descripción y metadatos
- ✅ **LokiJS Storage**: Almacenamiento eficiente de metadatos
- ✅ **Embeddings Locales**: Búsqueda semántica sin servicios externos
- ✅ **Fallback**: Funciona con o sin RAG (búsqueda por keywords)

## Uso

### Básico (Sin RAG)

```python
from credentials_vault import CredentialsVault

# Crear vault (sin RAG)
vault = CredentialsVault(
    vault_path="credentials.vault.json",
    use_rag=False  # Búsqueda por keywords
)

# Almacenar credencial
vault.store_credential(
    credential_id="api-token",
    credential_type="bearer-token",
    value="secret-token-12345",
    metadata={"api": "user-api"}
)
```

### Con RAG (Búsqueda Semántica)

```python
from credentials_vault import CredentialsVault

# Crear vault con RAG (automático si está disponible)
vault = CredentialsVault(
    vault_path="credentials.vault.json",
    use_rag=True  # Por defecto True
)

# Almacenar credencial con descripción
vault.store_credential(
    credential_id="user-api-token",
    credential_type="bearer-token",
    value="secret-token-12345",
    metadata={"api": "user-api", "environment": "production"},
    description="Token para API de usuarios en producción"
)

# Buscar credenciales semánticamente
results = vault.search_credentials(
    query="token para API de usuarios",
    top_k=3
)

# Resultados (solo metadatos, nunca valores):
# [
#   {
#     "id": "user-api-token",
#     "type": "bearer-token",
#     "metadata": {"api": "user-api", "environment": "production"},
#     "description": "Token para API de usuarios en producción",
#     "score": 0.85
#   }
# ]
```

## Búsqueda Semántica

### Con RAG

```python
# Buscar por descripción semántica
results = vault.search_credentials(
    query="credencial para autenticación de usuarios",
    top_k=5
)

# Encuentra credenciales relevantes aunque no coincidan exactamente las palabras
```

### Sin RAG (Fallback)

```python
# Búsqueda por keywords
results = vault.search_credentials(
    query="user api token",
    top_k=5
)

# Busca coincidencias exactas en descripción, metadatos e ID
```

## Integración con RAG

El vault usa el mismo sistema RAG que:
- Operaciones
- APIs y endpoints
- Knowledge bases

**Importante**: El vault **NUNCA** indexa valores encriptados en RAG. Solo indexa:
- ID de credencial
- Tipo
- Metadatos
- Descripción

Los valores encriptados permanecen seguros y nunca se exponen.

## Ejemplo Completo

```python
from credentials_vault import CredentialsVault, CredentialCapabilitiesAnnouncer

# Crear vault con RAG
vault = CredentialsVault(
    vault_path="credentials.vault.json",
    use_rag=True
)

# Almacenar múltiples credenciales
vault.store_credential(
    credential_id="user-api-token",
    credential_type="bearer-token",
    value=os.getenv("USER_API_TOKEN"),
    metadata={"api": "user-api", "environment": "production"},
    description="Token de autenticación para API de usuarios en producción"
)

vault.store_credential(
    credential_id="data-api-key",
    credential_type="api-key",
    value=os.getenv("DATA_API_KEY"),
    metadata={"api": "data-api", "environment": "production"},
    description="API key para acceso a datos en producción"
)

# Buscar credenciales relevantes
results = vault.search_credentials(
    query="credencial para API de usuarios",
    top_k=3
)

# Anunciar al agente (solo metadatos)
announcer = CredentialCapabilitiesAnnouncer(vault)
capabilities = announcer.build_capabilities_message()
# Enviar al agente
```

## Ventajas

1. **Búsqueda Inteligente**: Encuentra credenciales por significado, no solo palabras exactas
2. **Seguridad**: Valores nunca se indexan en RAG
3. **Flexibilidad**: Funciona con o sin RAG
4. **Eficiencia**: LokiJS es rápido y ligero
5. **Sin Servicios Externos**: Embeddings locales

## Compatibilidad

El vault es **completamente compatible** con código existente:
- ✅ Sin cambios en la API básica
- ✅ RAG es opcional (por defecto True si está disponible)
- ✅ Fallback automático a keywords si RAG no está disponible
- ✅ Misma seguridad y encriptación

## Conclusión

✅ **El vault de credenciales ahora incluye RAG opcional para búsqueda semántica.**

Mantiene toda la seguridad original mientras agrega capacidades de búsqueda inteligente cuando RAG está disponible.

