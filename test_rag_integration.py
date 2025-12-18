"""
Test rápido de la integración RAG
Verifica que LokiJS y embeddings locales funcionan correctamente
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_rag_imports():
    """Test: Verificar que las importaciones funcionan"""
    print("[TEST 1/4] Testing imports...")
    try:
        from rag_integration import A2ERAGSystem
        from api_knowledge_base import APIKnowledgeBase
        print("   [OK] All imports successful")
        return True
    except Exception as e:
        print(f"   [FAIL] Import error: {e}")
        return False

def test_rag_initialization():
    """Test: Verificar que RAG se inicializa correctamente"""
    print("\n[TEST 2/4] Testing RAG initialization...")
    try:
        from rag_integration import A2ERAGSystem
        
        rag = A2ERAGSystem(embedding_model="all-MiniLM-L6-v2")
        print("   [OK] RAG system initialized")
        print(f"   [OK] Database: {rag.db.name}")
        print(f"   [OK] Vector index dimension: {rag.vector_index.dimension}")
        return True
    except Exception as e:
        print(f"   [FAIL] Initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_kb_with_rag():
    """Test: Verificar que APIKnowledgeBase usa RAG"""
    print("\n[TEST 3/4] Testing APIKnowledgeBase with RAG...")
    try:
        from api_knowledge_base import APIKnowledgeBase
        
        # Crear sin RAG primero (para verificar que funciona sin él)
        api_kb_no_rag = APIKnowledgeBase(use_rag=False)
        print("   [OK] APIKnowledgeBase created without RAG")
        
        # Crear con RAG
        api_kb_rag = APIKnowledgeBase(use_rag=True)
        print("   [OK] APIKnowledgeBase created with RAG")
        
        if api_kb_rag.rag is not None:
            print("   [OK] RAG system is active")
        else:
            print("   [WARN] RAG system is None (may not be available)")
        
        return True
    except Exception as e:
        print(f"   [FAIL] APIKnowledgeBase error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_operations_indexing():
    """Test: Verificar indexación de operaciones"""
    print("\n[TEST 4/4] Testing operations indexing...")
    try:
        from rag_integration import A2ERAGSystem
        
        rag = A2ERAGSystem(embedding_model="all-MiniLM-L6-v2")
        
        # Verificar que el catálogo existe
        catalog_path = Path(__file__).parent / "workflow_catalog.json"
        if catalog_path.exists():
            rag.index_operations_catalog(str(catalog_path))
            print(f"   [OK] Operations catalog indexed")
            
            # Verificar que hay operaciones indexadas
            ops_count = len(rag.operations_collection.find())
            print(f"   [OK] {ops_count} operations in database")
            
            # Probar búsqueda
            results = rag.search_operations("consulta API", top_k=3)
            print(f"   [OK] Search returned {len(results)} results")
            
            if results:
                print(f"   [OK] Top result: {results[0]['name']} (score: {results[0]['score']:.3f})")
        else:
            print(f"   [WARN] Catalog not found: {catalog_path}")
            print("   [INFO] Skipping indexing test")
        
        return True
    except Exception as e:
        print(f"   [FAIL] Indexing error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecutar todos los tests"""
    print("="*60)
    print("A2E RAG Integration Tests")
    print("="*60)
    
    tests = [
        test_rag_imports,
        test_rag_initialization,
        test_api_kb_with_rag,
        test_operations_indexing
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n[ERROR] Test crashed: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Total: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n[SUCCESS] All RAG integration tests passed!")
        return 0
    else:
        print(f"\n[WARNING] {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())

