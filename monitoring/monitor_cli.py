"""
CLI para monitoreo y consulta de ejecuciones de A2E
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from monitoring.audit_logger import AuditLogger, ExecutionStatus


def list_executions(args):
    """Lista ejecuciones con filtros"""
    logger = AuditLogger(log_dir=args.log_dir)
    
    status = None
    if args.status:
        try:
            status = ExecutionStatus(args.status)
        except ValueError:
            print(f"Error: Invalid status '{args.status}'")
            return 1
    
    start_date = None
    if args.start_date:
        start_date = datetime.fromisoformat(args.start_date)
    
    end_date = None
    if args.end_date:
        end_date = datetime.fromisoformat(args.end_date)
    
    executions = logger.query_executions(
        agent_id=args.agent_id,
        workflow_id=args.workflow_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=args.limit
    )
    
    if not executions:
        print("No executions found")
        return 0
    
    print(f"\nFound {len(executions)} executions:\n")
    for exec in executions:
        print(f"Execution ID: {exec.get('execution_id', 'N/A')}")
        print(f"  Agent: {exec.get('agent_id', 'N/A')}")
        print(f"  Workflow: {exec.get('workflow_id', 'N/A')}")
        print(f"  Status: {exec.get('status', 'N/A')}")
        print(f"  Timestamp: {exec.get('timestamp', 'N/A')}")
        if exec.get('total_duration_ms'):
            print(f"  Duration: {exec['total_duration_ms']}ms")
        print()
    
    return 0


def show_execution(args):
    """Muestra detalles de una ejecución"""
    logger = AuditLogger(log_dir=args.log_dir)
    details = logger.get_execution_details(args.execution_id)
    
    if not details:
        print(f"Error: Execution '{args.execution_id}' not found")
        return 1
    
    print(f"\nExecution: {args.execution_id}\n")
    print("="*60)
    
    # Información general
    if details["timeline"]:
        first_entry = details["timeline"][0]
        last_entry = details["timeline"][-1]
        
        print(f"Agent ID: {first_entry.get('agent_id', 'N/A')}")
        print(f"Workflow ID: {first_entry.get('workflow_id', 'N/A')}")
        print(f"Status: {last_entry.get('status', 'N/A')}")
        print(f"Started: {first_entry.get('timestamp', 'N/A')}")
        if last_entry.get('total_duration_ms'):
            print(f"Duration: {last_entry['total_duration_ms']}ms")
    
    # Credenciales usadas
    if details["credentials_used"]:
        print(f"\nCredentials Used ({len(details['credentials_used'])}):")
        for cred in details["credentials_used"]:
            print(f"  - {cred.get('credential_id')} ({cred.get('credential_type')})")
            print(f"    Operation: {cred.get('operation_id')}")
            print(f"    Context: {cred.get('usage_context')}")
    
    # Operaciones
    if details["operations"]:
        print(f"\nOperations ({len(details['operations'])}):")
        for op in details["operations"]:
            print(f"  - {op.get('operation_id')} ({op.get('operation_type')})")
            print(f"    Status: {op.get('status')}")
            if op.get('duration_ms'):
                print(f"    Duration: {op['duration_ms']}ms")
            if op.get('error'):
                print(f"    Error: {op['error']}")
    
    # Timeline
    if args.verbose:
        print(f"\nTimeline ({len(details['timeline'])} events):")
        for event in details["timeline"]:
            print(f"  {event.get('timestamp')} - {event.get('event_type', 'event')}")
    
    # Resultados
    if last_entry.get('results'):
        print(f"\nResults:")
        print(json.dumps(last_entry['results'], indent=2))
    
    return 0


def stats(args):
    """Muestra estadísticas de ejecuciones"""
    logger = AuditLogger(log_dir=args.log_dir)
    
    # Obtener todas las ejecuciones
    executions = logger.query_executions(limit=10000)
    
    if not executions:
        print("No executions found")
        return 0
    
    # Calcular estadísticas
    total = len(executions)
    by_status = {}
    by_agent = {}
    total_duration = 0
    successful_durations = []
    
    for exec in executions:
        # Por estado
        status = exec.get('status', 'unknown')
        by_status[status] = by_status.get(status, 0) + 1
        
        # Por agente
        agent = exec.get('agent_id', 'unknown')
        by_agent[agent] = by_agent.get(agent, 0) + 1
        
        # Duración
        if exec.get('total_duration_ms'):
            duration = exec['total_duration_ms']
            total_duration += duration
            if status == 'success':
                successful_durations.append(duration)
    
    print("\nExecution Statistics")
    print("="*60)
    print(f"Total Executions: {total}")
    print(f"\nBy Status:")
    for status, count in sorted(by_status.items()):
        percentage = (count / total) * 100
        print(f"  {status}: {count} ({percentage:.1f}%)")
    
    print(f"\nBy Agent:")
    for agent, count in sorted(by_agent.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total) * 100
        print(f"  {agent}: {count} ({percentage:.1f}%)")
    
    if total_duration > 0:
        avg_duration = total_duration / total
        print(f"\nAverage Duration: {avg_duration:.2f}ms")
    
    if successful_durations:
        avg_success_duration = sum(successful_durations) / len(successful_durations)
        print(f"Average Success Duration: {avg_success_duration:.2f}ms")
    
    return 0


def export_logs(args):
    """Exporta logs en formato JSON"""
    logger = AuditLogger(log_dir=args.log_dir)
    
    executions = logger.query_executions(
        agent_id=args.agent_id,
        workflow_id=args.workflow_id,
        limit=args.limit
    )
    
    output = {
        "exported_at": datetime.now().isoformat(),
        "total": len(executions),
        "executions": executions
    }
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"✓ Exported {len(executions)} executions to {args.output}")
    else:
        print(json.dumps(output, indent=2))
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="A2E Monitoring CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List recent executions
  python monitor_cli.py list --limit 10

  # Show execution details
  python monitor_cli.py show --execution-id abc123

  # Show statistics
  python monitor_cli.py stats

  # Export logs
  python monitor_cli.py export --output logs.json
        """
    )
    
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Log directory (default: logs)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List executions")
    list_parser.add_argument("--agent-id", help="Filter by agent ID")
    list_parser.add_argument("--workflow-id", help="Filter by workflow ID")
    list_parser.add_argument("--status", help="Filter by status (pending/running/success/failed)")
    list_parser.add_argument("--start-date", help="Start date (ISO format)")
    list_parser.add_argument("--end-date", help="End date (ISO format)")
    list_parser.add_argument("--limit", type=int, default=100, help="Limit results")
    list_parser.set_defaults(func=list_executions)
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show execution details")
    show_parser.add_argument("--execution-id", required=True, help="Execution ID")
    show_parser.add_argument("--verbose", action="store_true", help="Show detailed timeline")
    show_parser.set_defaults(func=show_execution)
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show execution statistics")
    stats_parser.set_defaults(func=stats)
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export logs")
    export_parser.add_argument("--agent-id", help="Filter by agent ID")
    export_parser.add_argument("--workflow-id", help="Filter by workflow ID")
    export_parser.add_argument("--limit", type=int, default=1000, help="Limit results")
    export_parser.add_argument("--output", help="Output file (default: stdout)")
    export_parser.set_defaults(func=export_logs)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

