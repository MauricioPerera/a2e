"""
Vault module — almacenamiento seguro de credenciales
"""

from .credentials_vault import CredentialsVault, CredentialInjector, CredentialCapabilitiesAnnouncer

__all__ = [
    'CredentialsVault',
    'CredentialInjector',
    'CredentialCapabilitiesAnnouncer',
]
