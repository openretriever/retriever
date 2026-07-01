"""
OpenTelemetry setup via Uptrace.

Reads UPTRACE_DSN from environment. If set, configures traces + logs automatically.
"""

import os
import logging
from typing import Optional, Dict

logger = logging.getLogger('retriever')


def _reset_otel_providers() -> None:
    """
    HACK: Reset OTel global providers to allow reconfiguration after fork.

    This is needed because forked child processes inherit the parent's
    configured providers, and OTel refuses to override them.
    """
    try:
        from opentelemetry.trace import _TRACER_PROVIDER_SET_ONCE
        _TRACER_PROVIDER_SET_ONCE._done = False

        from opentelemetry.metrics import _internal as metrics_internal
        metrics_internal._METER_PROVIDER_SET_ONCE._done = False

        from opentelemetry._logs import _internal as logs_internal
        logs_internal._LOGGER_PROVIDER_SET_ONCE._done = False
    except Exception:
        pass


def configure_otel(
    service_name: str,
    attrs: Optional[Dict[str, str]] = None,
    reset_providers: bool = False,
) -> bool:
    """
    Configure OpenTelemetry via Uptrace if UPTRACE_DSN is set.

    Args:
        service_name: Service name (same for main and workers)
        attrs: Optional resource attributes (e.g., {'worker.id': 'node_0'})
        reset_providers: If True, reset inherited providers (for forked processes)

    Returns:
        True if configured, False if UPTRACE_DSN not set
    """
    dsn = os.environ.get('UPTRACE_DSN')
    if not dsn or not dsn.strip():
        return False

    try:
        if reset_providers:
            _reset_otel_providers()

        import uptrace

        uptrace.configure_opentelemetry(
            dsn=dsn,
            service_name=service_name,
            service_version="0.0.1",
            resource_attributes=attrs or {},
            deployment_environment="dev",
        )
        logger.debug(f'OpenTelemetry configured: {service_name} (attrs={attrs})')
        return True
    except ImportError:
        logger.debug('uptrace package not installed')
        return False
    except Exception as e:
        logger.warning(f'Failed to configure OpenTelemetry: {e}')
        return False


def shutdown_otel() -> None:
    """Shutdown OpenTelemetry and flush pending data."""
    dsn = os.environ.get('UPTRACE_DSN')
    if not dsn or not dsn.strip():
        return

    try:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        if hasattr(provider, 'force_flush'):
            provider.force_flush(timeout_millis=5000)

        import uptrace
        uptrace.shutdown()
    except Exception:
        pass
