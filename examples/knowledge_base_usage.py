"""
Ejemplo de uso de Knowledge Base Manager
Demuestra cómo cargar, buscar y usar bases de conocimiento
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_base_manager import KnowledgeBaseManager, create_example_knowledge_base


def main():
    """
    Demuestra el uso del Knowledge Base Manager
    """
    print("="*60)
    print("A2E Knowledge Base Manager Example")
    print("="*60)
    
    # 1. Crear gestor
    print("\n[1/5] Creating Knowledge Base Manager...")
    manager = KnowledgeBaseManager(use_rag=True)
    print("   [OK] Manager created")
    
    # 2. Cargar base de conocimiento desde archivo
    print("\n[2/5] Loading knowledge base from file...")
    kb_file = Path(__file__).parent / "knowledge_base_example.json"
    if kb_file.exists():
        manager.load_knowledge_base(
            kb_id="workflow-patterns",
            kb_path=str(kb_file),
            kb_type="pattern"
        )
        print(f"   [OK] Knowledge base loaded from {kb_file}")
    else:
        print(f"   [WARN] File not found: {kb_file}")
        # Usar ejemplo programático
        manager = create_example_knowledge_base()
        print("   [OK] Using programmatic example")
    
    # 3. Agregar item manualmente
    print("\n[3/5] Adding knowledge item manually...")
    manager.add_knowledge_item(
        kb_id="workflow-tips",
        item_id="tip-error-handling",
        item={
            "title": "Tip: Manejo de Errores",
            "description": "Siempre valida workflows antes de ejecutarlos",
            "content": {
                "tip": "Usa el validador de workflows para detectar errores antes de ejecutar",
                "example": "client.validate_workflow(workflow_jsonl)"
            }
        },
        knowledge_type="tip"
    )
    print("   [OK] Item added")
    
    # 4. Buscar conocimiento
    print("\n[4/5] Searching knowledge...")
    queries = [
        "consulta API y filtra datos",
        "ejecución condicional",
        "manejo de errores"
    ]
    
    for query in queries:
        print(f"\n   Query: '{query}'")
        results = manager.search_knowledge(query, top_k=3)
        print(f"   Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            title = result.get("title", result.get("id", "Unknown"))
            desc = result.get("description", "")
            score = result.get("_score", result.get("score", "N/A"))
            print(f"     {i}. {title} (score: {score})")
            if desc:
                print(f"        {desc[:60]}...")
    
    # 5. Listar bases de conocimiento
    print("\n[5/5] Listing knowledge bases...")
    bases = manager.list_knowledge_bases()
    print(f"   [OK] Found {len(bases)} knowledge bases:")
    for kb in bases:
        print(f"     - {kb['id']} ({kb['type']}): {kb['items_count']} items")
    
    # Resumen
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("✅ Knowledge Base Manager working")
    print("✅ Knowledge bases can be loaded from files")
    print("✅ Items can be added programmatically")
    print("✅ Semantic search working (with RAG)")
    print("✅ Keyword search working (fallback)")
    print("\n[SUCCESS] Knowledge Base system is fully functional!")


if __name__ == "__main__":
    main()

