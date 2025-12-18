# HNSW Index Implementation

## ✅ HNSW IMPLEMENTADO

A2E ahora incluye **HNSW (Hierarchical Navigable Small World)** como índice vectorial para búsqueda semántica eficiente.

## ¿Qué es HNSW?

HNSW es un algoritmo de búsqueda aproximada de vecinos más cercanos (ANN) que:
- ✅ **Muy rápido**: Búsqueda en O(log N) en lugar de O(N)
- ✅ **Escalable**: Maneja millones de vectores eficientemente
- ✅ **Calidad**: Mantiene alta precisión en resultados
- ✅ **Memoria eficiente**: Estructura de datos optimizada

## Comparación

| Método | Complejidad | Escalabilidad | Uso |
|--------|-------------|---------------|-----|
| **Búsqueda Exhaustiva** | O(N) | Hasta ~100K | Por defecto (simple) |
| **HNSW** | O(log N) | Millones | Automático si hnswlib está disponible |

## Uso

### Automático (Recomendado)

HNSW se activa automáticamente si `hnswlib` está instalado:

```python
from rag_integration import A2ERAGSystem

# HNSW se usa automáticamente si está disponible
rag = A2ERAGSystem(
    embedding_model="all-MiniLM-L6-v2",
    use_hnsw=True  # Por defecto True
)
```

### Configuración Avanzada

```python
rag = A2ERAGSystem(
    embedding_model="all-MiniLM-L6-v2",
    use_hnsw=True,
    max_elements=100000,      # Máximo de elementos
    ef_construction=200,      # Calidad de construcción (mayor = mejor, más lento)
    M=16,                     # Conexiones bidireccionales (mayor = mejor, más memoria)
    ef_search=50              # Calidad de búsqueda (mayor = mejor, más lento)
)
```

### Sin HNSW (Fallback)

Si `hnswlib` no está disponible, usa búsqueda exhaustiva automáticamente:

```python
# Funciona sin HNSW (usa búsqueda exhaustiva)
rag = A2ERAGSystem(use_hnsw=False)
```

## Parámetros HNSW

### `ef_construction` (200 por defecto)
- **Mayor**: Mejor calidad del índice, construcción más lenta
- **Menor**: Construcción más rápida, calidad menor
- **Rango recomendado**: 100-400

### `M` (16 por defecto)
- **Mayor**: Mejor calidad, más memoria
- **Menor**: Menos memoria, calidad menor
- **Rango recomendado**: 8-64

### `ef_search` (50 por defecto)
- **Mayor**: Mejor calidad de resultados, búsqueda más lenta
- **Menor**: Búsqueda más rápida, calidad menor
- **Rango recomendado**: 10-200

## Rendimiento

### Búsqueda Exhaustiva
- **Tiempo**: ~1-10ms para 1K vectores
- **Tiempo**: ~10-100ms para 10K vectores
- **Tiempo**: ~100ms-1s para 100K vectores

### HNSW
- **Tiempo**: ~1-5ms para 1K vectores
- **Tiempo**: ~2-10ms para 10K vectores
- **Tiempo**: ~5-20ms para 100K vectores
- **Tiempo**: ~10-50ms para 1M vectores

## Instalación

```bash
pip install hnswlib
```

O en `pyproject.toml`:
```toml
dependencies = [
    "hnswlib>=0.7.0"
]
```

## Persistencia

HNSW puede guardar y cargar índices:

```python
# Guardar
rag.vector_index.hnsw_index.save_index("index.hnsw")

# Cargar
rag.vector_index.hnsw_index.load_index("index.hnsw")
```

## Ajuste Dinámico

```python
# Ajustar calidad de búsqueda en tiempo de ejecución
rag.vector_index.hnsw_index.set_ef(100)  # Mayor calidad

# Redimensionar índice
rag.vector_index.hnsw_index.resize_index(200000)  # Más capacidad
```

## Estadísticas

```python
stats = rag.vector_index.hnsw_index.get_stats()
print(stats)
# {
#   "element_count": 5000,
#   "max_elements": 10000,
#   "dimension": 384,
#   "index_type": "HNSW"
# }
```

## Ventajas

1. **Velocidad**: 10-100x más rápido que búsqueda exhaustiva
2. **Escalabilidad**: Maneja millones de vectores
3. **Calidad**: Mantiene alta precisión
4. **Memoria**: Eficiente para grandes volúmenes
5. **Flexible**: Ajustable según necesidades

## Cuándo Usar HNSW

✅ **Usar HNSW cuando**:
- Tienes más de 10K vectores
- Necesitas búsquedas rápidas
- Tienes memoria disponible

⚠️ **Usar búsqueda exhaustiva cuando**:
- Tienes menos de 1K vectores
- Necesitas precisión exacta (no aproximada)
- Prefieres simplicidad

## Conclusión

✅ **HNSW está implementado y se activa automáticamente** si `hnswlib` está instalado.

El sistema funciona con ambos métodos:
- HNSW cuando está disponible (más rápido, escalable)
- Búsqueda exhaustiva como fallback (simple, preciso)

