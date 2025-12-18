# Modelo de Embedding e Índice Vectorial

## Modelo de Embedding

### Por Defecto: `all-MiniLM-L6-v2`

**Características**:
- **Proveedor**: sentence-transformers (Hugging Face)
- **Tamaño**: ~80MB
- **Dimensión**: 384 dimensiones
- **Velocidad**: Rápido (optimizado para CPU)
- **Calidad**: Buena para búsqueda semántica
- **Idioma**: Multilingüe (incluye español)

**Uso**:
```python
from rag_integration import A2ERAGSystem

# Por defecto usa all-MiniLM-L6-v2
rag = A2ERAGSystem(embedding_model="all-MiniLM-L6-v2")
```

### Modelos Alternativos

Puedes usar otros modelos de sentence-transformers:

#### Opción 1: Mejor Calidad (Más Lento)
```python
rag = A2ERAGSystem(embedding_model="all-mpnet-base-v2")
# - Dimensión: 768
# - Tamaño: ~420MB
# - Calidad: Mejor
# - Velocidad: Más lento
```

#### Opción 2: Más Rápido (Menor Calidad)
```python
rag = A2ERAGSystem(embedding_model="paraphrase-MiniLM-L3-v2")
# - Dimensión: 384
# - Tamaño: ~60MB
# - Calidad: Buena
# - Velocidad: Muy rápido
```

#### Opción 3: Especializado en Español
```python
rag = A2ERAGSystem(embedding_model="paraphrase-multilingual-MiniLM-L12-v2")
# - Dimensión: 384
# - Tamaño: ~420MB
# - Calidad: Excelente para español
# - Velocidad: Medio
```

## Índice Vectorial

### Algoritmo: Búsqueda por Similitud Coseno

**Implementación**: `VectorIndex` en `rag_catalog/vector_index.py`

**Características**:
- ✅ **Almacenamiento**: NumPy arrays (eficiente)
- ✅ **Búsqueda**: Similitud coseno (cosine similarity)
- ✅ **Método**: Búsqueda exhaustiva (exhaustive search)
- ✅ **Escalabilidad**: Hasta ~100K vectores en memoria

**Algoritmo de Búsqueda**:
```python
# 1. Generar embedding de la query
query_vector = model.encode(query)

# 2. Calcular similitud coseno con todos los vectores
similarities = cosine_similarity(query_vector, all_vectors)

# 3. Ordenar por similitud y retornar top_k
top_indices = np.argsort(similarities)[-top_k:][::-1]
```

### Estructura del Índice

```python
class VectorIndex:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)  # Modelo de embedding
        self.vectors = np.ndarray([])  # Matriz de vectores (N x dimension)
        self.metadata = []  # Lista de metadatos por vector
        self.dimension = 384  # Dimensión del embedding
```

### Métricas de Búsqueda

**Similitud Coseno**:
- Rango: -1 a 1 (normalmente 0 a 1 para embeddings normalizados)
- Fórmula: `cos(θ) = (A · B) / (||A|| * ||B||)`
- Interpretación: 1 = idéntico, 0 = ortogonal, -1 = opuesto

## Comparación de Modelos

| Modelo | Dimensión | Tamaño | Velocidad | Calidad | Uso Recomendado |
|--------|-----------|--------|-----------|---------|-----------------|
| `all-MiniLM-L6-v2` | 384 | ~80MB | ⚡⚡⚡ Rápido | ⭐⭐⭐ Buena | **Por defecto** |
| `all-mpnet-base-v2` | 768 | ~420MB | ⚡ Medio | ⭐⭐⭐⭐ Muy Buena | Producción |
| `paraphrase-MiniLM-L3-v2` | 384 | ~60MB | ⚡⚡⚡⚡ Muy Rápido | ⭐⭐ Aceptable | Desarrollo |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | ~420MB | ⚡⚡ Medio | ⭐⭐⭐⭐ Excelente (ES) | Español |

## Configuración

### Cambiar Modelo

```python
# En rag_integration.py o al crear A2ERAGSystem
rag = A2ERAGSystem(embedding_model="all-mpnet-base-v2")
```

### Verificar Modelo Cargado

```python
rag = A2ERAGSystem()
print(f"Model: {rag.vector_index.model}")
print(f"Dimension: {rag.vector_index.dimension}")
```

## Rendimiento

### Búsqueda

- **Tiempo de búsqueda**: ~1-10ms para 1000 vectores
- **Memoria**: ~1.5KB por vector (384 dims)
- **Escalabilidad**: Hasta ~100K vectores en memoria

### Indexación

- **Tiempo por item**: ~10-50ms (depende del modelo)
- **Batch processing**: Más eficiente para múltiples items

## Índice Vectorial: HNSW Implementado ✅

**HNSW (Hierarchical Navigable Small World) está implementado** y se activa automáticamente si `hnswlib` está instalado.

### Ventajas de HNSW

- ✅ **Muy rápido**: Búsqueda en O(log N) vs O(N) de búsqueda exhaustiva
- ✅ **Escalable**: Maneja millones de vectores eficientemente
- ✅ **Calidad**: Mantiene alta precisión en resultados
- ✅ **Memoria eficiente**: Estructura de datos optimizada

### Uso

```python
# HNSW se activa automáticamente si hnswlib está instalado
rag = A2ERAGSystem(use_hnsw=True)  # Por defecto True

# Sin HNSW (fallback a búsqueda exhaustiva)
rag = A2ERAGSystem(use_hnsw=False)
```

Ver `README_HNSW.md` para más detalles.

## Conclusión

**Modelo**: `all-MiniLM-L6-v2` (sentence-transformers)  
**Dimensión**: 384  
**Índice**: Búsqueda exhaustiva con similitud coseno  
**Almacenamiento**: NumPy arrays en memoria  
**LokiJS**: Almacena metadatos y referencias a vectores

