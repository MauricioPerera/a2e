"""
CLI para gestionar bases de conocimiento en A2E
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_base_manager import KnowledgeBaseManager


def cmd_add(args):
    """Agrega un item de conocimiento"""
    manager = KnowledgeBaseManager(use_rag=not args.no_rag)
    
    # Cargar item desde archivo o crear desde argumentos
    if args.file:
        with open(args.file, "r") as f:
            item = json.load(f)
    else:
        item = {
            "title": args.title,
            "description": args.description,
            "content": args.content or {}
        }
    
    manager.add_knowledge_item(
        kb_id=args.kb_id,
        item_id=args.item_id,
        item=item,
        knowledge_type=args.type
    )
    
    print(f"✓ Added knowledge item '{args.item_id}' to '{args.kb_id}'")


def cmd_load(args):
    """Carga una base de conocimiento desde archivo"""
    manager = KnowledgeBaseManager(use_rag=not args.no_rag)
    
    manager.load_knowledge_base(
        kb_id=args.kb_id,
        kb_path=args.path,
        kb_type=args.type or "general"
    )
    
    print(f"✓ Loaded knowledge base '{args.kb_id}' from {args.path}")


def cmd_search(args):
    """Busca conocimiento"""
    manager = KnowledgeBaseManager(use_rag=not args.no_rag)
    
    # Cargar bases de conocimiento si se especifica
    if args.kb_file:
        manager.load_knowledge_base(
            kb_id=args.kb_id or "default",
            kb_path=args.kb_file,
            kb_type=args.type or "general"
        )
    
    results = manager.search_knowledge(
        query=args.query,
        kb_id=args.kb_id,
        knowledge_type=args.type,
        top_k=args.top_k
    )
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.get('title', result.get('id'))}")
        print(f"   Description: {result.get('description', 'N/A')}")
        print(f"   Score: {result.get('_score', result.get('score', 'N/A'))}")
        if args.verbose:
            print(f"   Content: {json.dumps(result.get('content', {}), indent=2)}")


def cmd_list(args):
    """Lista bases de conocimiento"""
    manager = KnowledgeBaseManager(use_rag=not args.no_rag)
    
    # Cargar desde directorio si se especifica
    if args.dir:
        kb_dir = Path(args.dir)
        for kb_file in kb_dir.glob("*.json"):
            kb_id = kb_file.stem
            manager.load_knowledge_base(
                kb_id=kb_id,
                kb_path=str(kb_file),
                kb_type=args.type or "general"
            )
    
    bases = manager.list_knowledge_bases()
    
    if not bases:
        print("No knowledge bases loaded")
        return
    
    print(f"\nKnowledge Bases ({len(bases)}):")
    for kb in bases:
        print(f"  - {kb['id']} ({kb['type']}): {kb['items_count']} items")
        if kb.get("description"):
            print(f"    {kb['description']}")


def cmd_export(args):
    """Exporta una base de conocimiento"""
    manager = KnowledgeBaseManager(use_rag=not args.no_rag)
    
    # Cargar si es necesario
    if args.load_from:
        manager.load_knowledge_base(
            kb_id=args.kb_id,
            kb_path=args.load_from,
            kb_type=args.type or "general"
        )
    
    manager.export_knowledge_base(args.kb_id, args.output)
    print(f"✓ Exported knowledge base '{args.kb_id}' to {args.output}")


def main():
    parser = argparse.ArgumentParser(description="Manage A2E Knowledge Bases")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add knowledge item")
    add_parser.add_argument("--kb-id", required=True, help="Knowledge base ID")
    add_parser.add_argument("--item-id", required=True, help="Item ID")
    add_parser.add_argument("--title", help="Item title")
    add_parser.add_argument("--description", help="Item description")
    add_parser.add_argument("--content", help="Item content (JSON string)")
    add_parser.add_argument("--file", help="Load item from JSON file")
    add_parser.add_argument("--type", help="Knowledge type")
    add_parser.add_argument("--no-rag", action="store_true", help="Disable RAG")
    add_parser.set_defaults(func=cmd_add)
    
    # Load command
    load_parser = subparsers.add_parser("load", help="Load knowledge base from file")
    load_parser.add_argument("--kb-id", required=True, help="Knowledge base ID")
    load_parser.add_argument("--path", required=True, help="Path to JSON file")
    load_parser.add_argument("--type", help="Knowledge type")
    load_parser.add_argument("--no-rag", action="store_true", help="Disable RAG")
    load_parser.set_defaults(func=cmd_load)
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search knowledge")
    search_parser.add_argument("--query", required=True, help="Search query")
    search_parser.add_argument("--kb-id", help="Filter by knowledge base")
    search_parser.add_argument("--type", help="Filter by knowledge type")
    search_parser.add_argument("--kb-file", help="Load KB from file before searching")
    search_parser.add_argument("--top-k", type=int, default=5, help="Number of results")
    search_parser.add_argument("--verbose", action="store_true", help="Show full content")
    search_parser.add_argument("--no-rag", action="store_true", help="Disable RAG")
    search_parser.set_defaults(func=cmd_search)
    
    # List command
    list_parser = subparsers.add_parser("list", help="List knowledge bases")
    list_parser.add_argument("--dir", help="Load KBs from directory")
    list_parser.add_argument("--type", help="Filter by type")
    list_parser.add_argument("--no-rag", action="store_true", help="Disable RAG")
    list_parser.set_defaults(func=cmd_list)
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export knowledge base")
    export_parser.add_argument("--kb-id", required=True, help="Knowledge base ID")
    export_parser.add_argument("--output", required=True, help="Output file path")
    export_parser.add_argument("--load-from", help="Load KB from file before exporting")
    export_parser.add_argument("--type", help="Knowledge type")
    export_parser.add_argument("--no-rag", action="store_true", help="Disable RAG")
    export_parser.set_defaults(func=cmd_export)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        args.func(args)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

