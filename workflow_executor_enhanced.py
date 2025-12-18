"""
Workflow Executor mejorado con Retry y Caché
"""

import aiohttp
import logging
from typing import Dict, Any, Optional

from workflow_executor_with_responses import RobustWorkflowExecutor
from retry import RetryHandler, RetryConfig, RetryableError
from cache import ResultCache, CacheConfig

logger = logging.getLogger(__name__)


class EnhancedWorkflowExecutor(RobustWorkflowExecutor):
    """
    Workflow Executor con Retry Logic y Caché integrados
    """
    
    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        cache_config: Optional[CacheConfig] = None,
        **kwargs
    ):
        """
        Inicializa el executor mejorado
        
        Args:
            retry_config: Configuración de reintentos
            cache_config: Configuración de caché
            **kwargs: Argumentos adicionales para RobustWorkflowExecutor
        """
        super().__init__(**kwargs)
        
        # Inicializar retry handler
        self.retry_handler = RetryHandler(config=retry_config) if retry_config else RetryHandler()
        
        # Inicializar caché
        self.cache = ResultCache(config=cache_config) if cache_config else ResultCache()
    
    async def _execute_api_call(self, config: Dict[str, Any]) -> Any:
        """
        Ejecuta llamada a API con retry y caché
        
        Args:
            config: Configuración de la llamada API
        
        Returns:
            Resultado de la API
        """
        operation_type = "ApiCall"
        
        # Verificar caché primero
        cached_result = self.cache.get(operation_type, config)
        if cached_result is not None:
            logger.info(f"Cache hit for ApiCall: {config.get('url', 'unknown')}")
            output_path = config.get("outputPath")
            if output_path:
                self._set_data(output_path, cached_result)
            return cached_result
        
        # Ejecutar con retry
        async def make_api_call():
            method = config["method"]
            url = self._resolve_path(config["url"])
            headers = self._resolve_object(config.get("headers", {}))
            body = self._resolve_object(config.get("body")) if config.get("body") else None
            timeout = config.get("timeout", 30000) / 1000.0  # Convertir ms a segundos
            
            logger.info(f"Executing {method} {url}")
            
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                try:
                    async with session.request(method, url, headers=headers, json=body) as response:
                        # Verificar si es un error retryable
                        if response.status >= 500:
                            # Error del servidor - retryable
                            error_text = await response.text()
                            raise RetryableError(f"Server error {response.status}: {error_text}")
                        
                        if response.status == 429:
                            # Rate limit - retryable
                            retry_after = response.headers.get('Retry-After', '60')
                            raise RetryableError(f"Rate limited. Retry after {retry_after}s")
                        
                        if response.status >= 400:
                            # Error del cliente - no retryable
                            error_text = await response.text()
                            raise Exception(f"Client error {response.status}: {error_text}")
                        
                        # Éxito
                        result = await response.json()
                        
                        # Guardar en data model
                        output_path = config.get("outputPath")
                        if output_path:
                            self._set_data(output_path, result)
                        
                        # Guardar en caché
                        self.cache.set(operation_type, config, result)
                        
                        return result
                
                except aiohttp.ClientError as e:
                    # Errores de conexión - retryable
                    raise RetryableError(f"Connection error: {str(e)}")
                except asyncio.TimeoutError:
                    # Timeout - retryable
                    raise RetryableError(f"Request timeout after {timeout}s")
        
        # Ejecutar con retry
        result = await self.retry_handler.execute_with_retry(
            make_api_call,
            operation_name=f"ApiCall {config.get('method', 'GET')} {config.get('url', 'unknown')}"
        )
        
        return result
    
    def _execute_filter_data(self, config: Dict[str, Any]) -> Any:
        """
        Ejecuta filtrado de datos con caché
        
        Args:
            config: Configuración del filtro
        
        Returns:
            Datos filtrados
        """
        operation_type = "FilterData"
        
        # Verificar caché
        cached_result = self.cache.get(operation_type, config)
        if cached_result is not None:
            logger.debug("Cache hit for FilterData")
            output_path = config.get("outputPath")
            if output_path:
                self._set_data(output_path, cached_result)
            return cached_result
        
        # Ejecutar filtrado (sin retry, es operación local)
        result = super()._execute_filter_data(config)
        
        # Guardar en caché
        self.cache.set(operation_type, config, result)
        
        return result
    
    def _execute_transform_data(self, config: Dict[str, Any]) -> Any:
        """
        Ejecuta transformación de datos con caché
        
        Args:
            config: Configuración de la transformación
        
        Returns:
            Datos transformados
        """
        operation_type = "TransformData"
        
        # Verificar caché
        cached_result = self.cache.get(operation_type, config)
        if cached_result is not None:
            logger.debug("Cache hit for TransformData")
            output_path = config.get("outputPath")
            if output_path:
                self._set_data(output_path, cached_result)
            return cached_result
        
        # Ejecutar transformación (sin retry, es operación local)
        result = super()._execute_transform_data(config)
        
        # Guardar en caché
        self.cache.set(operation_type, config, result)
        
        return result
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché
        
        Returns:
            Estadísticas del caché
        """
        return self.cache.get_stats()
    
    def clear_cache(self):
        """Limpia el caché"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def invalidate_cache(self, operation_type: Optional[str] = None):
        """
        Invalida el caché
        
        Args:
            operation_type: Tipo de operación a invalidar (None = todo)
        """
        self.cache.invalidate(operation_type=operation_type)
        logger.info(f"Cache invalidated for {operation_type or 'all operations'}")


import asyncio  # Para asyncio.TimeoutError

