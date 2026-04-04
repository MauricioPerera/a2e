# Guía del Dashboard A2E

## Descripción

El Dashboard A2E es una interfaz web simple que permite visualizar métricas, estadísticas y datos del sistema A2E en tiempo real.

## Características

- ✅ **Métricas Generales**: Total de ejecuciones, éxitos, fallos, duración promedio
- ✅ **Gráficos Interactivos**: Timeline de ejecuciones, operaciones más usadas
- ✅ **Ejecuciones Recientes**: Lista de las últimas ejecuciones con detalles
- ✅ **Agentes Más Activos**: Ranking de agentes por número de ejecuciones
- ✅ **APIs Disponibles**: Estadísticas de APIs registradas
- ✅ **Consultas SQL**: Estadísticas de consultas SQL en el catálogo
- ✅ **Auto-refresh**: Actualización automática cada 30 segundos

## Acceso

Una vez que el servidor A2E esté corriendo, accede al dashboard en:

```
http://localhost:8000/dashboard
```

## Métricas Disponibles

### 1. Estadísticas Generales

- **Total Ejecuciones**: Número total de ejecuciones en el período
- **Ejecuciones Exitosas**: Número y porcentaje de ejecuciones exitosas
- **Ejecuciones Fallidas**: Número y porcentaje de ejecuciones fallidas
- **Duración Promedio**: Tiempo promedio de ejecución en milisegundos
- **Agentes Activos**: Número de agentes únicos que han ejecutado workflows

### 2. Timeline de Ejecuciones

Gráfico de línea que muestra:
- Ejecuciones totales por día
- Ejecuciones exitosas por día
- Ejecuciones fallidas por día

### 3. Operaciones Más Usadas

Gráfico de dona que muestra:
- Tipos de operaciones más utilizadas
- Número de veces que se usó cada tipo
- Duración promedio por tipo

### 4. Ejecuciones Recientes

Tabla con las últimas 10 ejecuciones mostrando:
- ID de ejecución
- Agente que la ejecutó
- Workflow ID
- Estado (success, failed, pending, running)
- Duración
- Fecha y hora

### 5. Agentes Más Activos

Tabla con los top 5 agentes más activos:
- ID del agente
- Número de ejecuciones

### 6. APIs Disponibles

Información sobre:
- Total de APIs registradas
- Total de endpoints disponibles
- Lista de APIs con número de endpoints

### 7. Consultas SQL

Información sobre:
- Total de consultas SQL registradas
- Distribución por categoría (select, insert, update, analytics, etc.)

## API Endpoints

El dashboard utiliza los siguientes endpoints:

### Obtener Todas las Métricas

```http
GET /api/v1/dashboard/metrics?days=7
```

**Respuesta:**
```json
{
  "overview": {
    "total_executions": 150,
    "successful_executions": 140,
    "failed_executions": 10,
    "average_duration_ms": 1250.5,
    "total_agents": 5,
    "top_agents": [...]
  },
  "timeline": [...],
  "operations": [...],
  "recent_executions": [...],
  "apis": {...},
  "sql_queries": {...}
}
```

### Obtener Métricas Generales

```http
GET /api/v1/dashboard/overview?days=7
```

### Obtener Timeline

```http
GET /api/v1/dashboard/timeline?days=7
```

## Personalización

### Cambiar Período de Análisis

Por defecto, el dashboard muestra métricas de los últimos 7 días. Puedes cambiar esto modificando el parámetro `days` en las llamadas a la API:

```javascript
// En index.html, línea ~200
const response = await fetch('/api/v1/dashboard/metrics?days=30');
```

### Cambiar Frecuencia de Auto-refresh

Por defecto, el dashboard se actualiza cada 30 segundos. Puedes cambiar esto modificando:

```javascript
// En index.html, línea ~400
setInterval(loadDashboard, 60000); // 60 segundos
```

## Requisitos

- Servidor A2E corriendo
- Navegador web moderno (Chrome, Firefox, Safari, Edge)
- Acceso a internet (para cargar Chart.js desde CDN)

## Solución de Problemas

### El dashboard no carga

1. Verifica que el servidor esté corriendo:
   ```bash
   python server/a2e_server.py
   ```

2. Verifica que puedas acceder a `/api/v1/dashboard/metrics`:
   ```bash
   curl http://localhost:8000/api/v1/dashboard/metrics
   ```

3. Revisa la consola del navegador para errores JavaScript

### No se muestran datos

- Verifica que haya ejecuciones registradas en el sistema
- Revisa que `AuditLogger` esté correctamente configurado
- Verifica los logs del servidor para errores

### Gráficos no se renderizan

- Verifica la conexión a internet (Chart.js se carga desde CDN)
- Revisa la consola del navegador para errores
- Asegúrate de que los datos estén en el formato correcto

## Próximas Mejoras

- [ ] Filtros por agente, workflow, fecha
- [ ] Exportación de métricas a CSV/JSON
- [ ] Gráficos adicionales (distribución de duraciones, tasa de éxito por agente)
- [ ] Alertas y notificaciones
- [ ] Modo oscuro
- [ ] Dashboard personalizable

## Desarrollo

### Estructura de Archivos

```
dashboard/
  └── index.html          # Dashboard HTML principal

server/
  ├── a2e_server.py      # Servidor Flask con endpoints
  └── dashboard_metrics.py  # Lógica de cálculo de métricas
```

### Agregar Nuevas Métricas

1. Agregar método en `dashboard_metrics.py`:
   ```python
   def get_new_metric(self) -> Dict[str, Any]:
       # Calcular métrica
       return {"metric": value}
   ```

2. Agregar endpoint en `a2e_server.py`:
   ```python
   @app.route('/api/v1/dashboard/new-metric', methods=['GET'])
   def get_new_metric():
       metric = dashboard_metrics.get_new_metric()
       return jsonify(metric)
   ```

3. Agregar visualización en `dashboard/index.html`:
   ```javascript
   async function loadNewMetric() {
       const response = await fetch('/api/v1/dashboard/new-metric');
       const data = await response.json();
       // Renderizar métrica
   }
   ```

