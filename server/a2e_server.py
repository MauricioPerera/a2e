"""
Servidor REST API para A2E
Expone endpoints para que los agentes se conecten y ejecuten workflows
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Estado de la aplicación (reemplaza las 10 variables globales)
# ---------------------------------------------------------------------------

@dataclass
class AppState:
    """Encapsula todos los componentes del servidor"""
    api_kb: Any = None
    vault: Any = None
    auth: Any = None
    audit_logger: Any = None
    auth_middleware: Any = None
    kb_manager: Any = None
    sql_query_manager: Any = None
    rate_limiter: Any = None
    rate_limit_middleware: Any = None
    dashboard_metrics: Any = None


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(config: Dict[str, Any]) -> Flask:
    """Crea e inicializa la aplicación Flask con todos los componentes"""
    from api_knowledge_base import APIKnowledgeBase, ClientCapabilitiesAnnouncer
    from credentials_vault import CredentialsVault, CredentialCapabilitiesAnnouncer
    from auth.agent_auth import AgentAuth, AgentAuthMiddleware
    from monitoring.audit_logger import AuditLogger
    from knowledge_base_manager import KnowledgeBaseManager
    from sql_query_manager import SQLQueryManager
    from rate_limiting import RateLimiter, RateLimitConfig, RateLimitMiddleware
    from server.dashboard_metrics import DashboardMetrics

    app = Flask(__name__)
    CORS(app)

    state = AppState()

    # -- Configurar componentes ----------------------------------------------

    vault_path = config.get("vault", {}).get("path", "credentials.vault.json")
    api_kb_path = config.get("apiKnowledgeBase", {}).get("path", "api_definitions.json")
    auth_path = config.get("auth", {}).get("path", "agent_auth.json")
    log_dir = config.get("monitoring", {}).get("log_dir", "logs")
    kb_config = config.get("knowledgeBases", {})

    state.vault = CredentialsVault(vault_path=vault_path)

    # RAG system (compartido)
    try:
        from rag_integration import A2ERAGSystem
        rag_system = A2ERAGSystem()
        state.api_kb = APIKnowledgeBase(rag_system=rag_system, use_rag=True)
        if api_kb_path:
            state.api_kb.load_api_definitions(api_kb_path)

        state.kb_manager = KnowledgeBaseManager(rag_system=rag_system, use_rag=True)
        state.sql_query_manager = SQLQueryManager(rag_system=rag_system, use_rag=True)

        # Cargar bases de conocimiento
        kb_dir = kb_config.get("directory")
        if kb_dir:
            from pathlib import Path
            kb_path = Path(kb_dir)
            if kb_path.exists():
                for kb_file in kb_path.glob("*.json"):
                    kb_id = kb_file.stem
                    kb_type = kb_config.get("default_type", "general")
                    state.kb_manager.load_knowledge_base(
                        kb_id=kb_id,
                        kb_path=str(kb_file),
                        kb_type=kb_type,
                    )

        # Cargar consultas SQL
        sql_config = config.get("sqlQueries", {})
        sql_file = sql_config.get("file")
        if sql_file:
            from pathlib import Path
            sql_path = Path(sql_file)
            if sql_path.exists():
                state.sql_query_manager.load_sql_queries_from_file(str(sql_path))
    except ImportError:
        logger.warning("RAG not available, using keyword search only")
        state.api_kb = APIKnowledgeBase(use_rag=False)
        if api_kb_path:
            state.api_kb.load_api_definitions(api_kb_path)
        state.kb_manager = KnowledgeBaseManager(use_rag=False)
        state.sql_query_manager = SQLQueryManager(use_rag=False)

    state.auth = AgentAuth(config_path=auth_path)
    state.auth_middleware = AgentAuthMiddleware(state.auth)
    state.audit_logger = AuditLogger(log_dir=log_dir)

    # Rate Limiting
    rate_limit_config = config.get("rateLimiting", {})
    if rate_limit_config.get("enabled", True):
        rate_limiter_config = RateLimitConfig(
            requests_per_minute=rate_limit_config.get("requests_per_minute", 60),
            requests_per_hour=rate_limit_config.get("requests_per_hour", 1000),
            requests_per_day=rate_limit_config.get("requests_per_day", 10000),
            api_calls_per_minute=rate_limit_config.get("api_calls_per_minute", 30),
            api_calls_per_hour=rate_limit_config.get("api_calls_per_hour", 500),
            enable_throttling=rate_limit_config.get("enable_throttling", True),
            throttle_delay_ms=rate_limit_config.get("throttle_delay_ms", 100),
        )
        state.rate_limiter = RateLimiter(config=rate_limiter_config)
        state.rate_limit_middleware = RateLimitMiddleware(state.rate_limiter)

        app.before_request(state.rate_limit_middleware.before_request)

        # Límites por agente
        agent_limits = rate_limit_config.get("agents", {})
        for agent_id, agent_config in agent_limits.items():
            agent_limit_config = RateLimitConfig(
                requests_per_minute=agent_config.get("requests_per_minute", rate_limiter_config.requests_per_minute),
                requests_per_hour=agent_config.get("requests_per_hour", rate_limiter_config.requests_per_hour),
                requests_per_day=agent_config.get("requests_per_day", rate_limiter_config.requests_per_day),
                api_calls_per_minute=agent_config.get("api_calls_per_minute", rate_limiter_config.api_calls_per_minute),
                api_calls_per_hour=agent_config.get("api_calls_per_hour", rate_limiter_config.api_calls_per_hour),
                enable_throttling=agent_config.get("enable_throttling", rate_limiter_config.enable_throttling),
                throttle_delay_ms=agent_config.get("throttle_delay_ms", rate_limiter_config.throttle_delay_ms),
            )
            state.rate_limiter.set_agent_limits(agent_id, agent_limit_config)

        logger.info("Rate limiting enabled")
    else:
        logger.info("Rate limiting disabled")

    # Dashboard metrics
    state.dashboard_metrics = DashboardMetrics(
        audit_logger=state.audit_logger,
        api_kb=state.api_kb,
        sql_query_manager=state.sql_query_manager,
        rate_limiter=state.rate_limiter,
    )

    # Guardar estado en app
    app.state = state

    logger.info("A2E Server initialized")

    # -- Registrar rutas -----------------------------------------------------

    _register_routes(app)

    return app


# ---------------------------------------------------------------------------
# Helper: autenticación de request
# ---------------------------------------------------------------------------

def _authenticate(app_state):
    """Autentica la request actual. Retorna agent_id o None."""
    return app_state.auth_middleware.authenticate_request(request.headers)


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

def _register_routes(app: Flask):
    s = app.state  # atajo

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "healthy", "service": "a2e-server"})

    @app.route('/api/v1/rate-limit/status', methods=['GET'])
    def get_rate_limit_status():
        agent_id = _authenticate(s)
        if not agent_id:
            return jsonify({"error": "Authentication required"}), 401
        if not s.rate_limiter:
            return jsonify({"error": "Rate limiting not enabled"}), 404
        status = s.rate_limiter.get_rate_limit_status(agent_id)
        return jsonify(status)

    @app.route('/api/v1/capabilities', methods=['GET'])
    def get_capabilities():
        from api_knowledge_base import ClientCapabilitiesAnnouncer
        from credentials_vault import CredentialCapabilitiesAnnouncer

        agent_id = _authenticate(s)
        if not agent_id:
            return jsonify({"error": "Authentication required"}), 401

        api_announcer = ClientCapabilitiesAnnouncer(s.api_kb)
        cred_announcer = CredentialCapabilitiesAnnouncer(s.vault)

        all_apis = api_announcer.build_capabilities_message()["workflowCapabilities"]["availableApis"]
        all_credentials = cred_announcer.build_capabilities_message()["availableCredentials"]
        all_operations = ["ApiCall", "FilterData", "TransformData", "StoreData", "Wait", "Loop", "Conditional", "MergeData"]

        filtered = s.auth.filter_capabilities(
            agent_id=agent_id,
            all_apis=all_apis,
            all_credentials=all_credentials,
            all_operations=all_operations,
        )

        knowledge_bases_info = []
        if s.kb_manager:
            knowledge_bases_info = s.kb_manager.list_knowledge_bases()

        return jsonify({
            "agent_id": agent_id,
            "capabilities": {
                "availableApis": filtered["availableApis"],
                "availableCredentials": filtered["availableCredentials"],
                "supportedOperations": filtered["supportedOperations"],
                "knowledgeBases": knowledge_bases_info,
                "sqlQueriesAvailable": s.sql_query_manager is not None,
                "securityConstraints": {
                    "maxExecutionTime": 30000,
                    "maxOperations": 20,
                },
            },
        })

    @app.route('/api/v1/workflows/validate', methods=['POST'])
    def validate_workflow():
        from validation.workflow_validator import WorkflowValidator, ValidationLevel

        agent_id = _authenticate(s)
        if not agent_id:
            return jsonify({"error": "Authentication required"}), 401

        data = request.get_json()
        workflow_jsonl = data.get("workflow")
        if not workflow_jsonl:
            return jsonify({"error": "workflow field required"}), 400

        validator = WorkflowValidator(
            api_kb=s.api_kb,
            vault=s.vault,
            auth=s.auth,
            level=ValidationLevel.MODERATE,
        )
        report = validator.get_validation_report(workflow_jsonl, agent_id=agent_id)
        return jsonify(report)

    @app.route('/api/v1/workflows/execute', methods=['POST'])
    def execute_workflow():
        from validation.workflow_validator import WorkflowValidator, ValidationLevel
        from executor.workflow_executor import WorkflowExecutor, AuditMiddleware
        from responses.response_formatter import ResponseFormatter, ResponseFormat
        from responses.error_handler import ErrorHandler

        agent_id = _authenticate(s)
        if not agent_id:
            return jsonify({"error": "Authentication required"}), 401

        data = request.get_json()
        workflow_jsonl = data.get("workflow")
        if not workflow_jsonl:
            return jsonify({"error": "workflow field required"}), 400

        # Validar primero
        validate = data.get("validate", True)
        if validate:
            validator = WorkflowValidator(
                api_kb=s.api_kb,
                vault=s.vault,
                auth=s.auth,
                level=ValidationLevel.MODERATE,
            )
            is_valid, errors = validator.validate_workflow(workflow_jsonl, agent_id=agent_id)
            if not is_valid:
                return jsonify({
                    "error": "Workflow validation failed",
                    "validation_errors": [e.to_dict() for e in errors],
                }), 400

        # Crear ejecutor con middlewares
        middlewares = [
            AuditMiddleware(
                audit_logger=s.audit_logger,
                response_formatter=ResponseFormatter(format=ResponseFormat.SUMMARY),
                error_handler=ErrorHandler(),
            ),
        ]
        executor = WorkflowExecutor(middlewares=middlewares)
        executor.set_agent_context(agent_id)

        try:
            executor.load_workflow(workflow_jsonl, agent_id=agent_id)
            raw_results = asyncio.run(executor.execute())
            formatter = ResponseFormatter(format=ResponseFormat.SUMMARY)
            response = formatter.format_success_response(
                execution_id=executor.current_execution_id or "unknown",
                results=raw_results,
            )
            return jsonify(response)
        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            return jsonify({
                "status": "error",
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                },
            }), 500

    @app.route('/api/v1/executions/<execution_id>', methods=['GET'])
    def get_execution(execution_id: str):
        agent_id = _authenticate(s)
        if not agent_id:
            return jsonify({"error": "Authentication required"}), 401
        details = s.audit_logger.get_execution_details(execution_id)
        if not details:
            return jsonify({"error": "Execution not found"}), 404
        return jsonify(details)

    @app.route('/api/v1/executions', methods=['GET'])
    def list_executions():
        agent_id = _authenticate(s)
        if not agent_id:
            return jsonify({"error": "Authentication required"}), 401
        limit = request.args.get("limit", 100, type=int)
        executions = s.audit_logger.query_executions(agent_id=agent_id, limit=limit)
        return jsonify({"executions": executions, "count": len(executions)})

    @app.route('/api/v1/knowledge/search', methods=['POST'])
    def search_knowledge():
        agent_id = _authenticate(s)
        if not agent_id:
            return jsonify({"error": "Authentication required"}), 401
        if not s.kb_manager:
            return jsonify({"error": "Knowledge base manager not available"}), 503
        data = request.get_json()
        query = data.get("query")
        if not query:
            return jsonify({"error": "query field required"}), 400
        results = s.kb_manager.search_knowledge(
            query=query,
            kb_id=data.get("kb_id"),
            knowledge_type=data.get("type"),
            top_k=data.get("top_k", 5),
        )
        return jsonify({"query": query, "results": results, "count": len(results)})

    @app.route('/api/v1/knowledge/bases', methods=['GET'])
    def list_knowledge_bases():
        agent_id = _authenticate(s)
        if not agent_id:
            return jsonify({"error": "Authentication required"}), 401
        if not s.kb_manager:
            return jsonify({"knowledgeBases": []})
        bases = s.kb_manager.list_knowledge_bases()
        return jsonify({"knowledgeBases": bases, "count": len(bases)})

    @app.route('/api/v1/sql-queries/search', methods=['POST'])
    def search_sql_queries():
        agent_id = _authenticate(s)
        if not agent_id:
            return jsonify({"error": "Authentication required"}), 401
        if not s.sql_query_manager:
            return jsonify({"error": "SQL query manager not available"}), 503
        data = request.get_json()
        query = data.get("query")
        if not query:
            return jsonify({"error": "query field required"}), 400
        results = s.sql_query_manager.search_sql_queries(
            query=query,
            database=data.get("database"),
            category=data.get("category"),
            top_k=data.get("top_k", 5),
        )
        return jsonify({"query": query, "results": results, "count": len(results)})

    @app.route('/api/v1/sql-queries', methods=['GET'])
    def list_sql_queries():
        agent_id = _authenticate(s)
        if not agent_id:
            return jsonify({"error": "Authentication required"}), 401
        if not s.sql_query_manager:
            return jsonify({"sqlQueries": []})
        database = request.args.get("database")
        category = request.args.get("category")
        queries = s.sql_query_manager.list_sql_queries(database=database, category=category)
        return jsonify({"sqlQueries": queries, "count": len(queries)})

    @app.route('/api/v1/sql-queries/<query_id>', methods=['GET'])
    def get_sql_query(query_id: str):
        agent_id = _authenticate(s)
        if not agent_id:
            return jsonify({"error": "Authentication required"}), 401
        if not s.sql_query_manager:
            return jsonify({"error": "SQL query manager not available"}), 503
        query = s.sql_query_manager.get_sql_query(query_id)
        if not query:
            return jsonify({"error": "SQL query not found"}), 404
        return jsonify(query)

    @app.route('/dashboard', methods=['GET'])
    def dashboard():
        from flask import send_from_directory
        from pathlib import Path
        dashboard_path = Path(__file__).parent.parent / 'dashboard'
        return send_from_directory(str(dashboard_path), 'index.html')

    @app.route('/api/v1/dashboard/metrics', methods=['GET'])
    def get_dashboard_metrics():
        if not s.dashboard_metrics:
            return jsonify({"error": "Dashboard metrics not available"}), 503
        days = request.args.get("days", 7, type=int)
        agent_id = request.args.get("agent_id")
        workflow_id = request.args.get("workflow_id")
        metrics = s.dashboard_metrics.get_all_metrics(
            days=days, agent_id=agent_id, workflow_id=workflow_id
        )
        return jsonify(metrics)

    @app.route('/api/v1/dashboard/overview', methods=['GET'])
    def get_dashboard_overview():
        if not s.dashboard_metrics:
            return jsonify({"error": "Dashboard metrics not available"}), 503
        days = request.args.get("days", 7, type=int)
        overview = s.dashboard_metrics.get_overview_metrics(days=days)
        return jsonify(overview)

    @app.route('/api/v1/dashboard/timeline', methods=['GET'])
    def get_dashboard_timeline():
        if not s.dashboard_metrics:
            return jsonify({"error": "Dashboard metrics not available"}), 503
        days = request.args.get("days", 7, type=int)
        agent_id = request.args.get("agent_id")
        workflow_id = request.args.get("workflow_id")
        timeline = s.dashboard_metrics.get_executions_timeline(
            days=days, agent_id=agent_id, workflow_id=workflow_id
        )
        return jsonify({"timeline": timeline})

    @app.route('/api/v1/dashboard/export', methods=['GET'])
    def export_dashboard_metrics():
        from flask import Response
        from datetime import datetime
        import csv
        import io

        if not s.dashboard_metrics:
            return jsonify({"error": "Dashboard metrics not available"}), 503

        days = request.args.get("days", 7, type=int)
        agent_id = request.args.get("agent_id")
        workflow_id = request.args.get("workflow_id")
        format_type = request.args.get("format", "json")

        metrics = s.dashboard_metrics.get_all_metrics(
            days=days, agent_id=agent_id, workflow_id=workflow_id
        )

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if format_type == "csv":
            output = io.StringIO()
            writer = csv.writer(output)

            writer.writerow(["Métrica", "Valor"])
            writer.writerow(["Total Ejecuciones", metrics["overview"]["total_executions"]])
            writer.writerow(["Ejecuciones Exitosas", metrics["overview"]["successful_executions"]])
            writer.writerow(["Ejecuciones Fallidas", metrics["overview"]["failed_executions"]])
            writer.writerow(["Duración Promedio (ms)", metrics["overview"]["average_duration_ms"]])
            writer.writerow([])

            writer.writerow(["Fecha", "Total", "Exitosas", "Fallidas"])
            for day in metrics["timeline"]:
                writer.writerow([day["date"], day["total"], day["success"], day["failed"]])

            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-Disposition": f"attachment; filename=a2e_metrics_{timestamp}.csv"},
            )
        else:
            return Response(
                json.dumps(metrics, indent=2),
                mimetype="application/json",
                headers={"Content-Disposition": f"attachment; filename=a2e_metrics_{timestamp}.json"},
            )

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Compatibilidad: mantener run_server y __main__ funcionales
# ---------------------------------------------------------------------------

# Backward-compatible module-level app for tests that import `from server.a2e_server import app`
app = Flask(__name__)
CORS(app)


def init_server(config: Dict[str, Any]):
    """Backward-compatible init — re-creates the module-level app using create_app."""
    global app
    app = create_app(config)
    return app


def run_server(config_path: str = "a2e_config.json", host: str = "0.0.0.0", port: int = 8000):
    """Ejecuta el servidor"""
    with open(config_path, "r") as f:
        config = json.load(f)

    app = create_app(config)

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
