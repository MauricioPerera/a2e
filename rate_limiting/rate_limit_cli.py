"""
CLI para gestión de Rate Limits
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .rate_limiter import RateLimiter, RateLimitConfig


def load_rate_limiter(config_path: Optional[str] = None) -> RateLimiter:
    """
    Carga rate limiter desde configuración
    
    Args:
        config_path: Ruta al archivo de configuración
    
    Returns:
        RateLimiter configurado
    """
    limiter = RateLimiter()
    
    if config_path and Path(config_path).exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            
            # Configuración global
            if 'global' in config_data:
                global_config = config_data['global']
                limiter.config = RateLimitConfig(
                    requests_per_minute=global_config.get('requests_per_minute', 60),
                    requests_per_hour=global_config.get('requests_per_hour', 1000),
                    requests_per_day=global_config.get('requests_per_day', 10000),
                    api_calls_per_minute=global_config.get('api_calls_per_minute', 30),
                    api_calls_per_hour=global_config.get('api_calls_per_hour', 500),
                    enable_throttling=global_config.get('enable_throttling', True),
                    throttle_delay_ms=global_config.get('throttle_delay_ms', 100)
                )
            
            # Configuraciones por agente
            if 'agents' in config_data:
                for agent_id, agent_config in config_data['agents'].items():
                    agent_limit_config = RateLimitConfig(
                        requests_per_minute=agent_config.get('requests_per_minute', limiter.config.requests_per_minute),
                        requests_per_hour=agent_config.get('requests_per_hour', limiter.config.requests_per_hour),
                        requests_per_day=agent_config.get('requests_per_day', limiter.config.requests_per_day),
                        api_calls_per_minute=agent_config.get('api_calls_per_minute', limiter.config.api_calls_per_minute),
                        api_calls_per_hour=agent_config.get('api_calls_per_hour', limiter.config.api_calls_per_hour),
                        enable_throttling=agent_config.get('enable_throttling', limiter.config.enable_throttling),
                        throttle_delay_ms=agent_config.get('throttle_delay_ms', limiter.config.throttle_delay_ms)
                    )
                    limiter.set_agent_limits(agent_id, agent_limit_config)
    
    return limiter


def cmd_status(args):
    """Muestra estado de rate limits para un agente"""
    limiter = load_rate_limiter(args.config)
    status = limiter.get_rate_limit_status(args.agent_id)
    
    print(f"\nRate Limit Status for Agent: {args.agent_id}")
    print("=" * 60)
    print("\nLimits:")
    for key, value in status['limits'].items():
        print(f"  {key}: {value}")
    
    print("\nUsage:")
    for key, value in status['usage'].items():
        print(f"  {key}: {value}")
    
    print("\nRemaining:")
    for key, value in status['remaining'].items():
        print(f"  {key}: {value}")


def cmd_set_limits(args):
    """Establece límites personalizados para un agente"""
    limiter = load_rate_limiter(args.config)
    
    config = RateLimitConfig(
        requests_per_minute=args.requests_per_minute or limiter.config.requests_per_minute,
        requests_per_hour=args.requests_per_hour or limiter.config.requests_per_hour,
        requests_per_day=args.requests_per_day or limiter.config.requests_per_day,
        api_calls_per_minute=args.api_calls_per_minute or limiter.config.api_calls_per_minute,
        api_calls_per_hour=args.api_calls_per_hour or limiter.config.api_calls_per_hour,
        enable_throttling=args.enable_throttling if args.enable_throttling is not None else limiter.config.enable_throttling,
        throttle_delay_ms=args.throttle_delay_ms or limiter.config.throttle_delay_ms
    )
    
    limiter.set_agent_limits(args.agent_id, config)
    print(f"✅ Set custom rate limits for agent {args.agent_id}")
    
    # Guardar en configuración si se especifica
    if args.config:
        save_config(args.config, limiter)


def cmd_reset(args):
    """Resetea límites de un agente"""
    limiter = load_rate_limiter(args.config)
    limiter.reset_agent_limits(args.agent_id)
    print(f"✅ Reset rate limits for agent {args.agent_id}")


def save_config(config_path: str, limiter: RateLimiter):
    """Guarda configuración en archivo"""
    config_data = {
        'global': {
            'requests_per_minute': limiter.config.requests_per_minute,
            'requests_per_hour': limiter.config.requests_per_hour,
            'requests_per_day': limiter.config.requests_per_day,
            'api_calls_per_minute': limiter.config.api_calls_per_minute,
            'api_calls_per_hour': limiter.config.api_calls_per_hour,
            'enable_throttling': limiter.config.enable_throttling,
            'throttle_delay_ms': limiter.config.throttle_delay_ms
        },
        'agents': {}
    }
    
    for agent_id, agent_config in limiter.custom_limits.items():
        config_data['agents'][agent_id] = {
            'requests_per_minute': agent_config.requests_per_minute,
            'requests_per_hour': agent_config.requests_per_hour,
            'requests_per_day': agent_config.requests_per_day,
            'api_calls_per_minute': agent_config.api_calls_per_minute,
            'api_calls_per_hour': agent_config.api_calls_per_hour,
            'enable_throttling': agent_config.enable_throttling,
            'throttle_delay_ms': agent_config.throttle_delay_ms
        }
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2)
    
    print(f"✅ Saved configuration to {config_path}")


def main():
    parser = argparse.ArgumentParser(description='A2E Rate Limit Management CLI')
    parser.add_argument('--config', type=str, help='Path to rate limit configuration file')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show rate limit status for an agent')
    status_parser.add_argument('agent_id', type=str, help='Agent ID')
    status_parser.set_defaults(func=cmd_status)
    
    # Set limits command
    set_parser = subparsers.add_parser('set', help='Set custom rate limits for an agent')
    set_parser.add_argument('agent_id', type=str, help='Agent ID')
    set_parser.add_argument('--requests-per-minute', type=int, help='Requests per minute')
    set_parser.add_argument('--requests-per-hour', type=int, help='Requests per hour')
    set_parser.add_argument('--requests-per-day', type=int, help='Requests per day')
    set_parser.add_argument('--api-calls-per-minute', type=int, help='API calls per minute')
    set_parser.add_argument('--api-calls-per-hour', type=int, help='API calls per hour')
    set_parser.add_argument('--enable-throttling', type=bool, help='Enable throttling')
    set_parser.add_argument('--throttle-delay-ms', type=int, help='Throttle delay in milliseconds')
    set_parser.set_defaults(func=cmd_set_limits)
    
    # Reset command
    reset_parser = subparsers.add_parser('reset', help='Reset rate limits for an agent')
    reset_parser.add_argument('agent_id', type=str, help='Agent ID')
    reset_parser.set_defaults(func=cmd_reset)
    
    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

