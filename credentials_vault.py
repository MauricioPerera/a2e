"""
Vault de credenciales seguro para workflows
El agente puede referenciar credenciales por ID, pero nunca ver los valores

Ahora con soporte opcional para LokiJS y RAG para búsqueda semántica
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


class CredentialsVault:
    """
    Vault seguro para almacenar credenciales
    El agente puede referenciar credenciales, pero nunca ver los valores
    
    Soporta opcionalmente RAG con LokiJS para búsqueda semántica
    """
    
    def __init__(
        self,
        master_key: Optional[bytes] = None,
        vault_path: Optional[str] = None,
        rag_system: Optional[Any] = None,
        use_rag: bool = True
    ):
        """
        Inicializa el vault
        
        Args:
            master_key: Clave maestra para encriptar (si None, genera una)
            vault_path: Ruta al archivo del vault (si None, usa memoria)
            rag_system: Sistema RAG para búsqueda semántica (opcional)
            use_rag: Si usar RAG para búsqueda semántica (por defecto True si está disponible)
        """
        self.vault_path = vault_path
        self.credentials: Dict[str, Dict[str, Any]] = {}
        self.use_rag = use_rag
        
        # Generar o usar clave maestra
        if master_key:
            self.master_key = master_key
        else:
            # En producción, esto debería venir de una variable de entorno
            # o de un sistema de gestión de secretos
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
        """
        Genera una clave maestra (en producción, usar sistema de gestión de secretos)
        """
        return Fernet.generate_key()
    
    def _derive_key(self, master_key: bytes) -> bytes:
        """
        Deriva una clave de encriptación desde la clave maestra
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'a2ui_vault_salt',  # En producción, usar salt único por vault
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
        También la indexa en RAG si está habilitado (solo metadatos, nunca el valor)
        
        Args:
            credential_id: ID único de la credencial (ej: "api-token", "db-password")
            credential_type: Tipo (ej: "bearer-token", "api-key", "password")
            value: Valor de la credencial (se encripta)
            metadata: Metadatos adicionales (no se encriptan, ej: "api": "user-api")
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
        
        # Indexar en RAG si está habilitado (solo metadatos, NUNCA el valor)
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
        SOLO el cliente puede llamar esto, el agente NO
        """
        if credential_id not in self.credentials:
            logger.warning(f"Credential {credential_id} not found")
            return None
        
        cred = self.credentials[credential_id]
        encrypted_value = base64.b64decode(cred["encryptedValue"])
        decrypted_value = self.cipher.decrypt(encrypted_value)
        
        return decrypted_value.decode()
    
    def get_credential_metadata(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene metadatos de una credencial (sin desencriptar el valor)
        El agente puede usar esto para saber qué credenciales están disponibles
        """
        if credential_id not in self.credentials:
            return None
        
        cred = self.credentials[credential_id]
        return {
            "id": cred["id"],
            "type": cred["type"],
            "metadata": cred["metadata"]
        }
    
    def list_credentials(self) -> List[Dict[str, Any]]:
        """
        Lista todas las credenciales (solo metadatos, sin valores)
        El agente puede usar esto para saber qué credenciales están disponibles
        """
        return [
            {
                "id": cred["id"],
                "type": cred["type"],
                "metadata": cred.get("metadata", {}),
                "description": cred.get("description", "")
            }
            for cred in self.credentials.values()
        ]
    
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
        
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results[:top_k]
    
    def delete_credential(self, credential_id: str):
        """
        Elimina una credencial del vault
        """
        if credential_id in self.credentials:
            del self.credentials[credential_id]
            logger.info(f"Deleted credential: {credential_id}")
            
            if self.vault_path:
                self.save_vault()
    
    def resolve_credential_reference(self, reference: Dict[str, Any]) -> Optional[str]:
        """
        Resuelve una referencia a credencial desde el workflow
        
        El agente puede enviar:
        {"credentialRef": {"id": "api-token"}}
        
        El cliente resuelve esto a el valor real (sin que el agente lo vea)
        """
        if "credentialRef" not in reference:
            return None
        
        cred_id = reference["credentialRef"].get("id")
        if not cred_id:
            return None
        
        return self.get_credential(cred_id)
    
    def save_vault(self):
        """
        Guarda el vault encriptado en disco
        """
        if not self.vault_path:
            return
        
        vault_data = {
            "credentials": self.credentials
        }
        
        with open(self.vault_path, "w", encoding="utf-8") as f:
            json.dump(vault_data, f, indent=2)
        
        logger.info(f"Saved vault to {self.vault_path}")
    
    def load_vault(self):
        """
        Carga el vault desde disco
        También re-indexa en RAG si está habilitado
        """
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
    Inyecta credenciales en operaciones del workflow
    """
    
    def __init__(self, vault: CredentialsVault):
        self.vault = vault
    
    def inject_into_operation(
        self,
        operation_config: Dict[str, Any],
        operation_type: str
    ) -> Dict[str, Any]:
        """
        Inyecta credenciales en la configuración de una operación
        """
        config = operation_config.copy()
        
        if operation_type == "ApiCall":
            # Inyectar en headers si hay referencia a credencial
            headers = config.get("headers", {})
            
            # Buscar referencias a credenciales
            for key, value in headers.items():
                if isinstance(value, dict) and "credentialRef" in value:
                    cred_value = self.vault.resolve_credential_reference(value)
                    if cred_value:
                        # Formatear según tipo de credencial
                        cred_metadata = self.vault.get_credential_metadata(
                            value["credentialRef"]["id"]
                        )
                        cred_type = cred_metadata.get("type") if cred_metadata else None
                        
                        if cred_type == "bearer-token":
                            headers[key] = f"Bearer {cred_value}"
                        elif cred_type == "api-key":
                            headers[key] = cred_value
                        else:
                            headers[key] = cred_value
            
            config["headers"] = headers
        
        return config


class CredentialCapabilitiesAnnouncer:
    """
    Anuncia qué credenciales están disponibles (solo metadatos)
    """
    
    def __init__(self, vault: CredentialsVault):
        self.vault = vault
    
    def build_capabilities_message(self) -> Dict[str, Any]:
        """
        Construye mensaje de capacidades de credenciales
        Solo incluye metadatos, NUNCA valores
        """
        credentials = self.vault.list_credentials()
        
        return {
            "availableCredentials": [
                {
                    "id": cred["id"],
                    "type": cred["type"],
                    "metadata": cred.get("metadata", {}),
                    "description": cred.get("description", ""),
                    "usage": self._get_usage_hint(cred["type"])
                }
                for cred in credentials
            ]
        }
    
    def _get_usage_hint(self, cred_type: str) -> str:
        """
        Retorna pista de uso para el agente
        """
        hints = {
            "bearer-token": "Use in Authorization header: {'credentialRef': {'id': '...'}}",
            "api-key": "Use in X-API-Key header: {'credentialRef': {'id': '...'}}",
            "password": "Use for database connections or basic auth",
            "username": "Use with password for basic auth"
        }
        return hints.get(cred_type, "Reference using {'credentialRef': {'id': '...'}}")


# Ejemplo de uso
def main():
    # Crear vault
    vault = CredentialsVault(vault_path="credentials.vault.json")
    
    # Almacenar credenciales (solo el cliente hace esto)
    vault.store_credential(
        credential_id="user-api-token",
        credential_type="bearer-token",
        value="secret-api-token-12345",
        metadata={"api": "user-api", "description": "Token para API de usuarios"}
    )
    
    vault.store_credential(
        credential_id="db-password",
        credential_type="password",
        value="super-secret-password",
        metadata={"database": "main-db"}
    )
    
    # Agente puede ver metadatos (sin valores)
    capabilities = CredentialCapabilitiesAnnouncer(vault)
    message = capabilities.build_capabilities_message()
    print("Capacidades anunciadas al agente:")
    print(json.dumps(message, indent=2))
    
    # Agente genera workflow con referencia
    workflow_config = {
        "headers": {
            "Authorization": {
                "credentialRef": {"id": "user-api-token"}
            }
        }
    }
    
    # Cliente inyecta credencial real
    injector = CredentialInjector(vault)
    injected = injector.inject_into_operation(workflow_config, "ApiCall")
    print("\nConfiguración después de inyección:")
    print(json.dumps(injected, indent=2))
    # Resultado: {"headers": {"Authorization": "Bearer secret-api-token-12345"}}


if __name__ == "__main__":
    main()

