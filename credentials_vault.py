"""
Módulo de compatibilidad — redirige a vault.credentials_vault
"""

from vault.credentials_vault import *  # noqa: F401,F403
from vault.credentials_vault import CredentialsVault, CredentialInjector, CredentialCapabilitiesAnnouncer
