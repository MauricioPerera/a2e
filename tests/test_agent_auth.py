"""
Tests para Autenticación y Autorización de Agentes
"""

import pytest
import tempfile
import os
from auth.agent_auth import AgentAuth, AgentAuthMiddleware


@pytest.fixture
def auth():
    """Fixture para crear sistema de autenticación limpio"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
        config_path = f.name
    
    yield AgentAuth(config_path=config_path)
    
    # Cleanup
    if os.path.exists(config_path):
        os.unlink(config_path)


def test_register_agent(auth):
    """Test registrar un agente"""
    api_key = auth.register_agent(
        agent_id="agent-123",
        name="Test Agent",
        allowed_apis=["api-1"],
        allowed_credentials=["cred-1"]
    )
    
    assert api_key is not None
    assert len(api_key) > 0
    assert "agent-123" in auth.agents


def test_authenticate_with_api_key(auth):
    """Test autenticación con API key"""
    api_key = auth.register_agent(
        agent_id="agent-123",
        name="Test Agent"
    )
    
    agent_id = auth.authenticate(api_key)
    assert agent_id == "agent-123"
    
    # API key inválida
    invalid_id = auth.authenticate("invalid-key")
    assert invalid_id is None


def test_generate_and_verify_token(auth):
    """Test generación y verificación de token JWT"""
    auth.register_agent("agent-123", "Test Agent")
    
    token = auth.generate_token("agent-123", expires_in_hours=1)
    assert token is not None
    
    agent_id = auth.verify_token(token)
    assert agent_id == "agent-123"
    
    # Token inválido
    invalid_id = auth.verify_token("invalid-token")
    assert invalid_id is None


def test_get_agent_permissions(auth):
    """Test obtener permisos de agente"""
    auth.register_agent(
        agent_id="agent-123",
        name="Test Agent",
        allowed_apis=["api-1", "api-2"],
        allowed_credentials=["cred-1"],
        allowed_operations=["ApiCall", "FilterData"]
    )
    
    permissions = auth.get_agent_permissions("agent-123")
    assert permissions["allowed_apis"] == ["api-1", "api-2"]
    assert permissions["allowed_credentials"] == ["cred-1"]
    assert permissions["allowed_operations"] == ["ApiCall", "FilterData"]


def test_is_api_allowed(auth):
    """Test verificar si agente puede usar API"""
    auth.register_agent(
        agent_id="agent-123",
        name="Test Agent",
        allowed_apis=["api-1"]
    )
    
    assert auth.is_api_allowed("agent-123", "api-1") is True
    assert auth.is_api_allowed("agent-123", "api-2") is False
    
    # Agente sin restricciones (lista vacía = todas permitidas)
    auth.register_agent("agent-full", "Full Access Agent")
    assert auth.is_api_allowed("agent-full", "any-api") is True


def test_is_credential_allowed(auth):
    """Test verificar si agente puede usar credencial"""
    auth.register_agent(
        agent_id="agent-123",
        name="Test Agent",
        allowed_credentials=["cred-1"]
    )
    
    assert auth.is_credential_allowed("agent-123", "cred-1") is True
    assert auth.is_credential_allowed("agent-123", "cred-2") is False


def test_is_operation_allowed(auth):
    """Test verificar si agente puede usar operación"""
    auth.register_agent(
        agent_id="agent-123",
        name="Test Agent",
        allowed_operations=["ApiCall"]
    )
    
    assert auth.is_operation_allowed("agent-123", "ApiCall") is True
    assert auth.is_operation_allowed("agent-123", "FilterData") is False


def test_filter_capabilities(auth):
    """Test filtrar capacidades por agente"""
    all_apis = {
        "api-1": {"baseUrl": "https://api1.com"},
        "api-2": {"baseUrl": "https://api2.com"}
    }
    all_credentials = [
        {"id": "cred-1", "type": "bearer-token"},
        {"id": "cred-2", "type": "api-key"}
    ]
    all_operations = ["ApiCall", "FilterData", "StoreData"]
    
    auth.register_agent(
        agent_id="agent-123",
        name="Test Agent",
        allowed_apis=["api-1"],
        allowed_credentials=["cred-1"],
        allowed_operations=["ApiCall", "FilterData"]
    )
    
    filtered = auth.filter_capabilities(
        agent_id="agent-123",
        all_apis=all_apis,
        all_credentials=all_credentials,
        all_operations=all_operations
    )
    
    assert "api-1" in filtered["availableApis"]
    assert "api-2" not in filtered["availableApis"]
    assert len(filtered["availableCredentials"]) == 1
    assert filtered["availableCredentials"][0]["id"] == "cred-1"
    assert len(filtered["supportedOperations"]) == 2
    assert "ApiCall" in filtered["supportedOperations"]
    assert "StoreData" not in filtered["supportedOperations"]


def test_auth_middleware(auth):
    """Test middleware de autenticación"""
    api_key = auth.register_agent("agent-123", "Test Agent")
    token = auth.generate_token("agent-123")
    
    middleware = AgentAuthMiddleware(auth)
    
    # Autenticar con API key
    headers = {"X-API-Key": api_key}
    agent_id = middleware.authenticate_request(headers)
    assert agent_id == "agent-123"
    
    # Autenticar con token
    headers = {"Authorization": f"Bearer {token}"}
    agent_id = middleware.authenticate_request(headers)
    assert agent_id == "agent-123"
    
    # Headers inválidos
    headers = {}
    agent_id = middleware.authenticate_request(headers)
    assert agent_id is None

