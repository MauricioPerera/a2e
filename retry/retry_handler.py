"""
Retry Handler para A2E
Implementa reintentos automáticos con backoff exponencial
"""

import asyncio
import time
from typing import Callable, Any, Optional, Dict, Type
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Error que puede ser reintentado"""
    pass


class NonRetryableError(Exception):
    """Error que NO debe ser reintentado"""
    pass


@dataclass
class RetryConfig:
    """
    Configuración de reintentos
    """
    max_retries: int = 3
    initial_delay: float = 1.0  # Segundos
    max_delay: float = 60.0  # Segundos
    exponential_base: float = 2.0  # Base para backoff exponencial
    jitter: bool = True  # Agregar jitter aleatorio
    retryable_status_codes: list = None  # Códigos HTTP que deben reintentarse
    retryable_exceptions: tuple = None  # Excepciones que deben reintentarse
    
    def __post_init__(self):
        if self.retryable_status_codes is None:
            # Por defecto: 5xx y algunos 4xx específicos
            self.retryable_status_codes = [408, 429, 500, 502, 503, 504]
        
        if self.retryable_exceptions is None:
            # Por defecto: errores de conexión y timeouts
            self.retryable_exceptions = (
                ConnectionError,
                TimeoutError,
                asyncio.TimeoutError,
                RetryableError
            )


class RetryHandler:
    """
    Handler para reintentos automáticos
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Inicializa el retry handler
        
        Args:
            config: Configuración de reintentos (usa defaults si es None)
        """
        self.config = config or RetryConfig()
    
    def is_retryable_error(self, error: Exception) -> bool:
        """
        Determina si un error debe ser reintentado
        
        Args:
            error: Excepción a verificar
        
        Returns:
            True si debe reintentarse, False en caso contrario
        """
        # Verificar tipo de excepción
        if isinstance(error, NonRetryableError):
            return False
        
        if isinstance(error, RetryableError):
            return True
        
        # Verificar si es una excepción retryable
        if isinstance(error, self.config.retryable_exceptions):
            return True
        
        # Verificar códigos HTTP en errores de API
        if hasattr(error, 'status_code'):
            return error.status_code in self.config.retryable_status_codes
        
        if hasattr(error, 'code'):
            return error.code in self.config.retryable_status_codes
        
        return False
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calcula el delay para el siguiente intento
        
        Args:
            attempt: Número de intento (0-indexed)
        
        Returns:
            Delay en segundos
        """
        # Backoff exponencial
        delay = self.config.initial_delay * (self.config.exponential_base ** attempt)
        
        # Limitar delay máximo
        delay = min(delay, self.config.max_delay)
        
        # Agregar jitter si está habilitado
        if self.config.jitter:
            import random
            jitter = random.uniform(0, delay * 0.1)  # 10% de jitter
            delay += jitter
        
        return delay
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        operation_name: str = "operation",
        **kwargs
    ) -> Any:
        """
        Ejecuta una función con reintentos automáticos
        
        Args:
            func: Función a ejecutar (puede ser async o sync)
            *args: Argumentos posicionales
            operation_name: Nombre de la operación (para logging)
            **kwargs: Argumentos nombrados
        
        Returns:
            Resultado de la función
        
        Raises:
            Última excepción si todos los reintentos fallan
        """
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Ejecutar función
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Si llegamos aquí, la operación fue exitosa
                if attempt > 0:
                    logger.info(f"{operation_name} succeeded after {attempt} retries")
                
                return result
            
            except Exception as e:
                last_error = e
                
                # Verificar si debe reintentarse
                if not self.is_retryable_error(e):
                    logger.warning(f"{operation_name} failed with non-retryable error: {e}")
                    raise
                
                # Si es el último intento, no esperar
                if attempt >= self.config.max_retries:
                    logger.error(f"{operation_name} failed after {self.config.max_retries} retries: {e}")
                    break
                
                # Calcular delay y esperar
                delay = self.calculate_delay(attempt)
                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{self.config.max_retries + 1}): {e}. "
                    f"Retrying in {delay:.2f}s..."
                )
                
                await asyncio.sleep(delay)
        
        # Si llegamos aquí, todos los reintentos fallaron
        raise last_error
    
    def execute_sync_with_retry(
        self,
        func: Callable,
        *args,
        operation_name: str = "operation",
        **kwargs
    ) -> Any:
        """
        Ejecuta una función síncrona con reintentos (wrapper para sync)
        
        Args:
            func: Función síncrona a ejecutar
            *args: Argumentos posicionales
            operation_name: Nombre de la operación (para logging)
            **kwargs: Argumentos nombrados
        
        Returns:
            Resultado de la función
        
        Raises:
            Última excepción si todos los reintentos fallan
        """
        import asyncio
        
        # Crear coroutine wrapper
        async def async_wrapper():
            return func(*args, **kwargs)
        
        # Ejecutar con retry
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.execute_with_retry(async_wrapper, operation_name=operation_name)
        )


def retryable(max_retries: int = 3, initial_delay: float = 1.0):
    """
    Decorador para funciones que deben reintentarse
    
    Usage:
        @retryable(max_retries=5, initial_delay=2.0)
        async def my_function():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            config = RetryConfig(max_retries=max_retries, initial_delay=initial_delay)
            handler = RetryHandler(config=config)
            return await handler.execute_with_retry(
                func,
                *args,
                operation_name=func.__name__,
                **kwargs
            )
        return wrapper
    return decorator

