"""
Wizard interactivo para configurar A2E
Guía a un humano a través de la configuración inicial
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from credentials_vault import CredentialsVault
from api_knowledge_base import APIKnowledgeBase


def print_header(title):
    """Imprime un encabezado"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")


def setup_vault():
    """Configura el vault de credenciales"""
    print_header("Credentials Vault Setup")
    
    vault_path = input("Vault file path [credentials.vault.json]: ") or "credentials.vault.json"
    
    if Path(vault_path).exists():
        overwrite = input(f"Vault '{vault_path}' exists. Overwrite? (yes/no) [no]: ") or "no"
        if overwrite.lower() != "yes":
            print("Using existing vault")
            return vault_path
    
    print("\nCreating new vault...")
    master_key = input("Enter master key (or press Enter to auto-generate): ")
    master_key = master_key.encode() if master_key else None
    
    vault = CredentialsVault(master_key=master_key, vault_path=vault_path)
    print(f"✓ Vault created at {vault_path}")
    
    # Agregar credenciales iniciales
    add_creds = input("\nAdd credentials now? (yes/no) [yes]: ") or "yes"
    if add_creds.lower() == "yes":
        while True:
            cred_id = input("\nCredential ID (or 'done' to finish): ")
            if cred_id.lower() == "done":
                break
            
            cred_type = input("Type (bearer-token/api-key/password) [api-key]: ") or "api-key"
            cred_value = input(f"Value for '{cred_id}': ")
            cred_api = input("Associated API (optional): ") or None
            cred_desc = input("Description (optional): ") or None
            
            metadata = {}
            if cred_api:
                metadata["api"] = cred_api
            if cred_desc:
                metadata["description"] = cred_desc
            
            vault.store_credential(
                credential_id=cred_id,
                credential_type=cred_type,
                value=cred_value,
                metadata=metadata
            )
            print(f"✓ Credential '{cred_id}' stored")
    
    return vault_path


def setup_apis():
    """Configura la base de conocimiento de APIs"""
    print_header("API Knowledge Base Setup")
    
    api_file = input("API definitions file [api_definitions.json]: ") or "api_definitions.json"
    
    kb = APIKnowledgeBase()
    
    # Cargar existentes si hay
    if Path(api_file).exists():
        kb.load_api_definitions(api_file)
        print(f"✓ Loaded existing APIs from {api_file}")
    
    # Agregar APIs
    add_apis = input("\nAdd APIs now? (yes/no) [yes]: ") or "yes"
    if add_apis.lower() == "yes":
        while True:
            api_id = input("\nAPI ID (or 'done' to finish): ")
            if api_id.lower() == "done":
                break
            
            base_url = input("Base URL: ")
            
            auth_type = input("Authentication type (bearer/api-key/none) [none]: ") or "none"
            auth_config = {}
            if auth_type != "none":
                token_path = input("Token path in vault (e.g., /config/apiToken): ")
                auth_config = {
                    "type": auth_type,
                    "tokenPath": token_path
                }
            
            kb.add_api(
                api_id=api_id,
                base_url=base_url,
                endpoints=[],
                authentication=auth_config if auth_config else None
            )
            print(f"✓ API '{api_id}' created")
            
            # Agregar endpoints
            add_endpoints = input("Add endpoints for this API? (yes/no) [yes]: ") or "yes"
            if add_endpoints.lower() == "yes":
                while True:
                    ep_path = input("\n  Endpoint path (or 'done' to finish): ")
                    if ep_path.lower() == "done":
                        break
                    
                    ep_method = input("  HTTP method (GET/POST/PUT/DELETE) [GET]: ") or "GET"
                    ep_desc = input("  Description: ")
                    
                    kb.add_endpoint(
                        api_id=api_id,
                        endpoint_path=ep_path,
                        method=ep_method,
                        description=ep_desc
                    )
                    print(f"  ✓ Endpoint {ep_method} {ep_path} added")
    
    # Guardar
    output = {
        "apis": kb.apis,
        "operations": kb.operations
    }
    with open(api_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n✓ APIs saved to {api_file}")
    
    return api_file


def generate_config():
    """Genera archivo de configuración principal"""
    print_header("Configuration File Generation")
    
    config_file = input("Config file path [a2e_config.json]: ") or "a2e_config.json"
    
    vault_path = input("Vault path [credentials.vault.json]: ") or "credentials.vault.json"
    api_file = input("API definitions file [api_definitions.json]: ") or "api_definitions.json"
    
    config = {
        "vault": {
            "path": vault_path
        },
        "apiKnowledgeBase": {
            "path": api_file
        },
        "security": {
            "maxExecutionTime": 30000,
            "maxOperations": 20,
            "allowedDomains": []
        },
        "rag": {
            "enabled": True,
            "topK": 5
        }
    }
    
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✓ Configuration saved to {config_file}")
    return config_file


def main():
    print("="*60)
    print("  A2E Configuration Wizard")
    print("  Agent-to-Execution Setup")
    print("="*60)
    print("\nThis wizard will guide you through setting up A2E:")
    print("  1. Credentials Vault")
    print("  2. API Knowledge Base")
    print("  3. Configuration File")
    print("\nPress Ctrl+C at any time to cancel.\n")
    
    try:
        # Setup vault
        vault_path = setup_vault()
        
        # Setup APIs
        api_file = setup_apis()
        
        # Generate config
        config_file = generate_config()
        
        print_header("Setup Complete!")
        print(f"✓ Vault: {vault_path}")
        print(f"✓ APIs: {api_file}")
        print(f"✓ Config: {config_file}")
        print("\nYou can now start using A2E!")
        print("\nNext steps:")
        print("  1. Review the configuration files")
        print("  2. Start the A2E executor")
        print("  3. Connect your agent to use A2E")
        
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

