"""
Gestor de Bases de Conocimiento para A2E
Usa LokiJS para almacenamiento y embeddings locales para búsqueda semántica
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    from rag_integration import A2ERAGSystem
except ImportError:
    A2ERAGSystem = None

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """
    Gestor de bases de conocimiento para A2E
    Almacena y busca conocimiento usando LokiJS y embeddings locales
    """
    
    def __init__(
        self,
        rag_system: Optional[A2ERAGSystem] = None,
        use_rag: bool = True
    ):
        """
        Inicializa el gestor de bases de conocimiento
        
        Args:
            rag_system: Sistema RAG (se crea uno nuevo si es None y use_rag=True)
            use_rag: Si usar RAG para búsqueda semántica
        """
        self.use_rag = use_rag
        
        if use_rag:
            if A2ERAGSystem is None:
                logger.warning("RAG system not available. Knowledge bases will use keyword search only.")
                self.use_rag = False
                self.rag = None
            else:
                self.rag = rag_system or A2ERAGSystem()
        else:
            self.rag = None
        
        # Almacenamiento tradicional (fallback)
        self.knowledge_bases: Dict[str, Dict[str, Any]] = {}
    
    def load_knowledge_base(
        self,
        kb_id: str,
        kb_path: str,
        kb_type: str = "general"
    ):
        """
        Carga una base de conocimiento desde un archivo JSON
        
        Args:
            kb_id: ID único de la base de conocimiento
            kb_path: Ruta al archivo JSON
            kb_type: Tipo de conocimiento (ej: "documentation", "examples", "patterns")
        """
        with open(kb_path, "r", encoding="utf-8") as f:
            content = json.load(f)
        
        description = content.get("description", "")
        items = content.get("items", [])
        
        # Guardar en almacenamiento tradicional
        self.knowledge_bases[kb_id] = {
            "id": kb_id,
            "type": kb_type,
            "description": description,
            "items": items,
            "path": kb_path
        }
        
        # Indexar en RAG si está habilitado
        if self.use_rag and self.rag:
            for item in items:
                item_id = item.get("id", f"{kb_id}-{len(self.rag.knowledge_collection.find())}")
                item_description = item.get("description", item.get("title", ""))
                
                self.rag.index_knowledge(
                    knowledge_id=item_id,
                    knowledge_type=kb_type,
                    content=item,
                    description=item_description
                )
        
        logger.info(f"Loaded knowledge base: {kb_id} ({len(items)} items)")
    
    def add_knowledge_item(
        self,
        kb_id: str,
        item_id: str,
        item: Dict[str, Any],
        knowledge_type: Optional[str] = None
    ):
        """
        Agrega un item de conocimiento a una base de conocimiento
        
        Args:
            kb_id: ID de la base de conocimiento
            item_id: ID único del item
            item: Contenido del item
            knowledge_type: Tipo de conocimiento (opcional, usa el de la KB si no se especifica)
        """
        if kb_id not in self.knowledge_bases:
            # Crear nueva base de conocimiento si no existe
            self.knowledge_bases[kb_id] = {
                "id": kb_id,
                "type": knowledge_type or "general",
                "description": "",
                "items": []
            }
        
        # Agregar item
        item_with_id = item.copy()
        item_with_id["id"] = item_id
        self.knowledge_bases[kb_id]["items"].append(item_with_id)
        
        # Indexar en RAG si está habilitado
        if self.use_rag and self.rag:
            kb_type = knowledge_type or self.knowledge_bases[kb_id]["type"]
            description = item.get("description", item.get("title", ""))
            
            self.rag.index_knowledge(
                knowledge_id=item_id,
                knowledge_type=kb_type,
                content=item_with_id,
                description=description
            )
        
        logger.info(f"Added knowledge item: {item_id} to {kb_id}")
    
    def search_knowledge(
        self,
        query: str,
        kb_id: Optional[str] = None,
        knowledge_type: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Busca conocimiento relevante usando búsqueda semántica o keywords
        
        Args:
            query: Query de búsqueda
            kb_id: Filtrar por base de conocimiento (opcional)
            knowledge_type: Filtrar por tipo (opcional)
            top_k: Número de resultados
        
        Returns:
            Lista de items de conocimiento relevantes
        """
        # Usar RAG si está habilitado
        if self.use_rag and self.rag:
            results = self.rag.search_knowledge(
                query=query,
                knowledge_type=knowledge_type,
                top_k=top_k
            )
            
            # Filtrar por kb_id si se especifica
            if kb_id:
                results = [r for r in results if r.get("id", "").startswith(f"{kb_id}-")]
            
            return results
        
        # Fallback a búsqueda por keywords
        results = []
        kb_to_search = [kb_id] if kb_id else list(self.knowledge_bases.keys())
        
        for kb_id in kb_to_search:
            kb = self.knowledge_bases.get(kb_id)
            if not kb:
                continue
            
            # Filtrar por tipo si se especifica
            if knowledge_type and kb["type"] != knowledge_type:
                continue
            
            for item in kb.get("items", []):
                # Búsqueda simple por keywords
                description = item.get("description", "").lower()
                title = item.get("title", "").lower()
                content = str(item.get("content", "")).lower()
                
                query_lower = query.lower()
                score = 0
                
                for word in query_lower.split():
                    if word in description:
                        score += 3
                    if word in title:
                        score += 2
                    if word in content:
                        score += 1
                
                if score > 0:
                    item_copy = item.copy()
                    item_copy["kbId"] = kb_id
                    item_copy["_score"] = score
                    results.append(item_copy)
        
        # Ordenar por score y retornar top_k
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results[:top_k]
    
    def get_knowledge_base(self, kb_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene una base de conocimiento completa
        
        Args:
            kb_id: ID de la base de conocimiento
        
        Returns:
            Base de conocimiento o None si no existe
        """
        return self.knowledge_bases.get(kb_id)
    
    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """
        Lista todas las bases de conocimiento
        
        Returns:
            Lista de bases de conocimiento con metadatos
        """
        return [
            {
                "id": kb["id"],
                "type": kb["type"],
                "description": kb["description"],
                "items_count": len(kb.get("items", []))
            }
            for kb in self.knowledge_bases.values()
        ]
    
    def get_knowledge_item(
        self,
        kb_id: str,
        item_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtiene un item específico de conocimiento
        
        Args:
            kb_id: ID de la base de conocimiento
            item_id: ID del item
        
        Returns:
            Item de conocimiento o None si no existe
        """
        kb = self.knowledge_bases.get(kb_id)
        if not kb:
            return None
        
        for item in kb.get("items", []):
            if item.get("id") == item_id:
                return item
        
        return None
    
    def export_knowledge_base(self, kb_id: str, output_path: str):
        """
        Exporta una base de conocimiento a un archivo JSON
        
        Args:
            kb_id: ID de la base de conocimiento
            output_path: Ruta donde guardar el archivo
        """
        kb = self.knowledge_bases.get(kb_id)
        if not kb:
            raise ValueError(f"Knowledge base {kb_id} not found")
        
        export_data = {
            "id": kb["id"],
            "type": kb["type"],
            "description": kb["description"],
            "items": kb["items"]
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported knowledge base {kb_id} to {output_path}")


def create_example_knowledge_base():
    """
    Crea una base de conocimiento de ejemplo
    """
    manager = KnowledgeBaseManager(use_rag=True)
    
    # Agregar items de ejemplo
    manager.add_knowledge_item(
        kb_id="workflow-patterns",
        item_id="pattern-api-filter-store",
        item={
            "title": "Patrón: API → Filtrar → Almacenar",
            "description": "Patrón común de workflow: consultar API, filtrar resultados, almacenar",
            "pattern": {
                "operations": ["ApiCall", "FilterData", "StoreData"],
                "flow": "api -> filter -> store"
            },
            "example": {
                "query": "Consulta API de usuarios, filtra los activos, y guárdalos"
            }
        },
        knowledge_type="pattern"
    )
    
    manager.add_knowledge_item(
        kb_id="workflow-patterns",
        item_id="pattern-conditional-execution",
        item={
            "title": "Patrón: Ejecución Condicional",
            "description": "Ejecutar operaciones solo si se cumple una condición",
            "pattern": {
                "operations": ["Conditional", "ApiCall"],
                "flow": "check condition -> execute if true"
            }
        },
        knowledge_type="pattern"
    )
    
    return manager


if __name__ == "__main__":
    # Ejemplo de uso
    manager = create_example_knowledge_base()
    
    # Buscar conocimiento
    results = manager.search_knowledge("consulta API y filtra", top_k=3)
    print("Knowledge found:")
    for r in results:
        print(f"  - {r.get('title', r.get('id'))}: {r.get('description', '')}")

