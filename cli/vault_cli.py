"""
CLI para gestión del vault de credenciales
Permite a humanos configurar credenciales de forma segura
"""

import argparse
import getpass
import json
import sys
from pathlib import Path
from typing import Optional

# Asumimos que el vault está en el directorio padre
sys.path.insert(0, str(Path(__file__).parent.parent))
from credentials_vault import CredentialsVault


def create_vault(args):
    """Crea un nuevo vault"""
    vault_path = args.vault_path or "credentials.vault.json"
    
    if Path(vault_path).exists() and not args.force:
        print(f"Error: Vault already exists at {vault_path}")
        print("Use --force to overwrite")
        return 1
    
    # Solicitar clave maestra
    master_key = getpass.getpass("Enter master key (or press Enter to generate): ")
    if not master_key:
        master_key = None
    else:
        master_key = master_key.encode()
    
    vault = CredentialsVault(master_key=master_key, vault_path=vault_path)
    print(f"✓ Vault created at {vault_path}")
    return 0


def add_credential(args):
    """Agrega una credencial al vault"""
    vault = CredentialsVault(vault_path=args.vault_path)
    
    # Solicitar valor de forma segura
    if args.value:
        value = args.value
    else:
        value = getpass.getpass(f"Enter value for '{args.id}': ")
    
    # Solicitar tipo si no se proporciona
    cred_type = args.type or "api-key"
    
    # Solicitar metadata
    metadata = {}
    if args.api:
        metadata["api"] = args.api
    if args.description:
        metadata["description"] = args.description
    
    vault.store_credential(
        credential_id=args.id,
        credential_type=cred_type,
        value=value,
        metadata=metadata
    )
    
    print(f"✓ Credential '{args.id}' stored successfully")
    return 0


def list_credentials(args):
    """Lista todas las credenciales (solo metadatos)"""
    vault = CredentialsVault(vault_path=args.vault_path)
    credentials = vault.list_credentials()
    
    if not credentials:
        print("No credentials found")
        return 0
    
    print(f"\nFound {len(credentials)} credentials:\n")
    for cred in credentials:
        print(f"ID: {cred['id']}")
        print(f"  Type: {cred['type']}")
        if cred.get('metadata'):
            print(f"  Metadata: {json.dumps(cred['metadata'], indent=4)}")
        print()
    
    return 0


def show_credential(args):
    """Muestra metadatos de una credencial (NO el valor)"""
    vault = CredentialsVault(vault_path=args.vault_path)
    metadata = vault.get_credential_metadata(args.id)
    
    if not metadata:
        print(f"Error: Credential '{args.id}' not found")
        return 1
    
    print(f"\nCredential: {metadata['id']}")
    print(f"Type: {metadata['type']}")
    print(f"Metadata: {json.dumps(metadata['metadata'], indent=2)}")
    print("\n⚠️  Value is encrypted and not displayed for security")
    
    return 0


def delete_credential(args):
    """Elimina una credencial"""
    vault = CredentialsVault(vault_path=args.vault_path)
    
    if args.id not in vault.credentials:
        print(f"Error: Credential '{args.id}' not found")
        return 1
    
    # Confirmar
    if not args.force:
        confirm = input(f"Are you sure you want to delete '{args.id}'? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cancelled")
            return 0
    
    vault.delete_credential(args.id)
    print(f"✓ Credential '{args.id}' deleted")
    return 0


def export_metadata(args):
    """Exporta metadatos de credenciales (sin valores) para el agente"""
    vault = CredentialsVault(vault_path=args.vault_path)
    credentials = vault.list_credentials()
    
    output = {
        "availableCredentials": [
            {
                "id": cred["id"],
                "type": cred["type"],
                "metadata": cred["metadata"]
            }
            for cred in credentials
        ]
    }
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"✓ Metadata exported to {args.output}")
    else:
        print(json.dumps(output, indent=2))
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="A2E Credentials Vault CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new vault
  python vault_cli.py create --vault-path my-vault.json

  # Add a credential
  python vault_cli.py add --id api-token --type bearer-token --api user-api

  # List all credentials
  python vault_cli.py list

  # Export metadata for agent
  python vault_cli.py export-metadata --output capabilities.json
        """
    )
    
    parser.add_argument(
        "--vault-path",
        default="credentials.vault.json",
        help="Path to vault file (default: credentials.vault.json)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new vault")
    create_parser.add_argument("--force", action="store_true", help="Overwrite existing vault")
    create_parser.set_defaults(func=create_vault)
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add a credential")
    add_parser.add_argument("--id", required=True, help="Credential ID")
    add_parser.add_argument("--type", help="Credential type (bearer-token, api-key, password, etc.)")
    add_parser.add_argument("--value", help="Credential value (or will prompt securely)")
    add_parser.add_argument("--api", help="Associated API name")
    add_parser.add_argument("--description", help="Description")
    add_parser.set_defaults(func=add_credential)
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all credentials")
    list_parser.set_defaults(func=list_credentials)
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show credential metadata")
    show_parser.add_argument("--id", required=True, help="Credential ID")
    show_parser.set_defaults(func=show_credential)
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a credential")
    delete_parser.add_argument("--id", required=True, help="Credential ID")
    delete_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    delete_parser.set_defaults(func=delete_credential)
    
    # Export metadata command
    export_parser = subparsers.add_parser("export-metadata", help="Export credentials metadata for agent")
    export_parser.add_argument("--output", help="Output file (default: stdout)")
    export_parser.set_defaults(func=export_metadata)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

