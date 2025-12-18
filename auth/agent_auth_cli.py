"""
CLI para gestión de autenticación y autorización de agentes
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth.agent_auth import AgentAuth


def register_agent(args):
    """Registra un nuevo agente"""
    auth = AgentAuth(config_path=args.config)
    
    # Cargar permisos desde archivo si se proporciona
    allowed_apis = args.allowed_apis.split(",") if args.allowed_apis else []
    allowed_credentials = args.allowed_credentials.split(",") if args.allowed_credentials else []
    allowed_operations = args.allowed_operations.split(",") if args.allowed_operations else []
    
    # Filtrar listas vacías
    allowed_apis = [a.strip() for a in allowed_apis if a.strip()]
    allowed_credentials = [c.strip() for c in allowed_credentials if c.strip()]
    allowed_operations = [o.strip() for o in allowed_operations if o.strip()]
    
    api_key = auth.register_agent(
        agent_id=args.id,
        name=args.name,
        allowed_apis=allowed_apis if allowed_apis else None,
        allowed_credentials=allowed_credentials if allowed_credentials else None,
        allowed_operations=allowed_operations if allowed_operations else None,
        metadata={"description": args.description} if args.description else None
    )
    
    print(f"✓ Agent '{args.id}' registered")
    print(f"\nAPI Key: {api_key}")
    print("\n⚠️  Save this API key securely. It cannot be retrieved later.")
    print("\nTo use this API key:")
    print(f"  - Header: X-API-Key: {api_key}")
    print(f"  - Or generate JWT token: python agent_auth_cli.py generate-token --id {args.id}")
    
    return 0


def list_agents(args):
    """Lista todos los agentes"""
    auth = AgentAuth(config_path=args.config)
    agents = auth.list_agents()
    
    if not agents:
        print("No agents registered")
        return 0
    
    print(f"\nRegistered Agents ({len(agents)}):\n")
    for agent in agents:
        print(f"ID: {agent['id']}")
        print(f"  Name: {agent['name']}")
        print(f"  Allowed APIs: {len(agent['allowed_apis'])} ({'all' if not agent['allowed_apis'] else ', '.join(agent['allowed_apis'])})")
        print(f"  Allowed Credentials: {len(agent['allowed_credentials'])} ({'all' if not agent['allowed_credentials'] else ', '.join(agent['allowed_credentials'])})")
        print(f"  Allowed Operations: {len(agent['allowed_operations'])} ({'all' if not agent['allowed_operations'] else ', '.join(agent['allowed_operations'])})")
        print(f"  Created: {agent.get('created_at', 'N/A')}")
        print(f"  Last Used: {agent.get('last_used', 'Never')}")
        print()
    
    return 0


def show_agent(args):
    """Muestra detalles de un agente"""
    auth = AgentAuth(config_path=args.config)
    agents = auth.list_agents()
    
    agent = next((a for a in agents if a['id'] == args.id), None)
    if not agent:
        print(f"Error: Agent '{args.id}' not found")
        return 1
    
    print(f"\nAgent: {args.id}")
    print("="*60)
    print(f"Name: {agent['name']}")
    print(f"\nPermissions:")
    print(f"  Allowed APIs: {agent['allowed_apis'] if agent['allowed_apis'] else 'ALL'}")
    print(f"  Allowed Credentials: {agent['allowed_credentials'] if agent['allowed_credentials'] else 'ALL'}")
    print(f"  Allowed Operations: {agent['allowed_operations'] if agent['allowed_operations'] else 'ALL'}")
    print(f"\nMetadata:")
    print(f"  Created: {agent.get('created_at', 'N/A')}")
    print(f"  Last Used: {agent.get('last_used', 'Never')}")
    
    return 0


def update_permissions(args):
    """Actualiza permisos de un agente"""
    auth = AgentAuth(config_path=args.config)
    
    if args.id not in auth.agents:
        print(f"Error: Agent '{args.id}' not found")
        return 1
    
    agent = auth.agents[args.id]
    
    # Actualizar permisos
    if args.allowed_apis:
        agent["allowed_apis"] = [a.strip() for a in args.allowed_apis.split(",") if a.strip()]
    if args.allowed_credentials:
        agent["allowed_credentials"] = [c.strip() for c in args.allowed_credentials.split(",") if c.strip()]
    if args.allowed_operations:
        agent["allowed_operations"] = [o.strip() for o in args.allowed_operations.split(",") if o.strip()]
    
    auth.save_config()
    print(f"✓ Permissions updated for agent '{args.id}'")
    
    return 0


def generate_token(args):
    """Genera un token JWT para un agente"""
    auth = AgentAuth(config_path=args.config)
    
    if args.id not in auth.agents:
        print(f"Error: Agent '{args.id}' not found")
        return 1
    
    token = auth.generate_token(args.id, expires_in_hours=args.expires_in)
    
    print(f"✓ Token generated for agent '{args.id}'")
    print(f"\nToken: {token}")
    print(f"\nTo use this token:")
    print(f"  Authorization: Bearer {token}")
    print(f"\nToken expires in {args.expires_in} hours")
    
    return 0


def test_auth(args):
    """Prueba autenticación"""
    auth = AgentAuth(config_path=args.config)
    
    # Intentar autenticar con API key
    if args.api_key:
        agent_id = auth.authenticate(args.api_key)
        if agent_id:
            print(f"✓ Authentication successful")
            print(f"Agent ID: {agent_id}")
            permissions = auth.get_agent_permissions(agent_id)
            print(f"\nPermissions:")
            print(f"  APIs: {permissions['allowed_apis'] if permissions['allowed_apis'] else 'ALL'}")
            print(f"  Credentials: {permissions['allowed_credentials'] if permissions['allowed_credentials'] else 'ALL'}")
            print(f"  Operations: {permissions['allowed_operations'] if permissions['allowed_operations'] else 'ALL'}")
            return 0
        else:
            print("✗ Authentication failed: Invalid API key")
            return 1
    
    # Intentar autenticar con token
    if args.token:
        agent_id = auth.verify_token(args.token)
        if agent_id:
            print(f"✓ Token verification successful")
            print(f"Agent ID: {agent_id}")
            return 0
        else:
            print("✗ Token verification failed: Invalid or expired token")
            return 1
    
    print("Error: Provide either --api-key or --token")
    return 1


def main():
    parser = argparse.ArgumentParser(
        description="A2E Agent Authentication CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Register a new agent
  python agent_auth_cli.py register --id agent-123 --name "My Agent" --allowed-apis "user-api,product-api"

  # List all agents
  python agent_auth_cli.py list

  # Generate JWT token
  python agent_auth_cli.py generate-token --id agent-123

  # Test authentication
  python agent_auth_cli.py test --api-key <api-key>
        """
    )
    
    parser.add_argument(
        "--config",
        default="agent_auth.json",
        help="Agent auth config file (default: agent_auth.json)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Register a new agent")
    register_parser.add_argument("--id", required=True, help="Agent ID")
    register_parser.add_argument("--name", required=True, help="Agent name")
    register_parser.add_argument("--allowed-apis", help="Comma-separated list of allowed API IDs (empty = all)")
    register_parser.add_argument("--allowed-credentials", help="Comma-separated list of allowed credential IDs (empty = all)")
    register_parser.add_argument("--allowed-operations", help="Comma-separated list of allowed operations (empty = all)")
    register_parser.add_argument("--description", help="Agent description")
    register_parser.set_defaults(func=register_agent)
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all agents")
    list_parser.set_defaults(func=list_agents)
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show agent details")
    show_parser.add_argument("--id", required=True, help="Agent ID")
    show_parser.set_defaults(func=show_agent)
    
    # Update permissions command
    update_parser = subparsers.add_parser("update-permissions", help="Update agent permissions")
    update_parser.add_argument("--id", required=True, help="Agent ID")
    update_parser.add_argument("--allowed-apis", help="Comma-separated list of allowed API IDs")
    update_parser.add_argument("--allowed-credentials", help="Comma-separated list of allowed credential IDs")
    update_parser.add_argument("--allowed-operations", help="Comma-separated list of allowed operations")
    update_parser.set_defaults(func=update_permissions)
    
    # Generate token command
    token_parser = subparsers.add_parser("generate-token", help="Generate JWT token for agent")
    token_parser.add_argument("--id", required=True, help="Agent ID")
    token_parser.add_argument("--expires-in", type=int, default=24, help="Expiration in hours (default: 24)")
    token_parser.set_defaults(func=generate_token)
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test authentication")
    test_parser.add_argument("--api-key", help="API key to test")
    test_parser.add_argument("--token", help="JWT token to test")
    test_parser.set_defaults(func=test_auth)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

