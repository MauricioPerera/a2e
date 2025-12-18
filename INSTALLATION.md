# Instalación de A2E con RAG

## Dependencias

A2E requiere las siguientes dependencias para funcionar con RAG:

### Básicas

```bash
pip install aiohttp cryptography numpy PyJWT flask flask-cors requests
```

### Para RAG (LokiJS + Embeddings Locales)

```bash
# Embeddings locales
pip install sentence-transformers torch transformers

# Si tienes problemas con Keras 3:
pip install tf-keras
```

### Instalación del Módulo RAG

El módulo `rag_catalog` debe estar accesible. Tienes dos opciones:

#### Opción 1: Instalar como paquete

```bash
cd a2ui/samples/agent/adk/rag_catalog
pip install -e .
```

#### Opción 2: Agregar al PYTHONPATH

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/a2ui/samples/agent/adk"
```

O en Windows:
```cmd
set PYTHONPATH=%PYTHONPATH%;D:\repos\a2ui\a2ui\samples\agent\adk
```

## Verificación

```bash
cd a2ui/samples/agent/adk/workflow_executor
python -c "from rag_integration import A2ERAGSystem; print('OK')"
```

## Solución de Problemas

### Error: "No module named 'rag_catalog'"

**Solución**: Asegúrate de que `rag_catalog` está en el PYTHONPATH o instalado como paquete.

### Error: "No module named 'tf_keras'"

**Solución**: 
```bash
pip install tf-keras
```

### Error: "Could not import rag_catalog"

**Solución**: Verifica que el path a `rag_catalog` es correcto. El código intenta encontrarlo automáticamente, pero si falla, agrega manualmente al PYTHONPATH.

## Instalación Completa

```bash
# 1. Instalar dependencias básicas
pip install -e .

# 2. Instalar rag_catalog
cd ../rag_catalog
pip install -e .
cd ../workflow_executor

# 3. Verificar
python -c "from rag_integration import A2ERAGSystem; print('RAG OK')"
```

