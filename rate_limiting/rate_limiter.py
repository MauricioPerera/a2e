"""
Rate Limiter para A2E
Implementa límites de velocidad por agente, tiempo y operación
"""

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """
    Configuración de límites de velocidad
    """
    # Límites globales por agente
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    
    # Límites por operación
    api_calls_per_minute: int = 30
    api_calls_per_hour: int = 500
    
    # Throttling
    enable_throttling: bool = True
    throttle_delay_ms: int = 100  # Delay entre requests cuando se alcanza el límite
    
    # Ventana deslizante
    window_size_seconds: int = 60


@dataclass
class RateLimitRecord:
    """
    Registro de requests para un agente
    """
    requests: list = field(default_factory=list)  # Timestamps de requests
    api_calls: list = field(default_factory=list)  # Timestamps de ApiCall operations
    
    def cleanup_old_requests(self, window_seconds: int):
        """Limpia requests antiguos fuera de la ventana"""
        current_time = time.time()
        cutoff = current_time - window_seconds
        
        self.requests = [t for t in self.requests if t > cutoff]
        self.api_calls = [t for t in self.api_calls if t > cutoff]


class RateLimiter:
    """
    Rate limiter para controlar velocidad de ejecución
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        Inicializa el rate limiter
        
        Args:
            config: Configuración de límites (usa defaults si es None)
        """
        self.config = config or RateLimitConfig()
        self.records: Dict[str, RateLimitRecord] = defaultdict(RateLimitRecord)
        self.custom_limits: Dict[str, RateLimitConfig] = {}  # Límites personalizados por agente
        
    def set_agent_limits(self, agent_id: str, config: RateLimitConfig):
        """
        Establece límites personalizados para un agente
        
        Args:
            agent_id: ID del agente
            config: Configuración de límites
        """
        self.custom_limits[agent_id] = config
        logger.info(f"Set custom rate limits for agent {agent_id}")
    
    def check_rate_limit(
        self,
        agent_id: str,
        operation_type: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Verifica si una request está dentro de los límites
        
        Args:
            agent_id: ID del agente
            operation_type: Tipo de operación (ej: "ApiCall") o None para request general
        
        Returns:
            Tuple (allowed, error_message, retry_after_seconds)
            - allowed: True si está permitido, False si excede límites
            - error_message: Mensaje de error si no está permitido
            - retry_after_seconds: Segundos a esperar antes de reintentar
        """
        # Obtener configuración (personalizada o default)
        config = self.custom_limits.get(agent_id, self.config)
        
        # Obtener registro del agente
        record = self.records[agent_id]
        current_time = time.time()
        
        # Limpiar requests antiguos
        record.cleanup_old_requests(config.window_size_seconds)
        
        # Verificar límites de requests generales
        requests_count = len(record.requests)
        
        # Requests por minuto
        requests_last_minute = sum(1 for t in record.requests if t > current_time - 60)
        if requests_last_minute >= config.requests_per_minute:
            retry_after = 60 - (current_time - record.requests[-config.requests_per_minute])
            return False, f"Rate limit exceeded: {config.requests_per_minute} requests per minute", max(0, retry_after)
        
        # Requests por hora
        requests_last_hour = sum(1 for t in record.requests if t > current_time - 3600)
        if requests_last_hour >= config.requests_per_hour:
            retry_after = 3600 - (current_time - record.requests[-config.requests_per_hour])
            return False, f"Rate limit exceeded: {config.requests_per_hour} requests per hour", max(0, retry_after)
        
        # Requests por día
        requests_last_day = sum(1 for t in record.requests if t > current_time - 86400)
        if requests_last_day >= config.requests_per_day:
            retry_after = 86400 - (current_time - record.requests[-config.requests_per_day])
            return False, f"Rate limit exceeded: {config.requests_per_day} requests per day", max(0, retry_after)
        
        # Verificar límites por operación (si es ApiCall)
        if operation_type == "ApiCall":
            api_calls_last_minute = sum(1 for t in record.api_calls if t > current_time - 60)
            if api_calls_last_minute >= config.api_calls_per_minute:
                retry_after = 60 - (current_time - record.api_calls[-config.api_calls_per_minute])
                return False, f"Rate limit exceeded: {config.api_calls_per_minute} API calls per minute", max(0, retry_after)
            
            api_calls_last_hour = sum(1 for t in record.api_calls if t > current_time - 3600)
            if api_calls_last_hour >= config.api_calls_per_hour:
                retry_after = 3600 - (current_time - record.api_calls[-config.api_calls_per_hour])
                return False, f"Rate limit exceeded: {config.api_calls_per_hour} API calls per hour", max(0, retry_after)
        
        # Registrar request
        record.requests.append(current_time)
        if operation_type == "ApiCall":
            record.api_calls.append(current_time)
        
        # Throttling (delay opcional)
        if config.enable_throttling and len(record.requests) > 1:
            last_request_time = record.requests[-2]
            time_since_last = current_time - last_request_time
            min_interval = config.throttle_delay_ms / 1000.0
            
            if time_since_last < min_interval:
                delay = min_interval - time_since_last
                time.sleep(delay)
        
        return True, None, None
    
    def get_rate_limit_status(self, agent_id: str) -> Dict:
        """
        Obtiene el estado actual de rate limits para un agente
        
        Args:
            agent_id: ID del agente
        
        Returns:
            Diccionario con estadísticas de rate limits
        """
        config = self.custom_limits.get(agent_id, self.config)
        record = self.records.get(agent_id, RateLimitRecord())
        current_time = time.time()
        
        record.cleanup_old_requests(config.window_size_seconds)
        
        return {
            "agent_id": agent_id,
            "limits": {
                "requests_per_minute": config.requests_per_minute,
                "requests_per_hour": config.requests_per_hour,
                "requests_per_day": config.requests_per_day,
                "api_calls_per_minute": config.api_calls_per_minute,
                "api_calls_per_hour": config.api_calls_per_hour
            },
            "usage": {
                "requests_last_minute": sum(1 for t in record.requests if t > current_time - 60),
                "requests_last_hour": sum(1 for t in record.requests if t > current_time - 3600),
                "requests_last_day": sum(1 for t in record.requests if t > current_time - 86400),
                "api_calls_last_minute": sum(1 for t in record.api_calls if t > current_time - 60),
                "api_calls_last_hour": sum(1 for t in record.api_calls if t > current_time - 3600)
            },
            "remaining": {
                "requests_per_minute": max(0, config.requests_per_minute - sum(1 for t in record.requests if t > current_time - 60)),
                "requests_per_hour": max(0, config.requests_per_hour - sum(1 for t in record.requests if t > current_time - 3600)),
                "requests_per_day": max(0, config.requests_per_day - sum(1 for t in record.requests if t > current_time - 86400)),
                "api_calls_per_minute": max(0, config.api_calls_per_minute - sum(1 for t in record.api_calls if t > current_time - 60)),
                "api_calls_per_hour": max(0, config.api_calls_per_hour - sum(1 for t in record.api_calls if t > current_time - 3600))
            }
        }
    
    def reset_agent_limits(self, agent_id: str):
        """
        Resetea los límites de un agente (limpia historial)
        
        Args:
            agent_id: ID del agente
        """
        if agent_id in self.records:
            del self.records[agent_id]
        if agent_id in self.custom_limits:
            del self.custom_limits[agent_id]
        logger.info(f"Reset rate limits for agent {agent_id}")
    
    def cleanup_old_records(self, max_age_seconds: int = 86400):
        """
        Limpia registros antiguos para liberar memoria
        
        Args:
            max_age_seconds: Edad máxima en segundos (default: 1 día)
        """
        current_time = time.time()
        cutoff = current_time - max_age_seconds
        
        agents_to_remove = []
        for agent_id, record in self.records.items():
            record.cleanup_old_requests(max_age_seconds)
            # Si no hay requests recientes, eliminar registro
            if not record.requests or max(record.requests) < cutoff:
                agents_to_remove.append(agent_id)
        
        for agent_id in agents_to_remove:
            del self.records[agent_id]
        
        if agents_to_remove:
            logger.debug(f"Cleaned up {len(agents_to_remove)} old rate limit records")

