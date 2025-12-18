"""
Tests para API Knowledge Base
"""

import pytest
from api_knowledge_base import APIKnowledgeBase


@pytest.fixture
def api_kb():
    """Fixture para crear una base de conocimiento limpia"""
    return APIKnowledgeBase()


def test_add_api(api_kb):
    """Test agregar una API"""
    api_kb.add_api(
        api_id="test-api",
        base_url="https://api.example.com",
        endpoints=[]
    )
    
    assert "test-api" in api_kb.apis
    assert api_kb.apis["test-api"]["baseUrl"] == "https://api.example.com"


def test_add_endpoint(api_kb):
    """Test agregar un endpoint a una API"""
    api_kb.add_api(
        api_id="test-api",
        base_url="https://api.example.com",
        endpoints=[]
    )
    
    api_kb.add_endpoint(
        api_id="test-api",
        endpoint_path="/users",
        method="GET",
        description="Get users"
    )
    
    api_info = api_kb.get_api_info("test-api")
    assert len(api_info["endpoints"]) == 1
    assert api_info["endpoints"][0]["path"] == "/users"
    assert api_info["endpoints"][0]["method"] == "GET"


def test_search_endpoints(api_kb):
    """Test búsqueda de endpoints"""
    api_kb.add_api(
        api_id="user-api",
        base_url="https://api.example.com",
        endpoints=[]
    )
    
    api_kb.add_endpoint(
        api_id="user-api",
        endpoint_path="/users",
        method="GET",
        description="Get list of users with filters"
    )
    
    api_kb.add_endpoint(
        api_id="user-api",
        endpoint_path="/users/{id}",
        method="GET",
        description="Get user by ID"
    )
    
    results = api_kb.search_endpoints("get users", top_k=5)
    assert len(results) > 0
    assert any(ep["path"] == "/users" for ep in results)


def test_build_api_catalog(api_kb):
    """Test construcción de catálogo de APIs"""
    api_kb.add_api(
        api_id="test-api",
        base_url="https://api.example.com",
        endpoints=[]
    )
    
    api_kb.add_endpoint(
        api_id="test-api",
        endpoint_path="/users",
        method="GET",
        description="Get users"
    )
    
    catalog = api_kb.build_api_catalog_for_agent()
    assert "test-api" in catalog["apis"]
    assert len(catalog["apis"]["test-api"]["endpoints"]) == 1


def test_get_available_apis(api_kb):
    """Test obtener lista de APIs disponibles"""
    api_kb.add_api("api1", "https://api1.com", [])
    api_kb.add_api("api2", "https://api2.com", [])
    
    apis = api_kb.get_available_apis()
    assert len(apis) == 2
    assert "api1" in apis
    assert "api2" in apis

