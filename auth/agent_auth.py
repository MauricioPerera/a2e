"""
Sistema de autenticación y autorización para agentes A2E
Cada agente solo recibe los recursos que tiene asignados
"""

import json
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Set
from pathlib import Path
from datetime import datetime, timedelta
import jwt


class AgentAuth:
    """
    Sistema de autenticación y autorización de agentes
    """
    
    def __init__(self, config_path: str = "agent_auth.json", secret_key: Optional[str] = None):
        """
        Inicializa el sistema de autenticación
        
        Args:
            config_path: Ruta al archivo de configuración de agentes
            secret_key: Clave secreta para tokens JWT (si None, genera una)
        """
        self.config_path = Path(config_path)
        self.secret_key = secret_key or self._generate_secret_key()
        self.agents: Dict[str, Dict[str, Any]] = {}
        
        if self.config_path.exists():
            self.load_config()
    
    def _generate_secret_key(self) -> str:
        """Genera una clave secreta aleatoria"""
        return secrets.token_urlsafe(32)
    
    def load_config(self):
        """Carga configuración de agentes desde archivo"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            self.agents = config.get("agents", {})
    
    def save_config(self):
        """Guarda configuración de agentes"""
        config = {
            "agents": self.agents,
            "updated_at": datetime.now().isoformat()
        }
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    
    def register_agent(
        self,
        agent_id: str,
        name: str,
        allowed_apis: Optional[List[str]] = None,
        allowed_credentials: Optional[List[str]] = None,
        allowed_operations: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Registra un nuevo agente y retorna su API key
        
        Args:
            agent_id: ID único del agente
            name: Nombre del agente
            allowed_apis: Lista de IDs de APIs permitidas
            allowed_credentials: Lista de IDs de credenciales permitidas
            allowed_operations: Lista de operaciones permitidas
            metadata: Metadatos adicionales
        
        Returns:
            API key del agente
        """
        # Generar API key
        api_key = secrets.token_urlsafe(32)
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        self.agents[agent_id] = {
            "id": agent_id,
            "name": name,
            "api_key_hash": api_key_hash,
            "allowed_apis": allowed_apis or [],
            "allowed_credentials": allowed_credentials or [],
            "allowed_operations": allowed_operations or [],
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
            "last_used": None
        }
        
        self.save_config()
        return api_key
    
    def authenticate(self, api_key: str) -> Optional[str]:
        """
        Autentica un agente usando su API key
        
        Args:
            api_key: API key del agente
        
        Returns:
            Agent ID si la autenticación es exitosa, None si falla
        """
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        for agent_id, agent_data in self.agents.items():
            if agent_data["api_key_hash"] == api_key_hash:
                # Actualizar último uso
                agent_data["last_used"] = datetime.now().isoformat()
                self.save_config()
                return agent_id
        
        return None
    
    def generate_token(self, agent_id: str, expires_in_hours: int = 24) -> str:
        """
        Genera un token JWT para un agente
        
        Args:
            agent_id: ID del agente
            expires_in_hours: Horas hasta expiración
        
        Returns:
            Token JWT
        """
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        
        payload = {
            "agent_id": agent_id,
            "exp": datetime.utcnow() + timedelta(hours=expires_in_hours),
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_token(self, token: str) -> Optional[str]:
        """
        Verifica un token JWT y retorna el agent_id
        
        Args:
            token: Token JWT
        
        Returns:
            Agent ID si el token es válido, None si no
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            agent_id = payload.get("agent_id")
            
            if agent_id and agent_id in self.agents:
                return agent_id
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        
        return None
    
    def get_agent_permissions(self, agent_id: str) -> Dict[str, Any]:
        """
        Obtiene permisos de un agente
        
        Args:
            agent_id: ID del agente
        
        Returns:
            Diccionario con permisos del agente
        """
        if agent_id not in self.agents:
            return {}
        
        agent = self.agents[agent_id]
        return {
            "allowed_apis": agent.get("allowed_apis", []),
            "allowed_credentials": agent.get("allowed_credentials", []),
            "allowed_operations": agent.get("allowed_operations", [])
        }
    
    def is_api_allowed(self, agent_id: str, api_id: str) -> bool:
        """Verifica si un agente puede usar una API"""
        if agent_id not in self.agents:
            return False
        
        allowed_apis = self.agents[agent_id].get("allowed_apis", [])
        return len(allowed_apis) == 0 or api_id in allowed_apis  # Lista vacía = todas permitidas
    
    def is_credential_allowed(self, agent_id: str, credential_id: str) -> bool:
        """Verifica si un agente puede usar una credencial"""
        if agent_id not in self.agents:
            return False
        
        allowed_creds = self.agents[agent_id].get("allowed_credentials", [])
        return len(allowed_creds) == 0 or credential_id in allowed_creds
    
    def is_operation_allowed(self, agent_id: str, operation_type: str) -> bool:
        """Verifica si un agente puede usar una operación"""
        if agent_id not in self.agents:
            return False
        
        allowed_ops = self.agents[agent_id].get("allowed_operations", [])
        return len(allowed_ops) == 0 or operation_type in allowed_ops
    
    def filter_capabilities(
        self,
        agent_id: str,
        all_apis: Dict[str, Any],
        all_credentials: List[Dict[str, Any]],
        all_operations: List[str]
    ) -> Dict[str, Any]:
        """
        Filtra capacidades para un agente específico
        
        Args:
            agent_id: ID del agente
            all_apis: Todas las APIs disponibles
            all_credentials: Todas las credenciales disponibles
            all_operations: Todas las operaciones disponibles
        
        Returns:
            Capacidades filtradas para el agente
        """
        if agent_id not in self.agents:
            return {
                "availableApis": {},
                "availableCredentials": [],
                "supportedOperations": []
            }
        
        agent = self.agents[agent_id]
        allowed_apis = agent.get("allowed_apis", [])
        allowed_creds = agent.get("allowed_credentials", [])
        allowed_ops = agent.get("allowed_operations", [])
        
        # Filtrar APIs
        filtered_apis = {}
        if len(allowed_apis) == 0:
            filtered_apis = all_apis  # Todas permitidas
        else:
            for api_id in allowed_apis:
                if api_id in all_apis:
                    filtered_apis[api_id] = all_apis[api_id]
        
        # Filtrar credenciales
        filtered_credentials = []
        if len(allowed_creds) == 0:
            filtered_credentials = all_credentials  # Todas permitidas
        else:
            for cred in all_credentials:
                if cred.get("id") in allowed_creds:
                    filtered_credentials.append(cred)
        
        # Filtrar operaciones
        filtered_operations = []
        if len(allowed_ops) == 0:
            filtered_operations = all_operations  # Todas permitidas
        else:
            filtered_operations = [op for op in all_operations if op in allowed_ops]
        
        return {
            "availableApis": filtered_apis,
            "availableCredentials": filtered_credentials,
            "supportedOperations": filtered_operations
        }
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """Lista todos los agentes (sin API keys)"""
        return [
            {
                "id": agent["id"],
                "name": agent["name"],
                "allowed_apis": agent.get("allowed_apis", []),
                "allowed_credentials": agent.get("allowed_credentials", []),
                "allowed_operations": agent.get("allowed_operations", []),
                "created_at": agent.get("created_at"),
                "last_used": agent.get("last_used")
            }
            for agent in self.agents.values()
        ]


class AgentAuthMiddleware:
    """
    Middleware para validar autenticación en requests
    """
    
    def __init__(self, auth: AgentAuth):
        self.auth = auth
    
    def authenticate_request(self, headers: Dict[str, str]) -> Optional[str]:
        """
        Autentica un request desde headers
        
        Soporta:
        - X-API-Key: API key directa
        - Authorization: Bearer token (JWT)
        
        Args:
            headers: Headers del request
        
        Returns:
            Agent ID si autenticado, None si no
        """
        # Intentar API key
        api_key = headers.get("X-API-Key")
        if api_key:
            agent_id = self.auth.authenticate(api_key)
            if agent_id:
                return agent_id
        
        # Intentar JWT token
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            agent_id = self.auth.verify_token(token)
            if agent_id:
                return agent_id
        
        return None

