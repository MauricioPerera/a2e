"""
Métricas para el Dashboard de A2E
Calcula estadísticas y métricas del sistema
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from monitoring.audit_logger import AuditLogger, ExecutionStatus


class DashboardMetrics:
    """
    Calcula métricas para el dashboard
    """
    
    def __init__(
        self,
        audit_logger: AuditLogger,
        api_kb=None,
        sql_query_manager=None,
        rate_limiter=None
    ):
        """
        Inicializa el calculador de métricas
        
        Args:
            audit_logger: Logger de auditoría
            api_kb: API Knowledge Base (opcional)
            sql_query_manager: SQL Query Manager (opcional)
            rate_limiter: Rate Limiter (opcional)
        """
        self.audit_logger = audit_logger
        self.api_kb = api_kb
        self.sql_query_manager = sql_query_manager
        self.rate_limiter = rate_limiter
    
    def get_overview_metrics(
        self,
        days: int = 7,
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene métricas generales del sistema
        
        Args:
            days: Número de días a analizar
        
        Returns:
            Diccionario con métricas generales
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        executions = self.audit_logger.query_executions(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        # Contar por estado
        status_counts = Counter(exec.get("status", "unknown") for exec in executions)
        
        # Calcular duraciones
        durations = [
            exec.get("total_duration_ms", 0)
            for exec in executions
            if exec.get("total_duration_ms")
        ]
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Contar por agente
        agent_counts = Counter(exec.get("agent_id") for exec in executions if exec.get("agent_id"))
        
        return {
            "total_executions": len(executions),
            "successful_executions": status_counts.get("success", 0),
            "failed_executions": status_counts.get("failed", 0),
            "pending_executions": status_counts.get("pending", 0),
            "running_executions": status_counts.get("running", 0),
            "average_duration_ms": round(avg_duration, 2),
            "total_agents": len(agent_counts),
            "top_agents": [
                {"agent_id": agent_id, "count": count}
                for agent_id, count in agent_counts.most_common(5)
            ],
            "period_days": days
        }
    
    def get_executions_timeline(
        self,
        days: int = 7,
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene timeline de ejecuciones por día
        
        Args:
            days: Número de días a analizar
        
        Returns:
            Lista de ejecuciones por día
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        executions = self.audit_logger.query_executions(
            agent_id=agent_id,
            workflow_id=workflow_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        # Agrupar por día
        daily_counts = defaultdict(lambda: {"total": 0, "success": 0, "failed": 0})
        
        for exec in executions:
            exec_date = datetime.fromisoformat(exec["timestamp"]).date()
            date_str = exec_date.isoformat()
            
            daily_counts[date_str]["total"] += 1
            status = exec.get("status", "unknown")
            if status == "success":
                daily_counts[date_str]["success"] += 1
            elif status == "failed":
                daily_counts[date_str]["failed"] += 1
        
        # Convertir a lista ordenada
        timeline = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            date_str = current_date.isoformat()
            timeline.append({
                "date": date_str,
                "total": daily_counts[date_str]["total"],
                "success": daily_counts[date_str]["success"],
                "failed": daily_counts[date_str]["failed"]
            })
            current_date += timedelta(days=1)
        
        return timeline
    
    def get_operation_stats(
        self,
        days: int = 7,
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtiene estadísticas de operaciones
        
        Args:
            days: Número de días a analizar
        
        Returns:
            Lista de estadísticas por tipo de operación
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        executions = self.audit_logger.query_executions(
            agent_id=agent_id,
            workflow_id=workflow_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        # Extraer operaciones de los detalles
        operation_counts = Counter()
        operation_durations = defaultdict(list)
        
        for exec in executions:
            exec_id = exec.get("execution_id")
            if exec_id:
                details = self.audit_logger.get_execution_details(exec_id)
                if details:
                    for op in details.get("operations", []):
                        op_type = op.get("operation_type", "unknown")
                        operation_counts[op_type] += 1
                        
                        duration = op.get("duration_ms")
                        if duration:
                            operation_durations[op_type].append(duration)
        
        # Calcular estadísticas
        stats = []
        for op_type, count in operation_counts.most_common(10):
            durations = operation_durations[op_type]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            stats.append({
                "operation_type": op_type,
                "count": count,
                "average_duration_ms": round(avg_duration, 2),
                "total_duration_ms": round(sum(durations), 2)
            })
        
        return stats
    
    def get_recent_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtiene ejecuciones recientes
        
        Args:
            limit: Número de ejecuciones a retornar
        
        Returns:
            Lista de ejecuciones recientes
        """
        executions = self.audit_logger.query_executions(limit=limit)
        
        # Ordenar por timestamp descendente
        executions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Formatear para el dashboard
        formatted = []
        for exec in executions[:limit]:
            formatted.append({
                "execution_id": exec.get("execution_id", ""),
                "agent_id": exec.get("agent_id", ""),
                "workflow_id": exec.get("workflow_id", ""),
                "status": exec.get("status", "unknown"),
                "timestamp": exec.get("timestamp", ""),
                "duration_ms": exec.get("total_duration_ms")
            })
        
        return formatted
    
    def get_api_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de APIs
        
        Returns:
            Diccionario con estadísticas de APIs
        """
        if not self.api_kb:
            return {
                "total_apis": 0,
                "total_endpoints": 0,
                "apis": []
            }
        
        apis = self.api_kb.get_available_apis()
        total_endpoints = 0
        api_list = []
        
        for api_id in apis:
            api_info = self.api_kb.get_api_info(api_id)
            if api_info:
                endpoints = api_info.get("endpoints", [])
                total_endpoints += len(endpoints)
                
                api_list.append({
                    "id": api_id,
                    "base_url": api_info.get("baseUrl", ""),
                    "endpoints_count": len(endpoints)
                })
        
        return {
            "total_apis": len(apis),
            "total_endpoints": total_endpoints,
            "apis": api_list
        }
    
    def get_sql_query_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de consultas SQL
        
        Returns:
            Diccionario con estadísticas de consultas SQL
        """
        if not self.sql_query_manager:
            return {
                "total_queries": 0,
                "queries_by_database": {},
                "queries_by_category": {}
            }
        
        # Listar todas las consultas
        all_queries = self.sql_query_manager.list_sql_queries()
        
        # Agrupar por base de datos y categoría
        by_database = Counter()
        by_category = Counter()
        
        for query in all_queries:
            database = query.get("database", "unknown")
            category = query.get("category", "unknown")
            by_database[database] += 1
            by_category[category] += 1
        
        return {
            "total_queries": len(all_queries),
            "queries_by_database": dict(by_database),
            "queries_by_category": dict(by_category)
        }
    
    def get_rate_limit_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de rate limiting
        
        Returns:
            Diccionario con estadísticas de rate limiting
        """
        if not self.rate_limiter:
            return {
                "enabled": False,
                "stats": {}
            }
        
        # Obtener estadísticas de rate limiter
        # (esto requeriría métodos adicionales en RateLimiter)
        return {
            "enabled": True,
            "stats": {
                "message": "Rate limiting está habilitado"
            }
        }
    
    def get_agent_list(self) -> List[str]:
        """
        Obtiene lista de agentes únicos
        
        Returns:
            Lista de IDs de agentes
        """
        executions = self.audit_logger.query_executions(limit=10000)
        agents = set(exec.get("agent_id") for exec in executions if exec.get("agent_id"))
        return sorted(list(agents))
    
    def get_workflow_list(self) -> List[str]:
        """
        Obtiene lista de workflows únicos
        
        Returns:
            Lista de IDs de workflows
        """
        executions = self.audit_logger.query_executions(limit=10000)
        workflows = set(exec.get("workflow_id") for exec in executions if exec.get("workflow_id"))
        return sorted(list(workflows))
    
    def get_duration_distribution(self, days: int = 7) -> Dict[str, Any]:
        """
        Obtiene distribución de duraciones de ejecuciones
        
        Args:
            days: Número de días a analizar
        
        Returns:
            Diccionario con distribución de duraciones
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        executions = self.audit_logger.query_executions(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        durations = [
            exec.get("total_duration_ms", 0)
            for exec in executions
            if exec.get("total_duration_ms")
        ]
        
        if not durations:
            return {
                "buckets": [],
                "min": 0,
                "max": 0,
                "median": 0
            }
        
        # Crear buckets: 0-100ms, 100-500ms, 500-1000ms, 1000-5000ms, 5000+
        buckets = {
            "0-100ms": 0,
            "100-500ms": 0,
            "500-1000ms": 0,
            "1000-5000ms": 0,
            "5000ms+": 0
        }
        
        for duration in durations:
            if duration < 100:
                buckets["0-100ms"] += 1
            elif duration < 500:
                buckets["100-500ms"] += 1
            elif duration < 1000:
                buckets["500-1000ms"] += 1
            elif duration < 5000:
                buckets["1000-5000ms"] += 1
            else:
                buckets["5000ms+"] += 1
        
        sorted_durations = sorted(durations)
        median = sorted_durations[len(sorted_durations) // 2] if sorted_durations else 0
        
        return {
            "buckets": [{"range": k, "count": v} for k, v in buckets.items()],
            "min": min(durations),
            "max": max(durations),
            "median": median
        }
    
    def get_success_rate_by_agent(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Obtiene tasa de éxito por agente
        
        Args:
            days: Número de días a analizar
        
        Returns:
            Lista con tasa de éxito por agente
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        executions = self.audit_logger.query_executions(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        # Agrupar por agente
        agent_stats = defaultdict(lambda: {"total": 0, "success": 0, "failed": 0})
        
        for exec in executions:
            agent_id = exec.get("agent_id", "unknown")
            status = exec.get("status", "unknown")
            
            agent_stats[agent_id]["total"] += 1
            if status == "success":
                agent_stats[agent_id]["success"] += 1
            elif status == "failed":
                agent_stats[agent_id]["failed"] += 1
        
        # Calcular tasa de éxito
        results = []
        for agent_id, stats in agent_stats.items():
            success_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
            results.append({
                "agent_id": agent_id,
                "total": stats["total"],
                "success": stats["success"],
                "failed": stats["failed"],
                "success_rate": round(success_rate, 2)
            })
        
        # Ordenar por total descendente
        results.sort(key=lambda x: x["total"], reverse=True)
        
        return results
    
    def get_all_metrics(
        self,
        days: int = 7,
        agent_id: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Obtiene todas las métricas del dashboard
        
        Args:
            days: Número de días a analizar
            agent_id: Filtrar por agente (opcional)
            workflow_id: Filtrar por workflow (opcional)
        
        Returns:
            Diccionario con todas las métricas
        """
        return {
            "overview": self.get_overview_metrics(days, agent_id, workflow_id),
            "timeline": self.get_executions_timeline(days, agent_id, workflow_id),
            "operations": self.get_operation_stats(days, agent_id, workflow_id),
            "recent_executions": self.get_recent_executions(10),
            "apis": self.get_api_stats(),
            "sql_queries": self.get_sql_query_stats(),
            "rate_limiting": self.get_rate_limit_stats(),
            "duration_distribution": self.get_duration_distribution(days),
            "success_rate_by_agent": self.get_success_rate_by_agent(days),
            "agents": self.get_agent_list(),
            "workflows": self.get_workflow_list(),
            "generated_at": datetime.now().isoformat()
        }

