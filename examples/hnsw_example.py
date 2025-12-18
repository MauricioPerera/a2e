"""
Ejemplo de uso de HNSW en A2E
Demuestra la diferencia de rendimiento entre búsqueda exhaustiva y HNSW
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag_integration import A2ERAGSystem


def benchmark_search(rag: A2ERAGSystem, num_items: int, num_searches: int = 10):
    """Compara rendimiento de búsqueda"""
    print(f"\nBenchmarking with {num_items} items, {num_searches} searches...")
    
    # Indexar items directamente en el vector_index
    print(f"Indexing {num_items} items...")
    start = time.time()
    for i in range(num_items):
        text = f"Test item number {i} with some description and value {i}"
        metadata = {
            "type": "test",
            "id": f"item-{i}",
            "value": f"test value {i}"
        }
        rag.vector_index.add(text, metadata)
    index_time = time.time() - start
    print(f"  Indexing time: {index_time:.2f}s ({index_time/num_items*1000:.2f}ms per item)")
    
    # Buscar directamente en el vector_index
    print(f"Performing {num_searches} searches...")
    start = time.time()
    for i in range(num_searches):
        results = rag.vector_index.search(f"test item {i % 10}", top_k=5)
    search_time = time.time() - start
    avg_search = search_time / num_searches
    
    print(f"  Total search time: {search_time:.2f}s")
    print(f"  Average per search: {avg_search*1000:.2f}ms")
    print(f"  Results per search: {len(results) if results else 0}")
    
    return index_time, avg_search


def main():
    """
    Compara rendimiento de HNSW vs búsqueda exhaustiva
    """
    print("="*60)
    print("HNSW vs Exhaustive Search Benchmark")
    print("="*60)
    
    # Verificar si HNSW está disponible
    try:
        import hnswlib
        print("\n[OK] hnswlib is available")
    except ImportError:
        print("\n[WARN] hnswlib not available. Install with: pip install hnswlib")
        print("       Will use exhaustive search only.")
        return
    
    # Test con HNSW
    print("\n" + "="*60)
    print("Test 1: HNSW Index")
    print("="*60)
    rag_hnsw = A2ERAGSystem(
        embedding_model="all-MiniLM-L6-v2",
        use_hnsw=True,
        max_elements=10000
    )
    index_time_hnsw, search_time_hnsw = benchmark_search(rag_hnsw, 1000, 20)
    
    # Test sin HNSW (exhaustivo)
    print("\n" + "="*60)
    print("Test 2: Exhaustive Search")
    print("="*60)
    rag_exhaustive = A2ERAGSystem(
        embedding_model="all-MiniLM-L6-v2",
        use_hnsw=False
    )
    index_time_exh, search_time_exh = benchmark_search(rag_exhaustive, 1000, 20)
    
    # Comparación
    print("\n" + "="*60)
    print("Comparison")
    print("="*60)
    speedup = search_time_exh / search_time_hnsw if search_time_hnsw > 0 else 0
    print(f"Indexing time:")
    print(f"  HNSW:      {index_time_hnsw:.2f}s")
    print(f"  Exhaustive: {index_time_exh:.2f}s")
    print(f"\nSearch time (average):")
    print(f"  HNSW:      {search_time_hnsw*1000:.2f}ms")
    print(f"  Exhaustive: {search_time_exh*1000:.2f}ms")
    print(f"\nSpeedup: {speedup:.2f}x faster with HNSW")
    
    # Estadísticas HNSW
    print(f"\nHNSW Status:")
    print(f"  Using HNSW: {rag_hnsw.vector_index.use_hnsw if hasattr(rag_hnsw.vector_index, 'use_hnsw') else 'Unknown'}")
    if hasattr(rag_hnsw.vector_index, 'hnsw_index') and rag_hnsw.vector_index.use_hnsw:
        stats = rag_hnsw.vector_index.hnsw_index.get_stats()
        print(f"  Elements: {stats['element_count']}")
        print(f"  Max elements: {stats['max_elements']}")
        print(f"  Dimension: {stats['dimension']}")
    else:
        print(f"  Using exhaustive search (HNSW not active)")
    
    print(f"\nExhaustive Search Status:")
    print(f"  Using HNSW: {rag_exhaustive.vector_index.use_hnsw if hasattr(rag_exhaustive.vector_index, 'use_hnsw') else 'Unknown'}")
    
    print("\n[SUCCESS] HNSW benchmark completed!")


if __name__ == "__main__":
    main()

