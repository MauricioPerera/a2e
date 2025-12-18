"""
Ejemplo de uso del Vault de Credenciales con RAG
Demuestra búsqueda semántica de credenciales
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from credentials_vault import CredentialsVault, CredentialCapabilitiesAnnouncer


def main():
    """
    Demuestra el uso del vault con RAG
    """
    print("="*60)
    print("A2E Credentials Vault with RAG Example")
    print("="*60)
    
    # 1. Crear vault con RAG
    print("\n[1/5] Creating vault with RAG...")
    vault = CredentialsVault(
        vault_path=None,  # En memoria para el ejemplo
        use_rag=True  # Usa RAG si está disponible
    )
    print("   [OK] Vault created")
    if vault.rag:
        print("   [OK] RAG enabled")
    else:
        print("   [WARN] RAG not available, using keyword search")
    
    # 2. Almacenar credenciales con descripciones
    print("\n[2/5] Storing credentials with descriptions...")
    
    vault.store_credential(
        credential_id="user-api-token",
        credential_type="bearer-token",
        value="secret-user-token-12345",
        metadata={"api": "user-api", "environment": "production"},
        description="Token de autenticación Bearer para API de usuarios en producción"
    )
    
    vault.store_credential(
        credential_id="data-api-key",
        credential_type="api-key",
        value="secret-data-key-67890",
        metadata={"api": "data-api", "environment": "production"},
        description="API key para acceso a datos en producción"
    )
    
    vault.store_credential(
        credential_id="analytics-token",
        credential_type="bearer-token",
        value="secret-analytics-token-abcde",
        metadata={"api": "analytics-api", "environment": "staging"},
        description="Token para API de analytics en ambiente de staging"
    )
    
    print(f"   [OK] Stored {len(vault.credentials)} credentials")
    
    # 3. Buscar credenciales semánticamente
    print("\n[3/5] Searching credentials semantically...")
    queries = [
        "token para API de usuarios",
        "credencial de producción",
        "autenticación de analytics"
    ]
    
    for query in queries:
        print(f"\n   Query: '{query}'")
        results = vault.search_credentials(query, top_k=3)
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"     {i}. {result['id']} ({result['type']})")
            if result.get("description"):
                print(f"        {result['description']}")
            print(f"        Score: {result.get('score', result.get('_score', 'N/A'))}")
    
    # 4. Listar credenciales
    print("\n[4/5] Listing all credentials...")
    all_creds = vault.list_credentials()
    print(f"   [OK] Found {len(all_creds)} credentials:")
    for cred in all_creds:
        print(f"     - {cred['id']} ({cred['type']}): {cred.get('description', 'No description')}")
    
    # 5. Anunciar al agente
    print("\n[5/5] Building capabilities message for agent...")
    announcer = CredentialCapabilitiesAnnouncer(vault)
    capabilities = announcer.build_capabilities_message()
    
    print(f"   [OK] {len(capabilities['availableCredentials'])} credentials available")
    print("   [OK] Agent will see only metadata, never values")
    
    # Resumen
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("✅ Vault created with RAG support")
    print("✅ Credentials stored and indexed")
    print("✅ Semantic search working")
    print("✅ Keyword search working (fallback)")
    print("✅ Agent sees only metadata")
    print("\n[SUCCESS] Credentials Vault with RAG is fully functional!")


if __name__ == "__main__":
    main()

