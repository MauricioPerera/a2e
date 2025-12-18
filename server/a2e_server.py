"""
Servidor REST API para A2E
Expone endpoints para que los agentes se conecten y ejecuten workflows
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import asyncio
from typing import Dict, Any, Optional
import logging

from workflow_executor_with_responses import RobustWorkflowExecutor
from api_knowledge_base import APIKnowledgeBase, ClientCapabilitiesAnnouncer
from credentials_vault import CredentialsVault, CredentialCapabilitiesAnnouncer
from auth.agent_auth import AgentAuth, AgentAuthMiddleware
from validation.workflow_validator import WorkflowValidator, ValidationLevel
from monitoring.audit_logger import AuditLogger
from responses.response_formatter import ResponseFormat
from knowledge_base_manager import KnowledgeBaseManager
from sql_query_manager import SQLQueryManager
from rate_limiting import RateLimiter, RateLimitConfig, RateLimitMiddleware
from server.dashboard_metrics import DashboardMetrics

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Componentes globales (en producción, usar inyección de dependencias)
api_kb: Optional[APIKnowledgeBase] = None
vault: Optional[CredentialsVault] = None
auth: Optional[AgentAuth] = None
audit_logger: Optional[AuditLogger] = None
auth_middleware: Optional[AgentAuthMiddleware] = None
kb_manager: Optional[KnowledgeBaseManager] = None
sql_query_manager: Optional[SQLQueryManager] = None
rate_limiter: Optional[RateLimiter] = None
rate_limit_middleware: Optional[RateLimitMiddleware] = None
dashboard_metrics: Optional[DashboardMetrics] = None


def init_server(config: Dict[str, Any]):
    """Inicializa el servidor con configuración"""
    global api_kb, vault, auth, audit_logger, auth_middleware, kb_manager, sql_query_manager, rate_limiter, rate_limit_middleware, dashboard_metrics
    
    # Cargar configuración
    vault_path = config.get("vault", {}).get("path", "credentials.vault.json")
    api_kb_path = config.get("apiKnowledgeBase", {}).get("path", "api_definitions.json")
    auth_path = config.get("auth", {}).get("path", "agent_auth.json")
    log_dir = config.get("monitoring", {}).get("log_dir", "logs")
    kb_config = config.get("knowledgeBases", {})
    
    # Inicializar componentes
    vault = CredentialsVault(vault_path=vault_path)
    
    # Crear API KB con RAG (comparte el mismo sistema RAG)
    from rag_integration import A2ERAGSystem
    try:
        rag_system = A2ERAGSystem()
        api_kb = APIKnowledgeBase(rag_system=rag_system, use_rag=True)
        if api_kb_path:
            api_kb.load_api_definitions(api_kb_path)
        
        # Crear Knowledge Base Manager (comparte el mismo RAG)
        kb_manager = KnowledgeBaseManager(rag_system=rag_system, use_rag=True)
        
        # Crear SQL Query Manager (comparte el mismo RAG)
        sql_query_manager = SQLQueryManager(rag_system=rag_system, use_rag=True)
        
        # Cargar bases de conocimiento si se especifican
        kb_dir = kb_config.get("directory")
        if kb_dir:
            from pathlib import Path
            kb_path = Path(kb_dir)
            if kb_path.exists():
                for kb_file in kb_path.glob("*.json"):
                    kb_id = kb_file.stem
                    kb_type = kb_config.get("default_type", "general")
                    kb_manager.load_knowledge_base(
                        kb_id=kb_id,
                        kb_path=str(kb_file),
                        kb_type=kb_type
                    )
        
        # Cargar consultas SQL si se especifican
        sql_config = config.get("sqlQueries", {})
        sql_file = sql_config.get("file")
        if sql_file:
            from pathlib import Path
            sql_path = Path(sql_file)
            if sql_path.exists():
                sql_query_manager.load_sql_queries_from_file(str(sql_path))
    except ImportError:
        # RAG no disponible, usar sin RAG
        logger.warning("RAG not available, using keyword search only")
        api_kb = APIKnowledgeBase(use_rag=False)
        if api_kb_path:
            api_kb.load_api_definitions(api_kb_path)
        kb_manager = KnowledgeBaseManager(use_rag=False)
        sql_query_manager = SQLQueryManager(use_rag=False)
    
    auth = AgentAuth(config_path=auth_path)
    auth_middleware = AgentAuthMiddleware(auth)
    audit_logger = AuditLogger(log_dir=log_dir)
    
    # Inicializar Rate Limiting
    rate_limit_config = config.get("rateLimiting", {})
    if rate_limit_config.get("enabled", True):
        rate_limiter_config = RateLimitConfig(
            requests_per_minute=rate_limit_config.get("requests_per_minute", 60),
            requests_per_hour=rate_limit_config.get("requests_per_hour", 1000),
            requests_per_day=rate_limit_config.get("requests_per_day", 10000),
            api_calls_per_minute=rate_limit_config.get("api_calls_per_minute", 30),
            api_calls_per_hour=rate_limit_config.get("api_calls_per_hour", 500),
            enable_throttling=rate_limit_config.get("enable_throttling", True),
            throttle_delay_ms=rate_limit_config.get("throttle_delay_ms", 100)
        )
        rate_limiter = RateLimiter(config=rate_limiter_config)
        rate_limit_middleware = RateLimitMiddleware(rate_limiter)
        
        # Aplicar middleware
        app.before_request(rate_limit_middleware.before_request)
        
        # Cargar límites personalizados por agente si existen
        agent_limits = rate_limit_config.get("agents", {})
        for agent_id, agent_config in agent_limits.items():
            agent_limit_config = RateLimitConfig(
                requests_per_minute=agent_config.get("requests_per_minute", rate_limiter_config.requests_per_minute),
                requests_per_hour=agent_config.get("requests_per_hour", rate_limiter_config.requests_per_hour),
                requests_per_day=agent_config.get("requests_per_day", rate_limiter_config.requests_per_day),
                api_calls_per_minute=agent_config.get("api_calls_per_minute", rate_limiter_config.api_calls_per_minute),
                api_calls_per_hour=agent_config.get("api_calls_per_hour", rate_limiter_config.api_calls_per_hour),
                enable_throttling=agent_config.get("enable_throttling", rate_limiter_config.enable_throttling),
                throttle_delay_ms=agent_config.get("throttle_delay_ms", rate_limiter_config.throttle_delay_ms)
            )
            rate_limiter.set_agent_limits(agent_id, agent_limit_config)
        
        logger.info("Rate limiting enabled")
    else:
        rate_limiter = None
        rate_limit_middleware = None
        logger.info("Rate limiting disabled")
    
    # Inicializar métricas del dashboard
    dashboard_metrics = DashboardMetrics(
        audit_logger=audit_logger,
        api_kb=api_kb,
        sql_query_manager=sql_query_manager,
        rate_limiter=rate_limiter
    )
    
    logger.info("A2E Server initialized")


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "a2e-server"})

@app.route('/api/v1/rate-limit/status', methods=['GET'])
def get_rate_limit_status():
    """Obtiene el estado de rate limits para el agente autenticado"""
    # Autenticar
    agent_id = auth_middleware.authenticate_request(request.headers)
    if not agent_id:
        return jsonify({"error": "Authentication required"}), 401
    
    if not rate_limiter:
        return jsonify({"error": "Rate limiting not enabled"}), 404
    
    status = rate_limiter.get_rate_limit_status(agent_id)
    return jsonify(status)


@app.route('/api/v1/capabilities', methods=['GET'])
def get_capabilities():
    """Obtiene capacidades disponibles para el agente autenticado"""
    # Autenticar
    agent_id = auth_middleware.authenticate_request(request.headers)
    if not agent_id:
        return jsonify({"error": "Authentication required"}), 401
    
    # Construir capacidades
    api_announcer = ClientCapabilitiesAnnouncer(api_kb)
    cred_announcer = CredentialCapabilitiesAnnouncer(vault)
    
    all_apis = api_announcer.build_capabilities_message()["workflowCapabilities"]["availableApis"]
    all_credentials = cred_announcer.build_capabilities_message()["availableCredentials"]
    all_operations = ["ApiCall", "FilterData", "TransformData", "StoreData", "Wait", "Loop", "Conditional", "MergeData"]
    
    # Filtrar por permisos del agente
    filtered = auth.filter_capabilities(
        agent_id=agent_id,
        all_apis=all_apis,
        all_credentials=all_credentials,
        all_operations=all_operations
    )
    
    # Agregar información de knowledge bases disponibles
    knowledge_bases_info = []
    if kb_manager:
        knowledge_bases_info = kb_manager.list_knowledge_bases()
    
    return jsonify({
        "agent_id": agent_id,
        "capabilities": {
            "availableApis": filtered["availableApis"],
            "availableCredentials": filtered["availableCredentials"],
            "supportedOperations": filtered["supportedOperations"],
            "knowledgeBases": knowledge_bases_info,
            "sqlQueriesAvailable": sql_query_manager is not None,
            "securityConstraints": {
                "maxExecutionTime": 30000,
                "maxOperations": 20
            }
        }
    })


@app.route('/api/v1/workflows/validate', methods=['POST'])
def validate_workflow():
    """Valida un workflow antes de ejecutarlo"""
    # Autenticar
    agent_id = auth_middleware.authenticate_request(request.headers)
    if not agent_id:
        return jsonify({"error": "Authentication required"}), 401
    
    data = request.get_json()
    workflow_jsonl = data.get("workflow")
    
    if not workflow_jsonl:
        return jsonify({"error": "workflow field required"}), 400
    
    # Validar
    validator = WorkflowValidator(
        api_kb=api_kb,
        vault=vault,
        auth=auth,
        level=ValidationLevel.MODERATE
    )
    
    report = validator.get_validation_report(workflow_jsonl, agent_id=agent_id)
    
    return jsonify(report)


@app.route('/api/v1/workflows/execute', methods=['POST'])
def execute_workflow():
    """Ejecuta un workflow"""
    # Autenticar
    agent_id = auth_middleware.authenticate_request(request.headers)
    if not agent_id:
        return jsonify({"error": "Authentication required"}), 401
    
    data = request.get_json()
    workflow_jsonl = data.get("workflow")
    
    if not workflow_jsonl:
        return jsonify({"error": "workflow field required"}), 400
    
    # Validar primero (opcional, puede deshabilitarse)
    validate = data.get("validate", True)
    if validate:
        validator = WorkflowValidator(
            api_kb=api_kb,
            vault=vault,
            auth=auth,
            level=ValidationLevel.MODERATE
        )
        is_valid, errors = validator.validate_workflow(workflow_jsonl, agent_id=agent_id)
        
        if not is_valid:
            return jsonify({
                "error": "Workflow validation failed",
                "validation_errors": [e.to_dict() for e in errors]
            }), 400
    
    # Crear ejecutor
    executor = RobustWorkflowExecutor(
        audit_logger=audit_logger,
        response_format=ResponseFormat.SUMMARY
    )
    executor.set_agent_context(agent_id)
    
    # Ejecutar
    try:
        executor.load_workflow(workflow_jsonl, agent_id=agent_id)
        response = asyncio.run(executor.execute())
        return jsonify(response)
    except Exception as e:
        logger.error(f"Execution error: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": {
                "type": type(e).__name__,
                "message": str(e)
            }
        }), 500


@app.route('/api/v1/executions/<execution_id>', methods=['GET'])
def get_execution(execution_id: str):
    """Obtiene detalles de una ejecución"""
    # Autenticar
    agent_id = auth_middleware.authenticate_request(request.headers)
    if not agent_id:
        return jsonify({"error": "Authentication required"}), 401
    
    # Obtener detalles
    details = audit_logger.get_execution_details(execution_id)
    
    if not details:
        return jsonify({"error": "Execution not found"}), 404
    
    # Verificar que el agente tiene acceso (solo puede ver sus propias ejecuciones)
    # En producción, agregar verificación de permisos
    
    return jsonify(details)


@app.route('/api/v1/executions', methods=['GET'])
def list_executions():
    """Lista ejecuciones del agente autenticado"""
    # Autenticar
    agent_id = auth_middleware.authenticate_request(request.headers)
    if not agent_id:
        return jsonify({"error": "Authentication required"}), 401
    
    # Parámetros de consulta
    limit = request.args.get("limit", 100, type=int)
    status = request.args.get("status")
    
    # Consultar
    executions = audit_logger.query_executions(
        agent_id=agent_id,
        limit=limit
    )
    
    return jsonify({
        "executions": executions,
        "count": len(executions)
    })


@app.route('/api/v1/knowledge/search', methods=['POST'])
def search_knowledge():
    """Busca conocimiento relevante"""
    # Autenticar
    agent_id = auth_middleware.authenticate_request(request.headers)
    if not agent_id:
        return jsonify({"error": "Authentication required"}), 401
    
    if not kb_manager:
        return jsonify({"error": "Knowledge base manager not available"}), 503
    
    data = request.get_json()
    query = data.get("query")
    
    if not query:
        return jsonify({"error": "query field required"}), 400
    
    results = kb_manager.search_knowledge(
        query=query,
        kb_id=data.get("kb_id"),
        knowledge_type=data.get("type"),
        top_k=data.get("top_k", 5)
    )
    
    return jsonify({
        "query": query,
        "results": results,
        "count": len(results)
    })


@app.route('/api/v1/knowledge/bases', methods=['GET'])
def list_knowledge_bases():
    """Lista bases de conocimiento disponibles"""
    # Autenticar
    agent_id = auth_middleware.authenticate_request(request.headers)
    if not agent_id:
        return jsonify({"error": "Authentication required"}), 401
    
    if not kb_manager:
        return jsonify({"knowledgeBases": []})
    
    bases = kb_manager.list_knowledge_bases()
    return jsonify({
        "knowledgeBases": bases,
        "count": len(bases)
    })


@app.route('/api/v1/sql-queries/search', methods=['POST'])
def search_sql_queries():
    """Busca consultas SQL relevantes"""
    # Autenticar
    agent_id = auth_middleware.authenticate_request(request.headers)
    if not agent_id:
        return jsonify({"error": "Authentication required"}), 401
    
    if not sql_query_manager:
        return jsonify({"error": "SQL query manager not available"}), 503
    
    data = request.get_json()
    query = data.get("query")
    
    if not query:
        return jsonify({"error": "query field required"}), 400
    
    results = sql_query_manager.search_sql_queries(
        query=query,
        database=data.get("database"),
        category=data.get("category"),
        top_k=data.get("top_k", 5)
    )
    
    return jsonify({
        "query": query,
        "results": results,
        "count": len(results)
    })


@app.route('/api/v1/sql-queries', methods=['GET'])
def list_sql_queries():
    """Lista consultas SQL disponibles"""
    # Autenticar
    agent_id = auth_middleware.authenticate_request(request.headers)
    if not agent_id:
        return jsonify({"error": "Authentication required"}), 401
    
    if not sql_query_manager:
        return jsonify({"sqlQueries": []})
    
    database = request.args.get("database")
    category = request.args.get("category")
    
    queries = sql_query_manager.list_sql_queries(
        database=database,
        category=category
    )
    
    return jsonify({
        "sqlQueries": queries,
        "count": len(queries)
    })


@app.route('/api/v1/sql-queries/<query_id>', methods=['GET'])
def get_sql_query(query_id: str):
    """Obtiene una consulta SQL específica"""
    # Autenticar
    agent_id = auth_middleware.authenticate_request(request.headers)
    if not agent_id:
        return jsonify({"error": "Authentication required"}), 401
    
    if not sql_query_manager:
        return jsonify({"error": "SQL query manager not available"}), 503
    
    query = sql_query_manager.get_sql_query(query_id)
    
    if not query:
        return jsonify({"error": "SQL query not found"}), 404
    
    return jsonify(query)


@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Sirve el dashboard HTML"""
    from flask import send_from_directory
    from pathlib import Path
    dashboard_path = Path(__file__).parent.parent / 'dashboard'
    return send_from_directory(str(dashboard_path), 'index.html')


@app.route('/api/v1/dashboard/metrics', methods=['GET'])
def get_dashboard_metrics():
    """Obtiene todas las métricas del dashboard"""
    if not dashboard_metrics:
        return jsonify({"error": "Dashboard metrics not available"}), 503
    
    days = request.args.get("days", 7, type=int)
    agent_id = request.args.get("agent_id")
    workflow_id = request.args.get("workflow_id")
    
    metrics = dashboard_metrics.get_all_metrics(
        days=days,
        agent_id=agent_id,
        workflow_id=workflow_id
    )
    return jsonify(metrics)


@app.route('/api/v1/dashboard/overview', methods=['GET'])
def get_dashboard_overview():
    """Obtiene métricas generales"""
    if not dashboard_metrics:
        return jsonify({"error": "Dashboard metrics not available"}), 503
    
    days = request.args.get("days", 7, type=int)
    overview = dashboard_metrics.get_overview_metrics(days=days)
    return jsonify(overview)


@app.route('/api/v1/dashboard/timeline', methods=['GET'])
def get_dashboard_timeline():
    """Obtiene timeline de ejecuciones"""
    if not dashboard_metrics:
        return jsonify({"error": "Dashboard metrics not available"}), 503
    
    days = request.args.get("days", 7, type=int)
    agent_id = request.args.get("agent_id")
    workflow_id = request.args.get("workflow_id")
    
    timeline = dashboard_metrics.get_executions_timeline(
        days=days,
        agent_id=agent_id,
        workflow_id=workflow_id
    )
    return jsonify({"timeline": timeline})


@app.route('/api/v1/dashboard/export', methods=['GET'])
def export_dashboard_metrics():
    """Exporta métricas en formato CSV o JSON"""
    from flask import Response
    from datetime import datetime
    import csv
    import io
    import json
    
    if not dashboard_metrics:
        return jsonify({"error": "Dashboard metrics not available"}), 503
    
    days = request.args.get("days", 7, type=int)
    agent_id = request.args.get("agent_id")
    workflow_id = request.args.get("workflow_id")
    format_type = request.args.get("format", "json")  # json o csv
    
    metrics = dashboard_metrics.get_all_metrics(
        days=days,
        agent_id=agent_id,
        workflow_id=workflow_id
    )
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format_type == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Escribir overview
        writer.writerow(["Métrica", "Valor"])
        writer.writerow(["Total Ejecuciones", metrics["overview"]["total_executions"]])
        writer.writerow(["Ejecuciones Exitosas", metrics["overview"]["successful_executions"]])
        writer.writerow(["Ejecuciones Fallidas", metrics["overview"]["failed_executions"]])
        writer.writerow(["Duración Promedio (ms)", metrics["overview"]["average_duration_ms"]])
        writer.writerow([])
        
        # Escribir timeline
        writer.writerow(["Fecha", "Total", "Exitosas", "Fallidas"])
        for day in metrics["timeline"]:
            writer.writerow([day["date"], day["total"], day["success"], day["failed"]])
        
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename=a2e_metrics_{timestamp}.csv"}
        )
    else:
        # JSON
        return Response(
            json.dumps(metrics, indent=2),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment; filename=a2e_metrics_{timestamp}.json"}
        )


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


def run_server(config_path: str = "a2e_config.json", host: str = "0.0.0.0", port: int = 8000):
    """Ejecuta el servidor"""
    # Cargar configuración
    with open(config_path, "r") as f:
        config = json.load(f)
    
    init_server(config)
    
    logger.info(f"Starting A2E Server on {host}:{port}")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="A2E Server")
    parser.add_argument("--config", default="a2e_config.json", help="Config file path")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    run_server(config_path=args.config, host=args.host, port=args.port)

