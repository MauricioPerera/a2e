# Configuración de RAG en A2E

## Estado Actual

✅ **Código de integración completo**
⚠️ **Requiere configuración de dependencias**

## Pasos para Habilitar RAG

### 1. Instalar Dependencias de Embeddings

```bash
pip install sentence-transformers torch transformers
```

Si tienes problemas con Keras 3:
```bash
pip install tf-keras
```

### 2. Hacer Accesible rag_catalog

El módulo `rag_catalog` debe estar en el PYTHONPATH. Opciones:

#### Opción A: Agregar al PYTHONPATH

**Linux/Mac:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/a2ui/samples/agent/adk"
```

**Windows:**
```cmd
set PYTHONPATH=%PYTHONPATH%;D:\repos\a2ui\a2ui\samples\agent\adk
```

#### Opción B: Instalar como paquete

```bash
cd a2ui/samples/agent/adk/rag_catalog
pip install -e .
```

### 3. Verificar Instalación

```bash
cd a2ui/samples/agent/adk/workflow_executor
python -c "from rag_integration import A2ERAGSystem; print('RAG OK')"
```

## Uso

Una vez configurado, RAG se activa automáticamente:

```python
from api_knowledge_base import APIKnowledgeBase

# RAG se activa automáticamente (use_rag=True por defecto)
api_kb = APIKnowledgeBase(
    operations_catalog_path="workflow_catalog.json"
)

# Búsqueda semántica funciona
operations = api_kb.search_operations("consulta API", top_k=5)
```

## Sin RAG

Si RAG no está disponible, A2E funciona sin él:

```python
# Funciona sin RAG (búsqueda por keywords)
api_kb = APIKnowledgeBase(use_rag=False)
endpoints = api_kb.search_endpoints("usuarios")  # Búsqueda por keywords
```

## Solución de Problemas

### "No module named 'rag_catalog'"

**Causa**: `rag_catalog` no está en PYTHONPATH

**Solución**: Agregar al PYTHONPATH o instalar como paquete

### "No module named 'tf_keras'"

**Causa**: Dependencia faltante de sentence-transformers

**Solución**: `pip install tf-keras`

### "RAG system not available"

**Causa**: RAG no pudo inicializarse

**Solución**: Verificar que todas las dependencias están instaladas

## Conclusión

El código de integración está completo. Solo necesitas:
1. Instalar dependencias de embeddings
2. Hacer `rag_catalog` accesible
3. ¡Listo! RAG funciona automáticamente

