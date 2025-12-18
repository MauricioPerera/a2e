"""
CLI para gestión de la base de conocimiento de APIs
Permite a humanos definir qué APIs están disponibles
"""

import argparse
import json
import sys
from pathlib import Path

# Asumimos que el módulo está en el directorio padre
sys.path.insert(0, str(Path(__file__).parent.parent))
from api_knowledge_base import APIKnowledgeBase


def create_api(args):
    """Crea una nueva definición de API"""
    kb = APIKnowledgeBase()
    
    # Cargar APIs existentes si el archivo existe
    if Path(args.output).exists():
        kb.load_api_definitions(args.output)
    
    # Solicitar información
    api_id = args.id or input("API ID: ")
    base_url = args.base_url or input("Base URL: ")
    
    auth_type = args.auth_type or input("Authentication type (bearer/api-key/none) [none]: ") or "none"
    auth_config = {}
    if auth_type != "none":
        token_path = args.token_path or input("Token path in vault (e.g., /config/apiToken): ")
        auth_config = {
            "type": auth_type,
            "tokenPath": token_path
        }
    
    kb.add_api(
        api_id=api_id,
        base_url=base_url,
        endpoints=[],  # Se agregan con add-endpoint
        authentication=auth_config if auth_config else None
    )
    
    # Guardar
    save_kb(kb, args.output)
    print(f"✓ API '{api_id}' created")
    return 0


def add_endpoint(args):
    """Agrega un endpoint a una API"""
    kb = APIKnowledgeBase()
    
    # Cargar APIs existentes
    if not Path(args.api_file).exists():
        print(f"Error: API file '{args.api_file}' not found")
        return 1
    
    kb.load_api_definitions(args.api_file)
    
    # Solicitar información
    api_id = args.api_id or input("API ID: ")
    path = args.path or input("Endpoint path (e.g., /users): ")
    method = args.method or input("HTTP method (GET/POST/PUT/DELETE) [GET]: ") or "GET"
    description = args.description or input("Description: ")
    
    # Parámetros opcionales
    parameters = []
    if args.parameters:
        try:
            parameters = json.loads(args.parameters)
        except json.JSONDecodeError:
            print("Error: Invalid JSON for parameters")
            return 1
    
    kb.add_endpoint(
        api_id=api_id,
        endpoint_path=path,
        method=method,
        description=description,
        parameters=parameters
    )
    
    # Guardar
    save_kb(kb, args.api_file)
    print(f"✓ Endpoint {method} {path} added to API '{api_id}'")
    return 0


def list_apis(args):
    """Lista todas las APIs"""
    kb = APIKnowledgeBase()
    
    if not Path(args.api_file).exists():
        print(f"Error: API file '{args.api_file}' not found")
        return 1
    
    kb.load_api_definitions(args.api_file)
    
    apis = kb.get_available_apis()
    
    if not apis:
        print("No APIs found")
        return 0
    
    print(f"\nFound {len(apis)} APIs:\n")
    for api_id in apis:
        api_info = kb.get_api_info(api_id)
        print(f"API: {api_id}")
        print(f"  Base URL: {api_info['baseUrl']}")
        print(f"  Endpoints: {len(api_info.get('endpoints', []))}")
        if api_info.get('authentication'):
            print(f"  Auth: {api_info['authentication'].get('type', 'none')}")
        print()
    
    return 0


def show_api(args):
    """Muestra detalles de una API"""
    kb = APIKnowledgeBase()
    
    if not Path(args.api_file).exists():
        print(f"Error: API file '{args.api_file}' not found")
        return 1
    
    kb.load_api_definitions(args.api_file)
    api_info = kb.get_api_info(args.api_id)
    
    if not api_info:
        print(f"Error: API '{args.api_id}' not found")
        return 1
    
    print(f"\nAPI: {args.api_id}")
    print(f"Base URL: {api_info['baseUrl']}")
    if api_info.get('authentication'):
        print(f"Authentication: {json.dumps(api_info['authentication'], indent=2)}")
    print(f"\nEndpoints ({len(api_info.get('endpoints', []))}):")
    for ep in api_info.get('endpoints', []):
        print(f"  {ep['method']} {ep['path']}")
        print(f"    Description: {ep.get('description', 'N/A')}")
        if ep.get('parameters'):
            print(f"    Parameters: {len(ep['parameters'])}")
        print()
    
    return 0


def export_capabilities(args):
    """Exporta capacidades para el agente"""
    kb = APIKnowledgeBase()
    
    if not Path(args.api_file).exists():
        print(f"Error: API file '{args.api_file}' not found")
        return 1
    
    kb.load_api_definitions(args.api_file)
    catalog = kb.build_api_catalog_for_agent()
    
    output = {
        "workflowCapabilities": {
            "supportedOperations": list(kb.operations.keys()) if kb.operations else [],
            "availableApis": catalog["apis"],
            "securityConstraints": {
                "allowedDomains": kb._get_allowed_domains() if hasattr(kb, '_get_allowed_domains') else [],
                "maxExecutionTime": 30000,
                "maxOperations": 20
            }
        }
    }
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"✓ Capabilities exported to {args.output}")
    else:
        print(json.dumps(output, indent=2))
    
    return 0


def save_kb(kb: APIKnowledgeBase, output_path: str):
    """Guarda la base de conocimiento en un archivo JSON"""
    output = {
        "apis": kb.apis,
        "operations": kb.operations
    }
    
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="A2E API Knowledge Base CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new API
  python api_cli.py create --id user-api --base-url https://api.example.com --output apis.json

  # Add an endpoint
  python api_cli.py add-endpoint --api-file apis.json --api-id user-api --path /users --method GET

  # List all APIs
  python api_cli.py list --api-file apis.json

  # Export capabilities for agent
  python api_cli.py export-capabilities --api-file apis.json --output capabilities.json
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Create API command
    create_parser = subparsers.add_parser("create", help="Create a new API definition")
    create_parser.add_argument("--id", help="API ID")
    create_parser.add_argument("--base-url", help="Base URL")
    create_parser.add_argument("--auth-type", help="Authentication type (bearer/api-key/none)")
    create_parser.add_argument("--token-path", help="Token path in vault")
    create_parser.add_argument("--output", default="api_definitions.json", help="Output file")
    create_parser.set_defaults(func=create_api)
    
    # Add endpoint command
    add_ep_parser = subparsers.add_parser("add-endpoint", help="Add an endpoint to an API")
    add_ep_parser.add_argument("--api-file", required=True, help="API definitions file")
    add_ep_parser.add_argument("--api-id", help="API ID")
    add_ep_parser.add_argument("--path", help="Endpoint path")
    add_ep_parser.add_argument("--method", help="HTTP method")
    add_ep_parser.add_argument("--description", help="Description")
    add_ep_parser.add_argument("--parameters", help="Parameters as JSON array")
    add_ep_parser.set_defaults(func=add_endpoint)
    
    # List APIs command
    list_parser = subparsers.add_parser("list", help="List all APIs")
    list_parser.add_argument("--api-file", default="api_definitions.json", help="API definitions file")
    list_parser.set_defaults(func=list_apis)
    
    # Show API command
    show_parser = subparsers.add_parser("show", help="Show API details")
    show_parser.add_argument("--api-file", default="api_definitions.json", help="API definitions file")
    show_parser.add_argument("--api-id", required=True, help="API ID")
    show_parser.set_defaults(func=show_api)
    
    # Export capabilities command
    export_parser = subparsers.add_parser("export-capabilities", help="Export capabilities for agent")
    export_parser.add_argument("--api-file", default="api_definitions.json", help="API definitions file")
    export_parser.add_argument("--output", help="Output file (default: stdout)")
    export_parser.set_defaults(func=export_capabilities)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

