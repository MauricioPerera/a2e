"""
Vault de credenciales mejorado con LokiJS y RAG
Permite búsqueda semántica de credenciales por descripción y metadatos
"""

import json
import logging
import base64
from typing import Dict, Any, Optional, List
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os

try:
    from rag_integration import A2ERAGSystem
except ImportError:
    A2ERAGSystem = None

logger = logging.getLogger(__name__)


class CredentialsVaultRAG:
    """
    Vault de credenciales con LokiJS y RAG
    Permite búsqueda semántica de credenciales sin exponer valores
    """
    
    def __init__(
        self,
        master_key: Optional[bytes] = None,
        vault_path: Optional[str] = None,
        rag_system: Optional[Any] = None,
        use_rag: bool = True
    ):
        """
        Inicializa el vault con RAG
        
        Args:
            master_key: Clave maestra para encriptar
            vault_path: Ruta al archivo del vault
            rag_system: Sistema RAG (se crea uno nuevo si es None y use_rag=True)
            use_rag: Si usar RAG para búsqueda semántica
        """
        self.vault_path = vault_path
        self.credentials: Dict[str, Dict[str, Any]] = {}
        self.use_rag = use_rag
        
        # Generar o usar clave maestra
        if master_key:
            self.master_key = master_key
        else:
            self.master_key = self._generate_master_key()
        
        self.cipher = Fernet(self._derive_key(self.master_key))
        
        # Inicializar RAG si está disponible
        if use_rag:
            if A2ERAGSystem is None:
                logger.warning("RAG system not available. Credential search will use keywords only.")
                self.use_rag = False
                self.rag = None
            else:
                self.rag = rag_system or A2ERAGSystem()
        else:
            self.rag = None
        
        # Cargar vault si existe
        if vault_path and Path(vault_path).exists():
            self.load_vault()
    
    def _generate_master_key(self) -> bytes:
        """Genera una clave maestra"""
        return Fernet.generate_key()
    
    def _derive_key(self, master_key: bytes) -> bytes:
        """Deriva una clave de encriptación desde la clave maestra"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'a2ui_vault_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key))
        return key
    
    def store_credential(
        self,
        credential_id: str,
        credential_type: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None,
        description: str = ""
    ):
        """
        Almacena una credencial de forma encriptada
        También la indexa en RAG para búsqueda semántica
        
        Args:
            credential_id: ID único de la credencial
            credential_type: Tipo (ej: "bearer-token", "api-key")
            value: Valor de la credencial (se encripta)
            metadata: Metadatos adicionales (no se encriptan)
            description: Descripción de la credencial (para búsqueda semántica)
        """
        # Encriptar valor
        encrypted_value = self.cipher.encrypt(value.encode())
        
        credential_data = {
            "id": credential_id,
            "type": credential_type,
            "encryptedValue": base64.b64encode(encrypted_value).decode(),
            "metadata": metadata or {},
            "description": description
        }
        
        self.credentials[credential_id] = credential_data
        
        # Indexar en RAG si está habilitado (solo metadatos, nunca el valor)
        if self.use_rag and self.rag:
            # Crear texto para embedding (sin el valor real)
            text = f"{credential_type} credential: {description}"
            if metadata:
                for key, val in metadata.items():
                    if isinstance(val, str) and len(val) < 100:
                        text += f" {key}: {val}"
            
            # Indexar como conocimiento (sin el valor encriptado)
            self.rag.index_knowledge(
                knowledge_id=f"credential-{credential_id}",
                knowledge_type="credential",
                content={
                    "id": credential_id,
                    "type": credential_type,
                    "metadata": metadata or {},
                    "description": description
                    # NO incluir encryptedValue
                },
                description=description or f"{credential_type} credential for {credential_id}"
            )
        
        logger.info(f"Stored credential: {credential_id} (type: {credential_type})")
        
        # Guardar vault
        if self.vault_path:
            self.save_vault()
    
    def get_credential(self, credential_id: str) -> Optional[str]:
        """
        Obtiene y desencripta una credencial
        
        Args:
            credential_id: ID de la credencial
        
        Returns:
            Valor desencriptado o None si no existe
        """
        if credential_id not in self.credentials:
            return None
        
        cred = self.credentials[credential_id]
        encrypted_value = base64.b64decode(cred["encryptedValue"])
        decrypted_value = self.cipher.decrypt(encrypted_value)
        return decrypted_value.decode()
    
    def search_credentials(
        self,
        query: str,
        credential_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca credenciales relevantes usando búsqueda semántica o keywords
        Retorna solo metadatos, nunca valores
        
        Args:
            query: Query de búsqueda
            credential_type: Filtrar por tipo (opcional)
            top_k: Número de resultados
        
        Returns:
            Lista de credenciales relevantes (solo metadatos)
        """
        # Usar RAG si está habilitado
        if self.use_rag and self.rag:
            results = self.rag.search_knowledge(
                query=query,
                knowledge_type="credential",
                top_k=top_k * 2
            )
            
            # Filtrar por tipo si se especifica
            if credential_type:
                results = [r for r in results if r.get("content", {}).get("type") == credential_type]
            
            # Convertir a formato de credencial (sin valores)
            credentials = []
            for result in results[:top_k]:
                content = result.get("content", {})
                cred_id = content.get("id")
                if cred_id and cred_id in self.credentials:
                    cred = self.credentials[cred_id]
                    credentials.append({
                        "id": cred_id,
                        "type": cred["type"],
                        "metadata": cred.get("metadata", {}),
                        "description": cred.get("description", ""),
                        "score": result.get("score", 0)
                    })
            
            return credentials
        
        # Fallback a búsqueda por keywords
        results = []
        for cred_id, cred in self.credentials.items():
            # Filtrar por tipo si se especifica
            if credential_type and cred["type"] != credential_type:
                continue
            
            # Búsqueda por keywords
            description = cred.get("description", "").lower()
            metadata_str = str(cred.get("metadata", {})).lower()
            
            query_lower = query.lower()
            score = 0
            
            for word in query_lower.split():
                if word in description:
                    score += 3
                if word in metadata_str:
                    score += 2
                if word in cred_id.lower():
                    score += 1
            
            if score > 0:
                results.append({
                    "id": cred_id,
                    "type": cred["type"],
                    "metadata": cred.get("metadata", {}),
                    "description": cred.get("description", ""),
                    "_score": score
                })
        
        results.sort(key=lambda x: x.get("_score", x.get("score", 0)), reverse=True)
        return results[:top_k]
    
    def list_credentials(self) -> List[Dict[str, Any]]:
        """
        Lista todas las credenciales (solo metadatos, nunca valores)
        
        Returns:
            Lista de credenciales con metadatos
        """
        return [
            {
                "id": cred_id,
                "type": cred["type"],
                "metadata": cred.get("metadata", {}),
                "description": cred.get("description", "")
            }
            for cred_id, cred in self.credentials.items()
        ]
    
    def save_vault(self):
        """Guarda el vault encriptado"""
        if not self.vault_path:
            return
        
        vault_data = {
            "credentials": self.credentials,
            "version": "1.0"
        }
        
        with open(self.vault_path, "w", encoding="utf-8") as f:
            json.dump(vault_data, f, indent=2)
        
        logger.info(f"Vault saved to {self.vault_path}")
    
    def load_vault(self):
        """Carga el vault desde archivo"""
        if not self.vault_path or not Path(self.vault_path).exists():
            return
        
        with open(self.vault_path, "r", encoding="utf-8") as f:
            vault_data = json.load(f)
        
        self.credentials = vault_data.get("credentials", {})
        
        # Re-indexar en RAG si está habilitado
        if self.use_rag and self.rag:
            for cred_id, cred in self.credentials.items():
                description = cred.get("description", "")
                metadata = cred.get("metadata", {})
                
                text = f"{cred['type']} credential: {description}"
                if metadata:
                    for key, val in metadata.items():
                        if isinstance(val, str) and len(val) < 100:
                            text += f" {key}: {val}"
                
                self.rag.index_knowledge(
                    knowledge_id=f"credential-{cred_id}",
                    knowledge_type="credential",
                    content={
                        "id": cred_id,
                        "type": cred["type"],
                        "metadata": metadata,
                        "description": description
                    },
                    description=description or f"{cred['type']} credential for {cred_id}"
                )
        
        logger.info(f"Loaded {len(self.credentials)} credentials from vault")


class CredentialInjector:
    """
    Inyecta credenciales en operaciones
    Reemplaza referencias por valores reales (desencriptados)
    """
    
    def __init__(self, vault: CredentialsVaultRAG):
        self.vault = vault
    
    def inject_into_operation(
        self,
        operation_config: Dict[str, Any],
        operation_type: str
    ) -> Dict[str, Any]:
        """
        Inyecta credenciales en una configuración de operación
        
        Args:
            operation_config: Configuración de la operación
            operation_type: Tipo de operación (ej: "ApiCall")
        
        Returns:
            Configuración con credenciales inyectadas
        """
        config = operation_config.copy()
        
        # Para ApiCall, inyectar en headers
        if operation_type == "ApiCall":
            headers = config.get("headers", {})
            injected_headers = self._inject_into_dict(headers)
            if injected_headers:
                config["headers"] = injected_headers
        
        return config
    
    def _inject_into_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Inyecta credenciales recursivamente en un diccionario"""
        result = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                if "credentialRef" in value:
                    # Referencia a credencial
                    cred_id = value["credentialRef"].get("id")
                    if cred_id:
                        cred_value = self.vault.get_credential(cred_id)
                        if cred_value:
                            # Formatear según tipo
                            cred = self.vault.credentials[cred_id]
                            cred_type = cred["type"]
                            
                            if cred_type == "bearer-token":
                                result[key] = f"Bearer {cred_value}"
                            elif cred_type == "api-key":
                                result[key] = cred_value
                            else:
                                result[key] = cred_value
                        else:
                            raise ValueError(f"Credential {cred_id} not found")
                    else:
                        result[key] = value
                else:
                    # Recursión
                    result[key] = self._inject_into_dict(value)
            elif isinstance(value, list):
                result[key] = [self._inject_into_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                result[key] = value
        
        return result


class CredentialCapabilitiesAnnouncer:
    """
    Anuncia credenciales disponibles al agente (solo metadatos, nunca valores)
    """
    
    def __init__(self, vault: CredentialsVaultRAG):
        self.vault = vault
    
    def build_capabilities_message(self) -> Dict[str, Any]:
        """
        Construye mensaje de capacidades con credenciales disponibles
        
        Returns:
            Mensaje con credenciales (solo metadatos)
        """
        credentials = self.vault.list_credentials()
        
        return {
            "availableCredentials": [
                {
                    "id": cred["id"],
                    "type": cred["type"],
                    "metadata": cred.get("metadata", {}),
                    "description": cred.get("description", ""),
                    "usage": self._get_usage_instruction(cred["type"])
                }
                for cred in credentials
            ]
        }
    
    def _get_usage_instruction(self, cred_type: str) -> str:
        """Genera instrucción de uso para el tipo de credencial"""
        if cred_type == "bearer-token":
            return "Use in Authorization header: {'credentialRef': {'id': '<id>'}}"
        elif cred_type == "api-key":
            return "Use in headers or query params: {'credentialRef': {'id': '<id>'}}"
        else:
            return "Use as value: {'credentialRef': {'id': '<id>'}}"

