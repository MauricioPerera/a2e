"""
Middleware de Rate Limiting para Flask
"""

import time
from flask import request, jsonify, g
from functools import wraps
import logging
from typing import Optional

from .rate_limiter import RateLimiter, RateLimitConfig

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """
    Middleware de rate limiting para Flask
    """
    
    def __init__(self, rate_limiter: RateLimiter):
        """
        Inicializa el middleware
        
        Args:
            rate_limiter: Instancia de RateLimiter
        """
        self.rate_limiter = rate_limiter
    
    def get_agent_id(self) -> Optional[str]:
        """
        Extrae el ID del agente de la request
        
        Returns:
            ID del agente o None
        """
        # Intentar obtener de g (seteado por auth middleware)
        if hasattr(g, 'agent_id'):
            return g.agent_id
        
        # Intentar obtener de headers
        return request.headers.get('X-Agent-ID') or request.headers.get('Authorization')
    
    def rate_limit(self, operation_type: Optional[str] = None):
        """
        Decorador para aplicar rate limiting a endpoints
        
        Args:
            operation_type: Tipo de operación (ej: "ApiCall") o None
        
        Usage:
            @app.route('/api/v1/execute')
            @rate_limit_middleware.rate_limit()
            def execute_workflow():
                ...
        """
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                agent_id = self.get_agent_id()
                
                if not agent_id:
                    return jsonify({
                        "error": "Agent ID required for rate limiting"
                    }), 401
                
                # Verificar rate limit
                allowed, error_message, retry_after = self.rate_limiter.check_rate_limit(
                    agent_id,
                    operation_type
                )
                
                if not allowed:
                    response = jsonify({
                        "error": "Rate limit exceeded",
                        "message": error_message,
                        "retry_after": retry_after
                    })
                    response.headers['X-RateLimit-Limit'] = str(self.rate_limiter.config.requests_per_minute)
                    response.headers['X-RateLimit-Remaining'] = "0"
                    response.headers['Retry-After'] = str(int(retry_after)) if retry_after else "60"
                    return response, 429
                
                # Agregar headers de rate limit
                status = self.rate_limiter.get_rate_limit_status(agent_id)
                g.rate_limit_status = status
                
                # Ejecutar función
                response = f(*args, **kwargs)
                
                # Agregar headers de rate limit a la respuesta
                if isinstance(response, tuple):
                    response_obj, status_code = response
                else:
                    response_obj = response
                    status_code = 200
                
                if hasattr(response_obj, 'headers'):
                    remaining = status['remaining']['requests_per_minute']
                    response_obj.headers['X-RateLimit-Limit'] = str(status['limits']['requests_per_minute'])
                    response_obj.headers['X-RateLimit-Remaining'] = str(remaining)
                    response_obj.headers['X-RateLimit-Reset'] = str(int(time.time()) + 60)
                
                return response
            
            return decorated_function
        return decorator
    
    def before_request(self):
        """
        Hook de Flask before_request para rate limiting automático
        """
        # Solo aplicar a endpoints de API
        if not request.path.startswith('/api/'):
            return
        
        agent_id = self.get_agent_id()
        if not agent_id:
            return  # Auth middleware manejará esto
        
        # Verificar rate limit
        allowed, error_message, retry_after = self.rate_limiter.check_rate_limit(agent_id)
        
        if not allowed:
            response = jsonify({
                "error": "Rate limit exceeded",
                "message": error_message,
                "retry_after": retry_after
            })
            response.headers['X-RateLimit-Limit'] = str(self.rate_limiter.config.requests_per_minute)
            response.headers['X-RateLimit-Remaining'] = "0"
            response.headers['Retry-After'] = str(int(retry_after)) if retry_after else "60"
            return response, 429
        
        # Agregar status a g para uso en endpoints
        status = self.rate_limiter.get_rate_limit_status(agent_id)
        g.rate_limit_status = status

