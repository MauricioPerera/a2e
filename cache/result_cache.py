"""
Caché de Resultados para A2E
Implementa caché para resultados de operaciones
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """
    Configuración de caché
    """
    default_ttl: int = 300  # TTL por defecto en segundos (5 minutos)
    max_size: int = 1000  # Máximo número de entradas en caché
    enable_cache: bool = True  # Habilitar/deshabilitar caché
    
    # TTL por tipo de operación
    operation_ttl: Dict[str, int] = None
    
    def __post_init__(self):
        if self.operation_ttl is None:
            # TTL por defecto por operación
            self.operation_ttl = {
                "ApiCall": 300,  # 5 minutos
                "FilterData": 60,  # 1 minuto
                "TransformData": 60,  # 1 minuto
                "StoreData": 0,  # No cachear (escritura)
                "Wait": 0,  # No cachear
                "Loop": 0,  # No cachear
                "Conditional": 0,  # No cachear
                "MergeData": 60  # 1 minuto
            }


class CacheEntry:
    """
    Entrada en el caché
    """
    
    def __init__(self, key: str, value: Any, ttl: int, created_at: float = None):
        self.key = key
        self.value = value
        self.ttl = ttl
        self.created_at = created_at or time.time()
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Verifica si la entrada ha expirado"""
        if self.ttl == 0:
            return False  # Sin expiración
        return time.time() - self.created_at > self.ttl
    
    def access(self):
        """Registra un acceso"""
        self.access_count += 1
        self.last_accessed = time.time()


class ResultCache:
    """
    Caché de resultados de operaciones
    """
    
    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Inicializa el caché
        
        Args:
            config: Configuración de caché (usa defaults si es None)
        """
        self.config = config or CacheConfig()
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "sets": 0
        }
    
    def _generate_key(
        self,
        operation_type: str,
        operation_config: Dict[str, Any]
    ) -> str:
        """
        Genera una clave única para una operación
        
        Args:
            operation_type: Tipo de operación
            operation_config: Configuración de la operación
        
        Returns:
            Clave hash para el caché
        """
        # Crear string serializable de la configuración
        key_data = {
            "type": operation_type,
            "config": operation_config
        }
        key_string = json.dumps(key_data, sort_keys=True)
        
        # Generar hash
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def get(
        self,
        operation_type: str,
        operation_config: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Obtiene un resultado del caché
        
        Args:
            operation_type: Tipo de operación
            operation_config: Configuración de la operación
        
        Returns:
            Resultado cacheado o None si no existe o expiró
        """
        if not self.config.enable_cache:
            return None
        
        # Verificar si este tipo de operación debe cachearse
        if operation_type in self.config.operation_ttl:
            if self.config.operation_ttl[operation_type] == 0:
                return None  # No cachear esta operación
        
        key = self._generate_key(operation_type, operation_config)
        
        # Limpiar expirados antes de buscar
        self.cleanup_expired()
        
        # Buscar en caché
        if key in self.cache:
            entry = self.cache[key]
            
            # Verificar expiración (por si acaso)
            if entry.is_expired():
                del self.cache[key]
                self.stats["misses"] += 1
                return None
            
            # Mover al final (LRU)
            self.cache.move_to_end(key)
            entry.access()
            self.stats["hits"] += 1
            logger.debug(f"Cache hit for {operation_type}")
            return entry.value
        
        self.stats["misses"] += 1
        return None
    
    def set(
        self,
        operation_type: str,
        operation_config: Dict[str, Any],
        value: Any,
        ttl: Optional[int] = None
    ):
        """
        Almacena un resultado en el caché
        
        Args:
            operation_type: Tipo de operación
            operation_config: Configuración de la operación
            value: Valor a cachear
            ttl: TTL en segundos (usa default si es None)
        """
        if not self.config.enable_cache:
            return
        
        # Verificar si este tipo de operación debe cachearse
        if operation_type in self.config.operation_ttl:
            if self.config.operation_ttl[operation_type] == 0:
                return  # No cachear esta operación
        
        key = self._generate_key(operation_type, operation_config)
        
        # Determinar TTL
        if ttl is None:
            ttl = self.config.operation_ttl.get(operation_type, self.config.default_ttl)
        
        # Crear entrada
        entry = CacheEntry(key=key, value=value, ttl=ttl)
        
        # Verificar tamaño máximo
        if len(self.cache) >= self.config.max_size:
            # Evictar entrada más antigua (LRU)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            self.stats["evictions"] += 1
            logger.debug(f"Cache eviction: {oldest_key}")
        
        # Agregar entrada
        self.cache[key] = entry
        self.stats["sets"] += 1
        logger.debug(f"Cached result for {operation_type}")
    
    def invalidate(
        self,
        operation_type: Optional[str] = None,
        pattern: Optional[str] = None
    ):
        """
        Invalida entradas del caché
        
        Args:
            operation_type: Tipo de operación a invalidar (None = todos)
            pattern: Patrón de clave a invalidar (opcional)
        """
        if operation_type:
            # Invalidar por tipo de operación
            keys_to_remove = [
                key for key, entry in self.cache.items()
                if hasattr(entry.value, 'operation_type') and entry.value.operation_type == operation_type
            ]
        elif pattern:
            # Invalidar por patrón
            keys_to_remove = [key for key in self.cache.keys() if pattern in key]
        else:
            # Invalidar todo
            keys_to_remove = list(self.cache.keys())
        
        for key in keys_to_remove:
            del self.cache[key]
        
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries")
    
    def clear(self):
        """Limpia todo el caché"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def cleanup_expired(self):
        """Limpia entradas expiradas"""
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché
        
        Returns:
            Diccionario con estadísticas
        """
        self.cleanup_expired()
        
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.config.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "hit_rate": f"{hit_rate:.2f}%",
            "evictions": self.stats["evictions"],
            "sets": self.stats["sets"]
        }

