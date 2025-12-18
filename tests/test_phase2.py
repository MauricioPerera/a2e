"""
Tests para componentes de Fase 2: Rate Limiting, Retry, Caché
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock

from rate_limiting import RateLimiter, RateLimitConfig
from retry import RetryHandler, RetryConfig, RetryableError, NonRetryableError
from cache import ResultCache, CacheConfig


class TestRateLimiter:
    """Tests para Rate Limiter"""
    
    def test_rate_limit_allowed(self):
        """Test que permite requests dentro del límite"""
        limiter = RateLimiter(RateLimitConfig(requests_per_minute=10))
        agent_id = "test-agent"
        
        # Primeras 10 requests deben ser permitidas
        for i in range(10):
            allowed, error, retry_after = limiter.check_rate_limit(agent_id)
            assert allowed, f"Request {i+1} should be allowed"
            assert error is None
            assert retry_after is None
    
    def test_rate_limit_exceeded(self):
        """Test que rechaza requests que exceden el límite"""
        limiter = RateLimiter(RateLimitConfig(requests_per_minute=2))
        agent_id = "test-agent"
        
        # Primeras 2 requests permitidas
        allowed, _, _ = limiter.check_rate_limit(agent_id)
        assert allowed
        allowed, _, _ = limiter.check_rate_limit(agent_id)
        assert allowed
        
        # Tercera request debe ser rechazada
        allowed, error, retry_after = limiter.check_rate_limit(agent_id)
        assert not allowed
        assert error is not None
        assert "Rate limit exceeded" in error
        assert retry_after is not None
    
    def test_custom_agent_limits(self):
        """Test límites personalizados por agente"""
        limiter = RateLimiter(RateLimitConfig(requests_per_minute=10))
        agent_id = "premium-agent"
        
        # Establecer límite personalizado
        custom_config = RateLimitConfig(requests_per_minute=100)
        limiter.set_agent_limits(agent_id, custom_config)
        
        # Debe permitir más requests
        for i in range(50):
            allowed, _, _ = limiter.check_rate_limit(agent_id)
            assert allowed, f"Request {i+1} should be allowed for premium agent"
    
    def test_rate_limit_status(self):
        """Test obtención de estado de rate limits"""
        limiter = RateLimiter(RateLimitConfig(requests_per_minute=10))
        agent_id = "test-agent"
        
        # Hacer algunas requests
        for _ in range(5):
            limiter.check_rate_limit(agent_id)
        
        status = limiter.get_rate_limit_status(agent_id)
        assert status["agent_id"] == agent_id
        assert status["usage"]["requests_last_minute"] == 5
        assert status["remaining"]["requests_per_minute"] == 5


class TestRetryHandler:
    """Tests para Retry Handler"""
    
    @pytest.mark.asyncio
    async def test_retry_success_first_try(self):
        """Test que no reintenta si la primera llamada es exitosa"""
        handler = RetryHandler(RetryConfig(max_retries=3))
        
        call_count = 0
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await handler.execute_with_retry(success_func, operation_name="test")
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_success_after_retries(self):
        """Test que reintenta y eventualmente tiene éxito"""
        handler = RetryHandler(RetryConfig(max_retries=3, initial_delay=0.1))
        
        call_count = 0
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("Temporary error")
            return "success"
        
        result = await handler.execute_with_retry(flaky_func, operation_name="test")
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_max_retries_exceeded(self):
        """Test que falla después de max_retries"""
        handler = RetryHandler(RetryConfig(max_retries=2, initial_delay=0.1))
        
        call_count = 0
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise RetryableError("Always fails")
        
        with pytest.raises(RetryableError):
            await handler.execute_with_retry(always_fail, operation_name="test")
        
        assert call_count == 3  # 1 inicial + 2 reintentos
    
    @pytest.mark.asyncio
    async def test_retry_non_retryable_error(self):
        """Test que no reintenta errores no retryables"""
        handler = RetryHandler(RetryConfig(max_retries=3))
        
        call_count = 0
        async def non_retryable():
            nonlocal call_count
            call_count += 1
            raise NonRetryableError("Permanent error")
        
        with pytest.raises(NonRetryableError):
            await handler.execute_with_retry(non_retryable, operation_name="test")
        
        assert call_count == 1  # No reintenta
    
    def test_is_retryable_error(self):
        """Test detección de errores retryables"""
        handler = RetryHandler()
        
        assert handler.is_retryable_error(RetryableError("test"))
        assert handler.is_retryable_error(ConnectionError("test"))
        assert handler.is_retryable_error(TimeoutError("test"))
        assert not handler.is_retryable_error(NonRetryableError("test"))
        
        # Mock error con status_code
        mock_error = Mock()
        mock_error.status_code = 500
        assert handler.is_retryable_error(mock_error)
        
        mock_error.status_code = 400
        assert not handler.is_retryable_error(mock_error)


class TestResultCache:
    """Tests para Result Cache"""
    
    def test_cache_set_get(self):
        """Test almacenar y obtener del caché"""
        cache = ResultCache(CacheConfig(default_ttl=60))
        
        config = {"url": "https://api.example.com/data"}
        value = {"result": "data"}
        
        # No debe estar en caché
        result = cache.get("ApiCall", config)
        assert result is None
        
        # Almacenar
        cache.set("ApiCall", config, value)
        
        # Debe estar en caché
        result = cache.get("ApiCall", config)
        assert result == value
    
    def test_cache_expiration(self):
        """Test expiración de entradas"""
        # Configurar TTL de 1 segundo para ApiCall específicamente
        cache = ResultCache(CacheConfig(
            default_ttl=1,
            operation_ttl={"ApiCall": 1}  # 1 segundo TTL para ApiCall
        ))
        
        config = {"url": "https://api.example.com/data"}
        value = {"result": "data"}
        
        cache.set("ApiCall", config, value)
        
        # Debe estar en caché
        result = cache.get("ApiCall", config)
        assert result == value
        
        # Esperar expiración
        time.sleep(1.1)
        
        # No debe estar en caché (debe expirar)
        result = cache.get("ApiCall", config)
        assert result is None
    
    def test_cache_operation_ttl(self):
        """Test TTL por tipo de operación"""
        cache = ResultCache(CacheConfig(
            default_ttl=60,
            operation_ttl={"ApiCall": 300, "FilterData": 30}
        ))
        
        api_config = {"url": "https://api.example.com/data"}
        filter_config = {"inputPath": "/data", "conditions": []}
        
        cache.set("ApiCall", api_config, {"api": "data"})
        cache.set("FilterData", filter_config, {"filtered": "data"})
        
        # Ambos deben estar en caché
        assert cache.get("ApiCall", api_config) is not None
        assert cache.get("FilterData", filter_config) is not None
    
    def test_cache_no_cache_operations(self):
        """Test que no cachea operaciones con TTL=0"""
        cache = ResultCache(CacheConfig(
            operation_ttl={"StoreData": 0}  # No cachear
        ))
        
        config = {"path": "/data"}
        value = {"stored": "data"}
        
        cache.set("StoreData", config, value)
        
        # No debe estar en caché
        result = cache.get("StoreData", config)
        assert result is None
    
    def test_cache_lru_eviction(self):
        """Test eviction LRU cuando se alcanza max_size"""
        cache = ResultCache(CacheConfig(max_size=3))
        
        # Llenar caché
        for i in range(3):
            cache.set("ApiCall", {"url": f"https://api{i}.com"}, {"data": i})
        
        assert len(cache.cache) == 3
        
        # Agregar uno más (debe evictar el más antiguo)
        cache.set("ApiCall", {"url": "https://api3.com"}, {"data": 3})
        
        assert len(cache.cache) == 3
        assert cache.stats["evictions"] == 1
    
    def test_cache_invalidate(self):
        """Test invalidación de caché"""
        cache = ResultCache()
        
        # Almacenar varios items
        cache.set("ApiCall", {"url": "https://api1.com"}, {"data": 1})
        cache.set("ApiCall", {"url": "https://api2.com"}, {"data": 2})
        cache.set("FilterData", {"inputPath": "/data"}, {"filtered": 3})
        
        assert len(cache.cache) == 3
        
        # Invalidar todo (por ahora invalidate por tipo invalida todo)
        cache.invalidate()
        
        # Todo debe estar vacío
        assert len(cache.cache) == 0
    
    def test_cache_stats(self):
        """Test estadísticas del caché"""
        cache = ResultCache()
        
        config = {"url": "https://api.example.com/data"}
        
        # Miss
        cache.get("ApiCall", config)
        assert cache.stats["misses"] == 1
        
        # Set
        cache.set("ApiCall", config, {"data": "value"})
        assert cache.stats["sets"] == 1
        
        # Hit
        cache.get("ApiCall", config)
        assert cache.stats["hits"] == 1
        
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert "hit_rate" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

