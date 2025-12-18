"""
Tests para Credentials Vault
"""

import pytest
import tempfile
import os
from credentials_vault import CredentialsVault, CredentialInjector


@pytest.fixture
def vault():
    """Fixture para crear un vault limpio"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
        vault_path = f.name
    
    yield CredentialsVault(vault_path=vault_path)
    
    # Cleanup
    if os.path.exists(vault_path):
        os.unlink(vault_path)


def test_store_and_get_credential(vault):
    """Test almacenar y obtener credencial"""
    vault.store_credential(
        credential_id="test-token",
        credential_type="bearer-token",
        value="secret-token-123",
        metadata={"api": "test-api"}
    )
    
    value = vault.get_credential("test-token")
    assert value == "secret-token-123"


def test_credential_encryption(vault):
    """Test que las credenciales están encriptadas"""
    vault.store_credential(
        credential_id="test-token",
        credential_type="bearer-token",
        value="secret-token-123"
    )
    
    # El valor almacenado debe estar encriptado
    cred = vault.credentials["test-token"]
    assert "encryptedValue" in cred
    assert cred["encryptedValue"] != "secret-token-123"
    
    # Pero al obtenerlo, debe desencriptarse
    value = vault.get_credential("test-token")
    assert value == "secret-token-123"


def test_list_credentials(vault):
    """Test listar credenciales (solo metadatos)"""
    vault.store_credential("token1", "bearer-token", "value1")
    vault.store_credential("token2", "api-key", "value2")
    
    credentials = vault.list_credentials()
    assert len(credentials) == 2
    assert all("id" in cred for cred in credentials)
    assert all("type" in cred for cred in credentials)
    # Valores no deben estar en la lista
    assert all("encryptedValue" not in cred for cred in credentials)


def test_get_credential_metadata(vault):
    """Test obtener metadatos sin desencriptar"""
    vault.store_credential(
        credential_id="test-token",
        credential_type="bearer-token",
        value="secret",
        metadata={"api": "test-api"}
    )
    
    metadata = vault.get_credential_metadata("test-token")
    assert metadata["id"] == "test-token"
    assert metadata["type"] == "bearer-token"
    assert metadata["metadata"]["api"] == "test-api"
    # No debe incluir el valor
    assert "encryptedValue" not in metadata


def test_credential_injector(vault):
    """Test inyección de credenciales en operaciones"""
    vault.store_credential(
        credential_id="api-token",
        credential_type="bearer-token",
        value="secret-token-123"
    )
    
    injector = CredentialInjector(vault)
    
    config = {
        "headers": {
            "Authorization": {
                "credentialRef": {"id": "api-token"}
            }
        }
    }
    
    injected = injector.inject_into_operation(config, "ApiCall")
    assert injected["headers"]["Authorization"] == "Bearer secret-token-123"


def test_delete_credential(vault):
    """Test eliminar credencial"""
    vault.store_credential("test-token", "bearer-token", "value")
    assert "test-token" in vault.credentials
    
    vault.delete_credential("test-token")
    assert "test-token" not in vault.credentials
    assert vault.get_credential("test-token") is None

