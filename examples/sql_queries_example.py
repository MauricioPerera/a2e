"""
Ejemplo de uso de Consultas SQL en A2E
Demuestra cómo los clientes pueden registrar consultas SQL
y cómo los agentes pueden buscarlas usando búsqueda semántica
"""

import sys
from pathlib import Path

# Agregar el directorio padre al path
_current_file = Path(__file__).resolve()
_parent_dir = _current_file.parent.parent
sys.path.insert(0, str(_parent_dir))

from sql_query_manager import SQLQueryManager, create_example_sql_query_manager
from client.a2e_client import A2EClient


def example_register_queries():
    """
    Ejemplo: Cliente registra consultas SQL en el catálogo
    """
    print("=== Ejemplo: Registro de Consultas SQL ===\n")
    
    # Crear gestor de consultas SQL
    manager = SQLQueryManager(use_rag=True)
    
    # Registrar consultas SQL
    manager.add_sql_query(
        query_id="get-active-users",
        sql_query="SELECT id, name, email, status FROM users WHERE status = 'active' ORDER BY name",
        description="Obtiene todos los usuarios activos ordenados por nombre",
        database="main_db",
        category="select",
        parameters=["status"]
    )
    
    manager.add_sql_query(
        query_id="get-user-by-id",
        sql_query="SELECT * FROM users WHERE id = ?",
        description="Obtiene un usuario específico por su ID",
        database="main_db",
        category="select",
        parameters=["id"]
    )
    
    manager.add_sql_query(
        query_id="count-orders-by-status",
        sql_query="""
        SELECT status, COUNT(*) as count 
        FROM orders 
        WHERE created_at >= ? 
        GROUP BY status
        """,
        description="Cuenta órdenes agrupadas por estado desde una fecha",
        database="main_db",
        category="analytics",
        parameters=["created_at"]
    )
    
    manager.add_sql_query(
        query_id="get-top-products",
        sql_query="""
        SELECT p.id, p.name, SUM(oi.quantity) as total_sold
        FROM products p
        JOIN order_items oi ON p.id = oi.product_id
        WHERE oi.created_at >= ?
        GROUP BY p.id, p.name
        ORDER BY total_sold DESC
        LIMIT ?
        """,
        description="Obtiene los productos más vendidos desde una fecha",
        database="main_db",
        category="analytics",
        parameters=["created_at", "limit"]
    )
    
    print(f"[OK] Registradas {len(manager.sql_queries)} consultas SQL\n")
    return manager


def example_agent_search():
    """
    Ejemplo: Agente busca consultas SQL relevantes
    """
    print("=== Ejemplo: Búsqueda Semántica de Consultas SQL ===\n")
    
    manager = create_example_sql_query_manager()
    
    # Búsquedas de ejemplo
    queries = [
        "obtener usuarios activos",
        "contar órdenes por estado",
        "productos más vendidos",
        "actualizar estado de usuario"
    ]
    
    for query in queries:
        print(f"Búsqueda: '{query}'")
        results = manager.search_sql_queries(query, top_k=2)
        
        for i, result in enumerate(results, 1):
            score = result.get("score", result.get("_score", 0))
            print(f"  {i}. {result['id']} (score: {score:.3f})")
            print(f"     {result['description']}")
            print(f"     SQL: {result['sql'][:60]}...")
        print()


def example_filter_by_database():
    """
    Ejemplo: Filtrar consultas por base de datos
    """
    print("=== Ejemplo: Filtrar por Base de Datos ===\n")
    
    manager = create_example_sql_query_manager()
    
    # Agregar consulta en otra base de datos
    manager.add_sql_query(
        query_id="get-logs",
        sql_query="SELECT * FROM logs WHERE level = 'ERROR' ORDER BY timestamp DESC",
        description="Obtiene logs de error",
        database="logs_db",
        category="select"
    )
    
    # Buscar solo en main_db
    print("Consultas en 'main_db':")
    results = manager.search_sql_queries("obtener usuarios", database="main_db")
    for r in results:
        print(f"  - {r['id']} ({r['database']})")
    
    print("\nConsultas en 'logs_db':")
    results = manager.search_sql_queries("obtener logs", database="logs_db")
    for r in results:
        print(f"  - {r['id']} ({r['database']})")
    
    print()


def example_filter_by_category():
    """
    Ejemplo: Filtrar consultas por categoría
    """
    print("=== Ejemplo: Filtrar por Categoría ===\n")
    
    manager = create_example_sql_query_manager()
    
    # Buscar solo consultas SELECT
    print("Consultas SELECT:")
    results = manager.search_sql_queries("obtener datos", category="select")
    for r in results:
        print(f"  - {r['id']} ({r['category']})")
    
    # Buscar solo consultas ANALYTICS
    print("\nConsultas ANALYTICS:")
    results = manager.search_sql_queries("estadísticas", category="analytics")
    for r in results:
        print(f"  - {r['id']} ({r['category']})")
    
    print()


def example_load_from_file():
    """
    Ejemplo: Cargar consultas desde archivo JSON
    """
    print("=== Ejemplo: Cargar desde Archivo ===\n")
    
    import json
    from pathlib import Path
    
    # Crear archivo de ejemplo
    sql_queries_file = Path("example_sql_queries.json")
    example_data = {
        "queries": [
            {
                "id": "get-recent-orders",
                "sql": "SELECT * FROM orders WHERE created_at >= ? ORDER BY created_at DESC LIMIT ?",
                "description": "Obtiene órdenes recientes",
                "database": "main_db",
                "category": "select",
                "parameters": ["created_at", "limit"]
            },
            {
                "id": "get-order-items",
                "sql": "SELECT oi.*, p.name as product_name FROM order_items oi JOIN products p ON oi.product_id = p.id WHERE oi.order_id = ?",
                "description": "Obtiene items de una orden con nombres de productos",
                "database": "main_db",
                "category": "select",
                "parameters": ["order_id"]
            }
        ]
    }
    
    with open(sql_queries_file, "w", encoding="utf-8") as f:
        json.dump(example_data, f, indent=2)
    
    # Cargar desde archivo
    manager = SQLQueryManager(use_rag=True)
    manager.load_sql_queries_from_file(str(sql_queries_file))
    
    print(f"[OK] Cargadas {len(manager.sql_queries)} consultas desde {sql_queries_file}\n")
    
    # Limpiar
    sql_queries_file.unlink()


def example_client_usage():
    """
    Ejemplo: Uso desde el cliente A2E
    """
    print("=== Ejemplo: Uso desde Cliente A2E ===\n")
    
    # Crear cliente (requiere servidor corriendo)
    try:
        client = A2EClient(
            base_url="http://localhost:8000",
            api_key="your-api-key-here"
        )
        
        # Buscar consultas SQL
        results = client.search_sql_queries("obtener usuarios activos", top_k=3)
        print(f"Encontradas {len(results)} consultas:")
        for r in results:
            print(f"  - {r['id']}: {r['description']}")
        
        # Listar todas las consultas
        all_queries = client.list_sql_queries()
        print(f"\nTotal de consultas disponibles: {len(all_queries)}")
        
        # Obtener una consulta específica
        if results:
            query_id = results[0]['id']
            query = client.get_sql_query(query_id)
            print(f"\nConsulta '{query_id}':")
            print(f"  SQL: {query['sql']}")
            print(f"  Parámetros: {query.get('parameters', [])}")
    
    except Exception as e:
        print(f"⚠ Error al conectar con el servidor: {e}")
        print("  (Asegúrate de que el servidor esté corriendo)")


def example_export_queries():
    """
    Ejemplo: Exportar consultas a archivo
    """
    print("=== Ejemplo: Exportar Consultas ===\n")
    
    manager = create_example_sql_query_manager()
    
    # Exportar todas las consultas
    manager.export_sql_queries("exported_queries.json")
    print("[OK] Consultas exportadas a 'exported_queries.json'")
    
    # Exportar solo consultas SELECT
    manager.export_sql_queries("exported_select_queries.json", category="select")
    print("[OK] Consultas SELECT exportadas a 'exported_select_queries.json'")
    
    print()


if __name__ == "__main__":
    print("Ejemplos de Consultas SQL en A2E\n")
    print("=" * 50 + "\n")
    
    # Ejecutar ejemplos
    example_register_queries()
    example_agent_search()
    example_filter_by_database()
    example_filter_by_category()
    example_load_from_file()
    example_export_queries()
    example_client_usage()
    
    print("\n" + "=" * 50)
    print("[OK] Todos los ejemplos completados")

